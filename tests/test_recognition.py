"""Tests for NumberRecognizer (OCR mocked)."""

from unittest.mock import patch

from PIL import Image, ImageDraw


def _make_image(w: int = 100, h: int = 100) -> Image.Image:
    return Image.new("RGB", (w, h), color=(255, 255, 255))


def _draw_grid(img: Image.Image, left: int, top: int, size: int, n: int) -> None:
    draw = ImageDraw.Draw(img)
    right = left + size
    bottom = top + size
    draw.rectangle((left, top, right, bottom), outline=(0, 0, 0), width=2)
    step = size / n
    for i in range(1, n):
        x = int(round(left + i * step))
        y = int(round(top + i * step))
        draw.line((x, top, x, bottom), fill=(0, 0, 0), width=2)
        draw.line((left, y, right, y), fill=(0, 0, 0), width=2)


def test_recognize_with_explicit_grid_size():
    """Recognize a grid when grid_size is provided (OCR mocked)."""
    from hitori_solver.recognition import NumberRecognizer

    # Mock pytesseract to return predictable values per cell.
    cell_values = iter(["1", "2", "3", "4", "5", "6", "7", "8", "9"])

    with patch("pytesseract.image_to_string", side_effect=lambda img, config: next(cell_values)):
        recognizer = NumberRecognizer()
        img = _make_image(90, 90)
        grid = recognizer.recognize(img, grid_size=(3, 3))

    assert len(grid) == 3
    assert len(grid[0]) == 3
    assert grid[0][0] == 1
    assert grid[2][2] == 9


def test_recognize_unrecognized_cell_defaults_to_zero():
    """Cells where OCR returns non-numeric text default to 0."""
    from hitori_solver.recognition import NumberRecognizer

    with patch("pytesseract.image_to_string", return_value="?"):
        recognizer = NumberRecognizer()
        img = _make_image(50, 50)
        grid = recognizer.recognize(img, grid_size=(1, 1))

    assert grid == [[0]]


def test_recognize_with_grid_region():
    """Providing grid_region should crop the image before recognition."""
    from hitori_solver.recognition import NumberRecognizer

    with patch("pytesseract.image_to_string", return_value="5"):
        recognizer = NumberRecognizer()
        img = _make_image(200, 200)
        # Provide a grid_region so the image is cropped to 100×100 before OCR.
        grid = recognizer.recognize(img, grid_region=(50, 50, 150, 150), grid_size=(1, 1))

    assert grid == [[5]]


def test_recognize_with_region_returns_used_region():
    """recognize_with_region should return the region used for OCR."""
    from hitori_solver.recognition import NumberRecognizer

    with patch("pytesseract.image_to_string", return_value="7"):
        recognizer = NumberRecognizer()
        img = _make_image(200, 200)
        grid, used_region = recognizer.recognize_with_region(
            img,
            grid_region=(30, 40, 130, 140),
            grid_size=(1, 1),
        )

    assert grid == [[7]]
    assert used_region == (30, 40, 130, 140)


def test_infer_grid_size_smoke():
    """_infer_grid_size should not raise and return positive integers."""
    from hitori_solver.recognition import NumberRecognizer

    recognizer = NumberRecognizer()
    # Create a simple 50×50 white image (no dark lines → minimal inference).
    img = _make_image(50, 50)
    rows, cols = recognizer._infer_grid_size(img)
    assert rows >= 1
    assert cols >= 1


def test_recognize_writes_debug_grid_image(tmp_path):
    """When requested, recognizer should save a debug grid image."""
    from hitori_solver.recognition import NumberRecognizer

    debug_path = tmp_path / "debug-grid.png"

    with patch("pytesseract.image_to_string", return_value="1"):
        recognizer = NumberRecognizer()
        img = _make_image(60, 60)
        grid = recognizer.recognize(
            img,
            grid_size=(1, 1),
            debug_grid_path=str(debug_path),
        )

    assert grid == [[1]]
    assert debug_path.exists()


def test_locate_grid_region_prefers_grid_over_full_screen_border():
    """Detector should prefer the internal square grid, not outer screen border."""
    from hitori_solver.recognition import NumberRecognizer

    img = _make_image(420, 320)
    draw = ImageDraw.Draw(img)
    draw.rectangle((2, 2, 417, 317), outline=(0, 0, 0), width=2)
    _draw_grid(img, left=90, top=40, size=200, n=6)

    recognizer = NumberRecognizer()
    region = recognizer._locate_grid_region(img)

    assert region is not None
    left, top, right, bottom = region
    assert abs(left - 90) <= 30
    assert abs(top - 40) <= 20
    assert abs((right - left) - 200) <= 30
    assert abs((bottom - top) - 200) <= 30


def test_locate_grid_region_uses_grid_size_to_pick_matching_grid():
    """Expected grid size should bias selection toward matching candidate."""
    from hitori_solver.recognition import NumberRecognizer

    img = _make_image(520, 320)
    _draw_grid(img, left=20, top=40, size=220, n=6)
    _draw_grid(img, left=290, top=40, size=180, n=8)

    recognizer = NumberRecognizer()
    region = recognizer._locate_grid_region(img, grid_size=(8, 8))

    assert region is not None
    left, top, right, bottom = region
    assert abs(left - 290) <= 25
    assert abs(top - 40) <= 20
    assert abs((right - left) - 180) <= 30
    assert abs((bottom - top) - 180) <= 30


def test_locate_grid_region_refines_oversized_candidate_to_grid():
    """Detector should shrink from oversized connected shape to aligned grid."""
    from hitori_solver.recognition import NumberRecognizer

    img = _make_image(420, 320)
    _draw_grid(img, left=90, top=60, size=160, n=6)

    draw = ImageDraw.Draw(img)
    # Add a connected dark strip to make the raw component wider than the grid.
    draw.rectangle((250, 60, 300, 220), fill=(0, 0, 0))

    recognizer = NumberRecognizer()
    region = recognizer._locate_grid_region(img, grid_size=(6, 6))

    assert region is not None
    left, top, right, bottom = region
    assert abs(left - 90) <= 30
    assert abs(top - 60) <= 20
    assert abs((right - left) - 160) <= 35
    assert abs((bottom - top) - 160) <= 35
