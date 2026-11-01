const { execFile } = require('node:child_process');
const { promisify } = require('node:util');

const execFileAsync = promisify(execFile);
const SERVER = '.\\SEPANDYAR2014';
const DATABASE = 'Sepand_One_1405';
const DATE_FORMAT = new Intl.DateTimeFormat('en-u-ca-persian-nu-latn', {
  timeZone: 'UTC', year: 'numeric', month: 'numeric', day: 'numeric',
});

async function query(sql) {
  const { stdout } = await execFileAsync('sqlcmd', [
    '-S', SERVER, '-E', '-d', DATABASE, '-b', '-W', '-h', '-1', '-w', '65535',
    '-s', '|', '-f', '65001', '-Q', `SET NOCOUNT ON; ${sql}`,
  ], { windowsHide: true, timeout: 30_000, maxBuffer: 8 * 1024 * 1024 });
  return stdout.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

function gregorianDate(jalaliDate) {
  const match = /^(\d{4})\/(\d{1,2})\/(\d{1,2})$/.exec(jalaliDate || '');
  if (!match) throw new Error(`تاریخ سپهریار نامعتبر است: ${jalaliDate}`);
  const target = match.slice(1).map(Number);
  const read = (day) => {
    const parts = DATE_FORMAT.formatToParts(new Date(day));
    return ['year', 'month', 'day'].map((type) => Number(parts.find((part) => part.type === type)?.value));
  };
  let low = Date.UTC(target[0] + 620, 0, 1) / 86400000;
  let high = Date.UTC(target[0] + 623, 0, 1) / 86400000;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    const value = read(middle * 86400000);
    const order = value[0] - target[0] || value[1] - target[1] || value[2] - target[2];
    if (order < 0) low = middle + 1;
    else high = middle;
  }
  if (read(low * 86400000).some((value, index) => value !== target[index])) {
    throw new Error(`تاریخ سپهریار نامعتبر است: ${jalaliDate}`);
  }
  return new Date(low * 86400000).toISOString().slice(0, 10);
}

async function readInitialCursor() {
  // Start with the entire current SepandYar database. The server deduplicates
  // acknowledged FactorIDs, so retrying after an interrupted import is safe.
  return 0;
}

async function readSepehryarCatalog() {
  const rows = await query(`
    SELECT IDKala, REPLACE(REPLACE(REPLACE(MAX(Name), '|', ' '), CHAR(13), ' '), CHAR(10), ' ')
    FROM dbo.TblKala
    WHERE IDKala > 0 AND NULLIF(LTRIM(RTRIM(Name)), '') IS NOT NULL
    GROUP BY IDKala ORDER BY IDKala`);
  return rows.map((line) => {
    const parts = line.split('|');
    if (parts.length !== 2 || !Number.isSafeInteger(Number(parts[0]))) throw new Error('قالب فهرست کالاهای سپهریار نامعتبر است.');
    return { sourceItemId: Number(parts[0]), name: parts[1].trim() };
  });
}

function rowsToInvoices(rows) {
  const invoices = new Map();
  for (const line of rows) {
    const parts = line.split('|');
    if (parts.length !== 11) throw new Error('قالب ردیف فروش سپهریار نامعتبر است.');
    const [id, jalaliDate, rawTime, customerName, mobile, itemId, warehouseId, quantity, amount, discount, itemName] = parts;
    const factorId = Number(id);
    if (!Number.isSafeInteger(factorId) || factorId <= 0) throw new Error('شمارهٔ فاکتور سپهریار نامعتبر است.');
    let invoice = invoices.get(factorId);
    if (!invoice) {
      const clock = /(?:^|\s)(\d{1,2}:\d{2})(?::\d{2})?\s*$/.exec(rawTime)?.[1] || '00:00';
      invoice = {
        sourceInvoiceId: factorId, jalaliDate, postingDate: gregorianDate(jalaliDate),
        postingTime: `${clock}:00`, customerName, mobile, items: [],
      };
      invoices.set(factorId, invoice);
    }
    if (Number(itemId) > 0 && Number(quantity) > 0 && Number(amount) > 0) {
      invoice.items.push({
        sourceItemId: Number(itemId), warehouseId: Number(warehouseId), name: itemName,
        quantity: Number(quantity), amount: Number(amount), discount: Number(discount) || 0,
      });
    }
  }
  return [...invoices.values()];
}

async function readSepehryarSales(afterFactorId = 0) {
  if (!Number.isSafeInteger(afterFactorId) || afterFactorId < 0) throw new Error('نشانگر فروش نامعتبر است.');
  const rows = await query(`
    WITH next_factors AS (
      SELECT TOP (20) FactorID, DateFactor, Time, CustomerName, Mobile
      FROM dbo.Day_Factor
      WHERE ISNULL(Cancel, 0) = 0 AND FactorID > ${afterFactorId}
      ORDER BY FactorID ASC
    )
    SELECT f.FactorID, f.DateFactor,
      REPLACE(REPLACE(REPLACE(ISNULL(f.Time, ''), '|', ' '), CHAR(13), ' '), CHAR(10), ' '),
      REPLACE(REPLACE(REPLACE(ISNULL(f.CustomerName, ''), '|', ' '), CHAR(13), ' '), CHAR(10), ' '),
      ISNULL(f.Mobile, ''), ISNULL(t.IdKala, 0), ISNULL(t.IdAnbar, 0),
      ISNULL(t.Ted, 0), ISNULL(t.Bes, 0), ISNULL(t.Takh, 0),
      REPLACE(REPLACE(REPLACE(ISNULL(k.Name, ''), '|', ' '), CHAR(13), ' '), CHAR(10), ' ')
    FROM next_factors f
    LEFT JOIN dbo.Day_TR t ON t.Factor = f.FactorID AND t.IdKala > 0 AND t.Bes > 0
    LEFT JOIN dbo.TblKala k ON k.IDKala = t.IdKala AND k.IDAnbar = t.IdAnbar
    ORDER BY f.FactorID ASC, t.IdKala ASC`);
  return rowsToInvoices(rows);
}

module.exports = { readInitialCursor, readSepehryarCatalog, readSepehryarSales, rowsToInvoices, gregorianDate };
