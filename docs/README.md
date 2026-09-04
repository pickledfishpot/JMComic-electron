# JMComic-electron 文档索引

| 文档 | 说明 |
|---|---|
| [architecture.md](./architecture.md) | 总体架构：背景、技术栈、目录结构、Qt → Electron 移植改造点、实施阶段、风险 |
| [api.md](./api.md) | 后端 API 完整清单（按模块分表）与 HTTP/WebSocket 通信约定 |
| [jm-notes.md](./jm-notes.md) | JM 站点适配笔记：请求加密、scramble_id、图片反分割公式、重试策略 |
| [packaging.md](./packaging.md) | 打包链路、CI Release 流程、版本号规则、数据目录与日志排障 |
| [CHANGELOG/](./CHANGELOG/README.md) | 版本记录（每版本一个文件，索引页含 Unreleased） |

## 文档维护约定

- 功能/行为变更、bug 修复 → 同步更新对应文档（见根目录 `AGENTS.md`）
- 发版时把 `CHANGELOG/README.md` 的 Unreleased 段落落成新版本文件（`CHANGELOG/vX.Y.Z.md`）
- 移植 JM 相关"魔法常量"算法时，在 jm-notes.md 记录规则并与参考实现交叉验证
