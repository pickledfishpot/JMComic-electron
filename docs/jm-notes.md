# JM 站点适配笔记

> JM 站点的私有协议细节（加密、反分割、重试策略）。这些规则是硬编码的"魔法常量"，
> 修改前必须与参考实现交叉验证——本项目已踩过一次移植写反的坑（见 §3）。

## 1. API 请求加密

- 每个 API 请求头携带 `token` / `tokenparam`，由 `jmcomic` 库的 `JmCryptoTool.token_and_tokenparam(ts)` 按当前时间戳生成（`services/jm_client.py`）
- 响应的 `data` 字段是 base64 + AES-ECB 加密，用 `JmCryptoTool.decode_resp_data(encoded, ts)` 解密；解密结果可能是对象也可能是数组
- 业务错误：`code != 200` 时抛 `JmApiError`（携带上游 code 与文案），未登录见 `is_auth_error`

## 2. scramble_id（反分割参数）

- 每个章节一个，从 `chapter_view_template` 返回的 HTML 里正则提取 `var scramble_id = (\d+)`（`jm_client.py get_scramble_id`）
- 提取失败兜底 `220980`（与 jmcomic 库一致）
- 前端不直接关心：章节 pages 接口返回的每页 url 已带 `?scramble_id=`，图片代理据此反分割

## 3. 图片反分割（descramble）

JM 把章节图片纵向切成 num 条、倒序堆叠，客户端需还原（`services/deslice.py`）。

图片路径规则：`media/photos/{epsId}/{pictureName}.{ext}`，md5 计算用**去扩展名**的 pictureName。

**分割数公式**（与 qt `tool.py GetSegmentationNum`、jmcomic 库 `JmImageTool.get_num` 三方一致）：

| epsId 区间 | num |
|---|---|
| `epsId < scramble_id` | 0（未分割） |
| `scramble_id ≤ epsId < 268850` | 固定 10 |
| `268850 ≤ epsId ≤ 421926` | `(md5(epsId+pictureName) 末位字符码 % 10) * 2 + 2` |
| `epsId > 421926` | `(md5(...) 末位字符码 % 8) * 2 + 2` |

**还原方式**：源图按高度等分 num 条（余数归最后一条），倒序贴回新图。

> ⚠️ 历史教训（2026-09-04 修复）：移植时曾把两个区间的 `% 10` / `% 8` 写反，导致切条边界全错位、拼出图片多层乱序。
> **改这里之前务必跑 parity 校验**：随机采样与 `jmcomic.jm_toolkit.JmImageTool.get_num` 对比（修复时用 300 组样本 0 mismatch 确认）。

## 4. 网络稳定性

- JM 服务器不稳定：`JmClient` 对所有请求内置 3 次重试；连续失败后上层返回 502，前端提示"JM 服务器不太稳定"
- 站点模拟/反爬依赖 `curl_cffi`（libcurl-impersonate），打包时必须 `--collect-all curl_cffi` 带齐原生库（见 [packaging.md](./packaging.md)）
- 代理：设置保存后即时写入 `JmClient` 全局默认代理（http/https/socks5 取第一个非空）

## 5. 参考实现

- 原项目：`/Users/fish/Code/lijiayu/JMComic-qt`（`src/server/req.py`、`src/tools/tool.py`）
- 官方库：`jmcomic`（本项目依赖，`jmcomic/jm_toolkit.py` 的 `JmImageTool` / `JmCryptoTool` / `JmMagicConstants`）
