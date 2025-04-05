from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any


class BaseModelInterface(ABC):
    @abstractmethod
    async def load_model(self) -> None:
        """Load the model and its tokenizer"""
        pass

    @abstractmethod
    async def generate_stream(
        self, prompt: str, **params: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Stream generated tokens"""
        pass

    @abstractmethod
    async def tokenize(self, text: str) -> list:
        """Tokenize input text"""
        pass

    @property
    @abstractmethod
    def model_info(self) -> Dict[str, Any]:
        """Return model information"""
        pass
