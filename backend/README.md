# JMComic Backend

FastAPI 后端服务，负责 JM 站点请求、图片处理、下载管理与本地数据持久化。

## 开发环境

```bash
# 虚拟环境通常由根目录 postinstall 自动创建
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 启动

```bash
.venv/bin/uvicorn jmcomic_backend.main:app --host 127.0.0.1 --port 8000 --data-dir /tmp/jmcomic-test
```

**注意**：`--data-dir` 是 Electron 传入的数据目录，禁止在代码中写死路径。
