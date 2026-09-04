# JMComic-electron 架构设计

> 总体架构与移植设计。详细子文档：[api.md](./api.md)（后端 API 与通信协议）、
> [jm-notes.md](./jm-notes.md)（JM 站点加密/反分割规则）、[packaging.md](./packaging.md)（打包发布与排障）、
> [CHANGELOG/](./CHANGELOG/README.md)（版本记录）。

## 1. 背景与可行性结论

原 JMComic-qt 是基于 PySide6 的跨平台桌面漫画阅读客户端。用户目标是：**彻底弃用 Qt 框架，使用 Electron 重写前端，并复用现有 Python 后端逻辑**。

可行性结论：**完全可行**。原项目的 UI 层与业务逻辑层已有一定分离，网络请求、下载管理、图片处理、数据持久化等核心逻辑 mostly 是纯 Python，只需解耦 Qt signal 和 QSettings/QSqlDatabase 后即可作为后端服务复用。

## 2. 原项目分层分析

### 2.1 可复用的后端逻辑

| 模块 | 位置 | 说明 |
|---|---|---|
| API 请求构建 | `src/server/req.py` | 所有 JM 站点请求构建，含 curl_cffi、代理、ECH、URL 切换 |
| 请求调度器 | `src/server/server.py` | 线程池队列（HTTP / 下载 / 测速） |
| 响应解析 | `src/server/res.py`、`user_handler.py` | 解析 HTTP 响应为领域对象 |
| 数据模型 | `src/tools/book.py`、`user.py` | BookInfo、BookEps、User 等 |
| 工具函数 | `src/tools/tool.py` | 图片解析、反分割、ComicInfo XML、URL 工具 |
| 配置 | `src/config/config.py`、`global_config.py` | 常量、远端可覆盖配置 |
| 设置 | `src/config/setting.py` | 用户设置定义（需替换 QSettings） |
| 下载管理 | `src/task/task_download.py` | 下载状态机 |
| 反分割 | `src/task/task_multi.py` | JM 图片反分割多进程处理 |
| 超分 | `src/task/task_waifu2x.py` | sr_vulkan 包装 |
| 本地图库 | `src/task/task_local.py` | 目录/zip 扫描 |
| 数据库 | `src/view/download/download_db.py` 等 | SQLite 表结构 |

### 2.2 必须重写的前端部分

- `src/view/`：约 30 个业务视图页面
- `src/component/`：约 40 个自定义组件
- `src/interface/`：49 个 Qt Designer 生成的 UI 文件
- `src/view/read/`：基于 QGraphicsView 的阅读器引擎
- 原生交互：系统托盘、单实例、剪贴板、文件对话框、无边框窗口

### 2.3 当前异步通信模式

原项目所有后端结果通过 Qt signal 回调：

| Signal | 用途 |
|---|---|
| `taskBack` | HTTP/API 结果 |
| `downloadBack` | 下载进度与最终字节 |
| `downloadStBack` | 下载状态元数据 |
| `convertBack` | Waifu2x 完成 |
| `imageBack` | 解码后的 QImage |
| `localBack` | 本地扫描结果 |
| `localReadBack` | 本地图片字节 |

在 Electron 方案中，这些 signal 替换为 HTTP REST + WebSocket 事件流（协议见 [api.md](./api.md) §9）。

## 3. 推荐技术栈

| 层级 | 选型 | 理由 |
|---|---|---|
| 前端框架 | **Electron + Vite + Vue 3 + TypeScript** | 响应式精准更新、模板语法适合漫画列表与表单 |
| UI 组件 | **Tailwind CSS** | 快速重建对话框、列表、设置表单、暗色/亮色主题 |
| 虚拟滚动 | **vue-virtual-scroller** | 长漫画列表和竖向滚动阅读器 |
| 状态管理 | **Pinia** + **VueUse** | 替代 Qt signal 式异步状态，CRUD 业务写起来更直观 |
| 后端框架 | **FastAPI + uvicorn** | 原生异步、WebSocket、OpenAPI、打包体积小 |
| JM HTTP 客户端 | **curl_cffi**（复用） | 站点模拟 / ECH / 反爬 |
| 图片/CPU | **Pillow**、**ProcessPoolExecutor**、**sr_vulkan** | 复用现有算法和模型 |
| 持久化 | **sqlite3** + **configparser** | 替代 QSettings 和 QSqlDatabase |
| 打包 | **electron-builder** + **PyInstaller（onedir）** | Electron 负责安装包，PyInstaller 打包 Python 为 extraResources |
| E2E 测试 | **Playwright Electron** | 可测试打包后的应用 |

## 4. 项目目录结构

