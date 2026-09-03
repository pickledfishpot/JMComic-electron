import {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  shell,
  Tray,
  Menu,
} from "electron";
import path from "node:path";
import fs from "node:fs";
import { ChildProcess } from "node:child_process";
import {
  startBackend,
  stopBackend,
  getDefaultDataDir,
  findFreePort,
  waitForBackend,
} from "./utils/backend-launcher";
import {
  loadWindowState,
  saveWindowState,
  trackWindowState,
  type WindowState,
} from "./utils/window-state";

let mainWindow: BrowserWindow | null = null;
let splashWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;
let backendPort = 0;
let tray: Tray | null = null;
let quitting = false;

function sendBackendState(type: string, message: string) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send("backend-state", { type, message });
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("backend-state", { type, message });
  }
}

async function createSplashWindow(): Promise<BrowserWindow> {
  const win = new BrowserWindow({
    width: 420,
    height: 320,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  const splashPath = app.isPackaged
    ? path.join(__dirname, "../renderer/splash.html")
    : path.join(process.cwd(), "renderer/public/splash.html");

  await win.loadFile(splashPath);
  return win;
}

function getTrayIconPath(): string {
  const icon = process.platform === "darwin" ? "tray-22.png" : "tray.png";
  // 打包后 electron-builder 通过 extraResources 把 icons 放到 Resources/icons
  const candidates = [
    path.join(process.resourcesPath, "icons", icon),
    path.join(app.getAppPath(), "resources/icons", icon),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return candidates[1];
}

function showMainWindow() {
  if (!mainWindow) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

function quitApp() {
  quitting = true;
  app.quit();
}

function createTray() {
  try {
    tray = new Tray(getTrayIconPath());
    tray.setToolTip("JMComic");
    tray.setContextMenu(
      Menu.buildFromTemplate([
        { label: "显示主窗口", click: showMainWindow },
        { type: "separator" },
        { label: "退出", click: quitApp },
      ]),
    );
    tray.on("click", () => {
      if (mainWindow?.isVisible()) {
        mainWindow.hide();
      } else {
        showMainWindow();
      }
    });
  } catch (err) {
    console.warn("Tray unavailable:", err);
  }
}

async function createMainWindow(): Promise<BrowserWindow> {
  const state: WindowState = loadWindowState(getDefaultDataDir());
  const win = new BrowserWindow({
    width: state.width,
    height: state.height,
    minWidth: 900,
    minHeight: 600,
    x: state.x,
    y: state.y,
    show: false,
    title: "JMComic",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  if (app.isPackaged) {
    await win.loadFile(path.join(__dirname, "../renderer/index.html"));
  } else {
    await win.loadURL("http://localhost:5173");
  }

  win.once("ready-to-show", () => {
    win.show();
    if (state.maximized) win.maximize();
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
  });

  // 关闭到托盘：点 X 隐藏，托盘/菜单退出才真正退出（quitting 时放行）
  win.on("close", (event) => {
    if (!quitting) {
      event.preventDefault();
      saveWindowState(getDefaultDataDir(), win);
      win.hide();
      return;
    }
    saveWindowState(getDefaultDataDir(), win);
  });

  win.on("closed", () => {
    mainWindow = null;
  });

  trackWindowState(win);
  return win;
}

async function initializeBackend() {
  const dataDir = getDefaultDataDir();
  // 开发模式下由 dev 脚本指定固定端口，保证与 vite 代理一致
  const envPort = process.env.JMCOMIC_BACKEND_PORT;
  backendPort = envPort ? Number(envPort) : await findFreePort();

  sendBackendState("starting", `正在启动后端服务 (端口 ${backendPort})...`);

  backendProcess = await startBackend({ port: backendPort, dataDir });
  backendProcess.on("exit", (code) => {
    console.log(`[backend] exited with code ${code}`);
    sendBackendState("stopped", `后端服务已退出 (code ${code ?? "unknown"})`);
    backendProcess = null;
  });

  sendBackendState("waiting", "等待后端服务就绪...");
  await waitForBackend(backendPort);
  sendBackendState("ready", "后端服务已就绪");
}

async function shutdownBackend() {
  sendBackendState("stopping", "正在停止后端服务...");
  await stopBackend(backendProcess);
  backendProcess = null;
}

// ---------------- 单实例 ----------------

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    showMainWindow();
  });

  app.on("ready", async () => {
    try {
      splashWindow = await createSplashWindow();
      await initializeBackend();
      mainWindow = await createMainWindow();
      createTray();
    } catch (err) {
      console.error("Failed to start application:", err);
      sendBackendState("error", String(err));
    }
  });
}

app.on("before-quit", async (event) => {
  if (backendProcess) {
    event.preventDefault();
    await shutdownBackend();
    app.quit();
  }
});

app.on("window-all-closed", () => {
  // 关闭到托盘：窗口全关不退出（macOS 惯例也由托盘接管）
  if (quitting && process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", async () => {
  if (BrowserWindow.getAllWindows().length === 0 && mainWindow === null) {
    mainWindow = await createMainWindow();
  } else {
    showMainWindow();
  }
});

ipcMain.handle("open-external", async (_event, url: string) => {
  await shell.openExternal(url);
});

ipcMain.handle("select-folder", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle("get-backend-port", () => backendPort);

// 渲染进程主动请求退出（如设置页"退出应用"）
ipcMain.handle("quit-app", () => {
  quitApp();
});
