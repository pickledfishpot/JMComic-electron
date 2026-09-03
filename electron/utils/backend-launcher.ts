import { app } from "electron";
import path from "node:path";
import { spawn, ChildProcess } from "node:child_process";
import fs from "node:fs/promises";

export interface BackendLauncherOptions {
  port: number;
  dataDir: string;
}

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
): Promise<ChildProcess> {
  const { port, dataDir } = options;
  await fs.mkdir(dataDir, { recursive: true });

  const isDev = !app.isPackaged;
  const cmd = isDev
    ? path.join(process.cwd(), "backend", ".venv", "bin", "python")
    : getPythonExecutable();

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

  const cwd = getBackendCwd();

  const child = spawn(cmd, fullArgs, {
    cwd,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      JMCOMIC_DATA_DIR: dataDir,
    },
    // macOS/Linux: start in new process group so we can kill the whole tree
    detached: process.platform !== "win32",
    windowsHide: true,
  });

  child.stderr?.on("data", (data: Buffer) => {
    console.error(`[backend stderr] ${data.toString("utf8")}`);
  });

  child.stdout?.on("data", (data: Buffer) => {
    console.log(`[backend stdout] ${data.toString("utf8")}`);
  });

  return child;
}

export async function stopBackend(child: ChildProcess | null): Promise<void> {
  if (!child || child.killed) return;

  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      if (!child.killed) {
        if (process.platform === "win32") {
          child.kill("SIGKILL");
        } else {
          try {
            process.kill(-child.pid!, "SIGKILL");
          } catch {
            child.kill("SIGKILL");
          }
        }
      }
      resolve();
    }, 5000);

    child.on("exit", () => {
      clearTimeout(timeout);
      resolve();
    });

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
  timeoutMs = 30000,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
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
  throw new Error(`Backend health check failed on port ${port}`);
}
