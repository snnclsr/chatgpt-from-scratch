from typing import Dict, Any

MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    # "gemma-3-1b-it": {
    #     "type": "huggingface",
    #     # "model_name": "google/gemma-3-1b-it",
    #     "model_name": "/Users/sinan/Desktop/repos/chatgpt-from-scratch/backend/gemma-3-1b-it",
    #     "generation_params": {
    #         # "max_new_tokens": 100,
    #         "temperature": 0.7,
    #         "top_p": 0.9,
    #         "do_sample": True,
    #     },
    # },
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
    "SmolVLM-256M-Instruct": {
        "type": "vision_huggingface",
        # "model_name": "SmolVLM/SmolVLM-256M-Instruct",
        "model_name": "/Users/sinan/Desktop/repos/chatgpt-from-scratch/backend/SmolVLM-256M-Instruct",
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
