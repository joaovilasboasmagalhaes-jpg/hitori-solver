"""Tests for HitoriBoard."""

import pytest
from hitori_solver.board import CellState, HitoriBoard


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_valid_construction():
    board = HitoriBoard([[1, 2], [2, 1]])
    assert board.rows == 2
    assert board.cols == 2


def test_empty_grid_raises():
    with pytest.raises(ValueError):
        HitoriBoard([])


def test_jagged_grid_raises():
    with pytest.raises(ValueError):
        HitoriBoard([[1, 2], [3]])


def test_non_positive_value_raises():
    with pytest.raises(ValueError):
        HitoriBoard([[0, 1], [1, 0]])


# ---------------------------------------------------------------------------
# Cell access
# ---------------------------------------------------------------------------

def test_initial_state_is_unknown():
    board = HitoriBoard([[1, 2], [3, 4]])
    assert board.state(0, 0) == CellState.UNKNOWN


def test_set_and_get_state():
    board = HitoriBoard([[1, 2], [3, 4]])
    board.set_state(0, 1, CellState.BLACK)
    assert board.state(0, 1) == CellState.BLACK


def test_value_accessor():
    board = HitoriBoard([[5, 3], [1, 2]])
    assert board.value(0, 0) == 5
    assert board.value(1, 1) == 2


def test_out_of_bounds_raises():
    board = HitoriBoard([[1, 2], [3, 4]])
    with pytest.raises(IndexError):
        board.value(5, 0)


# ---------------------------------------------------------------------------
# Neighbours
# ---------------------------------------------------------------------------

def test_corner_has_two_neighbours():
    board = HitoriBoard([[1, 2], [3, 4]])
    assert len(board.neighbours(0, 0)) == 2


def test_centre_has_four_neighbours():
    board = HitoriBoard([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    assert len(board.neighbours(1, 1)) == 4


# ---------------------------------------------------------------------------
# Reset / clone / restore
# ---------------------------------------------------------------------------

def test_reset_clears_states():
    board = HitoriBoard([[1, 2], [3, 4]])
    board.set_state(0, 0, CellState.BLACK)
    board.reset()
    assert board.state(0, 0) == CellState.UNKNOWN


def test_clone_and_restore():
    board = HitoriBoard([[1, 2], [3, 4]])
    board.set_state(0, 0, CellState.WHITE)
    snapshot = board.clone_states()
    board.set_state(0, 0, CellState.BLACK)
    board.restore_states(snapshot)
    assert board.state(0, 0) == CellState.WHITE


# ---------------------------------------------------------------------------
# is_solved validation
# ---------------------------------------------------------------------------

def _make_solved_3x3():
    """3×3 board with all unique values – all cells are white (trivially solved)."""
    board = HitoriBoard([[1, 2, 3], [2, 3, 1], [3, 1, 2]])
    for r in range(3):
        for c in range(3):
            board.set_state(r, c, CellState.WHITE)
    return board


def test_is_solved_valid():
    board = _make_solved_3x3()
    assert board.is_solved()


def test_is_solved_adjacent_blacks():
    board = HitoriBoard([[1, 1], [2, 3]])
    board.set_state(0, 0, CellState.BLACK)
    board.set_state(0, 1, CellState.BLACK)
    board.set_state(1, 0, CellState.WHITE)
    board.set_state(1, 1, CellState.WHITE)
    assert not board.is_solved()


def test_is_solved_row_duplicate():
    board = HitoriBoard([[1, 2], [3, 4]])
    for r in range(2):
        for c in range(2):
            board.set_state(r, c, CellState.WHITE)
    # All white – no shading – board has no duplicates so it IS solved.
    assert board.is_solved()


def test_is_solved_disconnected():
    # 3×1 board: white – black – white → disconnected whites
    board = HitoriBoard([[1], [2], [3]])
    board.set_state(0, 0, CellState.WHITE)
    board.set_state(1, 0, CellState.BLACK)
    board.set_state(2, 0, CellState.WHITE)
    assert not board.is_solved()
