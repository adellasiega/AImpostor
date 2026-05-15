
import random
import requests
import json

# ─── Configuration ────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2"

WORD_PAIRS = [
    ("cat", "dog"),
    ("coffee", "tea"),
    ("beach", "pool"),
    ("pizza", "pasta"),
    ("sword", "knife"),
    ("castle", "fortress"),
    ("river", "lake"),
    ("guitar", "violin"),
]

# ─── Game State ───────────────────────────────────────────────────────────────

def make_player(name, word, role, is_human):
    return {
        "name": name,
        "word": word,
        "role": role,       # "civilian" or "undercover"
        "is_human": is_human,
        "alive": True,
        "clues": [],        # list of clues given, one per round
    }

def make_game(players):
    return {
        "players": players,
        "round": 0,
        "history": [],      # list of round dicts
        "eliminations": [], # list of {"round": N, "name": X, "role": Y}
    }

# ─── Ollama API ───────────────────────────────────────────────────────────────

def ollama_chat(messages):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json()["message"]["content"].strip()

# ─── Context Builder ──────────────────────────────────────────────────────────

def build_context(game, player):
    """Build the full game context from a player's perspective."""
    lines = []

    lines.append("You are playing a game called Undercover.")
    lines.append(f"Your secret word is: {player['word']}")
    lines.append(f"Your role is: {player['role']}")
    lines.append("")
    lines.append("Rules:")
    lines.append("- Each player has a secret word. Civilians share one word, undercover agents share another similar word.")
    lines.append("- Each round, every player gives one short clue describing their word.")
    lines.append("- After all clues, players vote to eliminate the most suspicious player.")
    lines.append("- Civilians win by eliminating all undercover agents.")
    lines.append("- Undercover agents win by surviving until they equal or outnumber civilians.")
    lines.append("")

    if game["eliminations"]:
        lines.append("Eliminated players so far:")
        for e in game["eliminations"]:
            lines.append(f"  - Round {e['round']}: {e['name']} was eliminated (they were {e['role']})")
        lines.append("")

    if game["history"]:
        lines.append("Game history:")
        for round_data in game["history"]:
            lines.append(f"  Round {round_data['round']} clues:")
            for name, clue in round_data["clues"].items():
                tag = " (you)" if name == player["name"] else ""
                lines.append(f"    - {name}{tag}: {clue}")
        lines.append("")

    return "\n".join(lines)

def alive_players(game):
    return [p for p in game["players"] if p["alive"]]

def alive_names(game, exclude=None):
    return [p["name"] for p in alive_players(game) if p["name"] != exclude]

# ─── Clue Phase ───────────────────────────────────────────────────────────────

def get_clue_human(player, game):
    clue = input(f"  {player['name']}, enter your clue: ").strip()
    return clue

def get_clue_llm(player, game):
    context = build_context(game, player)
    others = alive_names(game, exclude=player["name"])
    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": (
            f"The other players are: {', '.join(others)}.\n"
            "It is your turn to give a clue. "
            "Reply with a SINGLE word that describes your secret word. "
            "Do not explain, do not add punctuation. Just one word."
        )},
    ]
    raw = ollama_chat(messages)
    # Take only the first word in case the model adds extra text
    clue = raw.split()[0].strip(".,!?\"'") if raw else "..."
    return clue

def clue_phase(game):
    print(f"\n--- Round {game['round']} clues ---")
    clues = {}
    for player in alive_players(game):
        if player["is_human"]:
            clue = get_clue_human(player, game)
        else:
            print(f"  {player['name']} is thinking...")
            clue = get_clue_llm(player, game)
            print(f"  {player['name']}: {clue}")
        clues[player["name"]] = clue
        player["clues"].append(clue)
    return clues

# ─── Vote Phase ───────────────────────────────────────────────────────────────

def get_vote_human(player, game):
    candidates = alive_names(game, exclude=player["name"])
    print(f"  Alive players: {', '.join(candidates)}")
    while True:
        vote = input(f"  {player['name']}, who do you vote to eliminate? ").strip()
        if vote in candidates:
            return vote
        print(f"  Invalid choice. Choose from: {', '.join(candidates)}")

