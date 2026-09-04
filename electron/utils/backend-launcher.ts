import { app } from "electron";
import path from "node:path";
import { spawn, ChildProcess } from "node:child_process";
import fs from "node:fs";
import fsp from "node:fs/promises";
import { createWriteStream, type WriteStream } from "node:fs";

export interface BackendLauncherOptions {
  port: number;
  dataDir: string;
}

/** 启动后的后端句柄：进程引用 + 崩溃诊断信息 */
export interface LaunchedBackend {
  child: ChildProcess;
  /** 最近的 stdout/stderr 输出（环形缓冲，最近 200 行），用于崩溃诊断 */
  recentOutput: () => string;
  /** 进程已退出时返回 "exit code=..., signal=..."，仍在运行时返回 null */
  exitInfo: () => string | null;
}

const MAX_OUTPUT_LINES = 200;

function getPythonExecutable(): string {
  const isDev = !app.isPackaged;
  if (isDev) {
    const venvPython =
      process.platform === "win32"
        ? path.join(process.cwd(), "backend", ".venv", "Scripts", "python.exe")
        : path.join(process.cwd(), "backend", ".venv", "bin", "python");
    return venvPython;
  }
  const prodExe =
    process.platform === "win32"
      ? path.join(
          process.resourcesPath,
          "backend_dist",
          "jmcomic_backend",
          "jmcomic_backend.exe",
        )
      : path.join(
          process.resourcesPath,
          "backend_dist",
          "jmcomic_backend",
          "jmcomic_backend",
        );
  return prodExe;
}

function getBackendCwd(): string {
  const isDev = !app.isPackaged;
  if (isDev) {
    return path.join(process.cwd(), "backend");
  }
  return path.join(process.resourcesPath, "backend_dist", "jmcomic_backend");
}

export async function startBackend(
  options: BackendLauncherOptions,
): Promise<LaunchedBackend> {
  const { port, dataDir } = options;
  await fsp.mkdir(dataDir, { recursive: true });

  const isDev = !app.isPackaged;
  const cmd = getPythonExecutable();

  // 先做存在性检查：backend_dist 缺失/平台不匹配时立即给出明确报错，
  // 而不是 spawn 失败后干等 30 秒报一个误导性的 health check 失败
  if (!fs.existsSync(cmd)) {
    throw new Error(
      `后端可执行文件不存在: ${cmd}。` +
        (isDev
          ? "请先运行 pnpm install 创建 backend/.venv。"
          : "安装包可能不完整（backend_dist 缺失）或与当前平台不匹配，请重新下载对应平台的安装包。"),
    );
  }

  // Dev: run the Python module directly so it can parse custom CLI args like --data-dir.
  // Prod: PyInstaller onedir executable takes the same args directly (frozen entry).
  const args = [
    "--host",
    "127.0.0.1",
    "--port",
    String(port),
    "--data-dir",
    dataDir,
  ];
  const fullArgs = isDev ? ["-m", "jmcomic_backend.main", ...args] : args;

  const child = spawn(cmd, fullArgs, {
    cwd: getBackendCwd(),
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      JMCOMIC_DATA_DIR: dataDir,
    },
    // macOS/Linux: start in new process group so we can kill the whole tree
    detached: process.platform !== "win32",
    windowsHide: true,
  });

  // 等 spawn/error 事件二选一：spawn 失败（exe 缺失/被拦截等）在这里立刻抛出。
  // 不能用 Promise.race([spawnError, Promise.resolve(child)])——child 已 settle 恒赢，
  // spawn 错误会被吞掉
  await new Promise<void>((resolve, reject) => {
    child.once("error", (err) => {
      reject(
        new Error(
          `后端进程启动失败 (${cmd}): ${err.message}。` +
            "若发生在打包环境，可能是安装包不完整或杀毒软件拦截了后端程序。",
        ),
      );
    });
    child.once("spawn", () => resolve());
  });

  // 捕获后端输出：环形缓冲供崩溃诊断，同时追加写入 dataDir/logs/backend-stdout.log。
  // 后端自身的 logging 要到 FastAPI lifespan 才初始化，导入期崩溃只能靠这里兜底。
  const lines: string[] = [];
  let exitInfo: string | null = null;
  let logStream: WriteStream | null = null;
  try {
    const logDir = path.join(dataDir, "logs");
    await fsp.mkdir(logDir, { recursive: true });
    logStream = createWriteStream(path.join(logDir, "backend-stdout.log"), {
      flags: "a",
    });
  } catch {
    // 日志文件创建失败不影响启动
  }
  const record = (chunk: Buffer) => {
    const text = chunk.toString("utf8");
    for (const line of text.split("\n")) {
      const trimmed = line.endsWith("\r") ? line.slice(0, -1) : line;
      if (!trimmed) continue;
      lines.push(trimmed);
      if (lines.length > MAX_OUTPUT_LINES) lines.shift();
    }
    logStream?.write(text);
  };
  child.stdout?.on("data", record);
  child.stderr?.on("data", record);
  child.once("exit", (code, signal) => {
    exitInfo = `exit code=${code ?? "null"} signal=${signal ?? "null"}`;
    logStream?.end();
  });

  return {
    child,
    recentOutput: () => lines.join("\n"),
    exitInfo: () => exitInfo,
  };
}

