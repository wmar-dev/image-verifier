# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`verify_images.py` — a CLI tool that scans directories for `.zip` files and reports corrupted images found within them. Outputs a terminal summary and a timestamped CSV report.

## Running the script

The environment uses a `uv`-managed Python venv at `~/.venv`. Pillow must be injected at runtime:

```bash
# Scan one or more directories
uv run --with Pillow python3 verify_images.py <dir1> [dir2 ...]

# Custom CSV output path
uv run --with Pillow python3 verify_images.py <dir1> --output results.csv
```

Exit code 0 = all images OK; exit code 1 = corruption or bad zips found.

## Architecture

The script is a single file with four logical sections:

1. **`find_zips`** — recursively locates `.zip` files under the given directories.
2. **`verify_image`** — takes raw `bytes`, runs `Image.verify()` (structural check) then re-opens and calls `img.load()` (full pixel decode). Two passes are required because `verify()` exhausts the stream and cannot detect truncation on its own.
3. **`scan_zip`** — opens a zip, filters entries by `IMAGE_EXTENSIONS`, calls `verify_image` per entry, prints live per-file results, and returns a flat list of result dicts.
4. **`main`** — argument parsing, orchestration, summary printing, and CSV write via `write_csv`.

## Key behaviors to preserve

- `verify_image` must do **both** `img.verify()` and `img.load()` (on a fresh `BytesIO`). Removing either pass will miss a class of corruption.
- `IMAGE_EXTENSIONS` is the single place to add/remove supported formats.
- The script never extracts or modifies files — it is read-only with respect to the zips.
