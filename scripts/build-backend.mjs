/**
 * 用 PyInstaller 把 FastAPI 后端打成 onedir 可执行产物（backend_dist/jmcomic_backend/）。
 * 产物由 electron-builder 通过 extraResources 打进安装包。
 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const backendDir = path.join(root, "backend");
const venvPython =
  process.platform === "win32"
    ? path.join(backendDir, ".venv", "Scripts", "python.exe")
    : path.join(backendDir, ".venv", "bin", "python");

if (!fs.existsSync(venvPython)) {
  console.error(`backend venv not found: ${venvPython}`);
  console.error("请先运行 pnpm install（postinstall 会创建 venv）");
  process.exit(1);
}

const outDir = path.join(root, "backend_dist");
fs.rmSync(outDir, { recursive: true, force: true });

// 需要显式收集的隐藏导入（反射/懒加载）
const hiddenImports = [
  "uvicorn.logging",
  "uvicorn.loops.auto",
  "uvicorn.protocols.http.auto",
  "uvicorn.protocols.websockets.auto",
  "uvicorn.lifespan.on",
  "jmcomic",
  "curl_cffi",
  "pydantic_settings",
  "yaml",
];

const args = [
  "-m",
  "PyInstaller",
  "--noconfirm",
  "--clean",
  "--onedir",
  "--name",
  "jmcomic_backend",
  "--distpath",
  outDir,
  "--workpath",
  path.join(backendDir, "build"),
  "--specpath",
  backendDir,
  ...hiddenImports.flatMap((m) => ["--hidden-import", m]),
  "--collect-all",
  "jmcomic",
  "--collect-all",
  "curl_cffi",
  path.join(backendDir, "pyinstaller_entry.py"),
];

console.log(`> ${venvPython} ${args.join(" ")}`);
const result = spawnSync(venvPython, args, {
  cwd: backendDir,
  stdio: "inherit",
});

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}

// 瘦身：删掉 PyInstaller 产物里用不到的巨型目录（测试/类型检查等）
const prune = [
  "lib2to3",
  "test",
  "tests",
  "idlelib",
  "tkinter",
  "turtledemo",
  "lib-dynload/tkinter*",
];
const distLib = path.join(outDir, "jmcomic_backend", "_internal");
for (const entry of fs.readdirSync(distLib)) {
  if (prune.some((p) => entry === p || entry.startsWith(p))) {
    fs.rmSync(path.join(distLib, entry), { recursive: true, force: true });
  }
}

const exe = path.join(
  outDir,
  "jmcomic_backend",
  process.platform === "win32" ? "jmcomic_backend.exe" : "jmcomic_backend",
);
console.log(`backend built: ${exe}`);
