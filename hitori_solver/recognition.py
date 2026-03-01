"""NumberRecognizer – extract the Hitori grid from a screenshot."""

from __future__ import annotations

from typing import List, Optional, Tuple

try:
    import numpy as np
    import pytesseract
    from PIL import Image, ImageDraw, ImageOps
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
        debug_grid_path: Optional[str] = None,
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
        debug_grid_path:
            Optional path where a debug image of the recognized grid is
            saved. The output image includes cell boundary lines showing
            how the recognizer segmented the puzzle before OCR.

        Returns
        -------
        List[List[int]]
            A rectangular list-of-lists of positive integers representing
            the recognized puzzle values.
        """
        grid, _region = self.recognize_with_region(
            image,
            grid_region=grid_region,
            grid_size=grid_size,
            debug_grid_path=debug_grid_path,
        )
        return grid

    def recognize_with_region(
        self,
        image: "Image.Image",
        grid_region: Optional[Tuple[int, int, int, int]] = None,
        grid_size: Optional[Tuple[int, int]] = None,
        debug_grid_path: Optional[str] = None,
    ) -> Tuple[List[List[int]], Tuple[int, int, int, int]]:
        """Recognize the puzzle and return both values and used grid region."""
        image_w, image_h = image.size
        if grid_region is None:
            grid_region = self._locate_grid_region(image, grid_size=grid_size)

        if grid_region is None:
            grid_region = (0, 0, image_w, image_h)

        image = image.crop(grid_region)

        if grid_size is not None:
            rows, cols = grid_size
        else:
            rows, cols = self._infer_grid_size(image)

        if debug_grid_path:
            self._save_debug_grid_image(image, rows, cols, debug_grid_path)

        return self._extract_grid(image, rows, cols), grid_region

    def _save_debug_grid_image(
        self,
        image: "Image.Image",
        rows: int,
        cols: int,
        path: str,
    ) -> None:
        """Save a debug image with the inferred grid segmentation."""
        debug_img = image.convert("RGB").copy()
        draw = ImageDraw.Draw(debug_img)

        width, height = debug_img.size
        for r in range(rows + 1):
            y = int(round(r * height / rows))
            draw.line([(0, y), (width - 1, y)], fill=(255, 0, 0), width=1)

        for c in range(cols + 1):
            x = int(round(c * width / cols))
            draw.line([(x, 0), (x, height - 1)], fill=(255, 0, 0), width=1)

        debug_img.save(path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _locate_grid_region(
        self,
        image: "Image.Image",
        grid_size: Optional[Tuple[int, int]] = None,
    ) -> Optional[Tuple[int, int, int, int]]:
        """Locate the most likely puzzle grid region in the image.

        The heuristic searches connected dark components and only accepts
        candidates whose projected grid lines align with dark lines in the
        image. Candidate boxes are refined by local resizing/shifting until
        grid alignment score is maximized.
        """
        gray = ImageOps.grayscale(image)
        orig_w, orig_h = gray.size
        if orig_w < 20 or orig_h < 20:
            return None

        max_dim = 700
        scale = min(1.0, max_dim / max(orig_w, orig_h))
        if scale < 1.0:
            small = gray.resize(
                (max(1, int(orig_w * scale)), max(1, int(orig_h * scale))),
                Image.Resampling.BILINEAR,
            )
        else:
            small = gray

        arr = np.array(small, dtype=np.uint8)
        threshold = int(max(40, min(180, np.percentile(arr, 25))))
        dark = arr <= threshold

        components = self._connected_components(dark)
        if not components:
            return None

        best_score = -1.0
        best_box = None
        min_side = max(24, int(min(arr.shape[0], arr.shape[1]) * 0.12))

        for top, left, bottom, right, _count in components:
            h = bottom - top + 1
            w = right - left + 1
            if h < min_side or w < min_side:
                continue

            side_ratio = min(h, w) / max(h, w)
            if side_ratio < 0.70:
                continue

            candidate_sizes = self._candidate_grid_sizes(
                dark,
                top,
                left,
                bottom,
                right,
                grid_size,
            )
            if not candidate_sizes:
                continue

            edge_margin = max(2, int(min(arr.shape[0], arr.shape[1]) * 0.01))
            touches_edges = 0
            if top <= edge_margin:
                touches_edges += 1
            if left <= edge_margin:
                touches_edges += 1
            if bottom >= arr.shape[0] - 1 - edge_margin:
                touches_edges += 1
            if right >= arr.shape[1] - 1 - edge_margin:
                touches_edges += 1
            edge_penalty = 0.2**touches_edges

            for rows, cols in candidate_sizes:
                refined_box, fit_score = self._refine_box_by_grid_fit(
                    dark,
                    (top, left, bottom, right),
                    rows,
                    cols,
                )

                # Reject candidates that do not convincingly align with a grid.
                if fit_score < 0.08:
                    continue

                area = (refined_box[2] - refined_box[0] + 1) * (
                    refined_box[3] - refined_box[1] + 1
                )
                refined_h = refined_box[2] - refined_box[0] + 1
                refined_w = refined_box[3] - refined_box[1] + 1
                refined_ratio = min(refined_h, refined_w) / max(refined_h, refined_w)
                area_bonus = 1.0 + min(2.0, float(np.log1p(area)) / 10.0)

                size_bonus = 1.0
                if grid_size is not None:
                    g_rows, g_cols = grid_size
                    size_error = abs(rows - g_rows) / max(1, g_rows) + abs(
                        cols - g_cols
                    ) / max(1, g_cols)
                    size_bonus = 1.0 / (1.0 + 8.0 * size_error)

                score = (
                    fit_score
                    * (0.4 + 0.6 * refined_ratio)
                    * area_bonus
                    * edge_penalty
                    * size_bonus
                )

                if score > best_score:
                    best_score = score
                    best_box = refined_box

        if best_box is None:
            return None

        top, left, bottom, right = best_box
        inv = 1.0 / scale
        out_left = max(0, int(left * inv))
        out_top = max(0, int(top * inv))
        out_right = min(orig_w, int((right + 1) * inv))
        out_bottom = min(orig_h, int((bottom + 1) * inv))
        if out_right - out_left < 4 or out_bottom - out_top < 4:
            return None
        return (out_left, out_top, out_right, out_bottom)

    def _candidate_grid_sizes(
        self,
        dark: "np.ndarray",
        top: int,
        left: int,
        bottom: int,
        right: int,
        grid_size: Optional[Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """Return plausible (rows, cols) candidates for a region."""
        if grid_size is not None:
            return [grid_size]

        region = dark[top : bottom + 1, left : right + 1]
        row_groups = self._count_dense_line_groups(region.mean(axis=1))
        col_groups = self._count_dense_line_groups(region.mean(axis=0))

        base_rows = max(1, row_groups - 1)
        base_cols = max(1, col_groups - 1)
        candidates: List[Tuple[int, int]] = []

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rows = base_rows + dr
                cols = base_cols + dc
                if rows < 2 or cols < 2:
                    continue
                if rows > 25 or cols > 25:
                    continue
                candidate = (rows, cols)
                if candidate not in candidates:
                    candidates.append(candidate)

        return candidates

    def _refine_box_by_grid_fit(
        self,
        dark: "np.ndarray",
        box: Tuple[int, int, int, int],
        rows: int,
        cols: int,
    ) -> Tuple[Tuple[int, int, int, int], float]:
        """Iteratively shift/resize a box to maximize grid alignment score."""
        h, w = dark.shape
        top, left, bottom, right = box
        best_box = (top, left, bottom, right)
        best_score = self._grid_alignment_score(dark, best_box, rows, cols)

        max_side = max(bottom - top + 1, right - left + 1)
        step = max(2, max_side // 10)

        while step >= 1:
            improved = True
            while improved:
                improved = False
                t, l, b, r = best_box
                candidates = [
                    (t - step, l, b, r),
                    (t + step, l, b, r),
                    (t, l - step, b, r),
                    (t, l + step, b, r),
                    (t, l, b - step, r),
                    (t, l, b + step, r),
                    (t, l, b, r - step),
                    (t, l, b, r + step),
                    (t - step, l - step, b + step, r + step),
                    (t + step, l + step, b - step, r - step),
                    (t - step, l, b + step, r),
                    (t, l - step, b, r + step),
                    (t + step, l, b - step, r),
                    (t, l + step, b, r - step),
                ]

                for cand in candidates:
                    ct, cl, cb, cr = cand
                    ct = max(0, ct)
                    cl = max(0, cl)
                    cb = min(h - 1, cb)
                    cr = min(w - 1, cr)
                    if cb - ct < 10 or cr - cl < 10:
                        continue

                    candidate_box = (ct, cl, cb, cr)
                    score = self._grid_alignment_score(dark, candidate_box, rows, cols)
                    if score > best_score + 1e-6:
                        best_score = score
                        best_box = candidate_box
                        improved = True

            step //= 2

        return best_box, best_score

    def _grid_alignment_score(
        self,
        dark: "np.ndarray",
        box: Tuple[int, int, int, int],
        rows: int,
        cols: int,
    ) -> float:
        """Score how well expected grid lines align with dark pixels."""
        top, left, bottom, right = box
        region = dark[top : bottom + 1, left : right + 1]
        if region.size == 0:
            return 0.0

        row_density = region.mean(axis=1)
        col_density = region.mean(axis=0)
        row_score = self._axis_grid_score(row_density, rows)
        col_score = self._axis_grid_score(col_density, cols)

        if row_score <= 0.0 or col_score <= 0.0:
            return 0.0
        return float(np.sqrt(row_score * col_score))

    def _axis_grid_score(self, density: "np.ndarray", cells: int) -> float:
        """Score one axis by comparing line positions vs cell interiors."""
        n = density.shape[0]
        if n < 8 or cells < 1:
            return 0.0

        line_positions = [int(round(i * (n - 1) / cells)) for i in range(cells + 1)]
        thickness = max(1, n // max(20, cells * 6))

        line_vals = []
        for pos in line_positions:
            lo = max(0, pos - thickness)
            hi = min(n, pos + thickness + 1)
            line_vals.append(float(density[lo:hi].mean()))

        gap_vals = []
        for i in range(cells):
            mid = int(round((line_positions[i] + line_positions[i + 1]) / 2))
            lo = max(0, mid - thickness)
            hi = min(n, mid + thickness + 1)
            gap_vals.append(float(density[lo:hi].mean()))

        if not line_vals or not gap_vals:
            return 0.0

        line_dark = float(np.mean(line_vals))
        gap_dark = float(np.mean(gap_vals))
        contrast = line_dark - gap_dark
        if contrast <= 0:
            return 0.0

        outer_dark = float(min(line_vals[0], line_vals[-1]))
        if len(line_vals) > 2:
            inner_dark = float(np.mean(line_vals[1:-1]))
        else:
            inner_dark = line_dark
        border_ratio = outer_dark / max(1e-6, inner_dark)

        # Require enough line presence and separation from cell interiors.
        score = (
            contrast * (0.5 + 0.5 * line_dark) * (0.3 + 0.7 * min(1.0, border_ratio))
        )
        return max(0.0, score)

    @staticmethod
    def _connected_components(
        dark: "np.ndarray",
    ) -> List[Tuple[int, int, int, int, int]]:
        """Return connected component bounding boxes in a boolean image."""
        h, w = dark.shape
        visited = np.zeros((h, w), dtype=bool)
        components: List[Tuple[int, int, int, int, int]] = []

        for r in range(h):
            for c in range(w):
                if not dark[r, c] or visited[r, c]:
                    continue

                stack = [(r, c)]
                visited[r, c] = True
                min_r = max_r = r
                min_c = max_c = c
                count = 0

                while stack:
                    cr, cc = stack.pop()
                    count += 1
                    if cr < min_r:
                        min_r = cr
                    if cr > max_r:
                        max_r = cr
                    if cc < min_c:
                        min_c = cc
                    if cc > max_c:
                        max_c = cc

                    if cr > 0 and dark[cr - 1, cc] and not visited[cr - 1, cc]:
                        visited[cr - 1, cc] = True
                        stack.append((cr - 1, cc))
                    if cr + 1 < h and dark[cr + 1, cc] and not visited[cr + 1, cc]:
                        visited[cr + 1, cc] = True
                        stack.append((cr + 1, cc))
                    if cc > 0 and dark[cr, cc - 1] and not visited[cr, cc - 1]:
                        visited[cr, cc - 1] = True
                        stack.append((cr, cc - 1))
                    if cc + 1 < w and dark[cr, cc + 1] and not visited[cr, cc + 1]:
                        visited[cr, cc + 1] = True
                        stack.append((cr, cc + 1))

                components.append((min_r, min_c, max_r, max_c, count))

        return components

    @staticmethod
    def _count_dense_line_groups(density: "np.ndarray", threshold: float = 0.25) -> int:
        """Count contiguous groups in 1-D density data above threshold."""
        dense = density >= threshold
        groups = 0
        in_group = False
        for val in dense:
            if val and not in_group:
                groups += 1
                in_group = True
            elif not val:
                in_group = False
        return groups

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
