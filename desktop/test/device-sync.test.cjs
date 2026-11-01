const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { RemoteAgent } = require('../remote/agent.cjs');
const { createSalesApi } = require('../importer/device-api.cjs');
const { SalesImportService } = require('../importer/index.cjs');
const storage = {
  isEncryptionAvailable: () => true,
  encryptString: value => Buffer.from(value),
  decryptString: value => value.toString(),
};
function removeTestDirectory(directory) {
  assert.equal(path.dirname(path.resolve(directory)), path.resolve(os.tmpdir()));
  assert.ok(path.basename(directory).startsWith('one-cafe-device-test-'));
  fs.rmSync(directory, { recursive: true, force: true });
}

test('persisted device sync survives absent panel login, retries and app restart', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'one-cafe-device-test-'));
  try {
    const statePath = path.join(directory, 'remote.json');
    const token = 'a'.repeat(64);
    fs.writeFileSync(statePath, JSON.stringify({ deviceId: 'b'.repeat(64), encryptedToken: storage.encryptString(JSON.stringify(token)).toString('base64') }));
    const managerApi = { boot: async () => { throw new Error('Panel has no login'); }, enroll: async () => { throw new Error('Must reuse registered device'); } };
    const settingsPath = path.join(directory, 'sync.json');
    let failUpload = true;
    const calls = [];
    const source = {
      readInitialCursor: async () => 0,
      readSepehryarCatalog: async () => { throw new Error('Disabled catalog must not be queried'); },
      readSepehryarSales: async cursor => cursor < 23553 ? [{ sourceInvoiceId: 23553, postingDate: '2026-09-26', postingTime: '12:00:00', items: [] }] : [],
    };
    const call = async (method, sentToken) => {
      assert.equal(sentToken, token);
      calls.push(method);
      if (method === 'device_boot') return { ready: true, products_disabled: true };
      if (failUpload) throw new Error('Temporary network failure');
      return { created: [{ sourceInvoiceId: 23553 }], skipped: [] };
    };
    const makeService = () => {
      const agent = new RemoteAgent({ statePath, secureStorage: storage, api: managerApi, appVersion: '0.3.1' });
      return new SalesImportService({ settingsPath, source, api: createSalesApi({ getToken: () => agent.getDeviceToken(), call }), onState: () => {} });
    };
    const service = makeService();
    await service.scanOnce();
    assert.equal(service.settings.cursor, 0, 'An unacknowledged sale must be retried');
    failUpload = false;
    await service.scanOnce();
    assert.equal(service.settings.cursor, 23553);
    const restarted = makeService();
    await restarted.scanOnce();
    assert.equal(restarted.settings.cursor, 23553);
    assert.deepEqual(calls, ['device_boot', 'device_import_sales', 'device_boot', 'device_import_sales', 'device_boot']);
  } finally { removeTestDirectory(directory); }
});

test('revoked device cannot read SQL or advance the cursor', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'one-cafe-device-test-'));
  try {
    const settingsPath = path.join(directory, 'sync.json');
    fs.writeFileSync(settingsPath, JSON.stringify({ backfillAllV1: true, cursor: 23552 }));
    let reads = 0;
    const api = createSalesApi({ getToken: async () => 'a'.repeat(64), call: async () => { throw new Error('Device revoked'); } });
    const service = new SalesImportService({ settingsPath, api, onState: () => {}, source: { readSepehryarSales: async () => { reads++; return []; } } });
    await service.scanOnce();
    assert.equal(reads, 0);
    assert.equal(service.settings.cursor, 23552);
    assert.match(service.error, /revoked/);
  } finally { removeTestDirectory(directory); }
});

test('concurrent enrollment for maintenance and sales registers only once', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'one-cafe-device-test-'));
  try {
    let enrollments = 0;
    const agent = new RemoteAgent({ statePath: path.join(directory, 'state.json'), secureStorage: storage, appVersion: '0.3.1', api: {
      boot: async () => {},
      enroll: async () => { enrollments++; return { device_id: 'b'.repeat(64), device_token: 'a'.repeat(64) }; },
    } });
    const tokens = await Promise.all([agent.getDeviceToken(), agent.getDeviceToken()]);
    assert.deepEqual(tokens, ['a'.repeat(64), 'a'.repeat(64)]);
    assert.equal(enrollments, 1);
    assert.equal(JSON.parse(fs.readFileSync(agent.statePath)).deviceId, 'b'.repeat(64));
  } finally { removeTestDirectory(directory); }
});
