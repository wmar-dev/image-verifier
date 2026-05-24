# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`verify_images.py` — a CLI tool that scans directories for `.zip` files and reports corrupted images found within them. Outputs a terminal summary and a timestamped CSV report.

## Running the script

The environment uses a `uv`-managed Python venv. Install dependencies once with `uv sync`, then:

```bash
# Scan one or more directories
uv run python3 verify_images.py <dir1> [dir2 ...]

# Custom CSV output path
uv run python3 verify_images.py <dir1> --output results.csv
```

Exit code 0 = all images OK; exit code 1 = corruption or bad zips found.

## Architecture

The script is a single file with four logical sections:

1. **`find_zips`** — recursively locates `.zip` files under the given directories, skipping any with names starting with `._` (macOS metadata forks).
2. **`verify_image`** — takes raw `bytes`, runs `Image.verify()` (structural check) then re-opens and calls `img.load()` (full pixel decode). Two passes are required because `verify()` exhausts the stream and cannot detect truncation on its own.
3. **`scan_zip`** — opens a zip, filters entries by `IMAGE_EXTENSIONS` (also skipping `._`-prefixed files), calls `verify_image` per entry, and returns `(list[dict], list[rich.Text])`. Output lines are buffered as `rich.Text` objects and printed atomically by the caller to prevent interleaving across parallel workers.
4. **`main`** — argument parsing (`--output`, `--workers`), dispatches zips to a `ProcessPoolExecutor`, drives a `rich` progress bar at the bottom of the terminal, collects results, prints summary, and writes the CSV.

## Key behaviors to preserve

- `verify_image` must do **both** `img.verify()` and `img.load()` (on a fresh `BytesIO`). Removing either pass will miss a class of corruption.
- `IMAGE_EXTENSIONS` is the single place to add/remove supported formats.
- `scan_zip` must never call `print()` directly — it returns `rich.Text` lines so the main process can print them via `progress.console.print()` while the progress bar is live.
- The script never extracts or modifies files — it is read-only with respect to the zips.
