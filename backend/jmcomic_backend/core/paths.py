"""数据目录路径管理.

所有持久化路径都基于 Electron 传入的 --data-dir，禁止写死路径.
"""

from pathlib import Path


class AppPaths:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.cache_dir = self.data_dir / "cache"
        self.download_dir = self.data_dir / "downloads"
        self.log_dir = self.data_dir / "logs"
        self.db_dir = self.data_dir / "db"
        self.config_file = self.data_dir / "config.yaml"

    def ensure_all(self) -> None:
        for path in (self.cache_dir, self.download_dir, self.log_dir, self.db_dir):
            path.mkdir(parents=True, exist_ok=True)
