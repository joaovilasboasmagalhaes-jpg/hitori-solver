"""Tests for NumberRecognizer (OCR mocked)."""

import pytest
from unittest.mock import patch, MagicMock
from PIL import Image


def _make_image(w: int = 100, h: int = 100) -> Image.Image:
    return Image.new("RGB", (w, h), color=(255, 255, 255))


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


def test_infer_grid_size_smoke():
    """_infer_grid_size should not raise and return positive integers."""
    from hitori_solver.recognition import NumberRecognizer
    import numpy as np

    recognizer = NumberRecognizer()
    # Create a simple 50×50 white image (no dark lines → minimal inference).
    img = _make_image(50, 50)
    rows, cols = recognizer._infer_grid_size(img)
    assert rows >= 1
    assert cols >= 1
