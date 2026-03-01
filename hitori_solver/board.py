"""HitoriBoard – data model for a Hitori puzzle grid."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple


class CellState(Enum):
    """Possible states for a single board cell."""

    UNKNOWN = "unknown"
    WHITE = "white"   # unshaded – participates in the solution
    BLACK = "black"   # shaded   – removed from the solution


class HitoriBoard:
    """Represents a Hitori puzzle board.

    The puzzle is stored as a 2-D grid of integer *values* (the numbers
    printed on the board) together with a parallel grid of :class:`CellState`
    entries that track the solver's progress.

    Parameters
    ----------
    grid:
        A rectangular list-of-lists of positive integers.  Every row must
        have the same length.
    """

    def __init__(self, grid: List[List[int]]) -> None:
        if not grid or not grid[0]:
            raise ValueError("Grid must be non-empty.")
        row_len = len(grid[0])
        for row in grid:
            if len(row) != row_len:
                raise ValueError("All rows must have the same length.")
            for val in row:
                if not isinstance(val, int) or val < 1:
                    raise ValueError(
                        f"Cell values must be positive integers; got {val!r}."
                    )

        self._rows = len(grid)
        self._cols = row_len
        self._values: List[List[int]] = [list(row) for row in grid]
        self._states: List[List[CellState]] = [
            [CellState.UNKNOWN] * self._cols for _ in range(self._rows)
        ]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rows(self) -> int:
        """Number of rows."""
        return self._rows

    @property
    def cols(self) -> int:
        """Number of columns."""
        return self._cols

    # ------------------------------------------------------------------
    # Cell access
    # ------------------------------------------------------------------

    def value(self, row: int, col: int) -> int:
        """Return the numeric value of cell *(row, col)*."""
        self._check_bounds(row, col)
        return self._values[row][col]

    def state(self, row: int, col: int) -> CellState:
        """Return the current :class:`CellState` of cell *(row, col)*."""
        self._check_bounds(row, col)
        return self._states[row][col]

    def set_state(self, row: int, col: int, state: CellState) -> None:
        """Set the state of cell *(row, col)*."""
        self._check_bounds(row, col)
        self._states[row][col] = state

    # ------------------------------------------------------------------
    # Bulk helpers
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all cell states to :attr:`CellState.UNKNOWN`."""
        for r in range(self._rows):
            for c in range(self._cols):
                self._states[r][c] = CellState.UNKNOWN

    def clone_states(self) -> List[List[CellState]]:
        """Return a deep copy of the current state grid."""
        return [list(row) for row in self._states]

    def restore_states(self, states: List[List[CellState]]) -> None:
        """Overwrite the state grid with a previously cloned snapshot."""
        for r in range(self._rows):
            for c in range(self._cols):
                self._states[r][c] = states[r][c]

    # ------------------------------------------------------------------
    # Neighbour utilities
    # ------------------------------------------------------------------

    def neighbours(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Return the orthogonal neighbours of *(row, col)*."""
        result = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = row + dr, col + dc
            if 0 <= nr < self._rows and 0 <= nc < self._cols:
                result.append((nr, nc))
        return result

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_solved(self) -> bool:
        """Return ``True`` when the board satisfies all Hitori constraints.

        Three constraints are checked:

        1. No duplicate values in any row among white cells.
        2. No duplicate values in any column among white cells.
        3. No two black cells share an edge.
        4. All white cells form a single connected group.
        """
        return (
            self._no_row_duplicates()
            and self._no_col_duplicates()
            and self._no_adjacent_blacks()
            and self._whites_connected()
        )

    def _no_row_duplicates(self) -> bool:
        for r in range(self._rows):
            seen = set()
            for c in range(self._cols):
                if self._states[r][c] != CellState.BLACK:
                    v = self._values[r][c]
                    if v in seen:
                        return False
                    seen.add(v)
        return True

    def _no_col_duplicates(self) -> bool:
        for c in range(self._cols):
            seen = set()
            for r in range(self._rows):
                if self._states[r][c] != CellState.BLACK:
                    v = self._values[r][c]
                    if v in seen:
                        return False
                    seen.add(v)
        return True

    def _no_adjacent_blacks(self) -> bool:
        for r in range(self._rows):
            for c in range(self._cols):
                if self._states[r][c] == CellState.BLACK:
                    for nr, nc in self.neighbours(r, c):
                        if self._states[nr][nc] == CellState.BLACK:
                            return False
        return True

    def _whites_connected(self) -> bool:
        white_cells = [
            (r, c)
            for r in range(self._rows)
            for c in range(self._cols)
            if self._states[r][c] != CellState.BLACK
        ]
        if not white_cells:
            return False
        visited: set = set()
        stack = [white_cells[0]]
        while stack:
            cell = stack.pop()
            if cell in visited:
                continue
            visited.add(cell)
            r, c = cell
            for nr, nc in self.neighbours(r, c):
                if (nr, nc) not in visited and self._states[nr][nc] != CellState.BLACK:
                    stack.append((nr, nc))
        return len(visited) == len(white_cells)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __str__(self) -> str:  # pragma: no cover
        lines = []
        for r in range(self._rows):
            parts = []
            for c in range(self._cols):
                v = self._values[r][c]
                s = self._states[r][c]
                if s == CellState.BLACK:
                    parts.append(f"[{v:2d}]")
                elif s == CellState.WHITE:
                    parts.append(f" {v:2d} ")
                else:
                    parts.append(f" {v:2d}?")
            lines.append("".join(parts))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_bounds(self, row: int, col: int) -> None:
        if not (0 <= row < self._rows and 0 <= col < self._cols):
            raise IndexError(
                f"Cell ({row}, {col}) is out of bounds for a "
                f"{self._rows}×{self._cols} board."
            )
