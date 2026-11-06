"""Open Empatica Cloud zips onto the same tree the CSV planner already reads.

A PI may hand over one zip for the site or one zip per participant. Both use the
S3 layout. Avro and other non-CSV members stay inside the archive.
"""

import os
import zipfile
from pathlib import Path

MAX_MEMBER_BYTES = 200 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 ** 3
MAX_MEMBERS = 10000


def _safe_csv_member(name: str) -> Path | None:
    raw = str(name or "").replace("\\", "/").lstrip("/")
    if not raw or raw.endswith("/"):
        return None
    parts = [part for part in raw.split("/") if part]
    if not parts:
        return None
    if any(part in (".", "..") or part.startswith(".") for part in parts):
        return None
    if not parts[-1].lower().endswith(".csv"):
        return None
    return Path(*parts)


def expand_zips(data_dir: Path) -> int:
    """Extract biomarker CSVs from every zip under data_dir. Existing files stay."""
    root = Path(data_dir).resolve()
    zips = sorted(path for path in root.rglob("*.zip") if path.is_file())
    extracted = 0
    total = 0
    for zpath in zips:
        try:
            archive = zipfile.ZipFile(zpath)
        except zipfile.BadZipFile:
            print(f"skip {zpath.name}: not a zip file")
            continue
        with archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                rel = _safe_csv_member(info.filename)
                if rel is None:
                    continue
                if info.file_size > MAX_MEMBER_BYTES:
                    print(f"skip {info.filename}: larger than {MAX_MEMBER_BYTES // (1024 * 1024)}MB")
                    continue
                if extracted >= MAX_MEMBERS or total + info.file_size > MAX_TOTAL_BYTES:
                    print("zip extract stopped: file or size limit reached")
                    return extracted
                dest = (root / rel).resolve()
                if dest != root and not str(dest).startswith(str(root) + os.sep):
                    continue
                if dest.exists():
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with archive.open(info, "r") as src, dest.open("wb") as out:
                    while written < MAX_MEMBER_BYTES:
                        chunk = src.read(min(1024 * 1024, MAX_MEMBER_BYTES - written))
                        if not chunk:
                            break
                        out.write(chunk)
                        written += len(chunk)
                total += written
                extracted += 1
        print(f"expanded {zpath.name}")
    if extracted:
        print(f"expanded {extracted} CSV files from zip")
    return extracted
