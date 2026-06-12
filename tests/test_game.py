from framework.agent import Agent
from framework.game import Game
from framework.human import Human


class TestGameInit:

    def test_game_creates_with_defaults(self):
        game = Game()
        assert game.config_file == "config.json"

    def test_game_creates_with_custom_config(self):
        game = Game(config_file="custom.json")
        assert game.config_file == "custom.json"


class TestPlayerCreation:

    def test_create_human_players(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        players = game.create_players(sample_config, n_humans=3, n_agents=0)

        assert len(players) == 3
        assert all(isinstance(p, Human) for p in players)
        assert all(p.id is not None for p in players)

    def test_create_agent_players(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        players = game.create_players(sample_config, n_humans=0, n_agents=2)

        assert len(players) == 2
        assert all(isinstance(p, Agent) for p in players)

    def test_create_mixed_players(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        players = game.create_players(sample_config, n_humans=2, n_agents=2)

        assert len(players) == 4
        humans = [p for p in players if isinstance(p, Human)]
        agents = [p for p in players if isinstance(p, Agent)]
        assert len(humans) == 2
        assert len(agents) == 2


class TestRoleAssignment:

    def test_assign_roles_correctly(self, sample_config, tmp_config_file, mock_rng):
        game = Game(config_file=tmp_config_file, rng=mock_rng)
        players = game.create_players(sample_config, n_humans=5, n_agents=0)

        game.assign_roles(players, n_impostors=2)

        impostors = [p for p in players if p.is_impostor]
        civilians = [p for p in players if not p.is_impostor]

        assert len(impostors) == 2
        assert len(civilians) == 3

    def test_all_players_have_role(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        players = game.create_players(sample_config, n_humans=4, n_agents=0)

        game.assign_roles(players, n_impostors=1)

        assert all(hasattr(p, "is_impostor") for p in players)


class TestWordPairing:

    def test_choose_word_pair(self, sample_config, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        civilian_word, impostor_word = game.choose_word_pair(sample_config)

        assert civilian_word == "pizza"
        assert impostor_word == "focaccia"


class TestGameHelpers:

    def test_normalize_clue_valid(self):
        game = Game()
        assert game._normalize_clue("pizza") == "pizza"
        assert game._normalize_clue("  pizza  ") == "pizza"

    def test_normalize_clue_invalid(self):
        game = Game()
        assert game._normalize_clue("two words") == ""
        assert game._normalize_clue("") == ""

    def test_same_word_case_insensitive(self):
        game = Game()
        assert game._same_word("Pizza", "pizza")
        assert game._same_word("PIZZA", "pizza")
        assert game._same_word("  pizza  ", "pizza")

    def test_same_word_different(self):
        game = Game()
        assert not game._same_word("pizza", "focaccia")


class TestGameFlow:

    def test_route_after_win_check_continue(self):
        game = Game()
        state = {"game_over": False}
        assert game.route_after_win_check(state) == "new_turn"

    def test_route_after_win_check_end(self):
        game = Game()
        state = {"game_over": True}
        assert game.route_after_win_check(state) == "end_game"

    def test_build_graph_creates_valid_graph(self, tmp_config_file):
        game = Game(config_file=tmp_config_file)
        graph = game.build_graph()
        assert graph is not None
