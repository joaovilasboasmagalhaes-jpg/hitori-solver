"""NumberRecognizer – extract the Hitori grid from a screenshot."""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

try:
    from PIL import Image, ImageOps
    import pytesseract
    import numpy as np
    _DEPS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _DEPS_AVAILABLE = False


class NumberRecognizer:
    """Extracts a grid of integers from a screenshot of a Hitori puzzle.

    The recognizer assumes the puzzle is rendered as a square (or
    rectangular) grid of equal-sized cells each containing a single
    integer.  It locates the grid by finding the largest rectangular
    dark-bordered region in the image, divides it into cells, and runs
    Tesseract OCR on each cell.

    Parameters
    ----------
    cell_padding:
        Fraction of the cell size to crop from each edge before running
        OCR.  Reduces noise from cell borders.  Defaults to ``0.15``.
    tesseract_config:
        Extra Tesseract configuration string passed directly to
        ``pytesseract.image_to_string``.  Defaults to a single-digit
        page-segmentation mode suitable for small number cells.
    """

    _DEFAULT_CONFIG = "--psm 10 -c tessedit_char_whitelist=0123456789"

    def __init__(
        self,
        cell_padding: float = 0.15,
        tesseract_config: Optional[str] = None,
    ) -> None:
        if not _DEPS_AVAILABLE:
            raise ImportError(  # pragma: no cover
                "NumberRecognizer requires 'Pillow', 'pytesseract', and "
                "'numpy'.  Install them with: pip install Pillow pytesseract numpy"
            )
        self._cell_padding = cell_padding
        self._config = tesseract_config or self._DEFAULT_CONFIG

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recognize(
        self,
        image: "Image.Image",
        grid_region: Optional[Tuple[int, int, int, int]] = None,
        grid_size: Optional[Tuple[int, int]] = None,
    ) -> List[List[int]]:
        """Recognize the Hitori grid in *image* and return it as a 2-D list.

        Parameters
        ----------
        image:
            A Pillow ``Image`` containing the puzzle.
        grid_region:
            Optional ``(left, top, right, bottom)`` crop coordinates that
            precisely bound the puzzle grid within *image*.  When omitted,
            the whole image is used.
        grid_size:
            Optional ``(rows, cols)`` specifying how many cells the grid
            contains.  When omitted, the recognizer attempts to infer the
            size automatically by assuming equal-sized square cells.

        Returns
        -------
        List[List[int]]
            A rectangular list-of-lists of positive integers representing
            the recognized puzzle values.
        """
        if grid_region is not None:
            image = image.crop(grid_region)

        if grid_size is not None:
            rows, cols = grid_size
        else:
            rows, cols = self._infer_grid_size(image)

        return self._extract_grid(image, rows, cols)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _infer_grid_size(self, image: "Image.Image") -> Tuple[int, int]:
        """Guess grid dimensions by analysing line density in the image."""
        gray = ImageOps.grayscale(image)
        arr = np.array(gray)
        # Detect dark horizontal and vertical lines (grid separators).
        row_means = arr.mean(axis=1)
        col_means = arr.mean(axis=0)

        h_lines = self._count_dark_lines(row_means)
        v_lines = self._count_dark_lines(col_means)

        # Grid lines include the outer border → n cells = n-1 internal + 2
        rows = max(1, h_lines - 1)
        cols = max(1, v_lines - 1)
        return rows, cols

    @staticmethod
    def _count_dark_lines(means: "np.ndarray", threshold: float = 100.0) -> int:
        """Count transitions into dark regions (i.e. number of line groups)."""
        dark = means < threshold
        count = 0
        in_dark = False
        for val in dark:
            if val and not in_dark:
                count += 1
                in_dark = True
            elif not val:
                in_dark = False
        return count if count > 1 else 2  # at least one cell

    def _extract_grid(
        self, image: "Image.Image", rows: int, cols: int
    ) -> List[List[int]]:
        """Divide *image* into a *rows* × *cols* grid and OCR each cell."""
        width, height = image.size
        cell_w = width / cols
        cell_h = height / rows

        pad_x = cell_w * self._cell_padding
        pad_y = cell_h * self._cell_padding

        grid: List[List[int]] = []
        for r in range(rows):
            row_vals: List[int] = []
            for c in range(cols):
                left = int(c * cell_w + pad_x)
                top = int(r * cell_h + pad_y)
                right = int((c + 1) * cell_w - pad_x)
                bottom = int((r + 1) * cell_h - pad_y)
                cell_img = image.crop((left, top, right, bottom))
                row_vals.append(self._ocr_cell(cell_img))
            grid.append(row_vals)
        return grid

    def _ocr_cell(self, cell_img: "Image.Image") -> int:
        """Run Tesseract on a single cell and return the recognized integer."""
        # Upscale for better OCR accuracy on small cells.
        scale = max(1, 60 // min(cell_img.width, cell_img.height))
        if scale > 1:
            cell_img = cell_img.resize(
                (cell_img.width * scale, cell_img.height * scale),
                Image.LANCZOS,
            )
        cell_img = ImageOps.grayscale(cell_img)

        text = pytesseract.image_to_string(cell_img, config=self._config).strip()
        try:
            return int(text)
        except ValueError:
            return 0  # unrecognized cell defaults to 0
