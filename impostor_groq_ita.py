import os
import random
import json
from groq import Groq

# ─── Configuration ────────────────────────────────────────────────────────────

GROQ_MODEL = "llama-3.1-8b-instant"

def load_groq_api_key():
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key.strip()

    for path in (".env", ".groq_api_key"):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
                    if line and not line.startswith("#"):
                        return line

    return input("Inserisci la tua GROQ_API_KEY: ").strip()


# Initialize Groq client
GROQ_API_KEY = load_groq_api_key()
if not GROQ_API_KEY:
    raise RuntimeError("Manca la GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

WORD_PAIRS = [
    ("gatto", "cane"),
    ("caffe", "te"),
    ("spiaggia", "piscina"),
    ("spada", "coltello"),
    ("castello", "fortezza"),
    ("fiume", "lago"),
    ("chitarra", "violino"),
    ("mare", "oceano"),
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

def display_role(role):
    return "civile" if role == "civilian" else "impostor"

# ─── Groq API ─────────────────────────────────────────────────────────────────

def groq_chat(messages):
    """Send messages to Groq API and get response."""
    chat_completion = client.chat.completions.create(
        messages=messages,
        model=GROQ_MODEL,
    )
    return chat_completion.choices[0].message.content.strip()

# ─── Context Builder ──────────────────────────────────────────────────────────

def build_context(game, player):
    """Build the full game context from a player's perspective."""
    lines = []

    lines.append("Stai giocando a un gioco chiamato Impostor.")
    lines.append(f"La tua parola segreta e: {player['word']}")
    lines.append(f"Il tuo ruolo e: {display_role(player['role'])}")
    lines.append("")
    lines.append("Regole:")
    lines.append("- Ogni giocatore ha una parola segreta. I civili condividono una parola, i giocatori impostors ne condividono un'altra simile.")
    lines.append("- A ogni round, ogni giocatore dice un indizio breve che descrive la sua parola.")
    lines.append("- Dopo tutti gli indizi, i giocatori votano per eliminare il giocatore piu sospetto.")
    lines.append("- I civili vincono eliminando tutti i giocatori impostors.")
    lines.append("- I giocatori impostors vincono sopravvivendo fino a essere uguali o piu numerosi dei civili.")
    lines.append("")

    if game["eliminations"]:
        lines.append("Giocatori eliminati finora:")
        for e in game["eliminations"]:
            lines.append(f"  - Round {e['round']}: {e['name']} e stato eliminato (ruolo: {display_role(e['role'])})")
        lines.append("")

    if game["history"]:
        lines.append("Cronologia della partita:")
        for round_data in game["history"]:
            lines.append(f"  Indizi del round {round_data['round']}:")
            for name, clue in round_data["clues"].items():
                tag = " (tu)" if name == player["name"] else ""
                lines.append(f"    - {name}{tag}: {clue}")
        lines.append("")

    return "\n".join(lines)

def alive_players(game):
    return [p for p in game["players"] if p["alive"]]

def alive_names(game, exclude=None):
    return [p["name"] for p in alive_players(game) if p["name"] != exclude]

# ─── Clue Phase ───────────────────────────────────────────────────────────────

def get_clue_human(player, game):
    clue = input(f"  {player['name']}, inserisci il tuo indizio: ").strip()
    return clue

def get_clue_llm(player, game):
    context = build_context(game, player)
    others = alive_names(game, exclude=player["name"])
    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": (
            f"Gli altri giocatori sono: {', '.join(others)}.\n"
            "E il tuo turno di dare un indizio. "
            "Rispondi con UNA SOLA parola che descrive la tua parola segreta. "
            "Non spiegare, non usare punteggiatura. Solo una parola. "
            f"La parola non puo essere una di queste: {', '.join([clue for round_data in game['history'] for clue in round_data['clues'].values()])}."
        )},
    ]
    raw = groq_chat(messages)
    # Take only the first word in case the model adds extra text
    clue = raw.split()[0].strip(".,!?\"'") if raw else "..."
    return clue

