from typing import AsyncGenerator, Dict, Any, List

from ..base import BaseModelInterface
from ...my_ml.model_interface import ModelInterface


def format_input(prompt):
    instruction_text = (
        f"Below is an instruction that describes a task. "
        f"Write a response that appropriately completes the request."
        f"\n\n### Instruction:\n{prompt['content']}"
    )
    input_text = f"\n\n### Input:\n{prompt['input']}" if prompt["input"] else ""
    return instruction_text + input_text


class CustomGPTModel(BaseModelInterface):
    def __init__(self, model_name: str, model_config: Dict[str, Any]):
        self.model_name = model_name
        self.config = model_config
        self.model_interface = None

    async def load_model(self) -> None:
        if not self.model_interface:
            self.model_interface = ModelInterface(self.model_name)
            # Model is loaded in the constructor of ModelInterface

    async def generate_stream(
        self, prompt: List[Dict[str, Any]], **params: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        if not self.model_interface:
            await self.load_model()
        single_prompt = prompt[0]
        single_prompt["input"] = ""
        if "Input" in single_prompt["content"]:
            single_prompt["input"] = single_prompt["content"].split("Input:")[1].strip()

        # Convert user/assistant messages to the format expected by the model
        formatted_prompt = format_input(single_prompt)
        print("Custom GPT Prompt: ", formatted_prompt)
        async for token in self.model_interface.generate_stream(
            formatted_prompt,
            max_length=params.get("max_length", 100),
            temperature=params.get("temperature", 0.7),
            top_k=params.get("top_k", None),
            top_p=params.get("top_p", 0.9),
            eos_id=50256,  # params.get("eos_id", None),
        ):
            yield token

    async def tokenize(self, text: str) -> list:
        if not self.model_interface:
            await self.load_model()
        return self.model_interface.tokenizer.encode(text)

    @property
    def model_info(self) -> Dict[str, Any]:
        return {
            "name": self.model_name,
            "type": "custom_gpt",
            "config": self.config,
            "loaded": self.model_interface is not None,
            "device": str(self.model_interface.device)
            if self.model_interface
            else None,
        }
