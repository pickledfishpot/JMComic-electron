/**
 * Dev script: starts Vite renderer dev server and Electron.
 * In dev mode the Electron main process spawns the backend itself.
 */
import { spawn, spawnSync } from 'node:child_process';
import { createServer, type ViteDevServer } from 'vite';
import net from 'node:net';
import path from 'node:path';

const tscBin = path.resolve(__dirname, '..', 'node_modules/.bin/tsc');
const tscArgs = ['-p', path.resolve(__dirname, '..', 'electron/tsconfig.json')];

function findFreePort(start = 18500): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = (port: number) => {
      const server = net.createServer();
      server.once('error', () => probe(port + 1));
      server.once('listening', () => {
        server.close(() => resolve(port));
      });
      server.listen(port, '127.0.0.1');
    };
    probe(start);
  });
}

async function main() {
  // Electron 主进程是 TypeScript，必须先编译出 dist/electron/main.js
  const build = spawnSync(tscBin, tscArgs, { stdio: 'inherit' });
  if (build.status !== 0) {
    process.exit(build.status ?? 1);
  }
  const tscWatch = spawn(tscBin, [...tscArgs, '--watch'], { stdio: 'inherit' });

  let vite: ViteDevServer | null = null;
  let electron: ReturnType<typeof spawn> | null = null;
  let shuttingDown = false;

  const cleanup = async (code: number) => {
    if (shuttingDown) return;
    shuttingDown = true;
    tscWatch.kill();
    electron?.kill();
    if (vite) await vite.close();
    process.exit(code);
  };

  // 信号只到达父进程时兜底清理（Ctrl+C 等），避免 tsc --watch 成为孤儿
  process.on('SIGINT', () => void cleanup(0));
  process.on('SIGTERM', () => void cleanup(0));

  try {
    // 选定后端端口并写入环境变量：vite 代理配置与 Electron 启动的后端使用同一端口
    process.env.JMCOMIC_BACKEND_PORT = String(await findFreePort());

    vite = await createServer({
      configFile: path.resolve(__dirname, '..', 'vite.config.ts'),
    });
    await vite.listen();

    electron = spawn(
      path.resolve(__dirname, '..', 'node_modules/.bin/electron'),
      ['.', '--remote-debugging-port=9223'],
      {
        stdio: 'inherit',
        env: {
          ...process.env,
          NODE_ENV: 'development',
        },
      },
    );

    electron.on('close', () => void cleanup(0));
    electron.on('error', (err) => {
      console.error('Failed to start electron:', err);
      void cleanup(1);
    });
  } catch (err) {
    // 启动失败（如 5173 被占用）也要清理已拉起的 tsc --watch
    console.error(err);
    await cleanup(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
