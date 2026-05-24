#!/usr/bin/env python3
"""
Scan directories for zip files and report corrupted images within them.
Usage: python3 verify_images.py <dir1> [dir2 ...] [--output report.csv]
"""

import argparse
import csv
import io
import os
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    sys.exit("Error: Pillow is required. Run: uv add Pillow")

try:
    from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
    from rich.console import Console
    from rich.text import Text
except ImportError:
    sys.exit("Error: rich is required. Run: uv add rich")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".ico"}

console = Console(highlight=False)


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


def scan_zip(zip_path: Path) -> tuple[list[dict], list[Text]]:
    results = []
    lines: list[Text] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            entries = [e for e in zf.infolist() if not e.is_dir()]
            image_entries = [e for e in entries
                             if Path(e.filename).suffix.lower() in IMAGE_EXTENSIONS
                             and not Path(e.filename).name.startswith("._")]

            if not image_entries:
                return results, []

            lines.append(Text.assemble(("  " + zip_path.name, "cyan"), f"  ({len(image_entries)} image(s))"))

            for entry in image_entries:
                try:
                    data = zf.read(entry.filename)
                except Exception as e:
                    status = "unreadable"
                    error = f"zip read error: {e}"
                    lines.append(Text.assemble(("    ✗ ", "red"), entry.filename, ("  — " + error, "red")))
                else:
                    ok, error = verify_image(data)
                    if ok:
                        status = "ok"
                        lines.append(Text.assemble(("    ✓ ", "green"), entry.filename))
                    else:
                        status = "corrupted"
                        lines.append(Text.assemble(("    ✗ ", "red"), entry.filename, ("  — " + error, "red")))

                results.append({
                    "zip_file": str(zip_path),
                    "image_file": entry.filename,
                    "status": status,
                    "error": error if status != "ok" else "",
                    "compressed_size": entry.compress_size,
                    "uncompressed_size": entry.file_size,
                })

    except zipfile.BadZipFile as e:
        lines.append(Text.assemble(("  ⚠ bad zip: ", "yellow"), str(zip_path), ("  — " + str(e), "yellow")))
        results.append({
            "zip_file": str(zip_path),
            "image_file": "",
            "status": "bad_zip",
            "error": str(e),
            "compressed_size": 0,
            "uncompressed_size": 0,
        })
    except Exception as e:
        lines.append(Text.assemble(("  ⚠ error: ", "yellow"), str(zip_path), ("  — " + str(e), "yellow")))

    return results, lines


def find_zips(directories: list[Path]) -> list[Path]:
    zips = []
    for d in directories:
        if not d.exists():
            console.print(f"[yellow]Warning: directory not found: {d}[/yellow]")
            continue
        zips.extend(sorted(p for p in d.rglob("*.zip") if not p.name.startswith("._")))
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
    parser.add_argument("--workers", "-w", type=int, default=os.cpu_count(),
                        help="Number of parallel worker processes (default: cpu count)")
    args = parser.parse_args()

    console.print(f"\n[bold]Scanning {len(args.directories)} director(y/ies)...[/bold]\n")

    zip_files = find_zips(args.directories)
    if not zip_files:
        console.print("No zip files found.")
        return

    console.print(f"Found [bold]{len(zip_files)}[/bold] zip file(s)  [workers: {args.workers}]\n")

    all_results: list[dict] = []
    progress = Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
    task = progress.add_task("Scanning zips", total=len(zip_files))

    with progress:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(scan_zip, zp): zp for zp in zip_files}
            try:
                for future in as_completed(futures):
                    results, lines = future.result()
                    for line in lines:
                        progress.console.print(line)
                    all_results.extend(results)
                    progress.advance(task)
            except KeyboardInterrupt:
                progress.console.print("\n[yellow]Interrupted — shutting down workers...[/yellow]")
                pool.shutdown(wait=False, cancel_futures=True)
                sys.exit(130)

    # Summary
    total   = len([r for r in all_results if r["image_file"]])
    ok      = len([r for r in all_results if r["status"] == "ok"])
    corrupt = len([r for r in all_results if r["status"] == "corrupted"])
    unread  = len([r for r in all_results if r["status"] == "unreadable"])
    bad_zip = len([r for r in all_results if r["status"] == "bad_zip"])

    console.rule()
    console.print("[bold]Summary[/bold]")
    console.print(f"  Zips scanned : {len(zip_files)}")
    console.print(f"  Images found : {total}")
    console.print(f"  [green]OK           : {ok}[/green]")
    if corrupt:
        console.print(f"  [red]Corrupted    : {corrupt}[/red]")
    if unread:
        console.print(f"  [red]Unreadable   : {unread}[/red]")
    if bad_zip:
        console.print(f"  [yellow]Bad zips     : {bad_zip}[/yellow]")

    write_csv(all_results, args.output)
    console.print(f"\nReport saved to: [bold]{args.output}[/bold]\n")

    if corrupt or unread or bad_zip:
        sys.exit(1)


if __name__ == "__main__":
    main()
