from typing import Dict, Any

MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    # "gpt2": {
    #     "type": "huggingface",
    #     "model_name": "gpt2",
    #     "model_kwargs": {
    #         "low_cpu_mem_usage": True,
    #         "device_map": "auto",
    #         "torch_dtype": "auto",
    #     },
    #     "generation_params": {
    #         "max_new_tokens": 100,
    #         "temperature": 0.7,
    #         "top_p": 0.9,
    #         "do_sample": True,
    #     },
    # },
    "gemma-3-1b-it": {
        "type": "huggingface",
        # "model_name": "google/gemma-3-1b-it",
        "model_name": "/Users/sinan/Desktop/repos/chatgpt-from-scratch/backend/gemma-3-1b-it",
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
    # "opt-350m": {
    #     "type": "huggingface",
    #     "model_name": "facebook/opt-350m",
    #     "model_kwargs": {
    #         "low_cpu_mem_usage": True,
    #         "device_map": "auto",
    #         "torch_dtype": "auto",
    #     },
    # },
}

# Default parameters for text generation
DEFAULT_GENERATION_PARAMS: Dict[str, Any] = {
    # "max_new_tokens": 100,
    "temperature": 0.7,
    "top_p": 0.9,
    "do_sample": True,
    # Note: streaming is handled in the HuggingFaceModel class
}
