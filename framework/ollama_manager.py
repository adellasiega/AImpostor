import json
from typing import Type

from ollama import chat
from pydantic import BaseModel

from .utils.llm_manager import LLMManager


class OllamaManager(LLMManager):
    def __init__(
        self,
        model_name: str,
        think: bool = False,
        options: dict | None = None,
    ) -> None:
        self.model_name = model_name
        self.think = think
        self.options = options or {}

    def ask(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list | None = None,
        response_format: Type[BaseModel] | None = None,
    ) -> tuple[BaseModel | str | None, list | None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "tools": tools,
            "think": self.think,
            "options": self.options,
        }
        if response_format:
            kwargs["format"] = response_format.model_json_schema()

        response = chat(**kwargs)
        tool_calls = getattr(response.message, "tool_calls", None)

        if tool_calls:
            if tools:
                for call in tool_calls:
                    for tool in tools:
                        if tool.__name__ == call.function.name:
                            tool(**call.function.arguments)
            return None, tool_calls

        content = response.message.content or ""
        if not response_format:
            return content, None

        try:
            return response_format.model_validate_json(content), None
        except Exception:
            return response_format.model_validate(json.loads(content)), None
