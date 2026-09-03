# JMComic-electron

基于 Electron + React + TypeScript 的桌面漫画阅读客户端，后端复用并改造原 JMComic-qt 的 Python 逻辑。

> 本项目是 JMComic-qt 的重写版本，完全弃用 Qt/PySide6，保留 Python 后端用于网络请求、下载、图片处理和本地数据管理。

## 项目状态

当前处于**调研与架构设计阶段**。详细的可行性分析、技术选型和实施计划见 [`docs/architecture.md`](docs/architecture.md)。

## 技术栈

| 层级 | 选型 |
|---|---|
| 前端 | Electron + Vite + React + TypeScript |
| UI | shadcn/ui + Tailwind CSS |
| 状态 | Zustand + TanStack Query |
| 后端 | FastAPI + uvicorn |
| HTTP 客户端 | curl_cffi（复用原项目） |
| 图片/CPU | Pillow、multiprocessing、sr_vulkan |
| 持久化 | sqlite3 + configparser |
| 打包 | electron-builder + PyInstaller（onedir） |

## 开发计划

1. **Phase 0**: 搭建脚手架（Vite+React+Electron、FastAPI、IPC、健康检查）
2. **Phase 1**: 移植网络层，实现首页/搜索/分类/书籍详情/评论
3. **Phase 2**: 阅读器（图片拉取/反分割、多种阅读模式、快捷键）
4. **Phase 3**: 用户、收藏、历史、下载管理
5. **Phase 4**: Waifu2x、本地图库、NAS、工具
6. **Phase 5**: 原生外壳与跨平台打包

详见 [`docs/architecture.md`](docs/architecture.md)。

## 参考项目

- 原项目：`/Users/fish/Code/lijiayu/JMComic-qt`
- 核心需参考文件：
  - `src/server/req.py`：JM API 请求构建
  - `src/server/server.py`：请求调度线程池
  - `src/tools/tool.py`：图片解析与反分割
  - `src/tools/book.py`：书籍数据模型
  - `src/task/task_download.py`：下载状态机
