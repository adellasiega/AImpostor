from typing import Any

from .utils.data_types import (
    ChatOutputFormat,
    GameState,
    GuessOutputFormat,
    VoteOutputFormat,
    WordOutputFormat,
)
from .utils.llm_manager import LLMManager
from .utils.player import Player


class Agent(Player):
    def __init__(
        self,
        llm_manager: LLMManager,
        config: dict,
        is_impostor: bool = False,
    ) -> None:
        super().__init__(is_impostor=is_impostor)
        self.llm = llm_manager
        self.config = config

    def _visible_context(self, game_state: GameState) -> str:
        active_players = [
            {"id": player.id, "name": player.label}
            for player in game_state["players"]
        ]
        eliminated = [
            {"id": player.id, "name": player.label, "role": player.role}
            for player in game_state["eliminated_players"]
        ]
        return self.config["context_template"].format(
            player_id=self.id,
            player_name=self.label,
            role=self.role,
            own_word=self.word,
            active_players=active_players,
            eliminated_players=eliminated,
            chat_history=game_state["chat_history"],
            word_history=game_state["word_history"],
            turn=game_state["turn"],
        )

    def _ask(self, prompt_key: str, game_state: GameState, response_format):
        prompt = self.config[prompt_key].format(context=self._visible_context(game_state))
        response, _ = self.llm.ask(
            prompt=prompt,
            system_prompt=self.config["system_prompt_rules"],
            response_format=response_format,
        )
        return response

    def say_word(self, game_state: GameState) -> str:
        response = self._ask("say_word_prompt", game_state, WordOutputFormat)
        if isinstance(response, WordOutputFormat):
            return response.word.strip()
        return ""

    def send_message(self, game_state: GameState) -> str | None:
        response = self._ask("send_message_prompt", game_state, ChatOutputFormat)
        if not isinstance(response, ChatOutputFormat) or response.action == "skip":
            return None
        return response.message.strip() or None

    def vote(self, game_state: GameState) -> tuple[int, str]:
        response = self._ask("vote_prompt", game_state, VoteOutputFormat)
        if isinstance(response, VoteOutputFormat):
            return response.player_id, response.reason.strip()
        return -1, ""

    def guess_word(self, game_state: dict[str, Any]) -> str:
        response = self._ask("guess_word_prompt", game_state, GuessOutputFormat)
        if isinstance(response, GuessOutputFormat):
            return response.word.strip()
        return ""