def get_vote_llm(player, game):
    context = build_context(game, player)
    candidates = alive_names(game, exclude=player["name"])
    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": (
            f"Based on the clues given so far, vote to eliminate the most suspicious player.\n"
            f"Choose exactly one name from this list: {', '.join(candidates)}.\n"
            "Reply with ONLY the player name, nothing else."
        )},
    ]
    raw = ollama_chat(messages)
    # Match the response to a valid candidate
    for candidate in candidates:
        if candidate.lower() in raw.lower():
            return candidate
    # Fallback: random vote
    return random.choice(candidates)

def vote_phase(game):
    print(f"\n--- Round {game['round']} votes ---")
    votes = {}
    for player in alive_players(game):
        if player["is_human"]:
            vote = get_vote_human(player, game)
        else:
            print(f"  {player['name']} is voting...")
            vote = get_vote_llm(player, game)
            print(f"  {player['name']} votes for: {vote}")
        votes[player["name"]] = vote

    # Tally votes
    tally = {}
    for target in votes.values():
        tally[target] = tally.get(target, 0) + 1

    print(f"\n  Vote tally: {tally}")
    eliminated_name = max(tally, key=tally.get)
    return eliminated_name

# ─── Win Condition ────────────────────────────────────────────────────────────

def check_winner(game):
    alive = alive_players(game)
    n_undercover = sum(1 for p in alive if p["role"] == "undercover")
    n_civilian = sum(1 for p in alive if p["role"] == "civilian")
    if n_undercover == 0:
        return "civilians"
    if n_civilian <= 1:
        return "undercover"
    return None

# ─── Setup ────────────────────────────────────────────────────────────────────

def setup_game():
    print("=== UNDERCOVER GAME SETUP ===\n")

    n_total = int(input("Total number of players: "))
    n_undercover = int(input("Number of undercover agents: "))
    n_human = int(input("Number of human players: "))

    n_llm = n_total - n_human
    print(f"\n  {n_human} human(s), {n_llm} AI player(s), {n_undercover} undercover agent(s)\n")

    # Name human players
    player_names = []
    for i in range(n_human):
        name = input(f"  Name of human player {i+1}: ").strip()
        player_names.append((name, True))
    for i in range(n_llm):
        player_names.append((f"AI-{i+1}", False))

    # Shuffle and assign roles
    random.shuffle(player_names)
    roles = ["undercover"] * n_undercover + ["civilian"] * (n_total - n_undercover)
    random.shuffle(roles)

    # Pick word pair
    civilian_word, undercover_word = random.choice(WORD_PAIRS)

    players = []
    for (name, is_human), role in zip(player_names, roles):
        word = undercover_word if role == "undercover" else civilian_word
        players.append(make_player(name, word, role, is_human))

    # Tell human players their word privately
    print("\n--- Secret words (show only to the right player) ---")
    for p in players:
        if p["is_human"]:
            input(f"  Press Enter when {p['name']} is ready...")
            print(f"  {p['name']}, your word is: {p['word']}  (role: {p['role']})")
            input("  Press Enter to hide...")
            print("\n" * 10)

    return make_game(players)

# ─── Main Game Loop ───────────────────────────────────────────────────────────

def play(game):
    print("\n=== GAME START ===")
    print(f"Players: {[p['name'] for p in game['players']]}\n")

    while True:
        game["round"] += 1

        # Clue phase
        clues = clue_phase(game)
        game["history"].append({"round": game["round"], "clues": clues})

        # Show all clues summary
        print(f"\n  Summary of round {game['round']} clues:")
        for name, clue in clues.items():
            print(f"    {name}: {clue}")

        # Vote phase
        eliminated_name = vote_phase(game)

        # Eliminate player
        eliminated = next(p for p in game["players"] if p["name"] == eliminated_name)
        eliminated["alive"] = False
        game["eliminations"].append({
            "round": game["round"],
            "name": eliminated_name,
            "role": eliminated["role"],
        })
        print(f"\n  {eliminated_name} has been eliminated! They were a {eliminated['role']}.")

        # Check winner
        winner = check_winner(game)
        if winner:
            print(f"\n=== GAME OVER ===")
            if winner == "civilians":
                print("Civilians win! All undercover agents have been eliminated.")
            else:
                print("Undercover agents win! They have taken over.")
            print("\nFinal roles:")
            for p in game["players"]:
                print(f"  {p['name']}: {p['role']} (word: {p['word']})")
            break

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    game = setup_game()
    play(game)
