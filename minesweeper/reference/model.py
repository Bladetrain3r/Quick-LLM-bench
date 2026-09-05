"""
Shared data model for the minesweeper task — GIVEN to every candidate, never
generated. This is the contract's glue: fixing the Board and its helpers is what
lets independently-generated modules (logic / render / ui) compose in the split
test instead of inventing three incompatible board representations.
"""
from dataclasses import dataclass, field


@dataclass
class Board:
    width: int
    height: int
    mines: set = field(default_factory=set)      # {(row, col)} of mine cells
    revealed: set = field(default_factory=set)    # {(row, col)} revealed by the player
    flagged: set = field(default_factory=set)     # {(row, col)} flagged by the player


def in_bounds(board, r, c):
    return 0 <= r < board.height and 0 <= c < board.width


def neighbors(board, r, c):
    """The up-to-8 in-bounds neighbours of (r, c)."""
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr or dc:
                nr, nc = r + dr, c + dc
                if in_bounds(board, nr, nc):
                    yield (nr, nc)
