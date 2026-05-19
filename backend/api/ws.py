"""WebSocket 端点 — 实时推送流水线进度"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.progress_manager import progress_manager

router = APIRouter()


@router.websocket("/ws/pipeline/{task_id}")
async def pipeline_ws(ws: WebSocket, task_id: str):
    """WebSocket 连接：实时接收流水线进度"""
    await progress_manager.connect(task_id, ws)
    try:
        while True:
            # 保持连接，接收客户端心跳
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        progress_manager.disconnect(task_id, ws)
