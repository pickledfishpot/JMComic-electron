import { contextBridge, ipcRenderer } from "electron";

/** 主进程通过 additionalArguments 传入的后端端口（打包后渲染层拼 API/图片基址用） */
function readBackendPort(): number {
  const arg = process.argv.find((a) =>
    a.startsWith("--jmcomic-backend-port="),
  );
  return arg ? Number(arg.split("=")[1]) : 0;
}

export interface ElectronAPI {
  platform: string;
  versions: {
    node: string;
    chrome: string;
    electron: string;
  };
  /** 后端实际监听端口；开发模式为 0（渲染层走 vite 代理，不使用该值） */
  backendPort: number;
  openExternal: (url: string) => Promise<void>;
  selectFolder: () => Promise<string | null>;
  quitApp: () => Promise<void>;
  onBackendState: (
    callback: (state: { type: string; message: string }) => void,
  ) => () => void;
}

const api: ElectronAPI = {
  platform: process.platform,
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
  backendPort: readBackendPort(),
  openExternal: async (url: string) => {
    await ipcRenderer.invoke("open-external", url);
  },
  selectFolder: async () => {
    return ipcRenderer.invoke("select-folder");
  },
  quitApp: async () => {
    await ipcRenderer.invoke("quit-app");
  },
  onBackendState: (callback) => {
    const handler = (
      _event: unknown,
      state: { type: string; message: string },
    ) => callback(state);
    ipcRenderer.on("backend-state", handler);
    return () => {
      ipcRenderer.removeListener("backend-state", handler);
    };
  },
};

contextBridge.exposeInMainWorld("electronAPI", api);
// 同步暴露端口，渲染层 api client / 图片地址在模板渲染前即可读取
contextBridge.exposeInMainWorld(
  "__JMCOMIC_BACKEND_PORT__",
  readBackendPort(),
);

declare global {
  interface Window {
    electronAPI: ElectronAPI;
    /** 与 electronAPI.backendPort 相同，供 api client 直接同步读取 */
    __JMCOMIC_BACKEND_PORT__?: number;
  }
}
