from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, Field


class GameState(TypedDict, total=False):
    players: list[Any]
    eliminated_players: list[Any]
    turn: int
    current_player: int
    civilian_word: str
    impostor_word: str
    word_history: str
    chat_history: str
    used_words: list[str]
    votes: dict[int, int]
    vote_reasons: dict[int, str]
    last_eliminated: Any | None
    last_chance_guess: str | None
    winner: str | None
    game_over: bool
    config: dict[str, Any]
    config_file: NotRequired[str]
    force_final_vote: bool


class ChatOutputFormat(BaseModel):
    action: Literal["send", "skip"] = Field(
        description="Use 'send' to post a public message or 'skip' to stay silent."
    )
    message: str = Field(default="", description="Public chat message when action is send.")


class WordOutputFormat(BaseModel):
    word: str = Field(description="A single non-repeated one-word clue.")


class VoteOutputFormat(BaseModel):
    player_id: int = Field(description="The id of an active player to vote against.")
    reason: str = Field(default="", description="Short public reason for the vote.")


class GuessOutputFormat(BaseModel):
    word: str = Field(description="The guessed civilian secret word.")
