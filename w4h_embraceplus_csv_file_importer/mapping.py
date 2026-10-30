"""Build a GeoMTS mapping manifest from local CSV profiles — no API call."""

import re
from pathlib import Path

from .catalog import apply_catalog
from .config import VENDOR
from .profile import profile_csv
from .shapes import (
    NOT_SUBJECT,
    NOT_VALUES,
    PREFERRED_COLUMNS,
    SUBJECT_CANON,
    canonicalize_header,
    discover_csv_files,
    matched_shape,
    parse_cloud_filename,
)

_SUBJECT_RE = re.compile(r"\b(id|subject|participant|patient)([_-]?id)?\b", re.I)
_NUMERIC = {"integer", "bigint", "double precision", "numeric"}
_LAT_RE = re.compile(r"^(lat|latitude)$", re.I)
_LON_RE = re.compile(r"^(lon|lng|long|longitude)$", re.I)
_DATE_NAME_RE = re.compile(r"^date$", re.I)
_TIME_NAME_RE = re.compile(r"^(time|timestamp)$", re.I)
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TIME_CANON = {"timestamp", "datetime", "timestampiso"}


def slug_from_filename(name: str) -> str:
    parsed = parse_cloud_filename(name)
    if parsed:
        return parsed["slug"]
    stem = re.sub(r"\.[^./]+$", "", Path(name).name).lower()
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    if stem[:1].isdigit():
        stem = f"s_{stem}"
    return stem or "signal"


def sql_column_name(header: str) -> str:
    canon = canonicalize_header(header)
    if canon in PREFERRED_COLUMNS:
        return PREFERRED_COLUMNS[canon]
    stripped = str(header or "").strip()
    if _IDENT_RE.match(stripped):
        return stripped
    name = re.sub(r"[^A-Za-z0-9]+", "_", stripped).strip("_").lower()
    name = re.sub(r"_+", "_", name)
    if not name or name[0].isdigit():
        name = f"c_{name}" if name else "col"
    return name[:63]


def _is_subject_header(header: str) -> bool:
    canon = canonicalize_header(header)
    if canon in NOT_SUBJECT:
        return False
    if canon in SUBJECT_CANON:
        return True
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", header)
    spaced = re.sub(r"[_-]+", " ", spaced)
    return bool(_SUBJECT_RE.search(spaced))


def subject_label(csv_path: Path, data_dir: Path) -> str:
    path = Path(csv_path)
    parsed = parse_cloud_filename(path.name)
    if parsed:
        return parsed["participant"]
    try:
        rel = path.resolve().relative_to(Path(data_dir).resolve())
    except ValueError:
        rel = Path(path.name)
    for part in reversed(rel.parts[:-1]):
        if part.lower() not in {"fixtures", "data", "tests", "csv", "tmp", "aggregated_per_minute",
                                "digital_biomarkers", "participant_data"} and not part.startswith("."):
            return part
    return path.stem