import random
import requests
import json

# ─── Configuration ────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2"

WORD_PAIRS = [
    ("cat", "dog"),
    ("coffee", "tea"),
    ("beach", "pool"),
    ("pizza", "pasta"),
    ("sword", "knife"),
    ("castle", "fortress"),
    ("river", "lake"),
    ("guitar", "violin"),
]

# ─── Game State ───────────────────────────────────────────────────────────────

def make_player(name, word, role, is_human):
    return {
        "name": name,
        "word": word,
        "role": role,       # "civilian" or "undercover"
        "is_human": is_human,
        "alive": True,
        "clues": [],        # list of clues given, one per round
    }

def make_game(players):
    return {
        "players": players,
        "round": 0,
        "history": [],      # list of round dicts
        "eliminations": [], # list of {"round": N, "name": X, "role": Y}
    }

# ─── Ollama API ───────────────────────────────────────────────────────────────

def ollama_chat(messages):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json()["message"]["content"].strip()

# ─── Context Builder ──────────────────────────────────────────────────────────

def build_context(game, player):
    """Build the full game context from a player's perspective."""
    lines = []

    lines.append("You are playing a game called Undercover.")
    lines.append(f"Your secret word is: {player['word']}")
    lines.append(f"Your role is: {player['role']}")
    lines.append("")
    lines.append("Rules:")
    lines.append("- Each player has a secret word. Civilians share one word, undercover agents share another similar word.")
    lines.append("- Each round, every player gives one short clue describing their word.")
    lines.append("- After all clues, players vote to eliminate the most suspicious player.")
    lines.append("- Civilians win by eliminating all undercover agents.")
    lines.append("- Undercover agents win by surviving until they equal or outnumber civilians.")
    lines.append("")

    if game["eliminations"]:
        lines.append("Eliminated players so far:")
        for e in game["eliminations"]:
            lines.append(f"  - Round {e['round']}: {e['name']} was eliminated (they were {e['role']})")
        lines.append("")

    if game["history"]:
        lines.append("Game history:")
        for round_data in game["history"]:
            lines.append(f"  Round {round_data['round']} clues:")
            for name, clue in round_data["clues"].items():
                tag = " (you)" if name == player["name"] else ""
                lines.append(f"    - {name}{tag}: {clue}")
        lines.append("")

    return "\n".join(lines)

def alive_players(game):
    return [p for p in game["players"] if p["alive"]]

def alive_names(game, exclude=None):
    return [p["name"] for p in alive_players(game) if p["name"] != exclude]

# ─── Clue Phase ───────────────────────────────────────────────────────────────

def get_clue_human(player, game):
    clue = input(f"  {player['name']}, enter your clue: ").strip()
    return clue

def get_clue_llm(player, game):
    context = build_context(game, player)
    others = alive_names(game, exclude=player["name"])
    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": (
            f"The other players are: {', '.join(others)}.\n"
            "It is your turn to give a clue. "
            "Reply with a SINGLE word that describes your secret word. "
            "Do not explain, do not add punctuation. Just one word."
        )},
    ]
    raw = ollama_chat(messages)
    # Take only the first word in case the model adds extra text
    clue = raw.split()[0].strip(".,!?\"'") if raw else "..."
    return clue

def clue_phase(game):
    print(f"\n--- Round {game['round']} clues ---")
    clues = {}
    for player in alive_players(game):
        if player["is_human"]:
            clue = get_clue_human(player, game)
        else:
            print(f"  {player['name']} is thinking...")
            clue = get_clue_llm(player, game)
            print(f"  {player['name']}: {clue}")
        clues[player["name"]] = clue
        player["clues"].append(clue)
    return clues

# ─── Vote Phase ───────────────────────────────────────────────────────────────

def get_vote_human(player, game):
    candidates = alive_names(game, exclude=player["name"])
    print(f"  Alive players: {', '.join(candidates)}")
    while True:
        vote = input(f"  {player['name']}, who do you vote to eliminate? ").strip()
        if vote in candidates:
            return vote
        print(f"  Invalid choice. Choose from: {', '.join(candidates)}")

