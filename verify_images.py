#!/usr/bin/env python3
"""
Scan directories for zip files and report corrupted images within them.
Usage: python3 verify_images.py <dir1> [dir2 ...] [--output report.csv]
"""

import argparse
import csv
import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    sys.exit("Error: Pillow is required. Run: pip3 install Pillow")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".ico"}

RESET  = "\033[0m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"


def verify_image(data: bytes) -> tuple[bool, str]:
    """Return (is_ok, error_message). Empty error means no problem."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except UnidentifiedImageError:
        return False, "not a recognized image format"
    except Exception as e:
        return False, f"verify failed: {e}"

    # verify() exhausts the stream; re-open to force full pixel decode
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
    except Exception as e:
        return False, f"truncated or unreadable pixel data: {e}"

    return True, ""


def scan_zip(zip_path: Path) -> list[dict]:
    results = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            entries = [e for e in zf.infolist() if not e.is_dir()]
            image_entries = [e for e in entries if Path(e.filename).suffix.lower() in IMAGE_EXTENSIONS]

            if not image_entries:
                return results

            print(f"  {CYAN}{zip_path.name}{RESET}  ({len(image_entries)} image(s))")

            for entry in image_entries:
                try:
                    data = zf.read(entry.filename)
                except Exception as e:
                    status = "unreadable"
                    error = f"zip read error: {e}"
                    print(f"    {RED}✗{RESET} {entry.filename}  — {error}")
                else:
                    ok, error = verify_image(data)
                    if ok:
                        status = "ok"
                        print(f"    {GREEN}✓{RESET} {entry.filename}")
                    else:
                        status = "corrupted"
                        print(f"    {RED}✗{RESET} {entry.filename}  — {error}")

                results.append({
                    "zip_file": str(zip_path),
                    "image_file": entry.filename,
                    "status": status,
                    "error": error if status != "ok" else "",
                    "compressed_size": entry.compress_size,
                    "uncompressed_size": entry.file_size,
                })

    except zipfile.BadZipFile as e:
        print(f"  {YELLOW}⚠ bad zip:{RESET} {zip_path}  — {e}")
        results.append({
            "zip_file": str(zip_path),
            "image_file": "",
            "status": "bad_zip",
            "error": str(e),
            "compressed_size": 0,
            "uncompressed_size": 0,
        })
    except Exception as e:
        print(f"  {YELLOW}⚠ error:{RESET} {zip_path}  — {e}")

    return results


def find_zips(directories: list[Path]) -> list[Path]:
    zips = []
    for d in directories:
        if not d.exists():
            print(f"{YELLOW}Warning: directory not found: {d}{RESET}")
            continue
        zips.extend(sorted(d.rglob("*.zip")))
    return zips


def write_csv(rows: list[dict], output_path: Path) -> None:
    fields = ["zip_file", "image_file", "status", "error", "compressed_size", "uncompressed_size"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Find corrupted images inside zip files.")
    parser.add_argument("directories", nargs="+", type=Path, help="Directories to scan")
    parser.add_argument("--output", "-o", type=Path,
                        default=Path(f"image_report_{datetime.now():%Y%m%d_%H%M%S}.csv"),
                        help="CSV output path (default: image_report_<timestamp>.csv)")
    args = parser.parse_args()

    print(f"\n{BOLD}Scanning {len(args.directories)} director(y/ies)...{RESET}\n")

    zip_files = find_zips(args.directories)
    if not zip_files:
        print("No zip files found.")
        return

    print(f"Found {len(zip_files)} zip file(s)\n")

    all_results: list[dict] = []
    for zp in zip_files:
        all_results.extend(scan_zip(zp))

    # Summary
    total   = len([r for r in all_results if r["image_file"]])
    ok      = len([r for r in all_results if r["status"] == "ok"])
    corrupt = len([r for r in all_results if r["status"] == "corrupted"])
    unread  = len([r for r in all_results if r["status"] == "unreadable"])
    bad_zip = len([r for r in all_results if r["status"] == "bad_zip"])

    print(f"\n{BOLD}{'─'*50}{RESET}")
    print(f"{BOLD}Summary{RESET}")
    print(f"  Zips scanned : {len(zip_files)}")
    print(f"  Images found : {total}")
    print(f"  {GREEN}OK           : {ok}{RESET}")
    if corrupt:
        print(f"  {RED}Corrupted    : {corrupt}{RESET}")
    if unread:
        print(f"  {RED}Unreadable   : {unread}{RESET}")
    if bad_zip:
        print(f"  {YELLOW}Bad zips     : {bad_zip}{RESET}")

    write_csv(all_results, args.output)
    print(f"\nReport saved to: {BOLD}{args.output}{RESET}\n")

    if corrupt or unread or bad_zip:
        sys.exit(1)


if __name__ == "__main__":
    main()
