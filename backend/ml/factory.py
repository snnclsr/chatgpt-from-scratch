from typing import Dict, List, Any
import logging
from .base import BaseModelInterface, VisionModelInterface
from .providers.huggingface import HuggingFaceModel
from .providers.vision_huggingface import VisionHuggingFaceModel
from .providers.custom_gpt import CustomGPTModel
from .config import MODEL_CONFIGS

logger = logging.getLogger(__name__)


class ModelFactory:
    _models: Dict[str, BaseModelInterface] = {}
    _model_configs: Dict[str, dict] = MODEL_CONFIGS

    @classmethod
    def register_model(cls, model_id: str, model_config: dict) -> None:
        """Register a model configuration"""
        cls._model_configs[model_id] = model_config
        logger.info(f"Registered model configuration for {model_id}")

    @classmethod
    async def get_model(cls, model_id: str) -> BaseModelInterface:
        """Get or create a model instance"""
        if model_id not in cls._models:
            if model_id not in cls._model_configs:
                raise ValueError(f"Model {model_id} not registered")

            config = cls._model_configs[model_id]
            model_type = config.get("type", "huggingface")

            if model_type == "huggingface":
                model = HuggingFaceModel(config["model_name"], config)
                await model.load_model()
                cls._models[model_id] = model
            elif model_type == "vision_huggingface":
                model = VisionHuggingFaceModel(config["model_name"], config)
                await model.load_model()
                cls._models[model_id] = model
            elif model_type == "custom_gpt":
                model = CustomGPTModel(config["model_name"], config)
                await model.load_model()
                cls._models[model_id] = model
            else:
                raise ValueError(f"Unsupported model type: {model_type}")

        return cls._models[model_id]

    @classmethod
    async def unload_model(cls, model_id: str) -> None:
        """Unload a model from memory"""
        if model_id in cls._models:
            model = cls._models[model_id]
            if hasattr(model, "model"):
                del model.model
            if hasattr(model, "tokenizer"):
                del model.tokenizer
            if hasattr(model, "processor"):
                del model.processor
            del cls._models[model_id]
            logger.info(f"Unloaded model {model_id}")

    @classmethod
    def get_available_models(cls) -> List[Dict[str, Any]]:
        """Get information about all registered models"""
        models_info = []
        for model_id, config in cls._model_configs.items():
            info = {"id": model_id, "loaded": model_id in cls._models, **config}
            if model_id in cls._models:
                info.update(cls._models[model_id].model_info)
            models_info.append(info)
        return models_info

    @classmethod
    def is_vision_model(cls, model_id: str) -> bool:
        """Check if a model supports vision capabilities"""
        if model_id in cls._models:
            model = cls._models[model_id]
            return isinstance(model, VisionModelInterface) and model.supports_vision
        elif model_id in cls._model_configs:
            config = cls._model_configs[model_id]
            return config.get("type") == "vision_huggingface"
        return False
