# JMComic-electron 架构设计与实施计划

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
| NAS 上传 | `src/task/task_upload.py` + upload_* | WebDAV/SMB/本地上传 |
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
| `uploadBack` | NAS 上传结果 |

在 Electron 方案中，这些 signal 需要替换为 HTTP REST + WebSocket 事件流。

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
├── package.json / electron-builder.yml / tsconfig.json / vite.config.ts
├── electron/
│   ├── main.ts                 # 应用生命周期、启动 Python、托盘、单实例
│   ├── preload.ts              # contextBridge 安全 IPC
│   └── ipc-handlers/           # 剪贴板、对话框、外部链接、窗口状态
├── renderer/
│   └── src/
│       ├── main.ts
│       ├── App.vue             # 根组件
│       ├── router/             # Vue Router
│       ├── api/                # fetch + WebSocket 客户端
│       ├── views/              # Index, Search, BookInfo, Read, Downloads, ...
│       ├── components/         # ComicCard, ComicList, EpsList, Reader 等
│       ├── composables/        # useBackend, useImage, useTaskEvents
│       ├── stores/             # Pinia: user, settings, downloads, reader
│       ├── types/              # Book, User, Eps, Settings 类型
│       └── styles/
├── backend/
│   ├── pyproject.toml
│   └── jmcomic_backend/
│       ├── main.py             # FastAPI lifespan + uvicorn 入口
│       ├── api/
│       │   ├── deps.py
│       │   ├── ws.py
│       │   └── routes/
│       │       ├── auth.py
│       │       ├── books.py
│       │       ├── search.py
│       │       ├── images.py
│       │       ├── downloads.py
│       │       ├── favorites.py
│       │       ├── comments.py
│       │       ├── history.py
│       │       ├── local.py
│       │       ├── nas.py
│       │       ├── settings.py
│       │       ├── tasks.py
│       │       └── waifu2x.py
│       ├── core/
│       │   ├── config.py
│       │   ├── settings.py     # 替代 QSettings
│       │   ├── global_config.py
│       │   ├── paths.py
│       │   └── logging.py
│       ├── services/
│       │   ├── jm_client.py
│       │   ├── request_dispatcher.py
│       │   ├── response_handlers.py
│       │   ├── book_cache.py
│       │   ├── image_service.py
│       │   ├── download_manager.py
│       │   ├── waifu2x_service.py
│       │   ├── local_library.py
│       │   ├── nas_service.py
│       │   └── event_bus.py
│       ├── tasks/
│       └── db/
│           ├── db_manager.py
│           ├── download_db.py
│           ├── local_favorite_db.py
│           ├── local_read_db.py
│           ├── nas_db.py
│           └── batch_sr_tool_db.py
├── resources/
│   ├── icons/
│   └── tray/
└── tests/
    ├── backend/
    ├── renderer/
    └── e2e/
```

## 5. 后端 API 表面

### 5.1 认证
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/register`
- `GET /api/auth/captcha`
- `GET /api/auth/me`

### 5.2 书籍 / 目录
- `GET /api/books/{book_id}`
- `GET /api/books/{book_id}/eps`
- `GET /api/books/{book_id}/eps/{eps_index}/scramble`
- `GET /api/books/{book_id}/eps/{eps_index}/pages`
- `GET /api/index`
- `GET /api/latest?page=`
- `GET /api/week/categories`
- `GET /api/week/filter`

### 5.3 搜索
- `GET /api/search?q=&page=&sort=`
- `GET /api/categories`
- `GET /api/categories/{slug}/books`

### 5.4 收藏 / 历史 / 评论
- `GET /api/favorites`
- `POST /api/favorites`
- `POST /api/favorites/folders`
- `GET /api/history`
- `GET /api/books/{book_id}/comments`
- `POST /api/books/{book_id}/comments`

### 5.5 图片
- `GET /api/images/{path:path}` → 代理远端图床图片，返回原始字节
- `POST /api/images/fetch` → 返回 `{imageId, contentType, width, height}`
- `POST /api/images/descramble`
- `DELETE /api/images/{imageId}`

### 5.6 下载
- `GET /api/downloads`
- `POST /api/downloads/start`
- `POST /api/downloads/pause`
- `POST /api/downloads/remove`
- `POST /api/downloads/retry`

### 5.7 本地 / NAS / 工具
- `POST /api/local/scan`
- `GET /api/local/books/{id}/pages/{idx}`
- `POST /api/local/progress`
- `CRUD /api/nas`
- `POST /api/nas/{id}/test`
- `POST /api/nas/{id}/upload`
- `POST /api/tools/waifu2x/convert`
- `POST /api/tools/batch-sr`
- `POST /api/tools/dns/resolve`

