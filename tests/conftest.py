import pytest
import random
import json

@pytest.fixture
def sample_config():
    return {
        "ollama": {"model_name": "test-model", "think": False, "options": {}},
        "max_turns": 5,
        "chat_enabled": False,  # no chat for now
        "word_pairs": [
            {"civilian_word": "pizza", "impostor_word": "focaccia"}
        ],
        "system_prompt_rules": "Test",
        "context_template": "Player {player_id}",
        "say_word_prompt": "Say word",
        "vote_prompt": "Vote",
        "send_message_prompt": "Message",
        "guess_word_prompt": "Guess",
        "chat_history_header": "CHAT",
        "word_history_header": "WORDS",
        "chat_line_template": "\n{message}",
        "word_line_template": "\n{word}",
        "vote_line_template": "{reason}",
        "role_reveal_template": "{role}",
        "clear_screen_between_reveals": False,
    }

@pytest.fixture
def mock_rng():
    rng = random.Random()
    rng.seed(42)
    return rng

@pytest.fixture
def tmp_config_file(tmp_path, sample_config):
    config_file = tmp_path / "test_config.json"
    config_file.write_text(json.dumps(sample_config))
    return str(config_file)
