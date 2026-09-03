/**
 * 交叉打包平台校验：PyInstaller 产物是平台相关的，
 * 在 macOS 上执行 pnpm dist:win 会把 mac 后端二进制塞进 Windows 安装包。
 * 用法：node scripts/assert-platform.mjs <win|mac|linux>
 */
const target = process.argv[2];
const platformMap = { win: 'win32', mac: 'darwin', linux: 'linux' };
const expected = platformMap[target];

if (!expected) {
  console.error(`Unknown platform target: ${target} (expected win|mac|linux)`);
  process.exit(1);
}

if (process.platform !== expected) {
  console.error(
    `Cannot build ${target} installer on ${process.platform}: ` +
      `backend_dist/ contains a ${process.platform} PyInstaller binary, ` +
      `which would be shipped to the wrong platform. ` +
      `Run pnpm dist:${target} on a ${target} machine or in CI with that runner.`,
  );
  process.exit(1);
}
