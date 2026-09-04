# 打包与发布

> 打包链路、CI Release 流程、版本号规则与线上排障入口。

## 1. 打包链路

1. **Python 后端**：`scripts/build-backend.mjs` 调用 `backend/.venv` 里的 PyInstaller 6 `onedir` 模式，入口 `backend/pyinstaller_entry.py`；`--collect-all jmcomic curl_cffi` 收集数据文件与原生库，显式 hidden-import uvicorn 各协议子模块 / pydantic_settings / yaml；产物落 `backend_dist/jmcomic_backend/`（约 61MB），并删除 `lib2to3`/`tkinter` 等无用目录
2. **后端冒烟**：`scripts/smoke-backend.mjs` 直接运行冻结尾 `--host 127.0.0.1 --port 18555 --data-dir <tmp>` 并探活 `/api/health`（60s），失败 exit 1——把"后端在目标平台起不来"暴露在构建期
3. **Electron**：`pnpm run build`（tsc 主进程 + vite 渲染层）→ `electron-builder`；`electron-builder.yml` 的 `extraResources` 把 `backend_dist` 整体放入 `resources/backend_dist`；三平台图标在 `resources/icons/`

### 渲染层资源路径（白屏教训）

渲染层打包后走 `file://` 加载，`vite.config.ts` 必须保持 `base: "./"`——默认 `/` 会让产物引用 `/assets/*` 绝对路径，解析到文件系统根目录导致 JS/CSS 404 白屏（v0.1.1 修过）。路由用 `createWebHashHistory`，与 file:// 兼容。

### pnpm 11 注意

overrides 写在 `pnpm-workspace.yaml`（`@electron/get` 需 ^3.1.0，否则 electron-builder 报 `ElectronDownloadCacheMode` undefined）。

## 2. CI 与 Release 流程（.github/workflows/dist.yml）

- **触发**：`workflow_dispatch`（手动，仅出 artifacts）+ `push tags v*`（自动构建并发 **草稿** Release，人工核对后发布）；main push 不触发
- **版本号同步**：打 tag 时 CI 先跑 `pnpm version "${GITHUB_REF_NAME#v}" --no-git-tag-version`——electron-builder 的产物文件名读 package.json 的 version，**不读 git tag**。v0.1.1 曾因不同步导致产物还叫 `JMComic-0.1.0-win.zip`
- **矩阵**：当前仅 windows-latest（zip 产物）；mac/linux 步骤已注释保留
- **Release 资产**：单层 glob（`dist/installers/*.zip` 等），**不能** `dist/installers/**`——会把 `win-unpacked/` 整目录几百个文件传上去
- **Windows 产物当前仅 zip**（nsis/portable 在 electron-builder.yml 中注释保留）

发版操作：

```bash
git push origin main          # 先推 main
git tag v0.1.2 && git push origin v0.1.2   # 再打 tag，CI 自动构建+草稿 Release
```

## 3. 运行时数据目录与日志（排障入口）

数据目录 = `app.getPath("userData")/jmcomic-electron`，由 Electron 通过 `--data-dir` 传给后端（禁止写死路径）：

| 平台 | 路径 |
|---|---|
| Windows | `%APPDATA%\JMComic\jmcomic-electron` |
| macOS | `~/Library/Application Support/JMComic/jmcomic-electron` |
| Linux | `~/.config/JMComic/jmcomic-electron` |

| 内容 | 位置 |
|---|---|
| 后端启动日志（含导入期崩溃） | `logs/backend-stdout.log`（主进程环形缓冲 + 追加写入） |
| 后端自身日志 | `logs/backend.log`（FastAPI lifespan 初始化后才有） |
| SQLite | `db/app.db`（download_tasks / read_history） |
| 会话 | `session.json` |
| 图片缓存 | `cache/images/` |
| 下载产物 | `downloads/{book_id}/{章节:03d}/` |

启动失败排查顺序：splash 错误文本（多行 pre-wrap）→ `backend-stdout.log` → CI 冒烟日志。

## 4. 原生外壳

- 单实例锁（`requestSingleInstanceLock` + second-instance 聚焦）
- 系统托盘：关闭到托盘，托盘菜单退出
- 窗口状态持久化 `window-state.json`
- 退出时 SIGTERM/SIGKILL 进程组结束后端
