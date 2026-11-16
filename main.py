# MicroChess Engine v2 - High Performance Deterministic Evaluation
# Python 3.13 standard library only.
import json
import os
import sys
import urllib.error
import urllib.request

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")

# Positional and Material values
VAL = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 20000}

# Center control bonus table (files a-h, ranks 1-8)
CENTER = {
    "d4": 30, "e4": 30, "d5": 30, "e5": 30,
    "c4": 15, "f4": 15, "c5": 15, "f5": 15,
    "d3": 10, "e3": 10, "d6": 10, "e6": 10
}

def post(path, body):
    req = urllib.request.Request(
        ENV_URL + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")

def parse_board(fen):
    b = {}
    for r_idx, row in enumerate(fen.split()[0].split("/")):
        col = 0
        for ch in row:
            if ch.isdigit():
                col += int(ch)
            else:
                b["abcdefgh"[col] + str(8 - r_idx)] = ch
                col += 1
    return b

def evaluate_move(fen, move, is_white):
    board = parse_board(fen)
    from_sq = move[:2]
    to_sq = move[2:4]
    promo = move[4] if len(move) == 5 else None

    piece = board.get(from_sq, "")
    p_type = piece.lower()
    target = board.get(to_sq, "")
    t_type = target.lower()

    score = 0

    # 1. Capture evaluation (MVV-LVA: Most Valuable Victim - Least Valuable Attacker)
    if t_type:
        score += VAL.get(t_type, 0) * 10 - VAL.get(p_type, 0)
    elif p_type == "p" and from_sq[0] != to_sq[0]:
        # En-passant
        score += VAL["p"] * 10 - VAL["p"]

    # 2. Promotion evaluation
    if promo:
        score += VAL.get(promo.lower(), 0) * 10

    # 3. Center control & mobility bonus
    score += CENTER.get(to_sq, 0)

    # 4. Piece-Square and Development encouragement
    if p_type in ("n", "b"):
        # Encourage minor piece development away from back rank
        back_rank = "1" if is_white else "8"
        if from_sq[1] == back_rank:
            score += 25

    # 5. Pawn push advancement encouragement
    if p_type == "p":
        rank = int(to_sq[1])
        advancement = rank if is_white else (9 - rank)
        score += advancement * 5

    return score

def choose_best_move(fen, legal_moves):
    parts = fen.split()
    is_white = (parts[1] == "w") if len(parts) > 1 else True

    best_score = -10**9
    best_move = legal_moves[0]

    for m in legal_moves:
        s = evaluate_move(fen, m, is_white)
        # Deterministic tie-breaking on equal score
        if s > best_score:
            best_score = s
            best_move = m
        elif s == best_score and m < best_move:
            best_move = m

    return best_move

def main():
    while True:
        g = post("/game", {})
        if g.get("status") == "done":
            break
        while g.get("status") == "your_move":
            move = choose_best_move(g["fen"], g["legal_moves"])
            g = post("/move", {"game": g["game"], "move": move})
        print(f"game {g.get('game')}: {g.get('outcome')} by {g.get('reason')}", file=sys.stderr)
    print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)

if __name__ == "__main__":
    main()
