"""Tests for ScreenCapture (mocked to avoid real screen access)."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


def test_capture_returns_pil_image():
    """ScreenCapture.capture() should return a PIL Image."""
    from PIL import Image

    fake_screenshot = MagicMock()
    fake_screenshot.width = 100
    fake_screenshot.height = 80
    fake_screenshot.rgb = b"\x00\x00\x00" * (100 * 80)

    mock_monitors = [{}, {"left": 0, "top": 0, "width": 100, "height": 80}]

    with patch("mss.mss") as mock_mss:
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.monitors = mock_monitors
        ctx.grab = MagicMock(return_value=fake_screenshot)
        mock_mss.return_value = ctx

        from hitori_solver.screen_capture import ScreenCapture

        sc = ScreenCapture(monitor_index=1)
        img = sc.capture()

    assert isinstance(img, Image.Image)
    assert img.width == 100
    assert img.height == 80


def test_capture_with_region():
    """ScreenCapture.capture(region=...) should use the provided bounding box."""
    from PIL import Image

    fake_screenshot = MagicMock()
    fake_screenshot.width = 200
    fake_screenshot.height = 150
    fake_screenshot.rgb = b"\xff\xff\xff" * (200 * 150)

    with patch("mss.mss") as mock_mss:
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.grab = MagicMock(return_value=fake_screenshot)
        mock_mss.return_value = ctx

        from hitori_solver.screen_capture import ScreenCapture

        sc = ScreenCapture()
        img = sc.capture(region=(10, 20, 200, 150))

    ctx.grab.assert_called_once_with(
        {"left": 10, "top": 20, "width": 200, "height": 150}
    )
    assert img.width == 200


def test_save_writes_file(tmp_path):
    """ScreenCapture.save() should persist the image to disk."""
    from PIL import Image

    fake_screenshot = MagicMock()
    fake_screenshot.width = 4
    fake_screenshot.height = 4
    fake_screenshot.rgb = b"\x80\x80\x80" * (4 * 4)

    mock_monitors = [{}, {"left": 0, "top": 0, "width": 4, "height": 4}]

    with patch("mss.mss") as mock_mss:
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.monitors = mock_monitors
        ctx.grab = MagicMock(return_value=fake_screenshot)
        mock_mss.return_value = ctx

        from hitori_solver.screen_capture import ScreenCapture

        sc = ScreenCapture()
        path = str(tmp_path / "shot.png")
        sc.save(path)

    assert (tmp_path / "shot.png").exists()
