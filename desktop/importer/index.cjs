const fs = require('node:fs');
const path = require('node:path');
const sepehryarSource = require('./sepehryar-sql.cjs');

class SalesImportService {
  constructor({ settingsPath, api, onState, source = sepehryarSource }) {
    this.settingsPath = settingsPath;
    this.api = api;
    this.source = source;
    this.onState = onState;
    this.settings = this.loadSettings();
    this.running = false;
    this.timer = null;
    this.status = 'در انتظار ورود به پنل';
    this.error = null;
    this.lastSync = null;
    this.sentInvoices = 0;
    this.catalogCount = 0;
  }

  loadSettings() {
    try {
      const value = JSON.parse(fs.readFileSync(this.settingsPath, 'utf8'));
      return {
        // Version 0.2.0 started at today's invoices. Replay its cursor once so
        // an upgrade also backfills older sales; server-side IDs prevent copies.
        cursor: value.backfillAllV1 === true && Number.isSafeInteger(value.cursor) && value.cursor >= 0 ? value.cursor : 0,
        catalogAt: typeof value.catalogAt === 'number' ? value.catalogAt : 0,
        backfillAllV1: true,
      };
    } catch {
      return { cursor: null, catalogAt: 0, backfillAllV1: true };
    }
  }

  saveSettings() {
    fs.mkdirSync(path.dirname(this.settingsPath), { recursive: true });
    fs.writeFileSync(this.settingsPath, JSON.stringify(this.settings, null, 2), { mode: 0o600 });
  }

  getState() {
    return {
      importStatus: this.status, importError: this.error, lastSync: this.lastSync,
      sentInvoices: this.sentInvoices, catalogCount: this.catalogCount,
      cursor: this.settings.cursor, importRunning: this.running,
    };
  }

  publish() { this.onState(this.getState()); }

  start() {
    if (this.timer) return;
    this.timer = setInterval(() => void this.scanOnce(), 60_000);
    void this.scanOnce();
  }

  stop() { clearInterval(this.timer); this.timer = null; }

  async scanOnce() {
    if (this.running) return;
    this.running = true;
    this.error = null;
    this.publish();
    try {
      const authorization = await this.api.boot();
      if (!authorization?.products_disabled && (!this.settings.catalogAt || Date.now() - this.settings.catalogAt > 60 * 60 * 1000)) {
        this.status = 'در حال همگام‌سازی محصولات';
        this.publish();
        const products = await this.source.readSepehryarCatalog();
        for (let i = 0; i < products.length; i += 100) {
          await this.api.post('sync_products', { products: products.slice(i, i + 100) });
        }
        this.catalogCount = products.length;
        this.settings.catalogAt = Date.now();
        this.saveSettings();
      }
      if (this.settings.cursor === null) {
        this.settings.cursor = await this.source.readInitialCursor();
        this.saveSettings();
      }
      this.status = 'در حال همگام‌سازی فروش';
      this.publish();
      for (let batch = 0; batch < 5; batch += 1) {
        const invoices = await this.source.readSepehryarSales(this.settings.cursor);
        if (!invoices.length) break;
        // A just-opened bill may still change in the POS. Retry it next time.
        const firstRecent = invoices.findIndex((invoice) => {
          const occurred = new Date(`${invoice.postingDate}T${invoice.postingTime}+03:30`);
          return Number.isNaN(occurred.getTime()) || Date.now() - occurred.getTime() <= 3 * 60_000;
        });
        const ready = firstRecent === -1 ? invoices : invoices.slice(0, firstRecent);
        if (!ready.length) break;
        const result = await this.api.post('import_sales', { invoices: ready });
        const acknowledged = new Set([
          ...(result.created || []).map((row) => Number(row.sourceInvoiceId)),
          ...(result.skipped || []).map(Number),
        ]);
        if (ready.some((invoice) => !acknowledged.has(invoice.sourceInvoiceId))) {
          throw new Error('سرور همهٔ فاکتورهای ارسالی را تأیید نکرد.');
        }
        this.settings.cursor = ready.at(-1).sourceInvoiceId;
        this.saveSettings();
        this.sentInvoices += (result.created || []).length;
        if (ready.length < invoices.length || invoices.length < 20) break;
      }
      this.status = 'همگام‌سازی فعال';
      this.lastSync = new Date().toISOString();
    } catch (error) {
      this.error = error.message || String(error);
      this.status = error.status === 401 || error.status === 403 ? 'لطفاً وارد پنل شوید' : 'همگام‌سازی متوقف شد';
    } finally {
      this.running = false;
      this.publish();
    }
  }
}

module.exports = { SalesImportService };
