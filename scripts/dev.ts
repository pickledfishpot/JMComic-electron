/**
 * Dev script: starts Vite renderer dev server and Electron.
 * In dev mode the Electron main process spawns the backend itself.
 */
import { spawn } from 'node:child_process';
import { createServer } from 'vite';
import path from 'node:path';

async function main() {
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
    vite.close().then(() => process.exit(0));
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
