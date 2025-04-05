from typing import AsyncGenerator, Dict, Any
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread
import logging
from ..base import BaseModelInterface

logger = logging.getLogger(__name__)


class HuggingFaceModel(BaseModelInterface):
    def __init__(self, model_name: str, model_config: Dict[str, Any]):
        self.model_name = model_name
        self.config = model_config
        self.model = None
        self.tokenizer = None
        self._device = None

    async def load_model(self) -> None:
        self.device = "cpu"  # "mps" if torch.backends.mps.is_available() else "cpu"
        try:
            logger.info(f"Loading model {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            model_kwargs = self.config.get("model_kwargs", {})
            if "torch_dtype" in model_kwargs and model_kwargs["torch_dtype"] == "auto":
                model_kwargs["torch_dtype"] = (
                    torch.float16 if torch.cuda.is_available() else torch.float32
                )

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, **model_kwargs
            ).to(self.device)

            self._device = next(self.model.parameters()).device
            logger.info(
                f"Model {self.model_name} loaded successfully on device {self._device}"
            )

        except Exception as e:
            logger.error(f"Error loading model {self.model_name}: {str(e)}")
            raise

    async def generate_stream(
        self, prompt: str, **params: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        if not self.model or not self.tokenizer:
            await self.load_model()

        try:
            formatted_prompt = self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
            print(formatted_prompt)
            # Create input tokens
            inputs = self.tokenizer([formatted_prompt], return_tensors="pt").to(
                self._device
            )

            # Initialize the streamer
            streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True)

            # Prepare generation parameters
            generation_kwargs = {
                **self.config.get("generation_params", {}),  # Model-specific defaults
                **params,  # User-provided parameters
                **inputs,  # Input tokens
                "streamer": streamer,  # Add the streamer
            }

            # Run generation in a separate thread
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()

            # Stream the generated tokens
            for new_text in streamer:
                # print(new_text)
                yield new_text

            # Wait for the thread to complete
            thread.join()

        except Exception as e:
            logger.error(f"Error during generation: {str(e)}")
            raise

    async def tokenize(self, text: str) -> list:
        if not self.tokenizer:
            await self.load_model()
        try:
            return self.tokenizer.encode(text)
        except Exception as e:
            logger.error(f"Error during tokenization: {str(e)}")
            raise

    @property
    def model_info(self) -> Dict[str, Any]:
        info = {
            "name": self.model_name,
            "type": "huggingface",
            "config": {
                k: v
                for k, v in self.config.items()
                if k != "model_kwargs"  # Don't expose internal kwargs
            },
            "loaded": self.model is not None,
        }
        if self._device:
            info["device"] = str(self._device)
        return info
