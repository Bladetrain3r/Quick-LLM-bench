You are implementing part of a Python Minesweeper clone, split into modules with
a FIXED contract so independently-written modules compose. Follow the signatures
exactly. Stdlib only. Import the shared model; do not redefine Board.

# GIVEN (already exists as model.py — import it, do not rewrite it)

    from dataclasses import dataclass, field

    @dataclass
    class Board:
        width: int
        height: int
        mines: set    = {(row, col)}   # mine cells
        revealed: set = {(row, col)}   # cells the player has revealed
        flagged: set  = {(row, col)}   # cells the player has flagged

    def in_bounds(board, r, c) -> bool
    def neighbors(board, r, c) -> iterator of (r, c)   # the up-to-8 in-bounds neighbours

Rows are indexed 0..height-1, columns 0..width-1. A cell is the tuple (row, col).

# logic.py   (import from model)

    def new_board(width, height, mine_count, first_click, seed=0) -> Board
        # Return a Board with exactly mine_count mines placed pseudo-randomly.
        # NEVER place a mine on first_click (a (row, col) tuple) or on any of its
        # neighbours. Use random.Random(seed) so the layout is reproducible.

    def adjacent_mines(board, r, c) -> int
        # Number of mines among the neighbours of (r, c).

    def reveal(board, r, c) -> None
        # Reveal (r, c) by adding it to board.revealed (mutate in place). If the
        # cell is not a mine and has 0 adjacent mines, flood-fill: recursively
        # reveal its neighbours, spreading through the connected zero-region and
        # revealing the numbered cells that border it. Never reveal a flagged cell.
        # Revealing a mine simply marks it revealed (the game is then lost).

    def toggle_flag(board, r, c) -> None
        # Toggle (r, c) in board.flagged (mutate in place). Do nothing if the cell
        # is already revealed.

    def game_state(board) -> str
        # "lost"  if any revealed cell is a mine
        # "won"   if every non-mine cell is revealed (and not lost)
        # "playing" otherwise

# render.py   (import from model; compute counts yourself from board.mines)

    def render(board, reveal_all=False) -> str
        # Return the board as a string, one line per row, one character per cell,
        # no separators. Character rules, checked top to bottom:
        #   reveal_all and cell is a mine        -> '*'
        #   cell in board.flagged and not revealed -> 'F'
        #   cell not in board.revealed           -> '#'
        #   revealed and is a mine               -> '*'
        #   revealed and 0 adjacent mines        -> '.'
        #   revealed and n>0 adjacent mines      -> str(n)
        # Compute adjacent-mine counts from board.mines using model.neighbors;
        # do NOT import logic.

# ui.py   (import from model, logic and render)

    def parse_command(s) -> tuple
        # "r R C" or "reveal R C" -> ("reveal", R, C)   (R, C are ints)
        # "f R C" or "flag R C"   -> ("flag", R, C)
        # "q" or "quit"           -> ("quit", None, None)
        # anything else           -> ("invalid", None, None)

    def play(board, input_fn=input, output_fn=print) -> str
        # Game loop: output_fn(render(board)); read a line with input_fn();
        # apply reveal/flag via logic; quit ends the loop. Continue until
        # logic.game_state(board) != "playing" or the player quits.
        # Return the final logic.game_state(board). input_fn/output_fn are
        # injected so the loop can be driven by a test.
