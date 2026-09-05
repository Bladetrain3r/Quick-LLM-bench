from logic import reveal, toggle_flag, game_state
from render import render

def parse_command(s):
    parts = s.split()
    if not parts:
        return ("invalid", None, None)
    cmd = parts[0].lower()
    if cmd in ("q", "quit"):
        return ("quit", None, None)
    if cmd in ("r", "reveal", "f", "flag") and len(parts) == 3:
        try:
            r, c = int(parts[1]), int(parts[2])
        except ValueError:
            return ("invalid", None, None)
        return ("reveal" if cmd in ("r", "reveal") else "flag", r, c)
    return ("invalid", None, None)

def play(board, input_fn=input, output_fn=print):
    while game_state(board) == "playing":
        output_fn(render(board))
        action, r, c = parse_command(input_fn())
        if action == "quit":
            break
        if action == "reveal":
            reveal(board, r, c)
        elif action == "flag":
            toggle_flag(board, r, c)
    return game_state(board)
