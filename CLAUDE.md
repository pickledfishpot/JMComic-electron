@AGNETS.md

## 项目阶段

- Phase 0 ✅ 脚手架：Electron + Vue 3 + Vite + FastAPI，已 init commit。
- Phase 1 ✅ 最小闭环：移植 `req.py/server.py/tool.py` 到 `backend/jmcomic_backend/services/jm_client.py`，实现 `/api/index` 首页推荐、`/api/books/{id}` 书籍详情、`/api/images/{path}` 图片代理；前端首页与书籍详情页可浏览。
- Phase 2 ⏳ 搜索/分类/评论。
- Phase 3 ⏳ 阅读器与图片反分割。

## 关键约定

- 后端目录为 `backend/`，使用 `backend/.venv`。
- 数据目录由 Electron 通过 `--data-dir` 传入，禁止硬编码。
- 图片统一走 `GET /api/images/{path:path}` 代理，不直接暴露远端图床 URL 给前端。
- JM 服务器不稳定，`JmClient` 已内置 3 次重试；连续失败后由上层返回 502，前端需提示用户。
- 使用 `jmcomic` 库进行 token 生成与响应解密（AES-ECB）。
