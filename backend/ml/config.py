import os
from typing import Dict, Any

# Get base models directory from environment variable with fallback paths
BASE_MODELS_DIR = os.environ.get(
    "MODELS_BASE_PATH",  # First try the environment variable
    os.path.join(  # Fallback to a local path
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"
    ),
)

MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "mygpt": {
        "type": "custom_gpt",
        "model_name": os.path.join(BASE_MODELS_DIR, "gpt2-small-124M.pth"),
        "generation_params": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": None,
        },
    },
    "gemma-3-1b-it": {
        "type": "huggingface",
        # "model_name": "google/gemma-3-1b-it",
        "model_name": os.path.join(BASE_MODELS_DIR, "gemma-3-1b-it"),
        "generation_params": {
            # "max_new_tokens": 100,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True,
        },
    },
    "qwen-instruct": {
        "type": "huggingface",
        "model_name": "Qwen/Qwen2.5-0.5B-Instruct",
        "generation_params": {
            # "max_new_tokens": 100,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True,
        },
        # "model_kwargs": {
        #     "device_map": "auto",
        # },
    },
    "smolvlm": {
        # SmolVLM-256M-Instruct
        "type": "vision_huggingface",
        # "model_name": "SmolVLM/SmolVLM-256M-Instruct",
        "model_name": os.path.join(BASE_MODELS_DIR, "SmolVLM-256M-Instruct"),
        "generation_params": {
            "temperature": 0.7,
            "max_new_tokens": 30,
            "do_sample": True,
        },
        "supports_vision": True,
        "description": "A small vision-language model capable of understanding images",
    },
}

# Default parameters for text generation
DEFAULT_GENERATION_PARAMS: Dict[str, Any] = {
    # "max_new_tokens": 100,
    "temperature": 0.7,
    "top_p": 0.9,
    "do_sample": True,
    # Note: streaming is handled in the HuggingFaceModel class
}
