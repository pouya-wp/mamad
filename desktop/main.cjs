const path = require('node:path');
const { app, BrowserWindow, WebContentsView, ipcMain, session, shell, Tray, Menu, net, safeStorage } = require('electron');
const { SalesImportService } = require('./importer/index.cjs');
const { createSalesApi } = require('./importer/device-api.cjs');
const { RemoteAgent } = require('./remote/agent.cjs');

const PANEL_URL = 'https://onecafe.beyondex.one';
const PANEL_ORIGIN = new URL(PANEL_URL).origin;
const HEADER_HEIGHT = 64;
const SETTINGS_HEIGHT = 254;

let mainWindow;
let panelView;
let importer;
let remoteAgent;
let tray;
let quitRequested = false;
let settingsOpen = false;
let panelStatus = 'در حال اتصال';

const primaryInstance = app.requestSingleInstanceLock();
if (!primaryInstance) app.quit();
app.on('second-instance', () => {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
});

function isAllowedPanelUrl(raw) {
  try {
    const url = new URL(raw);
    return url.origin === PANEL_ORIGIN && url.protocol === 'https:';
  } catch {
    return false;
  }
}

function panelApi() {
  const panelSession = session.fromPartition('persist:one-cafe');
  return {
    async boot() {
      const response = await panelSession.fetch(`${PANEL_ORIGIN}/api/method/cafe_app.api.session.boot`, {
        credentials: 'include', redirect: 'error', signal: AbortSignal.timeout(30_000),
      });
      if (!response.ok) {
        const error = new Error(response.status === 401 || response.status === 403 ? 'ورود به پنل لازم است.' : `خطای سرور: ${response.status}`);
        error.status = response.status;
        throw error;
      }
      const body = await response.json();
      if (!body.message?.csrf_token) throw new Error('نشست پنل معتبر نیست.');
      this.csrfToken = body.message.csrf_token;
    },
    async post(method, data) {
      const response = await panelSession.fetch(`${PANEL_ORIGIN}/api/method/cafe_app.api.sepehryar.${method}`, {
        method: 'POST', credentials: 'include', redirect: 'error',
        signal: AbortSignal.timeout(90_000),
        headers: {
          'Content-Type': 'application/json',
          'X-Frappe-CSRF-Token': this.csrfToken,
        },
        body: JSON.stringify(data),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const error = new Error(body.message || body.exception || `خطای سرور: ${response.status}`);
        error.status = response.status;
        throw error;
      }
      return body.message;
    },
    async enroll(machineName, appVersion) {
      const response = await panelSession.fetch(`${PANEL_ORIGIN}/api/method/cafe_app.api.desktop_remote.enroll`, {
        method: 'POST', credentials: 'include', redirect: 'error',
        signal: AbortSignal.timeout(30_000),
        headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': this.csrfToken },
        body: JSON.stringify({ machine_name: machineName, app_version: appVersion }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.message || `ثبت دستگاه: خطای ${response.status}`);
      return body.message;
    },
    async devicePost(method, token, data = {}) {
      const response = await net.fetch(`${PANEL_ORIGIN}/api/method/cafe_app.api.desktop_remote.${method}`, {
        method: 'POST', credentials: 'omit', redirect: 'error', signal: AbortSignal.timeout(30_000),
        headers: { 'Content-Type': 'application/json', 'X-OneCafe-Device-Token': token },
        body: JSON.stringify(data),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.message || `فرمان مدیریتی: خطای ${response.status}`);
      return body.message;
    },
    async salesDevicePost(method, token, data = {}) {
      if (!['device_boot', 'device_import_sales'].includes(method)) throw new Error('روش همگام‌سازی نامعتبر است.');
      const response = await net.fetch(`${PANEL_ORIGIN}/api/method/cafe_app.api.sepehryar.${method}`, {
        method: 'POST', credentials: 'omit', redirect: 'error', signal: AbortSignal.timeout(90_000),
        headers: { 'Content-Type': 'application/json', 'X-OneCafe-Device-Token': token },
        body: JSON.stringify(data),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const error = new Error(response.status === 401 ? 'مجوز دستگاه معتبر نیست؛ ثبت دستگاه را بررسی کنید.' : body.message || body.exception || `خطای سرور: ${response.status}`);
        error.status = response.status;
        throw error;
      }
      return body.message;
    },
    poll(token) { return this.devicePost('poll', token); },
    report(token, result) { return this.devicePost('report', token, result); },
  };
}

function publishState() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('app:state', {
      panelStatus,
      settingsOpen,
      maximized: mainWindow.isMaximized(),
      ...importer.getState(),
      ...remoteAgent?.getState(),
    });
  }
}

function layoutView() {
  if (!mainWindow || !panelView) return;
  const [width, height] = mainWindow.getContentSize();
  const top = settingsOpen ? HEADER_HEIGHT + SETTINGS_HEIGHT : HEADER_HEIGHT;
  panelView.setBounds({ x: 8, y: top, width: Math.max(1, width - 16), height: Math.max(1, height - top - 8) });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 940,
    minHeight: 650,
    frame: false,
    roundedCorners: true,
    backgroundColor: '#0a0a0b',
    show: false,
    autoHideMenuBar: true,
    icon: path.join(__dirname, 'build', 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });
  mainWindow.loadFile(path.join(__dirname, 'shell', 'index.html'));
  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.on('close', (event) => {
    if (quitRequested) return;
    event.preventDefault();
    mainWindow.hide();
  });
  mainWindow.on('resize', layoutView);
  mainWindow.on('maximize', publishState);
  mainWindow.on('unmaximize', publishState);
  mainWindow.on('closed', () => { mainWindow = null; panelView = null; });

  panelView = new WebContentsView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      partition: 'persist:one-cafe',
    },
  });
  panelView.setBackgroundColor('#000000');
  panelView.setBorderRadius(12);
  mainWindow.contentView.addChildView(panelView);
  layoutView();

  panelView.webContents.on('did-start-loading', () => { panelStatus = 'در حال اتصال'; publishState(); });
  panelView.webContents.on('did-finish-load', () => { panelStatus = 'متصل'; publishState(); });
  panelView.webContents.on('did-fail-load', (_event, code, description, validatedURL, isMainFrame) => {
    if (isMainFrame && code !== -3) {
      panelStatus = 'اتصال برقرار نشد';
      console.error('Panel load failed:', description, validatedURL);
      publishState();
    }
  });
  panelView.webContents.on('will-navigate', (event, url) => {
    if (!isAllowedPanelUrl(url)) event.preventDefault();
  });
  panelView.webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowedPanelUrl(url)) panelView.webContents.loadURL(url);
    else if (url.startsWith('https://')) shell.openExternal(url);
    return { action: 'deny' };
  });
  panelView.webContents.session.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  panelView.webContents.loadURL(PANEL_URL);
}

