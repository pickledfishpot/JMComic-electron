/**
 * CI 冒烟测试：直接运行 PyInstaller 冻结尾后端并探活 /api/health。
 * 把"打包出来的后端在目标平台上起不来"这类问题在构建期暴露，
 * 并把后端 stdout/stderr 打进 workflow 日志，方便定位真实原因。
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const isWin = process.platform === "win32";
const exe = path.join(
  root,
  "backend_dist",
  "jmcomic_backend",
  isWin ? "jmcomic_backend.exe" : "jmcomic_backend",
);

if (!fs.existsSync(exe)) {
  console.error(`SMOKE FAIL: backend exe not found: ${exe}`);
  process.exit(1);
}

const port = 18555;
const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "jmcomic-smoke-"));

console.log(`> ${exe} --host 127.0.0.1 --port ${port} --data-dir ${dataDir}`);
const child = spawn(
  exe,
  ["--host", "127.0.0.1", "--port", String(port), "--data-dir", dataDir],
  { stdio: ["ignore", "pipe", "pipe"] },
);

let output = "";
child.stdout.on("data", (d) => {
  const s = d.toString("utf8");
  output += s;
  process.stdout.write(s);
});
child.stderr.on("data", (d) => {
  const s = d.toString("utf8");
  output += s;
  process.stderr.write(s);
});

function killBackend() {
  if (isWin && child.pid) {
    // Windows 下杀整棵进程树
    spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"]);
  } else {
    child.kill("SIGTERM");
  }
}

const deadline = Date.now() + 60_000;
let ok = false;
while (Date.now() < deadline) {
  if (child.exitCode !== null) break;
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/health`, {
      signal: AbortSignal.timeout(1000),
    });
    if (res.ok) {
      ok = true;
      break;
    }
  } catch {
    // ignore
  }
  await new Promise((r) => setTimeout(r, 500));
}

if (!ok) {
  console.error(
    `SMOKE FAIL: backend health check failed (exitCode=${child.exitCode})`,
  );
  if (!output.trim()) {
    console.error("(后端无任何输出——疑似被杀毒软件拦截或启动即崩溃)");
  }
  killBackend();
  process.exit(1);
}

console.log("SMOKE OK: /api/health reachable");
killBackend();
setTimeout(() => process.exit(0), 1000);
