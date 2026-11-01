const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('oneCafe', {
  windowAction: (action) => {
    if (['close', 'minimize', 'maximize'].includes(action)) ipcRenderer.send('window:action', action);
  },
  setSettingsOpen: (open) => ipcRenderer.send('app:settings', Boolean(open)),
  getState: () => ipcRenderer.invoke('app:get-state'),
  syncNow: () => ipcRenderer.invoke('import:sync-now'),
  onState: (callback) => {
    const listener = (_event, state) => callback(state);
    ipcRenderer.on('app:state', listener);
    return () => ipcRenderer.removeListener('app:state', listener);
  },
});
