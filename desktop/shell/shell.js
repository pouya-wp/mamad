const settingsButton = document.getElementById('settings-button');
const settings = document.getElementById('settings');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const syncCounts = document.getElementById('sync-counts');
const syncDetail = document.getElementById('sync-detail');
const remoteDetail = document.getElementById('remote-detail');
const badge = document.getElementById('import-badge');
let settingsOpen = false;

function render(state) {
  if (!state) return;
  if (state.panelStatus) {
    statusText.textContent = state.panelStatus;
    statusDot.className = state.panelStatus === 'متصل' ? 'online' : state.panelStatus === 'اتصال برقرار نشد' ? 'offline' : '';
  }
  if (typeof state.settingsOpen === 'boolean') {
    settingsOpen = state.settingsOpen;
    settings.hidden = !settingsOpen;
    settingsButton.classList.toggle('active', settingsOpen);
  }
  badge.textContent = state.importStatus || 'در انتظار ورود';
  syncCounts.textContent = `${state.catalogCount || 0} محصول · ${state.sentInvoices || 0} فروش در این اجرا`;
  syncDetail.textContent = state.importError || (state.lastSync ? `آخرین بررسی: ${new Date(state.lastSync).toLocaleString('fa-IR')}` : 'آخرین همگام‌سازی هنوز انجام نشده است.');
  remoteDetail.textContent = `${state.remoteError || state.remoteStatus || 'مدیریت از راه دور: در انتظار ثبت دستگاه'}${state.remoteDeviceId ? ` · شناسه دستگاه: ${state.remoteDeviceId}` : ''}`;
}

for (const button of document.querySelectorAll('[data-action]')) {
  button.addEventListener('click', () => window.oneCafe.windowAction(button.dataset.action));
}
settingsButton.addEventListener('click', () => {
  settingsOpen = !settingsOpen;
  settings.hidden = !settingsOpen;
  settingsButton.classList.toggle('active', settingsOpen);
  window.oneCafe.setSettingsOpen(settingsOpen);
});
document.getElementById('sync-now').addEventListener('click', () => void window.oneCafe.syncNow());
window.oneCafe.onState(render);
window.oneCafe.getState().then(render);