def build_signal(profile: dict) -> dict:
    columns, seen = [], set()
    for header, type_ in zip(profile["headers"], profile["inferred_types"]):
        name = sql_column_name(header)
        if name in seen:
            name = f"{name}_2"
        seen.add(name)
        columns.append({"name": name, "source": header, "type": type_, "description": ""})
    names = [c["name"] for c in columns]
    type_of = {c["name"]: c["type"] for c in columns}
    canon_of = {c["name"]: canonicalize_header(c["source"]) for c in columns}

    subject = None
    for canon in SUBJECT_CANON:
        subject = next((c["name"] for c in columns if canon_of[c["name"]] == canon), None)
        if subject:
            break
    if subject is None:
        subject = next((c["name"] for c in columns if _is_subject_header(c["source"])), None)
    injected = False
    if subject is None:
        subject = "subject_id"
        if subject in seen:
            subject = "subject_id_2"
        columns.append({
            "name": subject,
            "type": "text",
            "description": "",
            "injected": True,
        })
        names.append(subject)
        type_of[subject] = "text"
        canon_of[subject] = "subjectid"
        injected = True
    type_of[subject] = "text"
    next(c for c in columns if c["name"] == subject)["type"] = "text"

    iso = next((h for h in names if canon_of.get(h) == "timestampiso"), None)
    date_typed = [h for h in names if type_of[h] == "date"]
    ts_typed = [h for h in names if type_of[h] == "timestamp"]
    date_col = next((h for h in names if _DATE_NAME_RE.match(h)), None) or (
        date_typed[0] if len(date_typed) == 1 else None
    )
    time_col = next(
        (h for h in names if h != date_col and _TIME_NAME_RE.match(h) and type_of[h] != "timestamp"),
        None,
    )
    full_ts = iso or (ts_typed[0] if len(ts_typed) == 1 else None)

    time = None
    if iso:
        time = {"column": iso}
        next(c for c in columns if c["name"] == iso)["type"] = "timestamp"
    elif date_col and time_col:
        time = {"combine": [date_col, time_col]}
        next(c for c in columns if c["name"] == time_col)["type"] = "text"
    elif full_ts:
        time = {"column": full_ts}
    elif date_col:
        time = {"column": date_col}
    else:
        named = next((h for h in names if canon_of.get(h) in _TIME_CANON), None)
        if named:
            time = {"column": named}
    time_cols = time.get("combine") or [time["column"]] if time else []

    lat = next((h for h in names if _LAT_RE.match(h)), None)
    lon = next((h for h in names if _LON_RE.match(h)), None)
    geo = {"lat": lat, "lon": lon} if lat and lon else None

    used = {subject, *time_cols, *([lat, lon] if geo else [])} - {None}
    values = (
        []
        if time is None
        else [
            {"source": c["name"], "name": c["name"], "type": c["type"], "description": ""}
            for c in columns
            if c["name"] not in used
            and c["type"] in _NUMERIC
            and canon_of.get(c["name"]) not in NOT_VALUES
        ]
    )

    slug = slug_from_filename(profile["name"])
    mapping = {"signal_type": slug, "subject": subject, "time": time, "values": values}
    if geo:
        mapping["geo"] = geo
    signal = {
        "slug": slug,
        "file": profile["name"],
        "files": [profile["name"]],
        "delimiter": profile.get("delimiter", ","),
        "description": "",
        "columns": columns,
        "geomts_mapping": mapping,
        "dedupe_columns": [c for c in [subject, *time_cols] if c],
    }
    if injected:
        signal["subject_from_file"] = True
    shape = matched_shape(profile["headers"], profile["name"])
    if shape:
        signal["matched_shape"] = shape
    return signal


def build_manifest(profiles: list[dict]) -> dict:
    """One signal per biomarker; extra daily files append to ``files``."""
    by_slug: dict[str, dict] = {}
    signals = []
    for profile in profiles:
        sig = build_signal(profile)
        existing = by_slug.get(sig["slug"])
        if existing:
            existing.setdefault("files", [existing["file"]])
            if sig["file"] not in existing["files"]:
                existing["files"].append(sig["file"])
            continue
        by_slug[sig["slug"]] = sig
        signals.append(sig)
    manifest = {"vendor": VENDOR, "format": "csv", "version": "1.0.0", "signals": signals}
    apply_catalog(manifest)
    return manifest


def _rel_name(path: Path, data_dir: Path | None) -> str:
    if not data_dir:
        return path.name
    try:
        return str(path.resolve().relative_to(Path(data_dir).resolve()))
    except ValueError:
        return path.name


def plan_files(csv_files: list[Path], data_dir: Path | None = None) -> dict:
    """Profile the given CSVs (in list order) and return a draft manifest."""
    paths = [Path(p) for p in csv_files]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("CSV file(s) not found:\n  " + "\n  ".join(missing))
    if not paths:
        raise FileNotFoundError("No .csv files to plan")
    profiles = [profile_csv(p, name=_rel_name(p, data_dir)) for p in paths]
    empty = [p["name"] for p in profiles if not p["headers"]]
    if empty:
        raise ValueError(f"Empty or headerless CSV file(s): {', '.join(empty)}")
    return build_manifest(profiles)


def plan_directory(data_dir: Path) -> dict:
    """Profile Cloud per-minute CSVs under data_dir (nested dump or flat folder)."""
    data_dir = Path(data_dir)
    csv_files = discover_csv_files(data_dir)
    if not csv_files:
        raise FileNotFoundError(f"No EmbracePlus biomarker .csv files found in {data_dir}")
    return plan_files(csv_files, data_dir=data_dir)