### 5.8 设置与任务
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/settings/proxy/test`
- `POST /api/settings/speedtest`
- `GET /api/tasks`
- `WS /ws` JSON 事件流

## 6. 通信协议

### 6.1 HTTP
标准 REST + JSON。TanStack Query 负责缓存和重试。

### 6.2 WebSocket
每个异步命令携带客户端生成的 `reqId`（UUID）：

```json
// -> backend
{ "op": "download.start", "reqId": "uuid", "payload": { "bookId": "123", "epsIds": [0,1] } }
// <- backend
{ "op": "download.started", "reqId": "uuid", "taskGroupId": "tg-1" }
```

后续事件携带同一 `taskGroupId` 或 `reqId`：

```json
{ "channel": "task", "type": "progress", "taskId": 42, "reqId": "uuid", "data": {...} }
{ "channel": "download", "type": "epsComplete", "taskGroupId": "tg-1", "bookId": "123", "epsId": 0 }
{ "channel": "convert", "type": "progress", "taskId": 7, "data": { "tick": 1.2 } }
```

### 6.3 二进制图片流
1. 前端 `POST /api/images/fetch` 请求图片。
2. 后端通过 `curl_cffi` 下载，按需反分割，缓存字节，返回 `imageId`。
3. 前端渲染 `<img src="http://localhost:PORT/api/images/{imageId}">`。
4. 图片离开预加载窗口后，前端 `DELETE /api/images/{imageId}` 释放内存。

## 7. 复用现有 Python 逻辑的改造点

| 原文件 | 新位置 | 改造 |
|---|---|---|
| `src/server/req.py` | `services/jm_client.py` | 移除 `QtOwner().cookie`，复用 `jmcomic.JmCryptoTool` 生成 token 与解密响应 |
| `src/server/server.py` | `services/request_dispatcher.py` | 队列池改为 asyncio + ThreadPoolExecutor，signal 改事件总线 |
| `src/server/res.py` + `user_handler.py` | `services/response_handlers.py` | `pickle.dumps` 改为 dict 返回 |
| `src/tools/book.py` | `core/book.py` | 添加 `to_dict()` |
| `src/tools/tool.py` | `core/tool.py` | 移除 QImage/QPixmap，保留 PIL |
| `src/tools/user.py` | `core/user.py` | 添加 `to_dict()` |
| `src/config/setting.py` | `core/settings.py` | QSettings 改为 configparser |
| `src/task/task_download.py` | `services/download_manager.py` | signal 改事件总线 |
| `src/task/task_multi.py` | 保留 | ProcessPoolExecutor 调用 |
| `src/task/task_waifu2x.py` | `services/waifu2x_service.py` | 独立线程/执行器 |
| `src/task/task_local.py` | `services/local_library.py` | 保留扫描逻辑 |
| `src/task/task_upload.py` | `services/nas_service.py` | 保留客户端抽象 |
| DB 类 | `db/*.py` | QSqlDatabase 改为 sqlite3 |

## 8. 打包策略

1. **Python 后端**：PyInstaller `onedir` 模式，隐藏导入 `curl_cffi`、`jmcomic`、`PIL`、`lxml`、`natsort`、`pycryptodomex`、`sr_vulkan`、`sr_vulkan_model_*`、`webdavclient3`、`pysmb`、`smbprotocol`，并打包 `lib/` 原生库。
2. **Electron**：`electron-builder.yml` 配置 `extraResources` 把 Python 产物放入 `backend/`。
3. **运行时**：Electron 主进程找空闲端口，启动后端可执行文件并传入 `--port` 和 `--data-dir`，等待 `/api/health` 后加载渲染进程，退出时 SIGTERM/SIGKILL 结束后端。
4. **目标**：Windows nsis、macOS dmg、Linux AppImage/deb。

## 9. 实施阶段

| 阶段 | 重点 | 产出 |
|---|---|---|
| **0. 脚手架** ✅ | Vite+Vue3+Electron、FastAPI、IPC、健康检查屏 | 应用启动并连接后端 |
| **1. 最小闭环** ✅ | 移植 req.py/server.py/tool.py，首页推荐/书籍详情/封面图代理 | 可浏览首页与书籍详情 |
| **2. 搜索/分类/评论** ✅ | 搜索/分类/评论 API 与前端页面 | 浏览可用 |
| **3. 阅读器** | 图片拉取/反分割、阅读模式、快捷键、历史写入 | 可流畅阅读 |
| **4. 用户/收藏/下载** | 登录/注册/验证码、收藏/历史、下载队列+DB | 下载可持久化 |
| **5. 超分/本地/NAS/工具** | Waifu2x、本地图库、NAS 上传、代理/DNS 工具 | 高级功能完成 |
| **6. 原生外壳与打包** | 托盘、单实例、对话框、主题、安装包 | 三平台安装包 |

## 10. 主要风险与缓解

| 风险 | 缓解 |
|---|---|
| `curl_cffi`/libcurl-impersonate 打包后失效 | onedir + 包含 `lib/` + 各 OS 测试 + requests 回退 |
| `sr_vulkan`/Waifu2x GPU 不可用 | 可选功能，导入失败隐藏 UI |
| Electron 大图阅读性能 | async decoding、lazy loading、虚拟列表、canvas 双页、限制预加载 |
| 代理/ECH/SNI 被封 | 保留原请求构建，UI 暴露全部代理/DoH/ECH/域名切换 |
| 前后端任务状态漂移 | API 幂等、重连对账、WS 事件带 `reqId` |
| 跨平台数据目录 | Electron `app.getPath('userData')` 传给后端 |
| 单实例聚焦 | `app.requestSingleInstanceLock` + IPC |

## 11. 参考文件

- 原项目路径：`/Users/fish/Code/lijiayu/JMComic-qt`
- 核心参考文件：
  - `src/server/req.py`
  - `src/server/server.py`
  - `src/tools/tool.py`
  - `src/tools/book.py`
  - `src/task/task_download.py`
