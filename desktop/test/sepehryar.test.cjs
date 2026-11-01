const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { gregorianDate, rowsToInvoices, readInitialCursor } = require('../importer/sepehryar-sql.cjs');
const { SalesImportService } = require('../importer/index.cjs');

test('SepandYar date and accounting row normalize correctly', () => {
  assert.equal(gregorianDate('1405/07/04'), '2026-09-26');
  const invoices = rowsToInvoices([
    '23437|1405/07/04|1405/07/04 22:19|||12|1|1.00|2490000|0|قهوه',
    '23437|1405/07/04|1405/07/04 22:19|||0|0|0|0|0|',
  ]);
  assert.equal(invoices.length, 1);
  assert.equal(invoices[0].items.length, 1);
  assert.equal(invoices[0].items[0].sourceItemId, 12);
  assert.equal(invoices[0].items[0].warehouseId, 1);
  assert.equal(invoices[0].items[0].name, 'قهوه');
  assert.equal(invoices[0].items[0].amount, 2490000);
});

test('new installations start before the first source invoice', async () => {
  assert.equal(await readInitialCursor(), 0);
});

test('old daily cursor is reset once for historical backfill', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'one-cafe-upgrade-'));
  try {
    const settingsPath = path.join(directory, 'state.json');
    fs.writeFileSync(settingsPath, JSON.stringify({ cursor: 23436, catalogAt: 1 }));
    const service = new SalesImportService({ settingsPath, api: {}, onState: () => {} });
    assert.equal(service.settings.cursor, 0);
    service.saveSettings();
    const restarted = new SalesImportService({ settingsPath, api: {}, onState: () => {} });
    assert.equal(restarted.settings.cursor, 0);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test('catalogue and sales are acknowledged before the cursor advances', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'one-cafe-sync-'));
  try {
    const settingsPath = path.join(directory, 'state.json');
    const tenMinutesAgo = new Date(Date.now() - 600_000);
    const postingDate = `${tenMinutesAgo.getFullYear()}-${String(tenMinutesAgo.getMonth() + 1).padStart(2, '0')}-${String(tenMinutesAgo.getDate()).padStart(2, '0')}`;
    const postingTime = `${String(tenMinutesAgo.getHours()).padStart(2, '0')}:${String(tenMinutesAgo.getMinutes()).padStart(2, '0')}:00`;
    const invoice = { sourceInvoiceId: 23437, postingDate, postingTime, items: [{ sourceItemId: 12, quantity: 1, amount: 2490000 }] };
    const calls = [];
    const source = {
      readInitialCursor: async () => 0,
      readSepehryarCatalog: async () => [{ sourceItemId: 12, name: 'قهوه' }],
      readSepehryarSales: async (cursor) => cursor < 23437 ? [invoice] : [],
    };
    const api = {
      boot: async () => {},
      post: async (method, body) => {
        calls.push(method);
        return method === 'import_sales' ? { created: [{ sourceInvoiceId: body.invoices[0].sourceInvoiceId }], skipped: [] } : { created: ['SEPAND-12'] };
      },
    };
    const service = new SalesImportService({ settingsPath, source, api, onState: () => {} });
    await service.scanOnce();
    assert.deepEqual(calls, ['sync_products', 'import_sales']);
    assert.equal(service.getState().cursor, 23437);
    assert.equal(JSON.parse(fs.readFileSync(settingsPath, 'utf8')).cursor, 23437);
    await service.scanOnce();
    assert.deepEqual(calls, ['sync_products', 'import_sales']);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
