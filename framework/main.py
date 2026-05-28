import argparse

from game import Game


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AImpostor CLI game.")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to the JSON configuration file.",
    )
    args = parser.parse_args()

    game = Game(config_file=args.config)
    game.run()


if __name__ == "__main__":
    main()
