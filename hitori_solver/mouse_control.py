"""MouseController – optional mouse automation to interact with the puzzle UI."""

from __future__ import annotations

import ctypes
import sys
import time
from typing import Optional, Tuple, Union

try:
    import pyautogui
    _DEPS_AVAILABLE = True
except Exception:  # ImportError or display-related errors in headless environments
    _DEPS_AVAILABLE = False


class FailsafeTriggered(RuntimeError):
    """Raised when the user triggers the runtime failsafe."""


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
        Size of a grid cell in pixels. Can be:

        - a single scalar for square cells
        - ``(cell_width, cell_height)`` for rectangular cells
    click_delay:
        Seconds to wait between consecutive clicks.  Defaults to ``0.05``.
    dry_run:
        When ``True``, log intended clicks without actually moving the
        mouse.  Useful for testing.
    """

    def __init__(
        self,
        grid_origin: Tuple[int, int],
        cell_size: Union[int, float, Tuple[float, float]],
        click_delay: float = 0.05,
        dry_run: bool = False,
        grid_bounds: Optional[Tuple[int, int, int, int]] = None,
        grid_shape: Optional[Tuple[int, int]] = None,
    ) -> None:
        if not _DEPS_AVAILABLE and not dry_run:
            raise ImportError(  # pragma: no cover
                "MouseController requires 'pyautogui'. "
                "Install it with: pip install pyautogui"
            )
        self._origin = grid_origin
        if isinstance(cell_size, tuple):
            self._cell_w = float(cell_size[0])
            self._cell_h = float(cell_size[1])
        else:
            self._cell_w = float(cell_size)
            self._cell_h = float(cell_size)
        if self._cell_w <= 0 or self._cell_h <= 0:
            raise ValueError("cell_size must be positive")
        self._delay = click_delay
        self._dry_run = dry_run
        self._grid_bounds = grid_bounds
        self._grid_shape = grid_shape

        if (self._grid_bounds is None) ^ (self._grid_shape is None):
            raise ValueError("grid_bounds and grid_shape must be provided together")
        if self._grid_bounds is not None and self._grid_shape is not None:
            left, top, right, bottom = self._grid_bounds
            rows, cols = self._grid_shape
            if right <= left or bottom <= top:
                raise ValueError("grid_bounds must describe a positive area")
            if rows < 1 or cols < 1:
                raise ValueError("grid_shape must be positive")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cell_center(self, row: int, col: int) -> Tuple[int, int]:
        """Return the screen ``(x, y)`` coordinates for cell *(row, col)*."""
        if self._grid_bounds is not None and self._grid_shape is not None:
            left, top, right, bottom = self._grid_bounds
            rows, cols = self._grid_shape
            width = right - left
            height = bottom - top
            x = left + int(round((col + 0.5) * width / cols))
            y = top + int(round((row + 0.5) * height / rows))
            return (x, y)

        x = self._origin[0] + int(round((col + 0.5) * self._cell_w))
        y = self._origin[1] + int(round((row + 0.5) * self._cell_h))
        return (x, y)

    @staticmethod
    def _esc_pressed() -> bool:
        """Return True when the ESC key is currently pressed."""
        if sys.platform != "win32":
            return False
        try:
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            # On some platforms or unusual environments, ctypes may not
            # expose `windll` or `user32`; in that case, treat ESC as not pressed.
            return False
        return bool(user32.GetAsyncKeyState(0x1B) & 0x8000)

    def _check_failsafe(self) -> None:
        if self._esc_pressed():
            raise FailsafeTriggered("ESC pressed. Stopping.")

    def click_cell(self, row: int, col: int) -> None:
        """Left-click the centre of cell *(row, col)* to toggle its shade.

        Parameters
        ----------
        row:
            Zero-based row index.
        col:
            Zero-based column index.
        """
        self._check_failsafe()
        x, y = self.cell_center(row, col)
        if self._dry_run:
            print(f"[dry-run] click ({row}, {col}) → screen ({x}, {y})")
            return
        self._check_failsafe()
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
                self._check_failsafe()
                if board.state(r, c) == CellState.BLACK:
                    self.click_cell(r, c)

    def click_all_cells(self, rows: int, cols: int) -> None:
        """Click every cell in row-major order.

        Parameters
        ----------
        rows:
            Number of grid rows.
        cols:
            Number of grid columns.
        """
        if rows < 1 or cols < 1:
            raise ValueError("rows and cols must be positive integers")

        for r in range(rows):
            for c in range(cols):
                self._check_failsafe()
                self.click_cell(r, c)
