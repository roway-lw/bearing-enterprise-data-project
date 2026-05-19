"""WebSocket 连接管理和进度广播"""
import asyncio
import time
from typing import Dict, List, Optional
from fastapi import WebSocket


class ProgressManager:
    """管理所有活跃的 WebSocket 连接，支持按 task_id 广播进度"""

    def __init__(self):
        # task_id -> [WebSocket]
        self.connections: Dict[str, List[WebSocket]] = {}
        # task_id -> 最新状态快照（用于重连时恢复）
        self.latest_state: Dict[str, dict] = {}

    async def connect(self, task_id: str, ws: WebSocket):
        """接受新的 WebSocket 连接"""
        await ws.accept()
        self.connections.setdefault(task_id, []).append(ws)
        # 发送最新状态快照
        if task_id in self.latest_state:
            try:
                await ws.send_json(self.latest_state[task_id])
            except Exception:
                pass

    def disconnect(self, task_id: str, ws: WebSocket):
        """断开 WebSocket 连接"""
        conns = self.connections.get(task_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self.connections.pop(task_id, None)

    async def broadcast(self, task_id: str, message: dict):
        """向 task_id 关联的所有连接广播消息"""
        self.latest_state[task_id] = message
        conns = self.connections.get(task_id, [])
        dead = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.remove(ws)

    def broadcast_sync(self, task_id: str, message: dict):
        """同步安全的广播方法（从非 async 上下文调用）"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.broadcast(task_id, message))
            else:
                loop.run_until_complete(self.broadcast(task_id, message))
        except RuntimeError:
            # 没有事件循环，存储状态等下次连接时发送
            self.latest_state[task_id] = message

    def clear(self, task_id: str):
        """清理已完成的任务"""
        self.connections.pop(task_id, None)
        self.latest_state.pop(task_id, None)


# 全局单例
progress_manager = ProgressManager()
