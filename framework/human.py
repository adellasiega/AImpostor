from typing import Any

from .utils.player import Player


class Human(Player):
    def __init__(self, is_impostor: bool = False, input_fn=input) -> None:
        super().__init__(is_impostor=is_impostor)
        self.input_fn = input_fn

    def say_word(self, game_state: dict[str, Any]) -> str:
        return self.input_fn(f"[{self.label}] Say a one-word clue: ").strip()

    def send_message(self, game_state: dict[str, Any]) -> str | None:
        message = self.input_fn(f"[{self.label}] Chat message, or press enter to skip: ").strip()
        return message or None

    def vote(self, game_state: dict[str, Any]) -> tuple[int, str]:
        vote = self.input_fn(f"[{self.label}] Vote choice number: ").strip()
        reason = self.input_fn(f"[{self.label}] Reason, optional: ").strip()
        return int(vote), reason

    def guess_word(self, game_state: dict[str, Any]) -> str:
        return self.input_fn(f"[{self.label}] Last chance. Guess the civilian word: ").strip()
