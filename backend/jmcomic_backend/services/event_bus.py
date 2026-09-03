"""Asyncio 事件总线，用于替代原 Qt 项目的 Signal/Slot.

后续 download/task/waifu2x 等异步事件都通过此总线发布，WebSocket 层订阅并广播给前端.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[Any], None]]] = {}

    def subscribe(self, channel: str, callback: Callable[[Any], None]) -> Callable[[], None]:
        self._listeners.setdefault(channel, []).append(callback)

        def unsubscribe() -> None:
            self._listeners.get(channel, []).remove(callback)

        return unsubscribe

    def publish(self, channel: str, data: Any) -> None:
        for callback in self._listeners.get(channel, []):
            try:
                callback(data)
            except Exception:
                # 事件总线不应因单个回调失败而中断
                import logging

                logging.exception("EventBus callback failed on channel %s", channel)

    async def publish_async(self, channel: str, data: Any) -> None:
        """在事件循环中异步发布事件."""
        await asyncio.get_event_loop().run_in_executor(None, self.publish, channel, data)


# 全局事件总线实例
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
