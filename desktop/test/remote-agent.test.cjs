const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { RemoteAgent, runPowerShell } = require('../remote/agent.cjs');

const storage = {
  isEncryptionAvailable: () => true,
  encryptString: (value) => Buffer.from(value, 'utf8'),
  decryptString: (value) => value.toString('utf8'),
};

test('enrollment, claim, execution and report are persisted in order', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'one-cafe-remote-test-'));
  try {
    const script = 'Write-Output "hello"';
    const calls = [];
    let claimed = false;
    const api = {
      boot: async () => { calls.push('boot'); },
      enroll: async () => { calls.push('enroll'); return { device_id: 'b'.repeat(64), device_token: 'a'.repeat(64) }; },
      poll: async () => {
        calls.push('poll');
        if (claimed) return { job: null };
        claimed = true;
        return { job: { id: 'job_12345678', script, sha256: crypto.createHash('sha256').update(script).digest('hex'), timeoutSeconds: 30 } };
      },
      report: async (_token, result) => { calls.push('report'); assert.equal(result.stdout, 'hello'); },
    };
    const agent = new RemoteAgent({
      statePath: path.join(directory, 'state.json'), secureStorage: storage,
      api, appVersion: '0.3.0', runner: async () => {
        calls.push('run'); return { exit_code: 0, stdout: 'hello', stderr: '', timed_out: false };
      },
    });
    await agent.tick();
    assert.deepEqual(calls, ['boot', 'enroll', 'poll', 'run', 'report']);
    assert.equal(JSON.parse(fs.readFileSync(agent.statePath, 'utf8')).inflight, undefined);
    await agent.tick();
    assert.deepEqual(calls.slice(5), ['poll']);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test('a crash before result reporting is recorded without running the script twice', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'one-cafe-remote-test-'));
  try {
    const statePath = path.join(directory, 'state.json');
    const encryptedToken = Buffer.from(JSON.stringify('a'.repeat(64))).toString('base64');
    fs.writeFileSync(statePath, JSON.stringify({ encryptedToken, deviceId: 'b'.repeat(64), inflight: 'job_12345678' }));
    let ran = false;
    let report;
    const agent = new RemoteAgent({
      statePath, secureStorage: storage, appVersion: '0.3.0',
      api: { report: async (_token, result) => { report = result; }, poll: async () => ({ job: null }) },
      runner: async () => { ran = true; },
    });
    await agent.tick();
    assert.equal(ran, false);
    assert.equal(report.job_id, 'job_12345678');
    assert.match(report.stderr, /not retried/);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test('PowerShell runner preserves Persian output and returns an exit code', { skip: process.platform !== 'win32' }, async () => {
  const result = await runPowerShell("Write-Output 'سلام'; exit 0", 15);
  assert.equal(result.exit_code, 0);
  assert.match(result.stdout, /سلام/);
  assert.equal(result.timed_out, false);
});

test('PowerShell runner stops a hung job and reports the timeout', { skip: process.platform !== 'win32' }, async () => {
  const result = await runPowerShell('Start-Sleep -Seconds 10', 1);
  assert.equal(result.timed_out, true);
  assert.notEqual(result.exit_code, 0);
});
