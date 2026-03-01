"""CLI entry point for hitori-solver."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional


def _parse_grid(text: str) -> List[List[int]]:
    """Parse a whitespace/newline-separated grid of integers."""
    rows = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append([int(x) for x in line.split()])
    return rows


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hitori-solver",
        description="Automated solver for the Hitori puzzle game.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ------ solve subcommand ------
    solve_p = subparsers.add_parser(
        "solve",
        help="Solve a puzzle from a text file or stdin.",
    )
    solve_p.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Path to a text file containing the grid (default: stdin).",
    )
    solve_p.add_argument(
        "--mouse",
        action="store_true",
        help="Use mouse control to shade cells in the puzzle UI after solving.",
    )
    solve_p.add_argument(
        "--origin",
        nargs=2,
        type=int,
        metavar=("X", "Y"),
        default=[0, 0],
        help="Screen (x, y) coordinates of the top-left corner of the grid.",
    )
    solve_p.add_argument(
        "--cell-size",
        type=int,
        default=50,
        help="Size of each grid cell in pixels (default: 50).",
    )
    solve_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended mouse actions without actually clicking.",
    )

    # ------ capture subcommand ------
    capture_p = subparsers.add_parser(
        "capture",
        help="Capture the screen, recognise the puzzle, and optionally solve it.",
    )
    capture_p.add_argument(
        "--region",
        nargs=4,
        type=int,
        metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"),
        default=None,
        help="Screen region to capture (default: full primary monitor).",
    )
    capture_p.add_argument(
        "--grid-size",
        nargs=2,
        type=int,
        metavar=("ROWS", "COLS"),
        default=None,
        help="Known grid dimensions (rows cols). Inferred when omitted.",
    )
    capture_p.add_argument(
        "--save-capture",
        metavar="PATH",
        default=None,
        help="Save the captured screenshot to this path.",
    )
    capture_p.add_argument(
        "--debug-grid",
        metavar="PATH",
        default=None,
        help=(
            "Save the image used for OCR with grid boundaries drawn "
            "to help debug recognition."
        ),
    )
    capture_p.add_argument(
        "--debug-mouse",
        action="store_true",
        help=(
            "After recognition, click every cell left-to-right and "
            "top-to-bottom, then stop."
        ),
    )
    capture_p.add_argument(
        "--solve",
        action="store_true",
        help="Solve the recognized puzzle.",
    )
    capture_p.add_argument(
        "--mouse",
        action="store_true",
        help="Use mouse control to shade cells after solving.",
    )
    capture_p.add_argument(
        "--origin",
        nargs=2,
        type=int,
        metavar=("X", "Y"),
        default=None,
        help=(
            "Screen (x, y) coordinates of the top-left corner of the grid. "
            "When omitted, uses recognized grid position."
        ),
    )
    capture_p.add_argument(
        "--cell-size",
        type=float,
        default=None,
        help=(
            "Cell size in pixels. When omitted, inferred from the recognized "
            "grid bounds."
        ),
    )
    capture_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended mouse actions without actually clicking.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "solve":
        return _cmd_solve(args)
    elif args.command == "capture":
        return _cmd_capture(args)
    else:
        parser.print_help()
        return 0


def _cmd_solve(args: argparse.Namespace) -> int:
    from .board import HitoriBoard
    from .solver import HitoriSolver

    if args.input == "-":
        text = sys.stdin.read()
    else:
        with open(args.input) as fh:
            text = fh.read()

    try:
        grid = _parse_grid(text)
    except ValueError as exc:
        print(f"Error parsing grid: {exc}", file=sys.stderr)
        return 1

    board = HitoriBoard(grid)
    solver = HitoriSolver(board)

    print("Solving…")
    if solver.solve():
        print("Solution found!\n")
        print(board)
    else:
        print("No solution found.", file=sys.stderr)
        return 1

    if args.mouse:
        from .mouse_control import MouseController

        mc = MouseController(
            grid_origin=tuple(args.origin),  # type: ignore[arg-type]
            cell_size=args.cell_size,
            dry_run=args.dry_run,
        )
        mc.shade_solution(board)

    return 0


def _cmd_capture(args: argparse.Namespace) -> int:
    from .board import HitoriBoard
    from .recognition import NumberRecognizer
    from .screen_capture import ScreenCapture
    from .solver import HitoriSolver

    sc = ScreenCapture()
    region = tuple(args.region) if args.region else None
    image = sc.capture(region=region)  # type: ignore[arg-type]

    if args.save_capture:
        image.save(args.save_capture)
        print(f"Screenshot saved to {args.save_capture}")

    grid_size = tuple(args.grid_size) if args.grid_size else None
    recognizer = NumberRecognizer()
    grid, recognized_region = recognizer.recognize_with_region(
        image,
        grid_size=grid_size,
        debug_grid_path=args.debug_grid,
    )  # type: ignore[arg-type]

    capture_left = region[0] if region else 0
    capture_top = region[1] if region else 0
    grid_left, grid_top, grid_right, grid_bottom = recognized_region
    auto_origin = (capture_left + grid_left, capture_top + grid_top)
    mouse_origin = tuple(args.origin) if args.origin is not None else auto_origin

    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    if args.cell_size is not None:
        mouse_cell_size = float(args.cell_size)
        mouse_grid_bounds = None
    elif rows > 0 and cols > 0:
        grid_width = max(1, grid_right - grid_left)
        grid_height = max(1, grid_bottom - grid_top)
        mouse_cell_size = (grid_width / cols, grid_height / rows)
        mouse_grid_bounds = (
            mouse_origin[0],
            mouse_origin[1],
            mouse_origin[0] + grid_width,
            mouse_origin[1] + grid_height,
        )
    else:
        mouse_cell_size = 50.0
        mouse_grid_bounds = None

    if args.debug_grid:
        print(f"Debug grid image saved to {args.debug_grid}")

    print("Recognized grid:")
    for row in grid:
        print(" ".join(str(v) for v in row))

    if args.debug_mouse:
        from .mouse_control import FailsafeTriggered, MouseController

        if not grid or not grid[0]:
            print("No grid recognized for mouse debug.", file=sys.stderr)
            return 1

        print(
            f"\nDebug mouse: clicking all {rows}×{cols} cells "
            "(left-to-right, top-to-bottom)…"
        )
        mc = MouseController(
            grid_origin=mouse_origin,
            cell_size=mouse_cell_size,
            dry_run=args.dry_run,
            grid_bounds=mouse_grid_bounds,
            grid_shape=(rows, cols) if mouse_grid_bounds is not None else None,
        )
        try:
            mc.click_all_cells(rows, cols)
        except FailsafeTriggered as exc:
            print(str(exc), file=sys.stderr)
            return 130
        return 0

    if not args.solve:
        return 0

    board = HitoriBoard(grid)
    solver = HitoriSolver(board)

    print("\nSolving…")
    if solver.solve():
        print("Solution found!\n")
        print(board)
    else:
        print("No solution found.", file=sys.stderr)
        return 1

    if args.mouse:
        from .mouse_control import FailsafeTriggered, MouseController

        mc = MouseController(
            grid_origin=mouse_origin,
            cell_size=mouse_cell_size,
            dry_run=args.dry_run,
            grid_bounds=mouse_grid_bounds,
            grid_shape=(rows, cols) if mouse_grid_bounds is not None else None,
        )
        try:
            mc.shade_solution(board)
        except FailsafeTriggered as exc:
            print(str(exc), file=sys.stderr)
            return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
