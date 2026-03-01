"""Tests for MouseController."""

import pytest
from hitori_solver.mouse_control import MouseController
from hitori_solver.board import CellState, HitoriBoard


def _controller(origin=(0, 0), cell_size=50):
    return MouseController(grid_origin=origin, cell_size=cell_size, dry_run=True)


# ---------------------------------------------------------------------------
# cell_center
# ---------------------------------------------------------------------------

def test_cell_center_top_left():
    mc = _controller(origin=(100, 200), cell_size=50)
    x, y = mc.cell_center(0, 0)
    assert x == 125  # 100 + 0.5*50
    assert y == 225  # 200 + 0.5*50


def test_cell_center_second_row():
    mc = _controller(origin=(0, 0), cell_size=40)
    x, y = mc.cell_center(1, 2)
    assert x == 100  # 0 + 2.5*40
    assert y == 60   # 0 + 1.5*40


# ---------------------------------------------------------------------------
# click_cell (dry-run – no real mouse movement)
# ---------------------------------------------------------------------------

def test_click_cell_dry_run(capsys):
    mc = _controller(origin=(10, 20), cell_size=50)
    mc.click_cell(0, 0)
    captured = capsys.readouterr()
    assert "dry-run" in captured.out
    assert "(0, 0)" in captured.out


# ---------------------------------------------------------------------------
# shade_solution
# ---------------------------------------------------------------------------

def test_shade_solution_calls_correct_cells(capsys):
    """shade_solution should click only BLACK cells."""
    board = HitoriBoard([[1, 2], [2, 1]])
    board.set_state(0, 0, CellState.BLACK)
    board.set_state(0, 1, CellState.WHITE)
    board.set_state(1, 0, CellState.WHITE)
    board.set_state(1, 1, CellState.BLACK)

    mc = _controller(origin=(0, 0), cell_size=50)
    mc.shade_solution(board)

    output = capsys.readouterr().out
    assert "(0, 0)" in output
    assert "(1, 1)" in output
    # White cells should NOT be clicked.
    assert "(0, 1)" not in output
    assert "(1, 0)" not in output
