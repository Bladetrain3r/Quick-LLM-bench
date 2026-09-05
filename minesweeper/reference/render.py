from model import neighbors

def render(board, reveal_all=False):
    lines = []
    for r in range(board.height):
        row = ""
        for c in range(board.width):
            cell = (r, c)
            if reveal_all and cell in board.mines:
                row += "*"
            elif cell in board.flagged and cell not in board.revealed:
                row += "F"
            elif cell not in board.revealed:
                row += "#"
            elif cell in board.mines:
                row += "*"
            else:
                n = sum(1 for nb in neighbors(board, r, c) if nb in board.mines)
                row += "." if n == 0 else str(n)
        lines.append(row)
    return "\n".join(lines)
