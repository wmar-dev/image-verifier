# image-verifier

Recursively scans directories for zip files and identifies corrupted images inside them. Reports results to the terminal and saves a CSV report.

## Requirements

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- Pillow (injected automatically via `uv run --with`)

## Usage

```bash
# Scan one or more directories (recursively finds all zip files)
uv run --with Pillow python3 verify_images.py <dir1> [dir2 ...]

# Specify a custom CSV output path
uv run --with Pillow python3 verify_images.py <dir1> --output results.csv
```

## Output

Terminal output shows a live per-file pass/fail as each zip is scanned, followed by a summary:

```text
Scanning 1 director(y/ies)...

Found 2 zip file(s)

  photos.zip  (3 image(s))
    ✓ vacation/img001.jpg
    ✗ vacation/img002.jpg  — truncated or unreadable pixel data
    ✓ vacation/img003.png

──────────────────────────────────────────────────
Summary
  Zips scanned : 2
  Images found : 3
  OK           : 2
  Corrupted    : 1

Report saved to: image_report_20260524_120000.csv
```

The CSV contains one row per image with columns: `zip_file`, `image_file`, `status`, `error`, `compressed_size`, `uncompressed_size`.

## Exit codes

| Code | Meaning                                                        |
|------|----------------------------------------------------------------|
| 0    | All images verified OK                                         |
| 1    | One or more corrupted/unreadable images or bad zip files found |

## Supported image formats

`.jpg` `.jpeg` `.png` `.gif` `.bmp` `.tiff` `.tif` `.webp` `.ico`