def get_vote_llm(player, game):
    context = build_context(game, player)
    candidates = alive_names(game, exclude=player["name"])
    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": (
            f"Based on the clues given so far, vote to eliminate the most suspicious player.\n"
            f"Choose exactly one name from this list: {', '.join(candidates)}.\n"
            "Reply with ONLY the player name, nothing else."
        )},
    ]
    raw = ollama_chat(messages)
    # Match the response to a valid candidate
    for candidate in candidates:
        if candidate.lower() in raw.lower():
            return candidate
    # Fallback: random vote
    return random.choice(candidates)

def vote_phase(game):
    print(f"\n--- Round {game['round']} votes ---")
    votes = {}
    for player in alive_players(game):
        if player["is_human"]:
            vote = get_vote_human(player, game)
        else:
            print(f"  {player['name']} is voting...")
            vote = get_vote_llm(player, game)
            print(f"  {player['name']} votes for: {vote}")
        votes[player["name"]] = vote

    # Tally votes
    tally = {}
    for target in votes.values():
        tally[target] = tally.get(target, 0) + 1

    print(f"\n  Vote tally: {tally}")
    eliminated_name = max(tally, key=tally.get)
    return eliminated_name

# ─── Win Condition ────────────────────────────────────────────────────────────

def check_winner(game):
    alive = alive_players(game)
    n_undercover = sum(1 for p in alive if p["role"] == "undercover")
    n_civilian = sum(1 for p in alive if p["role"] == "civilian")
    if n_undercover == 0:
        return "civilians"
    if n_civilian <= 1:
        return "undercover"
    return None

# ─── Setup ────────────────────────────────────────────────────────────────────

def setup_game():
    print("=== UNDERCOVER GAME SETUP ===\n")

    n_total = int(input("Total number of players: "))
    n_undercover = int(input("Number of undercover agents: "))
    n_human = int(input("Number of human players: "))

    n_llm = n_total - n_human
    print(f"\n  {n_human} human(s), {n_llm} AI player(s), {n_undercover} undercover agent(s)\n")

    # Name human players
    player_names = []
    for i in range(n_human):
        name = input(f"  Name of human player {i+1}: ").strip()
        player_names.append((name, True))
    for i in range(n_llm):
        player_names.append((f"AI-{i+1}", False))

    # Shuffle and assign roles
    random.shuffle(player_names)
    roles = ["undercover"] * n_undercover + ["civilian"] * (n_total - n_undercover)
    random.shuffle(roles)

    # Pick word pair
    civilian_word, undercover_word = random.choice(WORD_PAIRS)

    players = []
    for (name, is_human), role in zip(player_names, roles):
        word = undercover_word if role == "undercover" else civilian_word
        players.append(make_player(name, word, role, is_human))

    # Tell human players their word privately
    print("\n--- Secret words (show only to the right player) ---")
    for p in players:
        if p["is_human"]:
            input(f"  Press Enter when {p['name']} is ready...")
            print(f"  {p['name']}, your word is: {p['word']}  (role: {p['role']})")
            input("  Press Enter to hide...")
            print("\n" * 10)

    return make_game(players)

# ─── Main Game Loop ───────────────────────────────────────────────────────────

def play(game):
    print("\n=== GAME START ===")
    print(f"Players: {[p['name'] for p in game['players']]}\n")

    while True:
        game["round"] += 1

        # Clue phase
        clues = clue_phase(game)
        game["history"].append({"round": game["round"], "clues": clues})

        # Show all clues summary
        print(f"\n  Summary of round {game['round']} clues:")
        for name, clue in clues.items():
            print(f"    {name}: {clue}")

        # Vote phase
        eliminated_name = vote_phase(game)

        # Eliminate player
        eliminated = next(p for p in game["players"] if p["name"] == eliminated_name)
        eliminated["alive"] = False
        game["eliminations"].append({
            "round": game["round"],
            "name": eliminated_name,
            "role": eliminated["role"],
        })
        print(f"\n  {eliminated_name} has been eliminated! They were a {eliminated['role']}.")

        # Check winner
        winner = check_winner(game)
        if winner:
            print(f"\n=== GAME OVER ===")
            if winner == "civilians":
                print("Civilians win! All undercover agents have been eliminated.")
            else:
                print("Undercover agents win! They have taken over.")
            print("\nFinal roles:")
            for p in game["players"]:
                print(f"  {p['name']}: {p['role']} (word: {p['word']})")
            break

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    game = setup_game()
    play(game)