function createTray() {
  tray = new Tray(path.join(__dirname, 'build', 'icon.ico'));
  tray.setToolTip('ONE CAFE — همگام‌سازی سپهریار');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'نمایش ONE CAFE', click: () => mainWindow?.show() },
    { label: 'همگام‌سازی الآن', click: () => void importer?.scanOnce() },
    { type: 'separator' },
    { label: 'خروج و توقف همگام‌سازی', click: () => { quitRequested = true; app.quit(); } },
  ]));
  tray.on('double-click', () => mainWindow?.show());
}

app.whenReady().then(() => {
  if (!primaryInstance) return;
  if (app.isPackaged && process.platform === 'win32') {
    app.setLoginItemSettings({ openAtLogin: true });
  }
  const managementApi = panelApi();
  remoteAgent = new RemoteAgent({
    statePath: path.join(app.getPath('userData'), 'remote-agent.json'),
    secureStorage: safeStorage,
    api: managementApi,
    appVersion: app.getVersion(),
    onState: publishState,
  });
  importer = new SalesImportService({
    settingsPath: path.join(app.getPath('userData'), 'sepehryar-sync.json'),
    api: createSalesApi({
      getToken: () => remoteAgent.getDeviceToken(),
      call: (method, token, data) => managementApi.salesDevicePost(method, token, data),
    }),
    onState: publishState,
  });
  importer.start();
  remoteAgent.start();
  createTray();

  ipcMain.on('window:action', (event, action) => {
    if (event.sender !== mainWindow?.webContents) return;
    if (action === 'close') mainWindow.hide();
    if (action === 'minimize') mainWindow.minimize();
    if (action === 'maximize') {
      if (mainWindow.isMaximized()) mainWindow.unmaximize();
      else mainWindow.maximize();
    }
  });
  ipcMain.handle('app:get-state', (event) => {
    if (event.sender !== mainWindow?.webContents) return null;
    return { panelStatus, settingsOpen, maximized: mainWindow.isMaximized(), ...importer.getState(), ...remoteAgent.getState() };
  });
  ipcMain.handle('import:sync-now', (event) => {
    if (event.sender !== mainWindow?.webContents) return null;
    return importer.scanOnce();
  });
  ipcMain.on('app:settings', (event, open) => {
    if (event.sender !== mainWindow?.webContents) return;
    settingsOpen = Boolean(open);
    layoutView();
    publishState();
  });
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
  createWindow();
});

app.on('before-quit', () => { quitRequested = true; });

app.on('window-all-closed', () => {
  importer?.stop();
  remoteAgent?.stop();
  if (process.platform !== 'darwin') app.quit();
});
