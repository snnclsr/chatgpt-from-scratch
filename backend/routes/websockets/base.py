from abc import ABC, abstractmethod


class BaseWebSocketHandler(ABC):
    @abstractmethod
    async def handle_message(self, message: str):
        pass
