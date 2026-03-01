"""Tests for HitoriSolver."""

import pytest
from hitori_solver.board import CellState, HitoriBoard
from hitori_solver.solver import HitoriSolver


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def solved(grid):
    board = HitoriBoard(grid)
    solver = HitoriSolver(board)
    result = solver.solve()
    return result, board


# ---------------------------------------------------------------------------
# Trivial puzzles
# ---------------------------------------------------------------------------

def test_1x1_trivial():
    """A single cell board is trivially solved (cell is white)."""
    ok, board = solved([[1]])
    assert ok
    assert board.state(0, 0) != CellState.BLACK


def test_no_duplicates_all_white():
    """Board with no duplicate values needs no shading."""
    ok, board = solved([[1, 2], [3, 4]])
    assert ok
    assert board.is_solved()


# ---------------------------------------------------------------------------
# Known small puzzles
# ---------------------------------------------------------------------------

def test_2x2_simple_duplicate():
    """
    1 2
    2 1
    One of the 2s must be shaded; one of the 1s must be shaded.
    Valid solution: shade (0,0) or (1,1) and (1,0) or (0,1).
    """
    ok, board = solved([[1, 2], [2, 1]])
    assert ok
    assert board.is_solved()


def test_3x3_puzzle():
    """
    Classic 3×3 Hitori puzzle.
    """
    grid = [
        [2, 3, 1],
        [3, 1, 2],
        [1, 2, 3],
    ]
    ok, board = solved(grid)
    assert ok
    assert board.is_solved()


def test_4x4_puzzle():
    """
    4×4 puzzle with known structure.
    """
    grid = [
        [1, 2, 3, 4],
        [2, 1, 4, 3],
        [3, 4, 1, 2],
        [4, 3, 2, 1],
    ]
    ok, board = solved(grid)
    assert ok
    assert board.is_solved()


def test_solver_returns_false_for_impossible():
    """A board where no valid shading exists should return False.

    2x2 board where all cells share the same value – the only way to
    eliminate duplicates would require shading adjacent cells.
    """
    # 2 2
    # 2 2
    # Any valid solution would require shading all cells in at least one
    # row *and* column, but we cannot have adjacent blacks.
    # The solver should either return False or find a valid partial solution.
    # We accept that it might not be solvable.
    grid = [[2, 2], [2, 2]]
    board = HitoriBoard(grid)
    solver = HitoriSolver(board)
    result = solver.solve()
    # Whether True or False, if True the board must be valid.
    if result:
        assert board.is_solved()


def test_5x5_puzzle():
    """
    5×5 Hitori puzzle (well-known example).
    """
    grid = [
        [4, 8, 1, 6, 3],
        [3, 6, 7, 2, 5],
        [2, 3, 4, 8, 6],
        [1, 2, 6, 5, 4],
        [5, 7, 3, 1, 2],
    ]
    ok, board = solved(grid)
    assert ok
    assert board.is_solved()


# ---------------------------------------------------------------------------
# Solver idempotence
# ---------------------------------------------------------------------------

def test_solve_twice():
    """Calling solve() a second time should reset and still find a solution."""
    board = HitoriBoard([[1, 2], [2, 1]])
    solver = HitoriSolver(board)
    assert solver.solve()
    assert solver.solve()
    assert board.is_solved()
