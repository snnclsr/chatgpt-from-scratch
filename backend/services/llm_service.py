from typing import AsyncGenerator, Dict, Any, Optional
import logging

from ..my_ml.model_interface import ModelInterface

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMService:
    """
    Service class for handling LLM interactions.
    This acts as the intermediary between API endpoints and the model.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern to ensure one model instance across the application"""
        if cls._instance is None:
            cls._instance = super(LLMService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the service and model if not already initialized"""
        if not LLMService._initialized:
            logger.info("Initializing LLM service")
            self.model_interface = ModelInterface()
            LLMService._initialized = True
            logger.info("LLM service initialized")

    async def generate_stream(
        self,
        prompt: str,
        max_length: int = 20,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        """
        Generate a stream of tokens from the LLM.

        Args:
            prompt: User input prompt
            max_length: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter (0.0-1.0)
            kwargs: Additional model parameters

        Yields:
            Generated tokens one by one
        """
        try:
            # Input validation
            if not prompt or not isinstance(prompt, str):
                raise ValueError("Prompt must be a valid string")

            # Log request
            logger.info(
                f"Processing generation request: {len(prompt)} chars, max_len={max_length}"
            )

            # Stream tokens from the model
            async for token in self.model_interface.generate_stream(
                prompt=prompt,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                **kwargs,
            ):
                yield token

        except Exception as e:
            logger.error(f"Error in LLM service: {str(e)}")
            yield f"Error: {str(e)}"

    async def generate(
        self,
        prompt: str,
        max_length: int = 100,
        temperature: float = 0.7,
        **kwargs: Dict[str, Any],
    ) -> str:
        """
        Generate a complete response (non-streaming).

        Args:
            prompt: User input prompt
            max_length: Maximum token length
            temperature: Sampling temperature
            kwargs: Additional model parameters

        Returns:
            Complete generated text
        """
        try:
            return await self.model_interface.generate(
                prompt=prompt, max_length=max_length, temperature=temperature, **kwargs
            )
        except Exception as e:
            logger.error(f"Error in LLM service generate: {str(e)}")
            return f"Error: {str(e)}"
