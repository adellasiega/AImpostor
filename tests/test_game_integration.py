import json

import pytest

from framework.game import Game


class TestGameGraphBuilding:

    @pytest.fixture
    def integration_config(self, tmp_path):
        """Create a minimal config for integration testing"""
        config = {
            "ollama": {"model_name": "test-model", "think": False, "options": {}},
            "max_turns": 2,
            "chat_enabled": False,
            "word_pairs": [{"civilian_word": "apple", "impostor_word": "orange"}],
            "system_prompt_rules": "Be concise",
            "context_template": "Player {player_id}",
            "say_word_prompt": "Say a word",
            "vote_prompt": "Vote for a player",
            "send_message_prompt": "Send a message",
            "guess_word_prompt": "Guess the word",
            "chat_history_header": "CHAT:",
            "word_history_header": "WORDS:",
            "chat_line_template": "\n{player_name}: {message}",
            "word_line_template": "\n{player_name}: {word}",
            "vote_line_template": "{voter_name} votes {target_name}",
            "role_reveal_template": "You are {role}. Word: {word}",
            "clear_screen_between_reveals": False,
        }

        config_file = tmp_path / "integration_config.json"
        config_file.write_text(json.dumps(config))
        return str(config_file)

    def test_game_graph_builds_correctly(self, integration_config):
        """Test that the game graph is built with all nodes"""
        game = Game(config_file=integration_config)
        graph = game.build_graph()

        assert graph is not None


class TestGameValidation:

    def test_game_rejects_insufficient_players(self, sample_config, tmp_config_file, monkeypatch):
        """Test that game rejects less than 3 total players"""
        inputs = iter(["1", "1", "1"])

        def mock_input(prompt):
            return next(inputs)

        game = Game(config_file=tmp_config_file, input_fn=mock_input)

        with pytest.raises(ValueError, match="at least 3 total players"):
            game.run()

    def test_game_rejects_all_impostors(self, sample_config, tmp_config_file, monkeypatch):
        """Test that game rejects when all players are impostors"""
        inputs = iter(["2", "1", "3"])  # 3 players, 3 impostors

        def mock_input(prompt):
            return next(inputs)

        game = Game(config_file=tmp_config_file, input_fn=mock_input)

        with pytest.raises(ValueError, match="at least one civilian"):
            game.run()
