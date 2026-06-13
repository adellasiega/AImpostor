from framework.human import Human


class TestHumanInit:

    def test_human_creates_with_defaults(self):
        human = Human()

        assert human.is_impostor is False
        assert human.id is None 

    def test_human_creates_as_impostor(self):
        human = Human(is_impostor=True)

        assert human.is_impostor is True

    def test_human_accepts_custom_input_fn(self):
        def mock_input(prompt):
            return "test"

        human = Human(input_fn=mock_input)

        assert human.input_fn is mock_input

    def test_human_role_civilian(self):
        human = Human(is_impostor=False)

        assert human.role == "Civilian"

    def test_human_role_impostor(self):
        human = Human(is_impostor=True)

        assert human.role == "Impostor"

    def test_human_label_with_id(self):
        human = Human()
        human.id = 3

        assert human.label == "Player 3"

    def test_human_label_with_name(self):
        human = Human()
        human.id = 3
        human.name = "Bob"

        assert human.label == "Bob"


class TestHumanSayWord:

    def test_say_word_returns_input(self, sample_config):
        def mock_input(prompt):
            return "pizza"

        human = Human(input_fn=mock_input)
        state = {"config": sample_config}

        word = human.say_word(state)

        assert word == "pizza"

    def test_say_word_strips_whitespace(self, sample_config):
        def mock_input(prompt):
            return "  pizza  "

        human = Human(input_fn=mock_input)
        state = {"config": sample_config}

        word = human.say_word(state)

        assert word == "pizza"


class TestHumanVote:

    def test_vote_returns_id_and_reason(self, sample_config):
        responses = iter(["1", "suspicious behavior"])

        def mock_input(prompt):
            return next(responses)

        human = Human(input_fn=mock_input)
        state = {"config": sample_config}

        player_id, reason = human.vote(state)

        assert player_id == 1
        assert reason == "suspicious behavior"

    def test_vote_with_empty_reason(self, sample_config):
        responses = iter(["2", ""])

        def mock_input(prompt):
            return next(responses)

        human = Human(input_fn=mock_input)
        state = {"config": sample_config}

        player_id, reason = human.vote(state)

        assert player_id == 2
        assert reason == ""


class TestHumanSendMessage:

    def test_send_message_returns_message(self, sample_config):
        def mock_input(prompt):
            return "Hello everyone"

        human = Human(input_fn=mock_input)
        state = {"config": sample_config}

        message = human.send_message(state)

        assert message == "Hello everyone"

    def test_send_message_empty_returns_none(self, sample_config):
        def mock_input(prompt):
            return ""

        human = Human(input_fn=mock_input)
        state = {"config": sample_config}

        message = human.send_message(state)

        assert message is None

    def test_send_message_whitespace_returns_none(self, sample_config):
        def mock_input(prompt):
            return "   "

        human = Human(input_fn=mock_input)
        state = {"config": sample_config}

        message = human.send_message(state)

        assert message is None


class TestHumanGuessWord:

    def test_guess_word_returns_input(self, sample_config):
        def mock_input(prompt):
            return "civilian"

        human = Human(input_fn=mock_input)
        state = {"config": sample_config}

        guess = human.guess_word(state)

        assert guess == "civilian"

    def test_guess_word_strips_whitespace(self, sample_config):
        def mock_input(prompt):
            return "  civilian  "

        human = Human(input_fn=mock_input)
        state = {"config": sample_config}

        guess = human.guess_word(state)

        assert guess == "civilian"
