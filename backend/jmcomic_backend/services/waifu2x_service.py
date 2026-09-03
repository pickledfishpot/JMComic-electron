"""Waifu2x 超分服务，移植自原 JMComic-qt 的 task_waifu2x.py.

sr_vulkan 是原生 Vulkan 扩展，打包/环境中不可用时整个功能隐藏：
- available() 返回 False，前端不展示超分入口
- convert() 仅在可用时工作，模型参数与原项目一致（model/scale/width/high）
"""

from __future__ import annotations

import asyncio
import itertools
import logging
from typing import Any

logger = logging.getLogger(__name__)

_task_ids = itertools.count(1)

# 模块级缓存探测结果，避免每次 import 尝试的开销
_available: bool | None = None


def available() -> bool:
    """sr_vulkan 是否可用."""
    global _available
    if _available is None:
        try:
            from sr_vulkan import sr_vulkan  # noqa: F401
            _available = True
        except ImportError:
            _available = False
            logger.info("sr_vulkan not installed, waifu2x disabled")
    return _available


class Waifu2xError(Exception):
    """超分失败，message 面向用户."""


async def convert(
    img_data: bytes,
    model: int = 1,
    scale: int = 2,
    width: int = 0,
    high: int = 0,
    format: str = "",
    tile_size: int = 400,
) -> tuple[bytes, float]:
    """对单张图片做超分，返回 (结果字节, 耗时秒).

    移植自 task_waifu2x.py：sr.add 入队 -> 循环 sr.load 取结果.
    sr_vulkan 是阻塞式原生库，整体跑在线程池中.
    """
    if not available():
        raise Waifu2xError("超分引擎 sr_vulkan 不可用")

    def _run() -> tuple[bytes, float]:
        import time

        from sr_vulkan import sr_vulkan as sr

        task_id = next(_task_ids)
        if scale > 0:
            sts = sr.add(img_data, model, task_id, scale, format=format, tileSize=tile_size)
        else:
            sts = sr.add(img_data, model, task_id, width, high, format=format, tileSize=tile_size)
        if sts <= 0:
            raise Waifu2xError(f"超分任务入队失败: {sr.getLastError()}")

        t0 = time.time()
        while True:
            info = sr.load(0)
            if info:
                data, _format, done_id, _tick = info
                if done_id == task_id:
                    if not data:
                        raise Waifu2xError("超分结果为空（图片格式可能不受支持）")
                    return data, round(time.time() - t0, 3)
            else:
                time.sleep(0.01)

    return await asyncio.to_thread(_run)
