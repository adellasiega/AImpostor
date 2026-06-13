from framework.agent import Agent
from framework.game import Game
from framework.human import Human
from tests.fixtures.mock_llm import MockLLMManager


class TestNewTurnNode:

    def test_new_turn_increments_turn_counter(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        state = {
            "turn": 0,
            "current_player": 5,
            "votes": {"old": "data"},
            "vote_reasons": {"old": "reasons"},
            "last_eliminated": "someone",
            "last_chance_guess": "something",
            "players": [],
            "eliminated_players": [],
            "config": sample_config,
        }

        new_state = game.new_turn(state)

        assert new_state["turn"] == 1
        assert new_state["current_player"] == 0
        assert new_state["votes"] == {}
        assert new_state["vote_reasons"] == {}
        assert new_state["last_eliminated"] is None
        assert new_state["last_chance_guess"] is None


class TestChatNode:

    def test_chat_disabled_returns_unchanged_state(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        sample_config["chat_enabled"] = False

        state = {
            "config": sample_config,
            "players": [],
            "chat_history": "CHAT\n",
        }

        new_state = game.chat(state)

        assert new_state["chat_history"] == "CHAT\n"

    def test_chat_with_human_player(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        sample_config["chat_enabled"] = True
        sample_config["chat_messages_per_player"] = 1

        def mock_input(prompt):
            return "Hello everyone"

        human = Human(input_fn=mock_input)
        human.id = 0
        human.name = "Alice"

        state = {
            "config": sample_config,
            "players": [human],
            "eliminated_players": [],
            "chat_history": "CHAT",
        }

        new_state = game.chat(state)

        assert "Hello everyone" in new_state["chat_history"]

    def test_chat_with_agent_skip(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        sample_config["chat_enabled"] = True
        sample_config["chat_messages_per_player"] = 1

        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)
        agent.id = 1
        agent.word = "pizza"

        state = {
            "config": sample_config,
            "players": [agent],
            "eliminated_players": [],
            "chat_history": "CHAT",
            "word_history": "",
            "turn": 1,
        }

        new_state = game.chat(state)

        assert new_state["chat_history"] == "CHAT"


class TestSayWordNode:

    def test_say_word_with_human(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)

        def mock_input(prompt):
            return "delicious"

        human = Human(input_fn=mock_input)
        human.id = 0
        human.name = "Bob"

        state = {
            "config": sample_config,
            "players": [human],
            "eliminated_players": [],
            "used_words": [],
            "word_history": "",
        }

        new_state = game.say_word(state)

        assert "delicious" in new_state["used_words"]
        assert "delicious" in new_state["word_history"]

    def test_say_word_with_agent(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)

        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)
        agent.id = 1
        agent.word = "pizza"

        state = {
            "config": sample_config,
            "players": [agent],
            "eliminated_players": [],
            "used_words": [],
            "word_history": "",
            "chat_history": "",
            "turn": 1,
        }

        new_state = game.say_word(state)

        # MockLLM returns "word1"
        assert "word1" in new_state["used_words"]


class TestVotingNode:

    def test_voting_with_human(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)

        responses = iter(["1", "they seem suspicious", "0", "random guess"])

        def mock_input(prompt):
            return next(responses)

        human1 = Human(input_fn=mock_input)
        human1.id = 0
        human2 = Human(input_fn=mock_input)
        human2.id = 1

        state = {
            "config": sample_config,
            "players": [human1, human2],
            "eliminated_players": [],
            "votes": {},
            "vote_reasons": {},
        }

        new_state = game.voting(state)

        assert 0 in new_state["votes"]
        assert 1 in new_state["votes"]
        assert new_state["votes"][0] == 1
        assert new_state["vote_reasons"][0] == "they seem suspicious"


class TestWinCheckNode:

    def test_win_check_game_continues(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)

        human1 = Human()
        human1.id = 0
        human1.is_impostor = False

        human2 = Human()
        human2.id = 1
        human2.is_impostor = False

        human3 = Human()
        human3.id = 2
        human3.is_impostor = True

        state = {
            "config": sample_config,
            "players": [human1, human2, human3],
            "eliminated_players": [],
            "game_over": False,
            "winner": None,
            "turn": 1,
        }

        new_state = game.win_check(state)

        assert new_state["game_over"] is False

    def test_win_check_impostors_eliminated(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)

        human1 = Human()
        human1.id = 0
        human1.is_impostor = False

        state = {
            "config": sample_config,
            "players": [human1],
            "eliminated_players": [],
            "game_over": False,
            "winner": None,
        }

        new_state = game.win_check(state)

        assert new_state["game_over"] is True
        assert new_state["winner"] == "Civilians"


class TestRouteAfterWinCheck:

    def test_route_when_game_over(self):
        game = Game()
        state = {"game_over": True}

        route = game.route_after_win_check(state)

        assert route == "end_game"

    def test_route_when_game_continues(self):
        game = Game()
        state = {"game_over": False}

        route = game.route_after_win_check(state)

        assert route == "new_turn"
