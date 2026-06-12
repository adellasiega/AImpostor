"""Mock LLM to test without calling the actual API"""

from typing import Type

from pydantic import BaseModel

from framework.utils.data_types import (
    ChatOutputFormat,
    GuessOutputFormat,
    VoteOutputFormat,
    WordOutputFormat,
)
from framework.utils.llm_manager import LLMManager


class MockLLMManager(LLMManager):
    """Mock LLM to return predefined responses"""

    def __init__(self):
        self.call_count = 0

    def ask(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list | None = None,
        response_format: Type[BaseModel] | None = None,
    ) -> tuple[BaseModel | str | None, list | None]:
        self.call_count += 1

        if response_format == WordOutputFormat:
            return WordOutputFormat(word=f"word{self.call_count}"), None
        elif response_format == VoteOutputFormat:
            return VoteOutputFormat(player_id=1, reason="test"), None
        elif response_format == ChatOutputFormat:
            return ChatOutputFormat(action="skip", message=""), None
        elif response_format == GuessOutputFormat:
            return GuessOutputFormat(word="pizza"), None

        return "response", None
