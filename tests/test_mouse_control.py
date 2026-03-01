"""Tests for MouseController."""

import pytest

from hitori_solver.board import CellState, HitoriBoard
from hitori_solver.mouse_control import FailsafeTriggered, MouseController


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


def test_cell_center_rectangular_cell_size():
    mc = MouseController(grid_origin=(10, 20), cell_size=(33.0, 25.0), dry_run=True)
    x, y = mc.cell_center(1, 2)
    assert x == 92  # 10 + round(2.5*33)
    assert y == 58  # 20 + round(1.5*25)


def test_cell_center_rounding_reduces_drift():
    mc = MouseController(grid_origin=(0, 0), cell_size=(100 / 3, 80 / 2), dry_run=True)
    centers = [mc.cell_center(0, c)[0] for c in range(3)]
    assert centers == [17, 50, 83]


def test_cell_center_uses_grid_bounds_without_drift():
    mc = MouseController(
        grid_origin=(0, 0),
        cell_size=1,
        dry_run=True,
        grid_bounds=(100, 200, 430, 530),
        grid_shape=(8, 8),
    )

    first = mc.cell_center(0, 0)
    last = mc.cell_center(7, 7)

    assert first == (121, 221)
    assert last == (409, 509)


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


def test_click_all_cells_row_major_order(capsys):
    mc = _controller(origin=(0, 0), cell_size=50)
    mc.click_all_cells(2, 3)

    lines = [
        line for line in capsys.readouterr().out.splitlines() if "[dry-run]" in line
    ]
    expected = ["(0, 0)", "(0, 1)", "(0, 2)", "(1, 0)", "(1, 1)", "(1, 2)"]
    assert len(lines) == len(expected)
    for line, coord in zip(lines, expected):
        assert coord in line


def test_click_all_cells_invalid_dimensions():
    mc = _controller(origin=(0, 0), cell_size=50)
    with pytest.raises(ValueError):
        mc.click_all_cells(0, 2)


def test_click_cell_esc_failsafe(monkeypatch):
    mc = _controller(origin=(0, 0), cell_size=50)
    monkeypatch.setattr(mc, "_esc_pressed", lambda: True)
    with pytest.raises(FailsafeTriggered):
        mc.click_cell(0, 0)
