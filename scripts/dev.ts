/**
 * Dev script: starts Vite renderer dev server and Electron.
 * In dev mode the Electron main process spawns the backend itself.
 */
import { spawn, spawnSync } from 'node:child_process';
import { createServer } from 'vite';
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

  // 选定后端端口并写入环境变量：vite 代理配置与 Electron 启动的后端使用同一端口
  process.env.JMCOMIC_BACKEND_PORT = String(await findFreePort());

  const vite = await createServer({
    configFile: path.resolve(__dirname, '..', 'vite.config.ts'),
  });
  await vite.listen();

  const electron = spawn(
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

  electron.on('close', () => {
    tscWatch.kill();
    vite.close().then(() => process.exit(0));
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