```
JMComic-electron/
├── package.json / electron-builder.yml / vite.config.ts
├── electron/               # 主进程与 preload
│   ├── main.ts             # 应用生命周期、启动 Python、托盘、单实例
│   ├── preload.ts          # contextBridge 安全 IPC
│   └── utils/              # backend-launcher（后端拉起 + 诊断）等
├── renderer/               # Vue 3 前端（Vite 子项目，root 在仓库根的 vite.config.ts）
│   └── src/
│       ├── main.ts / App.vue
│       ├── router/         # createWebHashHistory（file:// 兼容）
│       ├── api/            # fetch + WebSocket 客户端
│       ├── views/          # Home/Search/BookDetail/Read/Downloads/Favorites/...
│       ├── components/     # BookCard, PageHeader, StateBlock 等
│       ├── composables/    # useGoBack 等
│       └── stores/         # Pinia: user 等
├── backend/                # FastAPI Python 后端（.venv）
│   ├── pyproject.toml
│   └── jmcomic_backend/
│       ├── main.py         # FastAPI lifespan + uvicorn 入口（--data-dir 必传）
│       ├── api/
│       │   ├── deps.py     # 依赖注入（会话/设置/缓存）
│       │   ├── ws.py       # WebSocket 事件流
│       │   └── routes/     # auth/books/search/images/downloads/favorites/...
│       ├── core/           # config / settings / paths / logging
│       └── services/       # jm_client / deslice / download_manager /
│                           # image_cache / local_library / waifu2x_service / event_bus
├── resources/              # 图标、托盘资源
├── scripts/                # dev.ts / build-backend.mjs / smoke-backend.mjs
└── tests/
    └── backend/            # pytest（vitest/Playwright 待补）
```

## 5. 复用现有 Python 逻辑的改造点

| 原文件 | 新位置 | 改造 |
|---|---|---|
| `src/server/req.py` | `services/jm_client.py` | 移除 `QtOwner().cookie`，复用 `jmcomic.JmCryptoTool` 生成 token 与解密响应 |
| `src/server/server.py` | 并入 `services/jm_client.py` | 线程池队列改 asyncio + 内置 3 次重试 |
| `src/tools/tool.py` | `services/deslice.py` | 移除 QImage/QPixmap，保留 PIL；反分割规则见 [jm-notes.md](./jm-notes.md) |
| `src/config/setting.py` | `core/settings.py` | QSettings 改为 configparser |
| `src/task/task_download.py` | `services/download_manager.py` | signal 改事件总线 |
| `src/task/task_waifu2x.py` | `services/waifu2x_service.py` | sr_vulkan 懒加载，不可用时前端隐藏 |
| `src/task/task_local.py` | `services/local_library.py` | natsort 用自然排序键替代；signal 改 REST |
| DB 类 | `services/history_db.py` 等 | QSqlDatabase 改为 sqlite3 |

## 6. 实施阶段

| 阶段 | 重点 | 产出 |
|---|---|---|
| **0. 脚手架** ✅ | Vite+Vue3+Electron、FastAPI、IPC、健康检查屏 | 应用启动并连接后端 |
| **1. 最小闭环** ✅ | 移植 req.py/server.py/tool.py，首页推荐/书籍详情/封面图代理 | 可浏览首页与书籍详情 |
| **2. 搜索/分类/评论** ✅ | 搜索/分类/评论 API 与前端页面 | 浏览可用 |
| **3. 阅读器** ✅ | 图片拉取/反分割（PIL 移植 tool.py）、翻页/滚动模式、相邻页预加载、快捷键、进度条、阅读历史 SQLite | 可流畅阅读，进度可恢复 |
| **4. 用户/收藏/下载** ✅ | 登录/注册/验证码、cookie 会话持久化、收藏列表与切换、本地历史、下载队列（SQLite + 反分割落盘 + 暂停/重试） | 下载可持久化 |
| **5. 超分/本地/工具** ✅ | 本地图库（目录本/zip 扫描 + 离线阅读 + 独立进度）、代理接入 JmClient + 代理测试/DNS 工具、Waifu2x 懒加载探测（不可用时隐藏）。NAS 功能已删除 | 高级功能完成 |
| **6. 原生外壳与打包** ✅ | 单实例锁、系统托盘（关闭到托盘）、窗口状态持久化、Pillow 生成三平台图标、PyInstaller 后端打包、electron-builder（当前仅 Windows zip） | 安装包 + tag 发版 |

## 7. 主要风险与缓解

| 风险 | 缓解 |
|---|---|
| `curl_cffi`/libcurl-impersonate 打包后失效 | onedir + `--collect-all` + CI 冒烟测试冻结尾 |
| `sr_vulkan`/Waifu2x GPU 不可用 | 可选功能，导入失败隐藏 UI |
| Electron 大图阅读性能 | lazy loading、相邻页预加载（浏览器 HTTP 缓存 + 后端磁盘缓存） |
| 代理/ECH/SNI 被封 | 保留原请求构建，UI 暴露代理设置与 DNS/代理测试工具 |
| 前后端任务状态漂移 | API 幂等、WS 事件流、下载任务 SQLite 持久化 + 重启重排 |
| 跨平台数据目录 | Electron `app.getPath('userData')` 经 `--data-dir` 传给后端 |
| 单实例聚焦 | `app.requestSingleInstanceLock` + IPC |

## 8. 参考文件

- 原项目路径：`/Users/fish/Code/lijiayu/JMComic-qt`
- 核心参考文件：
  - `src/server/req.py`
  - `src/server/server.py`
  - `src/tools/tool.py`
  - `src/tools/book.py`
  - `src/task/task_download.py`
