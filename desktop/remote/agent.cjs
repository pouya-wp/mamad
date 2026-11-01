const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');

const MAX_OUTPUT = 60 * 1024;
const POLL_MS = 30_000;

function cappedAppend(previous, chunk) {
  const next = previous + chunk.toString('utf8');
  if (next.length <= MAX_OUTPUT) return next;
  return `${next.slice(0, MAX_OUTPUT - 24)}\n[output truncated]`;
}

function runPowerShell(script, timeoutSeconds) {
  return new Promise((resolve) => {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'one-cafe-job-'));
    const scriptPath = path.join(directory, 'job.ps1');
    // This is a new temporary file belonging to the agent. Source files are untouched.
    // UTF-8 BOM matters for Persian literals in Windows PowerShell 5.1.
    const utf8 = '[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)\r\n' +
      '$OutputEncoding = [Console]::OutputEncoding\r\n' +
      "$ErrorActionPreference = 'Stop'\r\n";
    fs.writeFileSync(scriptPath, `\uFEFF${utf8}${script}`, { flag: 'wx', mode: 0o600 });
    let stdout = '';
    let stderr = '';
    let timedOut = false;
    let child;
    let timer;
    try {
      child = spawn('powershell.exe', [
        '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', scriptPath,
      ], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
      child.stdout.on('data', (chunk) => { stdout = cappedAppend(stdout, chunk); });
      child.stderr.on('data', (chunk) => { stderr = cappedAppend(stderr, chunk); });
      timer = setTimeout(() => {
        timedOut = true;
        if (process.platform === 'win32' && child.pid) {
          const killer = spawn('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
          killer.on('close', () => { if (!child.killed) child.kill('SIGKILL'); });
        } else {
          child.kill('SIGKILL');
        }
      }, timeoutSeconds * 1000);
      child.on('error', (error) => {
        stderr = cappedAppend(stderr, Buffer.from(error.message));
      });
      child.on('close', (code) => {
        clearTimeout(timer);
        try { fs.rmSync(directory, { recursive: true, force: true }); } catch { /* temp cleanup only */ }
        resolve({ exit_code: Number.isInteger(code) ? code : -1, stdout, stderr, timed_out: timedOut });
      });
    } catch (error) {
      clearTimeout(timer);
      try { fs.rmSync(directory, { recursive: true, force: true }); } catch { /* temp cleanup only */ }
      resolve({ exit_code: -1, stdout, stderr: error.message, timed_out: false });
    }
  });
}

class RemoteAgent {
  constructor({ statePath, secureStorage, api, machineName = os.hostname(), appVersion, onState = () => {}, runner = runPowerShell }) {
    this.statePath = statePath;
    this.secureStorage = secureStorage;
    this.api = api;
    this.machineName = machineName;
    this.appVersion = appVersion;
    this.onState = onState;
    this.runner = runner;
    this.timer = null;
    this.running = false;
    this.enrollmentPromise = null;
    this.status = 'در انتظار ثبت دستگاه';
    this.lastSeen = null;
    this.lastError = null;
    this.state = this.loadState();
  }

  loadState() {
    try {
      return JSON.parse(fs.readFileSync(this.statePath, 'utf8'));
    } catch {
      return {};
    }
  }

  saveState() {
    fs.mkdirSync(path.dirname(this.statePath), { recursive: true });
    const temp = `${this.statePath}.${process.pid}.tmp`;
    fs.writeFileSync(temp, JSON.stringify(this.state), { mode: 0o600 });
    fs.renameSync(temp, this.statePath);
  }

  encrypt(value) {
    if (!this.secureStorage.isEncryptionAvailable()) throw new Error('رمزنگاری امن ویندوز در دسترس نیست.');
    return this.secureStorage.encryptString(JSON.stringify(value)).toString('base64');
  }

  decrypt(value) {
    if (!this.secureStorage.isEncryptionAvailable()) throw new Error('رمزنگاری امن ویندوز در دسترس نیست.');
    return JSON.parse(this.secureStorage.decryptString(Buffer.from(value, 'base64')));
  }

  getState() {
    return { remoteStatus: this.status, remoteLastSeen: this.lastSeen, remoteError: this.lastError, remoteDeviceId: this.state.deviceId || null };
  }

  publish() { this.onState(this.getState()); }

  start() {
    if (this.timer) return;
    this.timer = setInterval(() => void this.tick(), POLL_MS);
    void this.tick();
  }

  stop() { clearInterval(this.timer); this.timer = null; }

  async getDeviceToken() {
    if (this.state.encryptedToken) return this.decrypt(this.state.encryptedToken);
    // Startup polling and sales sync may request enrollment concurrently.
    if (!this.enrollmentPromise) {
      this.enrollmentPromise = (async () => {
        await this.api.boot();
        const enrollment = await this.api.enroll(this.machineName, this.appVersion);
        if (!/^[a-f0-9]{64}$/.test(enrollment.device_token) || !/^[a-f0-9]{64}$/.test(enrollment.device_id)) {
          throw new Error('پاسخ ثبت دستگاه نامعتبر است.');
        }
        this.state.deviceId = enrollment.device_id;
        this.state.encryptedToken = this.encrypt(enrollment.device_token);
        this.saveState();
        return enrollment.device_token;
      })();
    }
    try { return await this.enrollmentPromise; }
    finally { this.enrollmentPromise = null; }
  }

  async tick() {
    if (this.running) return;
    this.running = true;
    try {
      const token = await this.getDeviceToken();
      if (this.state.inflight && !this.state.pendingResult) {
        this.state.pendingResult = this.encrypt({
          job_id: this.state.inflight, exit_code: -1, stdout: '',
          stderr: 'ONE CAFE stopped before this job completed. Execution was not retried.', timed_out: false,
        });
        this.saveState();
      }
      if (this.state.pendingResult) {
        await this.api.report(token, this.decrypt(this.state.pendingResult));
        delete this.state.pendingResult;
        delete this.state.inflight;
        this.saveState();
      }
      const response = await this.api.poll(token);
      this.lastSeen = new Date().toISOString();
      const job = response?.job;
      if (job) {
        if (!/^[a-zA-Z0-9_-]{8,140}$/.test(job.id) || typeof job.script !== 'string' || Buffer.byteLength(job.script, 'utf8') > 32768
          || crypto.createHash('sha256').update(job.script, 'utf8').digest('hex') !== job.sha256
          || !Number.isInteger(job.timeoutSeconds) || job.timeoutSeconds < 5 || job.timeoutSeconds > 600) {
          throw new Error('فرمان دریافتی نامعتبر است؛ اجرا نشد.');
        }
        this.state.inflight = job.id;
        this.saveState();
        this.status = 'در حال اجرای فرمان مدیریتی';
        this.publish();
        const result = await this.runner(job.script, job.timeoutSeconds);
        this.state.pendingResult = this.encrypt({ job_id: job.id, ...result });
        this.saveState();
        await this.api.report(token, this.decrypt(this.state.pendingResult));
        delete this.state.pendingResult;
        delete this.state.inflight;
        this.saveState();
      }
      this.status = 'مدیریت از راه دور فعال';
      this.lastError = null;
    } catch (error) {
      this.lastError = error.message || String(error);
      this.status = 'مدیریت از راه دور: خطا';
    } finally {
      this.running = false;
      this.publish();
    }
  }
}

module.exports = { RemoteAgent, runPowerShell, cappedAppend };
