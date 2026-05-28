from abc import ABC, abstractmethod
from typing import Type

from pydantic import BaseModel


class LLMManager(ABC):
    @abstractmethod
    def ask(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list | None = None,
        response_format: Type[BaseModel] | None = None,
    ) -> tuple[BaseModel | str | None, list | None]:
        pass
