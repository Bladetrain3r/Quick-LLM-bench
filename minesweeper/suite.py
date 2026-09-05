"""
Acceptance suite for the minesweeper task. Run against a project directory that
contains the given model.py plus candidate logic.py / render.py / ui.py:

    python3 suite.py <project_dir>

Prints one JSON line: {"l1":bool,"l1_note":..., "l2":..., "l3":...}.
  L1 = game logic (the gate): new_board, adjacent_mines, reveal flood-fill,
       toggle_flag, game_state — pure and deterministic.
  L2 = rendering: a fixed board renders to an exact expected string.
  L3 = ui + integration: parse_command, and a scripted play() that wins.
Each level imports only what it needs, so a broken render can't fail logic.
"""
import importlib
import json
import sys


def _fresh(projdir, name):
    sys.path.insert(0, projdir)
    for m in (name, "model", "logic", "render", "ui"):
        sys.modules.pop(m, None)
    return importlib.import_module(name)


def level1(projdir):
    model = _fresh(projdir, "model")
    logic = _fresh(projdir, "logic")

    nb = logic.new_board(6, 6, 6, (3, 3), seed=1)
    assert len(nb.mines) == 6, "mine_count"
    assert (3, 3) not in nb.mines, "first-click is a mine"
    assert all(n not in nb.mines for n in model.neighbors(nb, 3, 3)), "neighbour of first click is a mine"
    assert logic.new_board(6, 6, 6, (3, 3), seed=1).mines == nb.mines, "not deterministic under seed"

    b = model.Board(3, 3, mines={(0, 0)})
    assert logic.adjacent_mines(b, 1, 1) == 1, "adjacent (1,1)"
    assert logic.adjacent_mines(b, 2, 2) == 0, "adjacent (2,2)"
    assert logic.adjacent_mines(b, 0, 1) == 1, "adjacent (0,1)"

    b = model.Board(3, 3, mines={(0, 0)})
    logic.reveal(b, 2, 2)
    assert (2, 2) in b.revealed and (1, 1) in b.revealed, "reveal did not flood"
    assert (0, 0) not in b.revealed, "flood revealed the mine"
    assert len(b.revealed) == 8, f"flood revealed {len(b.revealed)} cells, expected 8"

    b = model.Board(3, 3)
    logic.toggle_flag(b, 1, 1)
    assert (1, 1) in b.flagged, "flag on"
    logic.toggle_flag(b, 1, 1)
    assert (1, 1) not in b.flagged, "flag off"
    b2 = model.Board(3, 3, revealed={(1, 1)})
    logic.toggle_flag(b2, 1, 1)
    assert (1, 1) not in b2.flagged, "flagged a revealed cell"

    assert logic.game_state(model.Board(3, 3, mines={(0, 0)}, revealed={(0, 0)})) == "lost", "lost"
    assert logic.game_state(model.Board(2, 2, mines={(0, 0)},
                                        revealed={(0, 1), (1, 0), (1, 1)})) == "won", "won"
    assert logic.game_state(model.Board(2, 2, mines={(0, 0)}, revealed={(1, 1)})) == "playing", "playing"


def level2(projdir):
    model = _fresh(projdir, "model")
    render = _fresh(projdir, "render")
    b = model.Board(2, 2, mines={(0, 0)}, revealed={(1, 1)}, flagged={(0, 1)})
    got = render.render(b)
    assert got == "#F\n#1", f"render mismatch: {got!r}"
    assert "*" in render.render(b, reveal_all=True), "reveal_all did not show the mine"


def level3(projdir):
    model = _fresh(projdir, "model")
    _fresh(projdir, "logic")
    _fresh(projdir, "render")
    ui = _fresh(projdir, "ui")
    assert ui.parse_command("r 1 2") == ("reveal", 1, 2), "parse reveal"
    assert ui.parse_command("f 0 0") == ("flag", 0, 0), "parse flag"
    assert ui.parse_command("quit") == ("quit", None, None), "parse quit"
    assert ui.parse_command("nonsense") == ("invalid", None, None), "parse invalid"

    b = model.Board(2, 2, mines={(0, 0)})
    seq = ["r 0 1", "r 1 0", "r 1 1"]
    inp = lambda *_: seq.pop(0) if seq else "q"      # noqa: E731
    res = ui.play(b, input_fn=inp, output_fn=lambda *a, **k: None)
    assert res == "won", f"play returned {res!r}, expected won"


def run(projdir):
    out = {}
    for lvl, fn in (("l1", level1), ("l2", level2), ("l3", level3)):
        try:
            fn(projdir)
            out[lvl], out[lvl + "_note"] = True, "ok"
        except AssertionError as e:
            out[lvl], out[lvl + "_note"] = False, str(e)
        except Exception as e:  # noqa: BLE001
            out[lvl], out[lvl + "_note"] = False, f"{type(e).__name__}: {e}"
    return out


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1])))
