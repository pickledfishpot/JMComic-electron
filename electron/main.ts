import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron';
import path from 'node:path';
import { ChildProcess } from 'node:child_process';
import {
  startBackend,
  stopBackend,
  getDefaultDataDir,
  findFreePort,
  waitForBackend,
} from './utils/backend-launcher';

let mainWindow: BrowserWindow | null = null;
let splashWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;
let backendPort = 0;

function sendBackendState(type: string, message: string) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send('backend-state', { type, message });
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('backend-state', { type, message });
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
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  const splashPath = app.isPackaged
    ? path.join(__dirname, '../renderer/splash.html')
    : path.join(process.cwd(), 'renderer/public/splash.html');

  await win.loadFile(splashPath);
  return win;
}

async function createMainWindow(): Promise<BrowserWindow> {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    show: false,
    title: 'JMComic',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  if (app.isPackaged) {
    await win.loadFile(path.join(__dirname, '../renderer/index.html'));
  } else {
    await win.loadURL('http://localhost:5173');
  }

  win.once('ready-to-show', () => {
    win.show();
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
  });

  return win;
}

async function initializeBackend() {
  const dataDir = getDefaultDataDir();
  backendPort = await findFreePort();

  sendBackendState('starting', `正在启动后端服务 (端口 ${backendPort})...`);

  backendProcess = await startBackend({ port: backendPort, dataDir });
  backendProcess.on('exit', (code) => {
    console.log(`[backend] exited with code ${code}`);
    sendBackendState('stopped', `后端服务已退出 (code ${code ?? 'unknown'})`);
    backendProcess = null;
  });

  sendBackendState('waiting', '等待后端服务就绪...');
  await waitForBackend(backendPort);
  sendBackendState('ready', '后端服务已就绪');
}

async function shutdownBackend() {
  sendBackendState('stopping', '正在停止后端服务...');
  await stopBackend(backendProcess);
  backendProcess = null;
}

app.on('ready', async () => {
  try {
    splashWindow = await createSplashWindow();
    await initializeBackend();
    mainWindow = await createMainWindow();
  } catch (err) {
    console.error('Failed to start application:', err);
    sendBackendState('error', String(err));
  }
});

app.on('before-quit', async (event) => {
  if (backendProcess) {
    event.preventDefault();
    await shutdownBackend();
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', async () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    mainWindow = await createMainWindow();
  }
});

ipcMain.handle('open-external', async (_event, url: string) => {
  await shell.openExternal(url);
});

ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('get-backend-port', () => backendPort);
