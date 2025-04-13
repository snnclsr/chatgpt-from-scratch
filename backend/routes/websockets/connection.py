import uuid
import logging
import asyncio
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and communication between clients.
    This is a singleton class that should be instantiated once and used across the application.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if not ConnectionManager._initialized:
            self.active_connections: Dict[str, WebSocket] = {}
            ConnectionManager._initialized = True

    async def connect(self, websocket: WebSocket) -> str:
        """Connect a client and return its unique ID"""
        client_id = str(uuid.uuid4())
        await websocket.accept()
        self.active_connections[client_id] = websocket
        return client_id

    def disconnect(self, client_id: str):
        """Remove a client from active connections"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, client_id: str, message: dict):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict, exclude: List[str] = None):
        """Send a message to all connected clients, optionally excluding some"""
        exclude = exclude or []
        for client_id, connection in self.active_connections.items():
            if client_id not in exclude:
                await connection.send_json(message)

    async def check_for_stop_command(
        self, client_id: str, timeout: float = 0.001
    ) -> bool:
        """Check if client has sent a stop command with a very short timeout"""
        if client_id not in self.active_connections:
            return False

        websocket = self.active_connections[client_id]
        try:
            # Non-blocking check for a stop message with a very short timeout
            data = await asyncio.wait_for(websocket.receive_json(), timeout=timeout)
            if data.get("command") == "stop":
                logger.info(f"Generation stopped by client request: {client_id}")
                return True
        except asyncio.TimeoutError:
            # No message received, continue generation
            pass
        return False


# Create a singleton instance
manager = ConnectionManager()