export async function stopBackend(child: ChildProcess | null): Promise<void> {
  if (!child) return;

  return new Promise((resolve) => {
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      resolve();
    };
    const timeout = setTimeout(() => {
      if (process.platform === "win32") {
        child.kill("SIGKILL");
      } else {
        try {
          process.kill(-child.pid!, "SIGKILL");
        } catch {
          child.kill("SIGKILL");
        }
      }
      done();
    }, 5000);

    // 以 exit 事件为准：child.killed 只表示信号已送达，进程可能仍在运行
    child.once("exit", done);

    if (child.exitCode !== null || child.signalCode !== null) {
      done();
      return;
    }

    if (process.platform === "win32") {
      child.kill("SIGTERM");
    } else {
      try {
        process.kill(-child.pid!, "SIGTERM");
      } catch {
        child.kill("SIGTERM");
      }
    }
  });
}

export function getDefaultDataDir(): string {
  const base = app.getPath("userData");
  return path.join(base, "jmcomic-electron");
}

export async function findFreePort(start = 18500): Promise<number> {
  const net = await import("node:net");
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(start, "127.0.0.1", () => {
      const address = server.address();
      const port =
        typeof address === "object" && address ? address.port : start;
      server.close(() => resolve(port));
    });
    server.on("error", (err: Error & { code?: string }) => {
      if (err.code === "EADDRINUSE") {
        findFreePort(start + 1).then(resolve, reject);
      } else {
        reject(err);
      }
    });
  });
}

export async function waitForBackend(
  port: number,
  launched: LaunchedBackend,
  timeoutMs = 30000,
): Promise<void> {
  const { child } = launched;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    // 后端已退出：立刻失败并带上退出码与最近输出，不等满 30 秒
    const exited =
      launched.exitInfo() ??
      (child.exitCode !== null || child.signalCode !== null
        ? `exit code=${child.exitCode} signal=${child.signalCode}`
        : null);
    if (exited) {
      throw new Error(
        `后端进程启动后立即退出 (${exited})。最近输出:\n` +
          `${launched.recentOutput() || "(无输出)"}`,
      );
    }
    try {
      const res = await fetch(`http://127.0.0.1:${port}/api/health`, {
        signal: AbortSignal.timeout(1000),
      });
      if (res.ok) return;
    } catch {
      // ignore
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(
    `Backend health check failed on port ${port}（${timeoutMs / 1000}s 超时）。` +
      `进程状态: ${launched.exitInfo() ?? "仍在运行但未监听端口"}。最近输出:\n` +
      `${launched.recentOutput() || "(无输出)"}\n` +
      "完整日志见数据目录 logs/backend-stdout.log；" +
      "若进程存活但无输出，可能是杀毒软件拦截了后端程序。",
  );
}
