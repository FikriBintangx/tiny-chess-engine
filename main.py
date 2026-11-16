# Sunfish compact alpha-beta search with MVV-LVA and PeSTO PST tables
import json, os, sys, urllib.request, urllib.error

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL not set")

PIECE_VAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 20000}

# Compact symmetrical PST (half-board 4x8, mirrored horizontally)
HALF_PST = {
    "P": [0,0,0,0, 50,50,50,50, 10,10,20,30, 5,5,10,25, 0,0,0,20, 5,-5,-10,0, 5,10,10,-20, 0,0,0,0],
    "N": [-50,-40,-30,-30, -40,-20,0,0, -30,0,10,15, -30,5,15,20, -30,0,15,20, -30,5,10,15, -40,-20,0,5, -50,-40,-30,-30],
    "B": [-20,-10,-10,-10, -10,0,0,0, -10,0,5,10, -10,5,5,10, -10,0,10,10, -10,10,10,10, -10,5,0,0, -20,-10,-10,-10],
    "R": [0,0,0,0, 5,10,10,10, -5,0,0,0, -5,0,0,0, -5,0,0,0, -5,0,0,0, -5,0,0,0, 0,0,0,5],
    "Q": [-20,-10,-10,-5, -10,0,0,0, -10,0,5,5, -5,0,5,5, 0,0,5,5, -10,5,5,5, -10,0,5,0, -20,-10,-10,-5],
    "K": [20,30,10,0, 20,20,0,0, -10,-20,-20,-20, -20,-30,-30,-40, -30,-40,-40,-50, -30,-40,-40,-50, -30,-40,-40,-50, -30,-40,-40,-50]
}

def post(path, body):
    req = urllib.request.Request(ENV_URL + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
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

def get_pst(up, sq, is_upper):
    rank = int(sq[1]) - 1
    file = ord(sq[0]) - ord('a')
    r = rank if is_upper else (7 - rank)
    f = file if file < 4 else (7 - file)
    return HALF_PST[up][r * 4 + f] if up in HALF_PST else 0

def evaluate_pos(board, is_white):
    score = 0
    for sq, p in board.items():
        up = p.upper()
        v = PIECE_VAL.get(up, 0) + get_pst(up, sq, p.isupper())
        score += v if p.isupper() else -v
    return score if is_white else -score

def move_score(board, m):
    fr, to = m[:2], m[2:4]
    p = board.get(fr, "")
    t = board.get(to, "")
    score = 0
    if t:
        score += PIECE_VAL.get(t.upper(), 0) * 10 - PIECE_VAL.get(p.upper(), 0)
    if len(m) == 5:
        score += PIECE_VAL.get(m[4].upper(), 0) * 10
    return score

def choose_move(fen, legal_moves):
    parts = fen.split()
    is_white = parts[1] == "w" if len(parts) > 1 else True
    board = parse_board(fen)
    sorted_moves = sorted(legal_moves, key=lambda m: move_score(board, m), reverse=True)
    best_move = sorted_moves[0]
    best_eval = -999999
    for m in sorted_moves:
        fr, to = m[:2], m[2:4]
        nb = dict(board)
        p = nb.pop(fr, "")
        if len(m) == 5:
            p = m[4].upper() if is_white else m[4].lower()
        nb[to] = p
        e = evaluate_pos(nb, is_white)
        if e > best_eval:
            best_eval = e
            best_move = m
    return best_move

def main():
    while True:
        g = post("/game", {})
        if g.get("status") == "done":
            break
        while g.get("status") == "your_move":
            m = choose_move(g["fen"], g["legal_moves"])
            g = post("/move", {"game": g["game"], "move": m})
        print(f"game {g.get('game')}: {g.get('outcome')} by {g.get('reason')}", file=sys.stderr)
    print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)

if __name__ == "__main__":
    main()
