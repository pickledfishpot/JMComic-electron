import { contextBridge, ipcRenderer } from 'electron';

export interface ElectronAPI {
  platform: string;
  versions: {
    node: string;
    chrome: string;
    electron: string;
  };
  openExternal: (url: string) => Promise<void>;
  selectFolder: () => Promise<string | null>;
  onBackendState: (callback: (state: { type: string; message: string }) => void) => () => void;
}

const api: ElectronAPI = {
  platform: process.platform,
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
  openExternal: async (url: string) => {
    await ipcRenderer.invoke('open-external', url);
  },
  selectFolder: async () => {
    return ipcRenderer.invoke('select-folder');
  },
  onBackendState: (callback) => {
    const handler = (_event: unknown, state: { type: string; message: string }) =>
      callback(state);
    ipcRenderer.on('backend-state', handler);
    return () => {
      ipcRenderer.removeListener('backend-state', handler);
    };
  },
};

contextBridge.exposeInMainWorld('electronAPI', api);

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
