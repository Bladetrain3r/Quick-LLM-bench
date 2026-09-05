import random
from model import Board, neighbors

def new_board(width, height, mine_count, first_click, seed=0):
    b = Board(width, height)
    rng = random.Random(seed)
    forbidden = {first_click} | set(neighbors(b, *first_click))
    cells = [(r, c) for r in range(height) for c in range(width) if (r, c) not in forbidden]
    b.mines = set(rng.sample(cells, mine_count))
    return b

def adjacent_mines(board, r, c):
    return sum(1 for nb in neighbors(board, r, c) if nb in board.mines)

def reveal(board, r, c):
    if (r, c) in board.flagged or (r, c) in board.revealed:
        return
    board.revealed.add((r, c))
    if (r, c) in board.mines:
        return
    if adjacent_mines(board, r, c) == 0:
        for nb in neighbors(board, r, c):
            if nb not in board.revealed and nb not in board.mines:
                reveal(board, *nb)

def toggle_flag(board, r, c):
    if (r, c) in board.revealed:
        return
    board.flagged.symmetric_difference_update({(r, c)})

def game_state(board):
    if any(m in board.revealed for m in board.mines):
        return "lost"
    if len(board.revealed) == board.width * board.height - len(board.mines):
        return "won"
    return "playing"
