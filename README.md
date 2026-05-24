# image-verifier

Recursively scans directories for zip files and identifies corrupted images inside them. Reports results to the terminal and saves a CSV report.

## Requirements

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- Pillow, rich (installed via `uv sync`)

## Installation

```bash
git clone https://github.com/wmar-dev/image-verifier.git
cd image-verifier
uv sync
```

## Usage

```bash
# Scan one or more directories (recursively finds all zip files)
uv run python3 verify_images.py <dir1> [dir2 ...]

# Specify a custom CSV output path
uv run python3 verify_images.py <dir1> --output results.csv

# Limit parallel workers (default: cpu count)
uv run python3 verify_images.py <dir1> --workers 4
```

## Output

Terminal output shows a live per-file pass/fail as each zip is scanned, followed by a summary:

```text
Scanning 2 director(y/ies)...

Found 2 zip file(s)  [workers: 10]

  photos.zip  (3 image(s))
    ✓ vacation/img001.jpg
    ✗ vacation/img002.jpg  — truncated or unreadable pixel data
    ✓ vacation/img003.png
  archive.zip  (1 image(s))
    ✓ scan001.tiff
 ⠸ Scanning zips ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2/2 0:00:03
────────────────────────────────────────────────────────────────────────
Summary
  Zips scanned : 2
  Images found : 4
  OK           : 3
  Corrupted    : 1

Report saved to: image_report_20260524_120000.csv
```

The CSV contains one row per image with columns: `zip_file`, `image_file`, `status`, `error`, `compressed_size`, `uncompressed_size`.

## Exit codes

| Code | Meaning                                                        |
|------|----------------------------------------------------------------|
| 0    | All images verified OK                                         |
| 1    | One or more corrupted/unreadable images or bad zip files found |

## Filtering the CSV report

```bash
# Show only corrupted images and bad zips
awk -F',' '$3 == "corrupted" || $3 == "bad_zip"' image_report_*.csv

# Same, but keep the header row
awk -F',' 'NR==1 || $3 == "corrupted" || $3 == "bad_zip"' image_report_*.csv

# List only the zip files that contain corrupted images (unique paths)
awk -F',' '$3 == "corrupted" || $3 == "bad_zip" {print $1}' image_report_*.csv | sort -u
```

## Supported image formats

`.jpg` `.jpeg` `.png` `.gif` `.bmp` `.tiff` `.tif` `.webp` `.ico`
