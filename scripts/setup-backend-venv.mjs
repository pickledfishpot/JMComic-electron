/**
 * 创建 backend/.venv 并安装后端依赖（postinstall 钩子）。
 * 跨平台：Windows 用 Scripts/python.exe，POSIX 用 bin/python。
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const backendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../backend");
const isWin = process.platform === "win32";
const venvDir = path.join(backendDir, ".venv");
const venvPython = path.join(
  venvDir,
  isWin ? "Scripts/python.exe" : "bin/python",
);

function run(cmd, args, cwd) {
  const result = spawnSync(cmd, args, { cwd, stdio: "inherit" });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

if (!fs.existsSync(venvPython)) {
  run(isWin ? "python" : "python3", ["-m", "venv", ".venv"], backendDir);
}

// 装 dev extra：PyInstaller(打包)与 pytest(测试)都在里面
run(venvPython, ["-m", "pip", "install", "-e", ".[dev]"], backendDir);
