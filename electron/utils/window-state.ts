/**
 * 窗口状态持久化：尺寸 / 位置 / 最大化，存 data_dir/window-state.json。
 */

import { app, BrowserWindow, screen } from "electron";
import fs from "node:fs";
import path from "node:path";

export interface WindowState {
  width: number;
  height: number;
  x?: number;
  y?: number;
  maximized: boolean;
}

const DEFAULT_STATE: WindowState = {
  width: 1280,
  height: 800,
  maximized: false,
};

function stateFile(dataDir: string): string {
  return path.join(dataDir, "window-state.json");
}

export function loadWindowState(dataDir: string): WindowState {
  try {
    const raw = fs.readFileSync(stateFile(dataDir), "utf-8");
    const parsed = JSON.parse(raw) as Partial<WindowState>;
    const state: WindowState = {
      width: Math.max(parsed.width ?? DEFAULT_STATE.width, 900),
      height: Math.max(parsed.height ?? DEFAULT_STATE.height, 600),
      maximized: parsed.maximized === true,
    };
    // 位置校验：显示器可能变了，不可见的位置直接丢弃让系统居中
    if (
      typeof parsed.x === "number" &&
      typeof parsed.y === "number" &&
      isVisibleOnSomeDisplay(parsed.x, parsed.y, state.width, state.height)
    ) {
      state.x = parsed.x;
      state.y = parsed.y;
    }
    return state;
  } catch {
    return { ...DEFAULT_STATE };
  }
}

export function saveWindowState(dataDir: string, win: BrowserWindow): void {
  if (win.isDestroyed()) return;
  const isMaximized = win.isMaximized();
  // 最大化时保存普通状态下的尺寸，恢复时才 maximize
  const bounds = isMaximized ? win.getNormalBounds() : win.getBounds();
  const state: WindowState = {
    width: bounds.width,
    height: bounds.height,
    x: bounds.x,
    y: bounds.y,
    maximized: isMaximized,
  };
  try {
    fs.mkdirSync(dataDir, { recursive: true });
    fs.writeFileSync(stateFile(dataDir), JSON.stringify(state));
  } catch (err) {
    console.warn("Failed to save window state:", err);
  }
}

/** 最大化/还原时跟踪状态，退出前由 close 处理器统一落盘. */
export function trackWindowState(win: BrowserWindow): void {
  win.on("maximize", () => saveSoon(win));
  win.on("unmaximize", () => saveSoon(win));
}

let saveTimer: NodeJS.Timeout | null = null;
let trackedWin: BrowserWindow | null = null;

function saveSoon(win: BrowserWindow) {
  trackedWin = win;
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    if (trackedWin && !trackedWin.isDestroyed()) {
      saveWindowState(getDefaultDataDirForState(), trackedWin);
    }
  }, 500);
}

function getDefaultDataDirForState(): string {
  return path.join(app.getPath("userData"), "jmcomic-electron");
}

function isVisibleOnSomeDisplay(
  x: number,
  y: number,
  width: number,
  height: number,
): boolean {
  return screen.getAllDisplays().some((display) => {
    const area = display.workArea;
    // 窗口至少要在屏幕工作区内露出 100x100
    return (
      x + width > area.x + 50 &&
      x < area.x + area.width - 50 &&
      y + height > area.y + 50 &&
      y < area.y + area.height - 50
    );
  });
}
