# hitori-solver

Automated solver for the puzzle game Hitori.

This project provides a CLI with two workflows:

- `solve`: solve a puzzle from text input
- `capture`: screenshot the puzzle, run OCR, and optionally solve

## Requirements

- Python 3.9+
- (For screenshot capture) `Pillow` and `mss`
- (For OCR) `pytesseract`, `numpy`, and a local Tesseract installation
- (For mouse automation) `pyautogui`

## Installation

From the project root:

```bash
pip install -r requirements.txt
pip install -e .
```

For OCR to work, install the Tesseract executable on your system and make sure it is available on your `PATH`.

After this, the CLI command `hitori-solver` is available.

## Quick start

Show help:

```bash
hitori-solver --help
hitori-solver solve --help
hitori-solver capture --help
```

## Input format for `solve`

Use a rectangular grid of positive integers, space-separated, one row per line.

Example (`puzzle.txt`):

```text
1 2 3 2
3 1 4 4
2 3 1 2
4 4 2 1
```

## Solve from a file

```bash
hitori-solver solve puzzle.txt
```

## Solve from stdin

```bash
echo "1 1 2
2 3 3
1 2 3" | hitori-solver solve
```

## Capture and recognize from screen

Capture full primary monitor and print recognized grid:

```bash
hitori-solver capture
```

Capture a specific region (`LEFT TOP WIDTH HEIGHT`):

```bash
hitori-solver capture --region 100 120 700 700
```

If you already know the puzzle dimensions (`ROWS COLS`):

```bash
hitori-solver capture --grid-size 8 8
```

Save screenshot while capturing:

```bash
hitori-solver capture --save-capture capture.png
```

Save the OCR debug grid image (with detected cell boundaries):

```bash
hitori-solver capture --grid-size 8 8 --debug-grid debug-grid.png
```

Debug recognition + mouse mapping by clicking every recognized cell
left-to-right, top-to-bottom, then stopping:

```bash
hitori-solver capture --grid-size 8 8 --debug-mouse --origin 250 180 --cell-size 48
```

## Capture and solve in one command

```bash
hitori-solver capture --solve
```

## Optional mouse automation

After solving, automatically click black cells in your puzzle UI:

```bash
hitori-solver solve puzzle.txt --mouse --origin 250 180 --cell-size 48
```

Or with capture flow:

```bash
hitori-solver capture --solve --mouse --origin 250 180 --cell-size 48
```

Useful option:

- `--dry-run`: prints intended clicks without moving/clicking the mouse
- In `capture` mode, if `--origin` is omitted, mouse actions use the recognized grid's top-left screen position automatically.
- Press `ESC` at any time during mouse actions to stop immediately.

Example:

```bash
hitori-solver capture --solve --mouse --origin 250 180 --cell-size 48 --dry-run
```

## Output format

When a solution is found, solved board states are printed:

- ` [n] ` style entries (brackets) represent black/shaded cells
- plain numbers represent white/unshaded cells

If no valid solution is found, the command exits with a non-zero status.

## Running tests

```bash
pytest
```
