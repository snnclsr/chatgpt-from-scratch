from typing import AsyncGenerator
import torch
import asyncio


class ModelInterface:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # Model loading will be implemented later
        self.model = None
        self.tokenizer = None

    async def generate_stream(
        self, prompt: str, max_length: int = 100
    ) -> AsyncGenerator[str, None]:
        """
        Streaming interface for the model.
        This will be implemented when we add the actual model.
        """
        # Placeholder for now - will be replaced with actual model
        for token in ["Hello", "world", "!..."]:
            yield token
            await asyncio.sleep(0.1)  # Simulate streaming
