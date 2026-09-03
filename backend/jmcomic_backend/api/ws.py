"""WebSocket 事件流占位.

后续所有异步任务事件（download/convert/task）都通过该端点广播给前端.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        await websocket.send_json({"channel": "system", "type": "connected"})
        while True:
            # 占位：echo 消息
            data = await websocket.receive_text()
            await websocket.send_json({"channel": "echo", "data": data})
    except WebSocketDisconnect:
        pass
