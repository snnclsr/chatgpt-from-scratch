from typing import AsyncGenerator, Dict, Any, Optional
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq, TextIteratorStreamer
from threading import Thread
import logging
import os
from PIL import Image
from ..base import VisionModelInterface

logger = logging.getLogger(__name__)


class VisionHuggingFaceModel(VisionModelInterface):
    def __init__(self, model_name: str, model_config: Dict[str, Any]):
        self.model_name = model_name
        self.config = model_config
        self.model = None
        self.processor = None
        self._device = None

    async def load_model(self) -> None:
        # self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = "cpu"
        try:
            logger.info(f"Loading vision model {self.model_name}")

            # For vision models, we use AutoProcessor instead of just a tokenizer
            self.processor = AutoProcessor.from_pretrained(self.model_name)

            model_kwargs = self.config.get("model_kwargs", {})
            if "torch_dtype" in model_kwargs and model_kwargs["torch_dtype"] == "auto":
                model_kwargs["torch_dtype"] = (
                    torch.float16 if torch.cuda.is_available() else torch.float32
                )

            # For vision models, we use AutoModelForVision2Seq
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.model_name,
                torch_dtype=torch.float32,
                **model_kwargs,  # torch_dtype=torch.bfloat16,
            ).to(self.device)

            self._device = next(self.model.parameters()).device
            logger.info(
                f"Vision model {self.model_name} loaded successfully on device {self._device}"
            )

        except Exception as e:
            logger.error(f"Error loading vision model {self.model_name}: {str(e)}")
            raise

    async def generate_stream(
        self, prompt: str, **params: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        if not self.model or not self.processor:
            await self.load_model()

        try:
            # Create a message without images
            messages = [
                {"role": "user", "content": [{"type": "text", "text": prompt}]},
            ]

            # Format the prompt for the model
            formatted_prompt = self.processor.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False
            )

            # Create input tokens with padding
            inputs = self.processor(
                text=formatted_prompt, return_tensors="pt", padding=True
            ).to(self._device)

            # Initialize the streamer
            streamer = TextIteratorStreamer(self.processor.tokenizer, skip_prompt=True)

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
                if self.processor.tokenizer.eos_token and new_text.endswith(
                    self.processor.tokenizer.eos_token
                ):
                    yield new_text.rstrip(self.processor.tokenizer.eos_token)
                    break
                yield new_text

            # Wait for the thread to complete
            thread.join()

        except Exception as e:
            logger.error(f"Error during text generation: {str(e)}")
            raise

    def _resize_image(
        self, image: Image.Image, size: tuple = (256, 256)
    ) -> Image.Image:
        """Resize image to the specified dimensions"""
        logger.info(f"Resizing image from {image.size} to {size}")
        return image.resize(size, Image.LANCZOS)

    async def generate_stream_with_image(
        self, prompt: str, image_path: str, **params: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        if not self.model or not self.processor:
            await self.load_model()

        try:
            # Load the image
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")

            # Load and resize the image to 256x256
            original_image = Image.open(image_path).convert("RGB")
            logger.info(
                f"Image loaded from {image_path} with original size {original_image.size}"
            )

            # Resize the image to 256x256
            image = self._resize_image(original_image, (256, 256))
            logger.info(f"Image resized to 256x256")

            # Create messages with image
            messages = [
                {
                    "role": "user",
                    "content": [{"type": "image"}, {"type": "text", "text": prompt}],
                },
            ]

            # Format the prompt for the model
            formatted_prompt = self.processor.apply_chat_template(
                messages,
                add_generation_prompt=True,  # tokenize=False
            )

            logger.info(f"Formatted prompt: {formatted_prompt[:100]}...")

            # Create inputs with image
            inputs = self.processor(
                text=formatted_prompt,
                images=[image],
                return_tensors="pt",  # padding=True
            ).to(self._device)

            # Initialize the streamer
            streamer = TextIteratorStreamer(
                self.processor, skip_prompt=True, skip_special_tokens=True
            )

            # Prepare generation parameters
            generation_kwargs = {
                **self.config.get("generation_params", {}),  # Model-specific defaults
                **params,  # User-provided parameters
                **inputs,  # Input tokens and image
                "streamer": streamer,  # Add the streamer
            }

            logger.info(
                f"Starting generation with parameters: {self.config.get('generation_params', {})}"
            )

            # Run generation in a separate thread
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()

            # Stream the generated tokens
            for new_text in streamer:
                # if self.processor.tokenizer.eos_token and new_text.endswith(
                #     self.processor.tokenizer.eos_token
                # ):
                #     yield new_text.rstrip(self.processor.tokenizer.eos_token)
                #     break
                yield new_text

            # Wait for the thread to complete
            thread.join()

        except Exception as e:
            logger.error(f"Error during vision generation: {str(e)}")
            raise

    async def tokenize(self, text: str) -> list:
        if not self.processor:
            await self.load_model()
        try:
            return self.processor.tokenizer.encode(text)
        except Exception as e:
            logger.error(f"Error during tokenization: {str(e)}")
            raise

    @property
    def model_info(self) -> Dict[str, Any]:
        info = {
            "name": self.model_name,
            "type": "vision_huggingface",
            "supports_vision": True,
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

    @property
    def supports_vision(self) -> bool:
        return True
