# JMComic-electron

基于 Electron + Vue 3 + TypeScript 的桌面漫画阅读客户端，后端复用并改造原 JMComic-qt 的 Python 逻辑。

> 本项目是 JMComic-qt 的重写版本，完全弃用 Qt/PySide6，保留 Python 后端（FastAPI 服务化）用于网络请求、下载、图片处理和本地数据管理。

## 技术栈

| 层级 | 选型 |
|---|---|
| 前端 | Electron + Vite + Vue 3 + TypeScript |
| UI | Tailwind CSS |
| 状态 | Pinia |
| 后端 | FastAPI + uvicorn（`backend/.venv`） |
| JM 加密 | jmcomic 库（token 生成 + AES-ECB 响应解密） |
| 图片/CPU | Pillow（反分割）、sr_vulkan（超分，可选） |
| 持久化 | sqlite3 + YAML 配置 |
| 打包 | electron-builder + PyInstaller（onedir） |

## 开发

```bash
pnpm install        # 装前端依赖 + 创建 backend/.venv
pnpm dev            # Vite + Electron（主进程自动拉起后端）
pnpm test           # 后端 pytest
pnpm build          # 构建 electron 主进程 + 渲染层
```

## 打包

```bash
pnpm dist:mac       # macOS dmg
pnpm dist:win       # Windows nsis
pnpm dist:linux     # Linux AppImage/deb
```

流程：`build` → `build:backend`（PyInstaller 把 FastAPI 打成 onedir 到 `backend_dist/`）→ electron-builder 通过 `extraResources` 把 `backend_dist` 与托盘图标打进安装包。

## 功能与进度

Phase 0-6 全部完成：浏览/搜索/分类/评论 → 阅读器（反分割、翻页/滚动、进度恢复）→ 登录/收藏/历史/下载队列 → 本地图库（离线阅读）/代理/DNS 工具 → 单实例/托盘/窗口状态持久化/三平台安装包。文档索引见 [`docs/README.md`](docs/README.md)（架构、API、JM 适配笔记、打包发布、CHANGELOG）。

## 参考项目

- 原项目：`/Users/fish/Code/lijiayu/JMComic-qt`
- 核心需参考文件：
  - `src/server/req.py`：JM API 请求构建
  - `src/tools/tool.py`：图片解析与反分割
  - `src/task/task_download.py`：下载状态机
  - `src/task/task_local.py`：本地图库扫描
  - `src/task/task_upload.py`：NAS 上传