def clue_phase(game):
    print(f"\n--- Round {game['round']} indizi ---")
    clues = {}
    for player in alive_players(game):
        if player["is_human"]:
            clue = get_clue_human(player, game)
        else:
            print(f"  {player['name']} sta pensando...")
            clue = get_clue_llm(player, game)
            print(f"  {player['name']}: {clue}")
        clues[player["name"]] = clue
        player["clues"].append(clue)
    return clues

# ─── Vote Phase ───────────────────────────────────────────────────────────────

def get_vote_human(player, game):
    candidates = alive_names(game, exclude=player["name"])
    print(f"  Giocatori vivi: {', '.join(candidates)}")
    while True:
        vote = input(f"  {player['name']}, chi voti per eliminare? ").strip()
        if vote in candidates:
            return vote
        print(f"  Scelta non valida. Scegli tra: {', '.join(candidates)}")

def get_vote_llm(player, game):
    context = build_context(game, player)
    candidates = alive_names(game, exclude=player["name"])
    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": (
            f"In base agli indizi dati finora, vota per eliminare il giocatore più sospetto.\n"
            f"Scegli esattamente un nome da questa lista: {', '.join(candidates)}.\n"
            "Rispondi SOLO con il nome del giocatore, nient'altro."
        )},
    ]
    raw = groq_chat(messages)
    # Match the response to a valid candidate
    for candidate in candidates:
        if candidate.lower() in raw.lower():
            return candidate
    # Fallback: random vote
    return random.choice(candidates)

def vote_phase(game):
    print(f"\n--- Round {game['round']} voti ---")
    votes = {}
    for player in alive_players(game):
        if player["is_human"]:
            vote = get_vote_human(player, game)
        else:
            print(f"  {player['name']} sta votando...")
            vote = get_vote_llm(player, game)
            print(f"  {player['name']} vota: {vote}")
        votes[player["name"]] = vote

    # Tally votes
    tally = {}
    for target in votes.values():
        tally[target] = tally.get(target, 0) + 1

    print(f"\n  Conteggio voti: {tally}")
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
    print("=== CONFIGURAZIONE DI IMPOSTOR ===\n")

    n_total = int(input("Numero totale di giocatori: "))
    n_undercover = int(input("Numero di giocatori impostors: "))
    n_human = int(input("Numero di giocatori umani: "))

    n_llm = n_total - n_human
    print(f"\n  {n_human} giocatore/i umano/i, {n_llm} giocatore/i AI, {n_undercover} giocatore/i impostors\n")

    # Name human players
    player_names = []
    for i in range(n_human):
        name = input(f"  Nome del giocatore umano {i+1}: ").strip()
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
    print("\n--- Parole segrete (mostrare solo al giocatore giusto) ---")
    for p in players:
        if p["is_human"]:
            input(f"  Premi Invio quando {p['name']} e pronto...")
            print(f"  {p['name']}, la tua parola e: {p['word']}  (ruolo: {display_role(p['role'])})")
            input("  Premi Invio per nascondere...")
            print("\n" * 10)

    return make_game(players)

# ─── Main Game Loop ───────────────────────────────────────────────────────────

def play(game):
    print("\n=== INIZIO PARTITA ===")
    print(f"Giocatori: {[p['name'] for p in game['players']]}\n")

    while True:
        game["round"] += 1

        # Clue phase
        clues = clue_phase(game)
        game["history"].append({"round": game["round"], "clues": clues})

        # Show all clues summary
        print(f"\n  Riassunto degli indizi del round {game['round']}:")
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
        print(f"\n  {eliminated_name} e stato eliminato! Era {display_role(eliminated['role'])}.")

        # Check winner
        winner = check_winner(game)
        if winner:
            print(f"\n=== FINE PARTITA ===")
            if winner == "civilians":
                print("Vincono i civili! Tutti i giocatori impostors sono stati eliminati.")
            else:
                print("Vincono i giocatori impostors! Hanno preso il controllo.")
            print("\nRuoli finali:")
            for p in game["players"]:
                print(f"  {p['name']}: {display_role(p['role'])} (parola: {p['word']})")
            break

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    game = setup_game()
    play(game)
