"""
SSE (Server-Sent Events) Connection Manager for real-time updates.
"""
import asyncio
from typing import Dict, List


class SSEConnectionManager:
    """Manages SSE connections for real-time exam updates."""
    
    def __init__(self):
        # Map exam_id -> list of queues
        self.active_connections: Dict[str, List[asyncio.Queue]] = {}

    async def connect(self, exam_id: str) -> asyncio.Queue:
        """Create a new connection for an exam."""
        if exam_id not in self.active_connections:
            self.active_connections[exam_id] = []
        queue: asyncio.Queue = asyncio.Queue()
        self.active_connections[exam_id].append(queue)
        return queue

    def disconnect(self, exam_id: str, queue: asyncio.Queue) -> None:
        """Remove a connection from an exam."""
        if exam_id in self.active_connections:
            if queue in self.active_connections[exam_id]:
                self.active_connections[exam_id].remove(queue)
            if not self.active_connections[exam_id]:
                del self.active_connections[exam_id]

    async def broadcast(self, exam_id: str, message: dict) -> None:
        """Broadcast a message to all connections for an exam."""
        if exam_id in self.active_connections:
            for queue in self.active_connections[exam_id]:
                await queue.put(message)


# Global manager instance
sse_manager = SSEConnectionManager()
