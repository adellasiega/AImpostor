import ollama
import random
import json

MODEL = "nemotron-3-super:cloud"

# =====================================
# GIOCATORI
# =====================================

human_player = "TU"

ai_players = ["p1", "p2", "p3"]

players = [human_player] + ai_players

impostor = random.choice(players)

keyword = "Estintore"

words_said = {}

print("\n====================")
print(" PARTY GAME AI ")
print("====================\n")

print(f"La keyword è: {keyword}")

if impostor == human_player:
    print("TU SEI L'IMPOSTORE!\n")
else:
    print("Tu conosci la keyword.\n")

# =====================================
# FASE PAROLE
# =====================================

print("=== FASE PAROLE ===\n")

for player in players:

    # =================================
    # PLAYER UMANO
    # =================================

    if player == human_player:

        user_word = input("Inserisci la tua parola: ")

        words_said[player] = user_word

        continue

    # =================================
    # AI PLAYER
    # =================================

    knows_keyword = player != impostor

    public_state = {
        "fase": "parole",
        "parole_gia_dette": words_said,
    }

    private_state = {
        "knows_keyword": knows_keyword,
        "keyword": keyword if knows_keyword else None,
    }

    prompt = f"""
                Sei il giocatore {player} in un party game sociale! 

                STATO PUBBLICO:
                {json.dumps(public_state, indent=2)}

                STATO PRIVATO:
                {json.dumps(private_state, indent=2)}

                REGOLE:
                - Devi dire UNA SOLA parola.
                - NON puoi dire la keyword (se la conosci).
                - Se conosci la keyword, dai un indizio coerente senza far capire in modo ovvio la keyword.
                - Se NON conosci la keyword, prova dire una parola coerente alle altre già dette. Se non sono state dette parole tira a caso.
                - NON spiegare.
                - NON fare frasi.
                - NON usare punteggiatura.

                Rispondi SOLO con una parola.
            """

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0.9,
        }
    )

    word = response["message"]["content"].strip()

    words_said[player] = word

    print(f"{player}: {word}")

# =====================================
# MOSTRA PAROLE
# =====================================

print("\n=== PAROLE DETTE ===\n")

for p, w in words_said.items():
    print(f"{p}: {w}")

# =====================================
# FASE VOTO
# =====================================

print("\n=== FASE VOTO ===\n")

votes = {}

# =====================================
# VOTO UMANO
# =====================================

human_vote = input("Chi vuoi votare? ")

votes[human_player] = human_vote

# =====================================
# VOTI AI
# =====================================

for player in ai_players:

    prompt = f"""
                Sei il giocatore {player}!

                Parole dette:
                {json.dumps(words_said, indent=2)}

                REGOLE:
                - Vota il giocatore che secondo te NON conosceva la keyword e ha provato a capirla. La sua parola sarà probabilmente meno coerente con la keyword rispetto agli altri.
                - Non votare te stesso.
                - Rispondi SOLO con il nome del player.
            """

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0.7,
        }
    )

    vote = response["message"]["content"].strip()

    votes[player] = vote

    print(f"{player} vota -> {vote}")

# =====================================
# RISULTATI
# =====================================

vote_count = {}

for v in votes.values():
    vote_count[v] = vote_count.get(v, 0) + 1

eliminated = max(vote_count, key=vote_count.get)

print("\n====================")
print(" RISULTATI ")
print("====================\n")

print(f"Impostore reale: {impostor}")
print(f"Eliminato: {eliminated}")

print("\nVoti:")

for p, v in votes.items():
    print(f"{p} -> {v}")

print()

if eliminated == impostor:
    print("I giocatori hanno VINTO")
else:
    print("L'impostore ha VINTO")
