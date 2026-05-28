import json
import os
import random
import re
from collections import Counter
from pathlib import Path
from typing import Callable

from agent import Agent
from human import Human
from utils.player import Player
from utils.data_types import GameState
from ollama_manager import OllamaManager
from langgraph.graph import END, START, StateGraph



class Game:
    def __init__(
        self,
        config_file: str = "config.json",
        input_fn: Callable[[str], str] = input,
        rng: random.Random | None = None,
    ) -> None:
        self.config_file = config_file
        self.input_fn = input_fn
        self.rng = rng or random.Random()

    def build_graph(self):

        graph = StateGraph(GameState)
        graph.add_node("game_settings", self.game_settings)
        graph.add_node("show_word_and_roles", self.show_word_and_roles)
        graph.add_node("new_turn", self.new_turn)
        graph.add_node("chat", self.chat)
        graph.add_node("say_word", self.say_word)
        graph.add_node("voting", self.voting)
        graph.add_node("win_check", self.win_check)
        graph.add_node("end_game", self.end_game)

        graph.add_edge(START, "game_settings")
        graph.add_edge("game_settings", "show_word_and_roles")
        graph.add_edge("show_word_and_roles", "new_turn")
        graph.add_edge("new_turn", "chat")
        graph.add_edge("chat", "say_word")
        graph.add_edge("say_word", "voting")
        graph.add_edge("voting", "win_check")
        graph.add_conditional_edges(
            "win_check",
            self.route_after_win_check,
            {"new_turn": "new_turn", "end_game": "end_game"},
        )
        graph.add_edge("end_game", END)
        return graph.compile()

    def run(self) -> GameState:
        graph = self.build_graph()
        return graph.invoke({"config_file": self.config_file})

    def load_config(self) -> dict:
        with open(self.config_file, "r", encoding="utf-8") as file:
            return json.load(file)

    def game_settings(self, state: GameState) -> GameState:
        config_file = state.get("config_file", self.config_file)
        self.config_file = config_file
        config = self.load_config()

        seed = config.get("random_seed")
        if seed is not None:
            self.rng.seed(seed)

        print("Insert game settings:")
        n_humans = self._read_int("- Number of human players: ", minimum=0)
        n_agents = self._read_int("- Number of LLM agents: ", minimum=0)
        n_impostors = self._read_int("- Number of impostors: ", minimum=1)
        total_players = n_humans + n_agents
        if total_players < 3:
            raise ValueError("The game needs at least 3 total players.")
        if n_impostors >= total_players:
            raise ValueError("There must be at least one civilian.")

        players = self.create_players(config, n_humans, n_agents)
        self.assign_roles(players, n_impostors)
        self._validate_role_counts(players, n_impostors)
        civilian_word, impostor_word = self.choose_word_pair(config)
        for player in players:
            player.word = impostor_word if player.is_impostor else civilian_word

        return {
            "players": players,
            "eliminated_players": [],
            "turn": 0,
            "current_player": 0,
            "civilian_word": civilian_word,
            "impostor_word": impostor_word,
            "word_history": config["word_history_header"],
            "chat_history": config["chat_history_header"],
            "used_words": [],
            "votes": {},
            "vote_reasons": {},
            "last_eliminated": None,
            "last_chance_guess": None,
            "winner": None,
            "game_over": False,
            "config": config,
            "force_final_vote": False,
        }

    def create_players(self, config: dict, n_humans: int, n_agents: int) -> list[Player]:
        players: list[Player] = []
        for idx in range(n_humans):
            player = Human(input_fn=self.input_fn)
            player.name = f"Human {idx + 1}"
            players.append(player)

        model_config = config.get("ollama", {})
        llm = OllamaManager(
            model_name=model_config.get("model_name", config.get("model_name", "llama3.1")),
            think=model_config.get("think", False),
            options=model_config.get("options", {}),
        )
        for idx in range(n_agents):
            player = Agent(llm, config=config)
            player.name = f"Agent {idx + 1}"
            players.append(player)

        self.rng.shuffle(players)
        for idx, player in enumerate(players):
            player.id = idx
        return players

    def assign_roles(self, players: list[Player], n_impostors: int) -> None:
        impostor_ids = set(self.rng.sample(range(len(players)), n_impostors))
        for idx, player in enumerate(players):
            player.is_impostor = idx in impostor_ids

    def _validate_role_counts(self, players: list[Player], n_impostors: int) -> None:
        actual_impostors = sum(1 for player in players if player.is_impostor)
        if actual_impostors != n_impostors:
            raise RuntimeError(
                f"Role assignment failed: expected {n_impostors} impostors, "
                f"got {actual_impostors}."
            )

    def choose_word_pair(self, config: dict) -> tuple[str, str]:
        word_pairs = config.get("word_pairs", [])
        if not word_pairs:
            raise ValueError("config.json must define at least one word pair.")
        pair = self.rng.choice(word_pairs)
        return pair["civilian_word"], pair["impostor_word"]

    def show_word_and_roles(self, state: GameState) -> GameState:
        config = state["config"]
        for player in state["players"]:
            if isinstance(player, Human):
                self._clear_screen(config)
                self.input_fn(
                    f"Private card for [{player.id}] {player.label}. "
                    "Only this player should look. Press enter to reveal..."
                )
                self._clear_screen(config)
                print(config["role_reveal_template"].format(
                    player_id=player.id,
                    player_name=player.label,
                    role=player.role,
                    word=player.word,
                ))
                self.input_fn("Press enter to hide this card...")
                self._clear_screen(config)
        return state

    def new_turn(self, state: GameState) -> GameState:
        state["turn"] += 1
        state["current_player"] = 0
        state["votes"] = {}
        state["vote_reasons"] = {}
        state["last_eliminated"] = None
        state["last_chance_guess"] = None
        print(f"\n===== TURN {state['turn']} =====")
        self.print_public_state(state)
        return state

    def chat(self, state: GameState) -> GameState:
        config = state["config"]
        if not config.get("chat_enabled", True):
            return state

        limit = int(config.get("chat_messages_per_player", 1))
        if limit <= 0:
            return state

        print("\n--- Optional public chat ---")
        for player in list(state["players"]):
            for _ in range(limit):
                message = self._safe_chat_message(player, state)
                if not message:
                    break
                state["chat_history"] += config["chat_line_template"].format(
                    player_id=player.id,
                    player_name=player.label,
                    message=message,
                )
                print(f"[{player.id} {player.label}] {message}")
        return state

    def say_word(self, state: GameState) -> GameState:
        config = state["config"]
        print("\n--- Clues ---")
        for player in list(state["players"]):
            word = self._read_valid_clue(player, state)
            state["used_words"].append(word.lower())
            state["word_history"] += config["word_line_template"].format(
                player_id=player.id,
                player_name=player.label,
                word=word,
            )
            print(f"[{player.id} {player.label}] {word}")
        return state

    def voting(self, state: GameState) -> GameState:
        config = state["config"]
        print("\n--- Voting ---")
        self.print_voting_options(state)
        active_ids = {player.id for player in state["players"]}
        votes: dict[int, int] = {}
        reasons: dict[int, str] = {}

        for player in list(state["players"]):
            vote_id, reason = self._read_valid_vote(player, state, active_ids)
            votes[player.id] = vote_id
            reasons[player.id] = reason
            target = self._player_by_id(state["players"], vote_id)
            print(config["vote_line_template"].format(
                voter_id=player.id,
                voter_name=player.label,
                target_id=vote_id,
                target_name=target.label,
                reason=reason,
            ))

        state["votes"] = votes
        state["vote_reasons"] = reasons
        if not votes:
            state["last_eliminated"] = None
            return state

        counts = Counter(votes.values())
        top_count = max(counts.values())
        top_targets = [player_id for player_id, count in counts.items() if count == top_count]
        if len(top_targets) > 1:
            print("Vote tied. No player is eliminated this turn.")
            state["last_eliminated"] = None
            return state

        eliminated_id = top_targets[0]
        eliminated = next(player for player in state["players"] if player.id == eliminated_id)
        state["players"] = [player for player in state["players"] if player.id != eliminated_id]
        state["eliminated_players"].append(eliminated)
        state["last_eliminated"] = eliminated
        print(f"Eliminated: [{eliminated.id}] {eliminated.label}. Role: {eliminated.role}.")
        return state

    def win_check(self, state: GameState) -> GameState:
        eliminated = state.get("last_eliminated")
        if eliminated and eliminated.is_impostor:
            guess = eliminated.guess_word(state)
            state["last_chance_guess"] = guess
            if self._same_word(guess, state["civilian_word"]):
                state["winner"] = "Impostors"
                state["game_over"] = True
                print("The eliminated impostor guessed correctly.")
                return state
            print("The eliminated impostor guessed incorrectly.")

        impostors = [player for player in state["players"] if player.is_impostor]
        civilians = [player for player in state["players"] if not player.is_impostor]

        if not impostors:
            state["winner"] = "Civilians"
        elif not civilians or (len(impostors) == 1 and len(civilians) == 1):
            state["winner"] = "Impostors"
        elif state["turn"] >= int(state["config"].get("max_turns", 10)):
            state["winner"] = "Civilians"

        state["game_over"] = state["winner"] is not None
        return state

    def route_after_win_check(self, state: GameState) -> str:
        return "end_game" if state.get("game_over") else "new_turn"

    def end_game(self, state: GameState) -> GameState:
        print("\n===== GAME OVER =====")
        print(f"Winner: {state['winner']}")
        print(f"Civilian word: {state['civilian_word']}")
        print(f"Impostor word: {state['impostor_word']}")
        print("\nFinal roles:")
        all_players = sorted(
            state["players"] + state["eliminated_players"],
            key=lambda player: player.id,
        )
        for player in all_players:
            status = "eliminated" if player in state["eliminated_players"] else "active"
            print(f"- [{player.id}] {player.label}: {player.role}, {status}")
        print(f"\n{state['word_history']}")
        print(f"\n{state['chat_history']}")
        return state

    def print_public_state(self, state: GameState) -> None:
        print("Active players:")
        for player in state["players"]:
            print(f"- [{player.id}] {player.label}")
        if state["eliminated_players"]:
            print("Eliminated players:")
            for player in state["eliminated_players"]:
                print(f"- [{player.id}] {player.label}: {player.role}")

    def print_voting_options(self, state: GameState) -> None:
        print("Vote choices:")
        for choice, player in enumerate(state["players"]):
            print(f"- choice {choice}: [{player.id}] {player.label}")

    def _safe_chat_message(self, player: Player, state: GameState) -> str | None:
        try:
            message = player.send_message(state)
        except Exception as exc:
            print(f"{player.label} skipped chat because of an error: {exc}")
            return None
        if not message:
            return None
        return message.strip()[: int(state["config"].get("max_chat_chars", 240))]

    def _read_valid_clue(self, player: Player, state: GameState) -> str:
        for attempt in range(3):
            word = self._normalize_clue(player.say_word(state))
            if word and word.lower() not in state["used_words"]:
                return word
            if isinstance(player, Human):
                print("Invalid clue. Use one non-repeated word.")
        fallback = f"clue{state['turn']}{player.id}"
        while fallback.lower() in state["used_words"]:
            fallback += "x"
        return fallback

    def _read_valid_vote(
        self,
        player: Player,
        state: GameState,
        active_ids: set[int],
    ) -> tuple[int, str]:
        choice_to_player_id = {
            choice: candidate.id
            for choice, candidate in enumerate(state["players"])
            if candidate.id != player.id
        }
        allowed_ids = active_ids - {player.id}
        while True:
            try:
                raw_vote_id, reason = player.vote(state)
            except EOFError:
                raise
            except Exception as exc:
                if isinstance(player, Human):
                    print(f"Invalid vote: {exc}")
                    continue
                raw_vote_id, reason = self._fallback_vote(player, allowed_ids), ""
            vote_id = (
                choice_to_player_id.get(raw_vote_id, raw_vote_id)
                if isinstance(player, Human)
                else raw_vote_id
            )
            if vote_id in allowed_ids:
                return vote_id, reason
            if not isinstance(player, Human):
                return self._fallback_vote(player, allowed_ids), "fallback vote"
            print(f"Vote must be one of these choices: {sorted(choice_to_player_id)}")

    def _fallback_vote(self, player: Player, allowed_ids: set[int]) -> int:
        return sorted(allowed_ids)[0]

    def _player_by_id(self, players: list[Player], player_id: int) -> Player:
        return next(player for player in players if player.id == player_id)

    def _read_int(self, prompt: str, minimum: int) -> int:
        while True:
            value = self.input_fn(prompt).strip()
            try:
                parsed = int(value)
            except ValueError:
                print("Please enter an integer.")
                continue
            if parsed >= minimum:
                return parsed
            print(f"Please enter a value >= {minimum}.")

    def _clear_screen(self, config: dict) -> None:
        if config.get("clear_screen_between_reveals", True):
            os.system("cls" if os.name == "nt" else "clear")

    def _normalize_clue(self, word: str) -> str:
        raw = word.strip()
        if len(raw.split()) != 1:
            return ""
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "", raw)
        if not cleaned:
            return ""
        return cleaned

    def _same_word(self, guess: str, word: str) -> bool:
        return guess.strip().casefold() == word.strip().casefold()


def load_game(config_file: str = "config.json") -> Game:
    path = Path(config_file)
    return Game(config_file=str(path))
