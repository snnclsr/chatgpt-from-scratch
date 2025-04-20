import time
import logging
import os
from typing import AsyncGenerator, Dict, Any

import torch
import tiktoken
from .gpt_model import GPTModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def text_to_token_ids(text, tokenizer):
    encoded = tokenizer.encode(text)
    encoded_tensor = torch.tensor(encoded).unsqueeze(0)  # add batch dimension
    return encoded_tensor


def token_ids_to_text(token_ids, tokenizer):
    flat = token_ids.squeeze(0)  # remove batch dimension
    return tokenizer.decode(flat.tolist())


class ModelInterface:
    def __init__(self, model_filename: str):
        """Initialize the model interface and load the model"""
        logger.info("Initializing model interface")
        # self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_filename = model_filename
        self.device = torch.device(
            "mps" if torch.backends.mps.is_available() else "cpu"
        )
        logger.info(f"Using device: {self.device}")

        # Load model - this will be done once at startup
        self._load_model()

    def _load_model(self) -> None:
        """Load the GPT model and tokenizer"""
        try:
            start_time = time.time()

            # Initialize tokenizer
            self.tokenizer = tiktoken.get_encoding("gpt2")

            # Set up model config directly - simplify config handling
            self.BASE_CONFIG = {
                "vocab_size": 50257,  # Vocabulary size
                "context_length": 1024,  # Context length
                "drop_rate": 0.0,  # Dropout rate
                "qkv_bias": True,  # Query-key-value bias
                "emb_dim": 768,
                "n_layers": 12,
                "n_heads": 12,  # Using gpt2-small config directly
            }

            # Use environment variable for model path with fallback to standard locations
            model_path = os.environ.get("MODEL_PATH")

            if not model_path:
                # Check Docker models volume first (as per docker-compose.yml configuration)
                models_dir = "/app/models"
                docker_path = os.path.join(models_dir, self.model_filename)

                # Check local directory as fallback
                current_dir = os.path.dirname(os.path.abspath(__file__))
                local_path = os.path.join(current_dir, self.model_filename)

                if os.path.exists(docker_path):
                    model_path = docker_path
                elif os.path.exists(local_path):
                    model_path = local_path
                else:
                    # Last resort - just use the filename and hope it's in the current directory
                    model_path = self.model_filename

            logger.info(f"Loading model from: {model_path}")

            self.model = GPTModel(self.BASE_CONFIG)
            self.model.load_state_dict(torch.load(model_path, weights_only=True))
            self.model = self.model.eval()

            # Check if Apple Silicon MPS is available
            if torch.backends.mps.is_available():
                logger.info("Using Apple Silicon MPS for acceleration")
                self.model.to("mps")
            else:
                logger.info(f"MPS not available, using {self.device}")
                self.model.to(self.device)

            load_time = time.time() - start_time
            logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            self.model = None
            self.tokenizer = None
            raise

    async def generate_stream(
        self,
        prompt: str,
        max_length: int = 100,
        temperature: float = 0.7,
        top_k: int = None,
        top_p: float = 0.9,
        eos_id: int = None,
        **kwargs: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from the model one by one.

        Args:
            prompt: The input prompt to generate from
            max_length: Maximum number of tokens to generate
            temperature: Sampling temperature (higher = more random)
            top_p: Nucleus sampling parameter
            kwargs: Additional parameters for the model

        Yields:
            Generated tokens one by one
        """
        if not self.model or not self.tokenizer:
            logger.error("Model or tokenizer not initialized")
            yield "Error: Model not initialized properly."
            return

        try:
            # Log inference start
            start_time = time.time()
            logger.info(f"Starting generation with prompt length: {len(prompt)}")

            # Validate input length
            if len(prompt) > 4000:  # Example limit
                logger.warning(f"Prompt too long: {len(prompt)} chars")
                yield "Error: Prompt too long. Please reduce length."
                return

            # Convert prompt to token IDs
            idx = text_to_token_ids(prompt, self.tokenizer)
            idx = idx.to(self.device)

            # Store original prompt length to track new tokens
            original_length = idx.shape[1]

            # For-loop is the same as before: Get logits, and only focus on last time step
            for _ in range(max_length):
                idx_cond = idx[:, -self.BASE_CONFIG["context_length"] :]
                with torch.no_grad():
                    logits = self.model(idx_cond)
                logits = logits[:, -1, :]

                # New: Filter logits with top_k sampling
                if top_k is not None:
                    # Keep only top_k values
                    top_logits, _ = torch.topk(logits, top_k)
                    min_val = top_logits[:, -1]
                    logits = torch.where(
                        logits < min_val,
                        torch.tensor(float("-inf")).to(self.device),
                        logits,
                    )

                # New: Apply temperature scaling
                if temperature > 0.0:
                    logits = logits / temperature

                    # Apply softmax to get probabilities
                    probs = torch.softmax(logits, dim=-1)  # (batch_size, context_len)

                    # Sample from the distribution
                    idx_next = torch.multinomial(
                        probs, num_samples=1
                    )  # (batch_size, 1)

                # Otherwise same as before: get idx of the vocab entry with the highest logits value
                else:
                    idx_next = torch.argmax(
                        logits, dim=-1, keepdim=True
                    )  # (batch_size, 1)

                # Append sampled index to the running sequence
                idx = torch.cat((idx, idx_next), dim=1)  # (batch_size, num_tokens+1)

                # Decode just the new token and yield it
                new_token = self.tokenizer.decode([idx_next.item()])
                yield new_token

                # Check if we hit the end token
                if idx_next.item() == eos_id and eos_id is not None:
                    break

            # Log completion
            total_time = time.time() - start_time
            token_count = idx.shape[1] - original_length
            logger.info(
                f"Generation completed: {token_count} tokens in {total_time:.2f}s"
            )
            logger.info(f"Generation speed: {token_count / total_time:.2f} tokens/s")

        except Exception as e:
            logger.error(f"Error during generation: {str(e)}")
            yield f"Error during generation: {str(e)}"

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
            prompt: The input prompt
            max_length: Maximum generation length
            temperature: Sampling temperature
            kwargs: Additional generation parameters

        Returns:
            The complete generated text
        """
        result = []
        async for token in self.generate_stream(
            prompt, max_length, temperature, **kwargs
        ):
            if token.startswith("Error:"):
                return token
            result.append(token)
        return "".join(result)
