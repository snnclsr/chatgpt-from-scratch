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


class VisionModelInterface(BaseModelInterface):
    @abstractmethod
    async def generate_stream_with_image(
        self, prompt: str, image_path: str, **params: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Stream generated tokens based on text and image input"""
        pass

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """Returns whether this model supports vision capabilities"""
        return True
