"""Local CSV profiling: delimiter, header cleanup and per-column type inference."""

import csv
import re
from pathlib import Path

from .shapes import keep_row

DELIMITERS = [",", "\t", ";"]
PREVIEW_ROWS = 20
TYPE_MATCH_THRESHOLD = 0.95
INT4_MAX = 2147483647

_US_DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
_US_DATETIME_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?$", re.I)
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?")
_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")

_TYPE_CANDIDATES = [
    ("integer", lambda v: bool(_INT_RE.match(v))),
    ("double precision", lambda v: bool(_FLOAT_RE.match(v))),
    ("boolean", lambda v: v.lower() in ("true", "false", "t", "f")),
    ("date", lambda v: bool(_ISO_DATE_RE.match(v) or _US_DATE_RE.match(v))),
    ("timestamp", lambda v: bool(_ISO_DATETIME_RE.match(v) or _US_DATETIME_RE.match(v))),
    ("text", lambda v: bool(_TIME_RE.match(v))),
]


def infer_type(values: list[str]) -> str:
    non_empty = [v.strip() for v in values if v is not None and v.strip() != ""]
    if not non_empty:
        return "text"
    for type_name, test in _TYPE_CANDIDATES:
        if sum(1 for v in non_empty if test(v)) / len(non_empty) >= TYPE_MATCH_THRESHOLD:
            if type_name == "integer" and any(
                abs(int(v)) > INT4_MAX for v in non_empty if _INT_RE.match(v)
            ):
                return "bigint"
            return type_name
    return "text"


def detect_delimiter(header_line: str) -> str:
    return max(DELIMITERS, key=lambda d: header_line.count(d))


def profile_csv(path: Path, name: str | None = None) -> dict:
    """Header, delimiter and inferred types from the first PREVIEW_ROWS kept rows."""
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        first = f.readline()
        delimiter = detect_delimiter(first)
        f.seek(0)
        reader = csv.reader(f, delimiter=delimiter)
        headers = [h.strip() for h in next(reader, [])]
        preview = []
        for row in reader:
            if keep_row(headers, row):
                preview.append(row)
            if len(preview) >= PREVIEW_ROWS:
                break
    inferred = [
        infer_type([row[i] if i < len(row) else "" for row in preview]) for i in range(len(headers))
    ]
    return {
        "name": name or Path(path).name,
        "delimiter": delimiter,
        "headers": headers,
        "inferred_types": inferred,
    }
