"""HitoriSolver – constraint-propagation + backtracking solver."""

from __future__ import annotations

from typing import List, Optional, Tuple

from .board import CellState, HitoriBoard


class HitoriSolver:
    """Solves a :class:`~hitori_solver.board.HitoriBoard`.

    The algorithm combines two phases:

    1. **Constraint propagation** – deterministic deductions applied
       repeatedly until no more progress can be made.
    2. **Backtracking** – when propagation stalls, the solver picks an
       undecided cell, guesses its state, and recurses.

    Parameters
    ----------
    board:
        The board to solve *in-place*.  The board's cell states are
        modified during solving and will reflect the solution on success.
    """

    def __init__(self, board: HitoriBoard) -> None:
        self._board = board

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def solve(self) -> bool:
        """Attempt to solve the board.

        Returns
        -------
        bool
            ``True`` if a valid solution was found (board states updated),
            ``False`` if no solution exists.
        """
        self._board.reset()
        return self._backtrack()

    # ------------------------------------------------------------------
    # Backtracking
    # ------------------------------------------------------------------

    def _backtrack(self) -> bool:
        # Apply deterministic rules first.
        if not self._propagate():
            return False

        # Find the first undecided cell.
        cell = self._pick_unknown()
        if cell is None:
            # All cells decided – check final validity.
            return self._board.is_solved()

        row, col = cell
        snapshot = self._board.clone_states()

        for state in (CellState.BLACK, CellState.WHITE):
            self._board.restore_states(snapshot)
            self._board.set_state(row, col, state)
            if self._backtrack():
                return True

        self._board.restore_states(snapshot)
        return False

    # ------------------------------------------------------------------
    # Constraint propagation
    # ------------------------------------------------------------------

    def _propagate(self) -> bool:
        """Apply all deterministic rules until a fixed point.

        Returns ``False`` immediately when a contradiction is detected.
        """
        changed = True
        while changed:
            changed = False

            # Rule 1 – if a black cell's neighbour is also black → contradiction
            if not self._board._no_adjacent_blacks():
                return False

            # Rule 2 – neighbours of black cells must be white
            for r in range(self._board.rows):
                for c in range(self._board.cols):
                    if self._board.state(r, c) == CellState.BLACK:
                        for nr, nc in self._board.neighbours(r, c):
                            if self._board.state(nr, nc) == CellState.BLACK:
                                return False
                            if self._board.state(nr, nc) == CellState.UNKNOWN:
                                self._board.set_state(nr, nc, CellState.WHITE)
                                changed = True

            # Rule 3 – if a value appears exactly once in a row/col → white
            for r in range(self._board.rows):
                changed |= self._mark_unique_in_line(
                    [(r, c) for c in range(self._board.cols)]
                )
            for c in range(self._board.cols):
                changed |= self._mark_unique_in_line(
                    [(r, c) for r in range(self._board.rows)]
                )

            # Rule 4 – if a row/col has duplicates among unknown/white cells,
            #          check whether one copy must be black to resolve them.
            for r in range(self._board.rows):
                if not self._resolve_duplicates_in_line(
                    [(r, c) for c in range(self._board.cols)]
                ):
                    return False
                changed |= self._last_changed
            for c in range(self._board.cols):
                if not self._resolve_duplicates_in_line(
                    [(r, c) for r in range(self._board.rows)]
                ):
                    return False
                changed |= self._last_changed

            # Rule 5 – white cells still need to be connected; prune if not
            if not self._connectivity_check():
                return False

        return True

    def _mark_unique_in_line(self, cells: List[Tuple[int, int]]) -> bool:
        """Mark cells whose value is unique in the line as WHITE."""
        from collections import Counter

        val_cells: dict = {}
        for r, c in cells:
            if self._board.state(r, c) != CellState.BLACK:
                v = self._board.value(r, c)
                val_cells.setdefault(v, []).append((r, c))

        changed = False
        for v, positions in val_cells.items():
            if len(positions) == 1:
                r, c = positions[0]
                if self._board.state(r, c) == CellState.UNKNOWN:
                    self._board.set_state(r, c, CellState.WHITE)
                    changed = True
        return changed

    _last_changed: bool = False  # set by _resolve_duplicates_in_line

    def _resolve_duplicates_in_line(
        self, cells: List[Tuple[int, int]]
    ) -> bool:
        """If all copies of a value except one must stay, force the others black.

        Returns ``False`` on contradiction.
        """
        self._last_changed = False
        val_cells: dict = {}
        for r, c in cells:
            if self._board.state(r, c) != CellState.BLACK:
                v = self._board.value(r, c)
                val_cells.setdefault(v, []).append((r, c))

        for v, positions in val_cells.items():
            if len(positions) < 2:
                continue
            # All non-black copies are unknown or white.
            unknowns = [
                (r, c)
                for r, c in positions
                if self._board.state(r, c) == CellState.UNKNOWN
            ]
            whites = [
                (r, c)
                for r, c in positions
                if self._board.state(r, c) == CellState.WHITE
            ]
            if len(whites) >= 2:
                # Two whites with same value in one line → contradiction.
                return False
            if len(whites) == 1:
                # All unknowns must be black.
                for r, c in unknowns:
                    self._board.set_state(r, c, CellState.BLACK)
                    self._last_changed = True
        return True

    def _connectivity_check(self) -> bool:
        """Return ``False`` if remaining unknown/white cells are already split."""
        # Treat UNKNOWN as white for this speculative check.
        white_cells = [
            (r, c)
            for r in range(self._board.rows)
            for c in range(self._board.cols)
            if self._board.state(r, c) != CellState.BLACK
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
            for nr, nc in self._board.neighbours(r, c):
                if (nr, nc) not in visited and self._board.state(nr, nc) != CellState.BLACK:
                    stack.append((nr, nc))
        return len(visited) == len(white_cells)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pick_unknown(self) -> Optional[Tuple[int, int]]:
        """Return the first UNKNOWN cell, or ``None`` if none remain."""
        for r in range(self._board.rows):
            for c in range(self._board.cols):
                if self._board.state(r, c) == CellState.UNKNOWN:
                    return (r, c)
        return None
