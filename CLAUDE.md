@AGNETS.md

## 项目阶段

- Phase 0 ✅ 脚手架：Electron + Vue 3 + Vite + FastAPI，已 init commit。
- Phase 1 ✅ 最小闭环：移植 `req.py/server.py/tool.py` 到 `backend/jmcomic_backend/services/jm_client.py`，实现 `/api/index` 首页推荐、`/api/books/{id}` 书籍详情、`/api/images/{path}` 图片代理；前端首页与书籍详情页可浏览。
- Phase 2 ✅ 搜索/分类/评论：`/api/search`、`/api/categories`、`/api/books/{id}/comments` 及对应前端页面。
- Phase 3 ✅ 阅读器与图片反分割：`services/deslice.py` 移植 tool.py 反分割算法（Pillow），`/api/books/{id}/eps/{idx}/pages` 章节分页（内含 scramble_id），图片代理支持 `?scramble_id=` 反分割并缓存到 `cache/images`；阅读进度存 SQLite（`db/app.db` 的 `read_history` 表），`GET/PUT /api/books/{id}/progress` 读写；前端 `ReadView.vue` 支持翻页/滚动模式、键盘快捷键（←/→/Esc/F/M）、进度条、预加载与失败重试。
- Phase 4 ✅ 用户/收藏/下载：`services/session.py` cookie 会话持久化（`session.json`），JmClient 自动注入 Cookie 头；`/api/auth/login|logout|me|captcha|register`；`/api/favorites`（列表/切换/收藏夹）；`/api/history` 本地历史（`read_history` 表含 title）；`services/download_manager.py` 下载队列（`download_tasks` 表 + 单 worker 串行 + 任务内 4 并发 + 逐页反分割落盘 `downloads/{book_id}/{章节}/{页}`，暂停/恢复/重试=断点续传/删除）。前端 LoginView/FavoritesView/HistoryView/DownloadsView + user store + 详情页收藏/下载按钮。
- Phase 5 ⏳ 超分/本地/NAS/工具。

## 关键约定

- 后端目录为 `backend/`，使用 `backend/.venv`。
- 数据目录由 Electron 通过 `--data-dir` 传入，禁止硬编码。
- 图片统一走 `GET /api/images/{path:path}` 代理，不直接暴露远端图床 URL 给前端。
- JM 服务器不稳定，`JmClient` 已内置 3 次重试；连续失败后由上层返回 502，前端需提示用户。
- 使用 `jmcomic` 库进行 token 生成与响应解密（AES-ECB）。
