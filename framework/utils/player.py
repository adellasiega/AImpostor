from abc import ABC, abstractmethod
from typing import Any


class Player(ABC):
    def __init__(self, is_impostor: bool = False) -> None:
        self.id: int | None = None
        self.name: str = ""
        self.is_impostor = is_impostor
        self.word = ""

    @property
    def role(self) -> str:
        return "Impostor" if self.is_impostor else "Civilian"

    @property
    def label(self) -> str:
        return self.name or f"Player {self.id}"

    @abstractmethod
    def say_word(self, game_state: dict[str, Any]) -> str:
        pass

    @abstractmethod
    def send_message(self, game_state: dict[str, Any]) -> str | None:
        pass

    @abstractmethod
    def vote(self, game_state: dict[str, Any]) -> tuple[int, str]:
        pass

    @abstractmethod
    def guess_word(self, game_state: dict[str, Any]) -> str:
        pass
