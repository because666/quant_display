"""Download and extract community Qlib CN dataset.

Usage:
    python scripts/fetch_qlib_data.py
    python scripts/fetch_qlib_data.py --target data/qlib_cn_data
"""

from __future__ import annotations

import argparse
import shutil
import tarfile
from pathlib import Path

import requests

DEFAULT_URL = "https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz"
DEFAULT_TARGET = Path("data/qlib_cn_data")
DEFAULT_ARCHIVE = Path("data/qlib_bin.tar.gz")


def download_file(url: str, out_path: Path, chunk_size: int = 1024 * 1024) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with out_path.open("wb") as fp:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    fp.write(chunk)


def extract_archive(archive_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(path=target_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Qlib CN data archive.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Download URL for qlib_bin.tar.gz")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET, help="Extraction directory")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE, help="Temporary archive path")
    parser.add_argument("--force", action="store_true", help="Re-download and re-extract even if exists")
    parser.add_argument("--keep-archive", action="store_true", help="Keep .tar.gz after extraction")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    qlib_bin_dir = args.target / "qlib_bin"

    if qlib_bin_dir.exists() and not args.force:
        print(f"Qlib data already exists: {qlib_bin_dir}")
        return

    if args.target.exists() and args.force:
        shutil.rmtree(args.target)

    print(f"Downloading: {args.url}")
    download_file(args.url, args.archive)
    print(f"Downloaded archive: {args.archive}")

    print(f"Extracting to: {args.target}")
    extract_archive(args.archive, args.target)
    print(f"Done. Qlib data directory: {qlib_bin_dir}")

    if not args.keep_archive and args.archive.exists():
        args.archive.unlink()
        print(f"Removed archive: {args.archive}")


if __name__ == "__main__":
    main()
