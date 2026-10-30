"""CSV read + chunked API import (no full-file load)."""

import csv
import json
from pathlib import Path
from typing import Iterator

from .client import W4HClient
from .config import SOURCE_NAME, TABLE_PREFIX
from .mapping import subject_label
from .shapes import keep_row

CHUNK_SIZE = 500
PROGRESS_MARKER = "@@PROGRESS@@"


def _resolve_csv(data_dir: Path, file_name: str) -> Path:
    path = Path(file_name)
    if path.is_absolute():
        return path
    return (Path(data_dir) / file_name).resolve()


def _project_row(headers: list[str], cells: list[str], columns: list[dict]) -> dict:
    raw = {h: (cells[i] if i < len(cells) else "") for i, h in enumerate(headers)}
    if not columns:
        return raw
    row = {}
    for col in columns:
        if col.get("injected"):
            continue
        src = col.get("source") or col["name"]
        row[col["name"]] = raw.get(src, "")
    return row


def iter_csv_rows(
    csv_path: Path,
    chunk_size: int = CHUNK_SIZE,
    delimiter: str = ",",
    columns: list[dict] | None = None,
    fill: dict | None = None,
) -> Iterator[list[dict]]:
    columns = columns or []
    fill = fill or {}
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=delimiter)
        headers = [h.strip() for h in next(reader, [])]
        chunk: list[dict] = []
        for cells in reader:
            if not keep_row(headers, cells):
                continue
            row = _project_row(headers, cells, columns)
            for key, value in fill.items():
                if not str(row.get(key, "")).strip():
                    row[key] = value
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


def count_csv_rows(csv_path: Path, delimiter: str = ",") -> int:
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=delimiter)
        headers = [h.strip() for h in next(reader, [])]
        return sum(1 for cells in reader if keep_row(headers, cells))


def _signal_files(signal: dict) -> list[str]:
    files = signal.get("files") or []
    if files:
        return list(files)
    return [signal["file"]] if signal.get("file") else []


def import_signal(
    client: W4HClient,
    dataset_id: str,
    signal: dict,
    data_dir: Path,
    mode: str = "append",
    csv_path: Path | None = None,
    signal_index: int = 1,
    signal_count: int = 1,
) -> dict:
    slug = signal["slug"]
    paths = [csv_path] if csv_path else [_resolve_csv(data_dir, name) for name in _signal_files(signal)]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"CSV missing for signal {slug!r}: {', '.join(missing)}")

    delimiter = signal.get("delimiter", ",")
    mapping = dict(signal.get("geomts_mapping") or {})
    if signal.get("sampling_interval"):
        mapping["sampling_interval"] = signal["sampling_interval"]

    try:
        total_rows = sum(count_csv_rows(p, delimiter) for p in paths)
    except (OSError, csv.Error, UnicodeDecodeError):
        total_rows = None
    total_chunks = -(-total_rows // CHUNK_SIZE) if total_rows else None

    total_inserted = total_skipped = rows_done = 0
    last_physical: dict = {}
    chunk_index = 0
    first_chunk = True
    for path in paths:
        fill = {}
        if signal.get("subject_from_file"):
            field = mapping.get("subject") or "subject_id"
            fill[field] = subject_label(path, data_dir)
        for chunk in iter_csv_rows(
            path, delimiter=delimiter, columns=signal.get("columns") or [], fill=fill
        ):
            chunk_index += 1
            payload = {
                "signal": slug,
                "table_prefix": TABLE_PREFIX,
                "mode": mode if first_chunk else "append",
                "dedupe_columns": signal.get("dedupe_columns", []),
                "columns": signal.get("columns", []),
                "mapping": mapping,
                "description": signal.get("description", ""),
                "source_name": SOURCE_NAME,
                "source_url": signal.get("source_url"),
                "rows": chunk,
            }
            first_chunk = False
            result = client.import_csv_batch(dataset_id, payload)
            total_inserted += int(result.get("inserted", 0))
            total_skipped += int(result.get("skipped", 0))
            last_physical = {
                "physical_schema": result.get("physical_schema"),
                "physical_table": result.get("physical_table"),
            }
            rows_done += len(chunk)
            of = f"/{total_chunks}" if total_chunks else ""
            rows_of = f"/{total_rows}" if total_rows else ""
            print(
                f"{slug}: chunk {chunk_index}{of} ({rows_done}{rows_of} rows, "
                f"inserted={total_inserted} skipped={total_skipped})",
                flush=True,
            )
            print(
                f"{PROGRESS_MARKER} "
                + json.dumps(
                    {
                        "signal": slug,
                        "signal_index": signal_index,
                        "signal_count": signal_count,
                        "rows_done": rows_done,
                        "rows_total": total_rows,
                        "inserted": total_inserted,
                        "skipped": total_skipped,
                    }
                ),
                flush=True,
            )

    return {"signal": slug, "inserted": total_inserted, "skipped": total_skipped, **last_physical}


def import_all(
    client: W4HClient, dataset_id: str, manifest: dict, data_dir: Path, mode: str = "append"
) -> list[dict]:
    signals = manifest.get("signals", [])
    return [
        import_signal(
            client, dataset_id, signal, data_dir, mode=mode, signal_index=i, signal_count=len(signals)
        )
        for i, signal in enumerate(signals, start=1)
    ]
