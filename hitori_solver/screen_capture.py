"""ScreenCapture – grab screenshots for board recognition."""

from __future__ import annotations

from typing import Optional, Tuple

try:
    from PIL import Image
    import mss
    import mss.tools
    _DEPS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _DEPS_AVAILABLE = False


class ScreenCapture:
    """Captures screenshots of the entire screen or a specific region.

    Parameters
    ----------
    monitor_index:
        The monitor to capture (1-based index as used by *mss*).
        Defaults to the primary monitor (``1``).
    """

    def __init__(self, monitor_index: int = 1) -> None:
        if not _DEPS_AVAILABLE:
            raise ImportError(  # pragma: no cover
                "ScreenCapture requires 'mss' and 'Pillow'. "
                "Install them with: pip install mss Pillow"
            )
        self._monitor_index = monitor_index

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> "Image.Image":
        """Capture a screenshot and return it as a Pillow ``Image``.

        Parameters
        ----------
        region:
            An optional ``(left, top, width, height)`` bounding box in
            screen pixels.  When ``None`` the full monitor is captured.

        Returns
        -------
        PIL.Image.Image
            The captured image in RGB mode.
        """
        with mss.mss() as sct:
            if region is not None:
                left, top, width, height = region
                monitor = {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                }
            else:
                monitor = sct.monitors[self._monitor_index]

            screenshot = sct.grab(monitor)
            return Image.frombytes(
                "RGB",
                (screenshot.width, screenshot.height),
                screenshot.rgb,
            )

    def save(
        self,
        path: str,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> None:
        """Capture a screenshot and save it to *path*.

        Parameters
        ----------
        path:
            Destination file path (format inferred from extension, e.g.
            ``.png``, ``.jpg``).
        region:
            Optional ``(left, top, width, height)`` bounding box.
        """
        img = self.capture(region=region)
        img.save(path)
