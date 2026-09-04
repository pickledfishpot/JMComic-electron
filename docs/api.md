# 后端 API 与通信协议

> 本文档列出 FastAPI 后端的完整 API 表面与前端的通信约定。路由代码在 `backend/jmcomic_backend/api/routes/`。

## 1. 通用约定

- 基础路径：`/api`，JSON 请求/响应
- 会话：单用户桌面应用，登录态为 JM 返回的 cookies，持久化到 `data_dir/session.json`，请求由后端自动携带；**不使用 Cookie/Header 鉴权**
- CORS：白名单制——打包后渲染层走 `file://`（Origin 为 `null`），dev 走 vite 代理同源；**不要改回正则全放开**（任意网页可驱动本机后端）
- 错误码：401 = 未登录/登录态失效；502 = JM 上游故障（前端提示"服务器不稳定"）；JM 服务器抖动由 `JmClient` 内置 3 次重试兜底

## 2. 认证（auth.py）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/login` | body `{username, password}`；成功 `{user}`，401 = 账号密码错误；登录后 cookies 写 `session.json` |
| POST | `/api/auth/logout` | 清除会话 |
| POST | `/api/auth/register` | 走 web 主站 `/signup` + toastr 解析；需先拿验证码 |
| GET | `/api/auth/captcha` | 验证码图片（点击刷新），暂存注册用 cookie |
| GET | `/api/auth/me` | `{user: {...} \| null}` |

## 3. 书籍 / 目录（books.py / index.py / categories.py）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/books/{book_id}` | 详情（已含 eps 列表，不再单列 `/eps`） |
| GET | `/api/books/{book_id}/eps/{eps_index}/pages` | `{epsId, scrambleId, pages:[{index, name, url}]}`，url 已带 `scramble_id` |
| GET | `/api/books/{book_id}/progress` | `{progress: {epsIndex, pageIndex, updatedAt} \| null}` |
| PUT | `/api/books/{book_id}/progress` | body `{epsIndex, pageIndex, title?}`（title 供历史页展示） |
| GET | `/api/index` | 首页推荐 |
| GET | `/api/latest?page=` | 最新更新 |
| GET | `/api/week/categories` / `/api/week/filter` | 每周必看 |
| GET | `/api/search?q=&page=&sort=` | 搜索，sort ∈ mr/mv/mp/tf |
| GET | `/api/categories` / `/api/categories/{slug}/books` | 分类 |

## 4. 收藏 / 历史 / 评论（favorites.py / history.py / comments.py）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/favorites?page=&sort=&folderId=` | 需登录（401 = 未登录）→ `{total, count, books, folders}` |
| POST | `/api/favorites` | body `{bookId}`，切换收藏状态 |
| POST | `/api/favorites/folders` | 新建收藏夹 |
| DELETE | `/api/favorites/folders/{fid}` | 删除收藏夹 |
| POST | `/api/favorites/move` | body `{bookId, folderId}` |
| GET | `/api/history?page=&pageSize=` | 本地阅读历史（`read_history` 表，倒序） |
| DELETE | `/api/history/{book_id}` | 删除一条历史 |
| GET | `/api/books/{book_id}/comments?page=` | 评论列表 |
| POST | `/api/books/{book_id}/comments` | 发评论 |

未登录判断：上游 `JmApiError.is_auth_error`（`code==401` 优先，文案匹配兜底）→ 路由映射 401。

## 5. 图片（images.py）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/images/{path:path}` | 代理远端图床图片，返回原始字节 |
| GET | `/api/images/{path:path}?scramble_id=` | 阅读器图片，按 JM 规则反分割后返回（算法见 [jm-notes.md](./jm-notes.md)） |

反分割结果缓存到 `data_dir/cache/images`（sha1 命名 + `.meta` 记录 content-type）；同图并发经 `lock_for` single-flight 只拉取一次；响应带 `Cache-Control: max-age=86400` 供浏览器 HTTP 缓存（前端预加载依赖它）。

## 6. 下载（downloads.py）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/downloads` | 任务列表（每章一个任务） |
| POST | `/api/downloads/start` | body `{bookId, epsIndexes?, bookTitle?}`，epsIndexes 缺省 = 全部章节 |
| POST | `/api/downloads/{id}/pause` / `resume` / `retry` | 状态切换 |
| DELETE | `/api/downloads/{id}` | 删除任务并删除已下载文件 |

实现要点（`services/download_manager.py`）：

- 任务持久化 `download_tasks` 表；worker 单循环串行执行，任务内 4 并发拉页
- 逐页反分割写入 `download_dir/{book_id}/{章节:03d}/{页:04d}.{ext}`；先写 `.part` 临时文件再原子替换（截断文件不会被当成已完成）
- 已存在的页自动跳过（重试 = 断点续传）；进程重启后 downloading 任务自动重新排队
- `remove()` 的后台目录删除登记 future，重建同目录任务时 `_run_task` 先等删除完成（防边删边写竞态）；只有活跃任务才进 `_cancelled` 取消集合

## 7. 本地图库 / 工具（local.py / tools.py）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/local/scan` | 扫描 downloads 与设置 `local.dirs` 中的额外目录 |
| GET | `/api/local/books` | 本地书籍列表；支持目录本（子目录各成一话）、zip/cbz 压缩本（内部图片最多的一组为一话） |
| GET | `/api/local/books/{id}` / `.../eps/{idx}/pages` | 分页结构与远端一致，url 指向 `/api/local/images/...` |
| GET | `/api/local/images/{book_id}/{eps_index}/{page_index}` | 本地文件/zip 内图片原始字节 |
| GET/PUT | `/api/local/books/{id}/progress` | 复用 read_history 表，book_id 加 `local:` 前缀（普通历史页过滤该前缀） |
| GET | `/api/tools/waifu2x/status` | sr_vulkan 懒加载探测，不可用时 `available=false`，前端隐藏入口 |
| POST | `/api/tools/waifu2x/convert` | 超分；引擎不可用返回 503；全局串行锁 + 120s 超时 |
| POST | `/api/tools/dns/resolve` | DNS 解析（getaddrinfo） |
| GET | `/api/tools/proxy/test` | 代理连通性测试（使用设置中的代理配置） |

## 8. 设置 / 健康检查（settings.py / health.py）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/settings` | 读取 config.yaml（proxy / network / reader / local.dirs） |
| PUT | `/api/settings` | 保存并即时生效代理（写入 JmClient 全局默认代理，http/https/socks5 取第一个非空） |
| GET | `/api/health` | Electron 主进程启动后轮询此接口确认后端就绪 |

## 9. WebSocket（ws.py / event_bus.py）

`WS /ws` JSON 事件流。异步任务（如下载进度）通过 `event_bus.py` 发布、WebSocket 广播给前端。事件携带任务标识，前端据此更新进度 UI。后端服务层保持无状态，会话经依赖注入 `deps.py` 获取。

## 10. 二进制图片流（阅读器以外的大图场景）

1. 前端 `POST /api/images/fetch` 请求图片
2. 后端通过 `curl_cffi` 下载，按需反分割，缓存字节，返回 `{imageId, contentType, width, height}`
3. 前端渲染 `<img src="/api/images/{imageId}">`
4. 图片离开预加载窗口后，前端 `DELETE /api/images/{imageId}` 释放内存
