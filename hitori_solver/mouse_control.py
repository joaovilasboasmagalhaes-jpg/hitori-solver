"""MouseController – optional mouse automation to interact with the puzzle UI."""

from __future__ import annotations

import time
from typing import Optional, Tuple

try:
    import pyautogui
    _DEPS_AVAILABLE = True
except Exception:  # ImportError or display-related errors in headless environments
    _DEPS_AVAILABLE = False


class MouseController:
    """Controls the mouse to shade cells in the Hitori puzzle UI.

    This class is **optional** – if PyAutoGUI is not installed, importing
    the module still works but instantiation will raise :class:`ImportError`.

    Parameters
    ----------
    grid_origin:
        ``(x, y)`` screen coordinates of the *top-left corner* of the
        puzzle grid in pixels.
    cell_size:
        Size (width and height) of a single grid cell in pixels.
    click_delay:
        Seconds to wait between consecutive clicks.  Defaults to ``0.05``.
    dry_run:
        When ``True``, log intended clicks without actually moving the
        mouse.  Useful for testing.
    """

    def __init__(
        self,
        grid_origin: Tuple[int, int],
        cell_size: int,
        click_delay: float = 0.05,
        dry_run: bool = False,
    ) -> None:
        if not _DEPS_AVAILABLE and not dry_run:
            raise ImportError(  # pragma: no cover
                "MouseController requires 'pyautogui'. "
                "Install it with: pip install pyautogui"
            )
        self._origin = grid_origin
        self._cell_size = cell_size
        self._delay = click_delay
        self._dry_run = dry_run

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cell_center(self, row: int, col: int) -> Tuple[int, int]:
        """Return the screen ``(x, y)`` coordinates for cell *(row, col)*."""
        x = self._origin[0] + int((col + 0.5) * self._cell_size)
        y = self._origin[1] + int((row + 0.5) * self._cell_size)
        return (x, y)

    def click_cell(self, row: int, col: int) -> None:
        """Left-click the centre of cell *(row, col)* to toggle its shade.

        Parameters
        ----------
        row:
            Zero-based row index.
        col:
            Zero-based column index.
        """
        x, y = self.cell_center(row, col)
        if self._dry_run:
            print(f"[dry-run] click ({row}, {col}) → screen ({x}, {y})")
            return
        pyautogui.click(x, y)
        time.sleep(self._delay)

    def shade_solution(self, board: "HitoriBoard") -> None:  # type: ignore[name-defined]
        """Click all cells that the solver marked as BLACK.

        Parameters
        ----------
        board:
            A solved :class:`~hitori_solver.board.HitoriBoard`.
        """
        from .board import CellState

        for r in range(board.rows):
            for c in range(board.cols):
                if board.state(r, c) == CellState.BLACK:
                    self.click_cell(r, c)
