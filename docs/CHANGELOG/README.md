# CHANGELOG 索引

每个版本一个文件（`vX.Y.Z.md`）。发版流程见 [../packaging.md](../packaging.md) §2
（打 tag 自动构建发草稿 Release，版本号由 CI 从 tag 同步）。

**发版时**：把下方 Unreleased 内容落成新版本文件（含分类小节），并将本节清空。

格式约定：`✨ 新增` / `🐞 修复` / `🔧 构建与 CI` / `🦄 重构`。

## Unreleased

### 🐞 修复

- 图片反分割层数算错：移植时 `%8`/`%10` 模数写反，导致拼出图片多层乱序（`a712f34`；与 qt 及 jmcomic 官方库交叉验证）
- 下载：`remove()` 后台删目录与重建同章任务竞态、`_cancelled` 集合泄漏（`635b4f4`）
- 图片缓存锁清扫逐出未 acquire 的新锁，single-flight 失效（`2dd4994`）
- waifu2x 异主结果分支持锁忙等、超时保护失效（`fbcf90d`）
- 详情页评论页码参数错绑（第二本书评论从第 2 页开始）；登录后回不到来源书页/收藏页（`3ae7504`）
- 搜索尾页不满员时"下一页"禁用条件失真，可点出空白页（`e3d4419`）
- dev.ts 在 Windows 下 spawn 无扩展名 bin 直接 ENOENT 且静默退 1（`2caea50`）

### ✨ 新增

- 阅读器滚动模式相邻页预加载（前后各 3 页，URL 去重）（`b21e7df`）

### 🦄 重构

- 401 判断从路由层文本匹配下沉为 `JmApiError.is_auth_error`（`f91b4b9`）

### 🔧 构建与 CI

- 打 tag 时 CI 同步 package.json 版本号，产物文件名与 tag 一致（`7cdbb73`）
- CORS 收敛为白名单（`null` + dev localhost），不再正则全放开（`88c8c65`）
- 捞回删除 NAS 时被连带删掉的 tools/settings 测试（`9c56bc5`）
- NAS 残留清理：存量库 `nas_configs` 表启动时自动 drop，文档同步（`d1e32ff`）

## 已发布

| 版本 | 日期 | 说明 |
|---|---|---|
| [v0.1.1](./v0.1.1.md) | 2026-09-04 | 打包白屏修复；CI 改 tag 触发 |
| [v0.1.0](./v0.1.0.md) | 2026-09-04 | 首个打包版本（Phase 0-6 全量，Windows zip） |
