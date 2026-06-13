from framework.agent import Agent
from tests.fixtures.mock_llm import MockLLMManager


class TestAgentInit:

    def test_agent_creates_with_defaults(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)

        assert agent.is_impostor is False
        assert agent.llm is llm
        assert agent.config == sample_config

    def test_agent_creates_as_impostor(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config, is_impostor=True)

        assert agent.is_impostor is True

    def test_agent_role_civilian(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config, is_impostor=False)

        assert agent.role == "Civilian"

    def test_agent_role_impostor(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config, is_impostor=True)

        assert agent.role == "Impostor"

    def test_agent_label_with_id(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)
        agent.id = 5

        assert agent.label == "Player 5"

    def test_agent_label_with_name(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)
        agent.id = 5
        agent.name = "Alice"

        assert agent.label == "Alice"


class TestAgentSayWord:

    def test_say_word_returns_word(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)
        agent.id = 1
        agent.word = "pizza"

        state = {
            "config": sample_config,
            "players": [agent],
            "eliminated_players": [],
            "used_words": set(),
            "chat_history": "",
            "word_history": "",
            "turn": 1,
        }

        word = agent.say_word(state)

        assert word == "word1"
        assert llm.call_count == 1

    def test_say_word_uses_llm_manager(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)
        agent.id = 1
        agent.word = "pizza"

        state = {
            "config": sample_config,
            "players": [agent],
            "eliminated_players": [],
            "used_words": set(),
            "chat_history": "",
            "word_history": "",
            "turn": 1,
        }

        agent.say_word(state)
        agent.say_word(state)

        assert llm.call_count == 2


class TestAgentVote:

    def test_vote_returns_player_id_and_reason(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)
        agent.id = 1
        agent.word = "pizza"

        state = {
            "config": sample_config,
            "players": [agent],
            "eliminated_players": [],
            "used_words": set(),
            "chat_history": "",
            "word_history": "",
            "turn": 1,
        }

        player_id, reason = agent.vote(state)

        assert player_id == 1
        assert reason == "test"
        assert llm.call_count == 1


class TestAgentSendMessage:

    def test_send_message_skip(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)
        agent.id = 1
        agent.word = "pizza"

        state = {
            "config": sample_config,
            "players": [agent],
            "eliminated_players": [],
            "used_words": set(),
            "chat_history": "",
            "word_history": "",
            "turn": 1,
        }

        message = agent.send_message(state)

        assert message is None
        assert llm.call_count == 1


class TestAgentGuessWord:

    def test_guess_word_returns_word(self, sample_config):
        llm = MockLLMManager()
        agent = Agent(llm_manager=llm, config=sample_config)
        agent.id = 1
        agent.word = "focaccia"

        state = {
            "config": sample_config,
            "players": [agent],
            "eliminated_players": [],
            "used_words": set(),
            "chat_history": "",
            "word_history": "",
            "turn": 1,
        }

        guess = agent.guess_word(state)

        assert guess == "pizza"
        assert llm.call_count == 1
