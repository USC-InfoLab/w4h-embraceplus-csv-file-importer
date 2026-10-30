"""Empatica EmbracePlus Cloud per-minute biomarker CSV layouts.

These are **not** Empatica E4 Connect files. Cloud dumps follow
``participant_data/<date>/<participant>-<serial>/digital_biomarkers/aggregated_per_minute/``
with headered CSVs named
``<study>-<site>-<participant>_<YYYY-MM-DD>_<biomarker>.csv``.

Column names follow Empatica Health Monitoring Platform Data Access
(EmbracePlus). Do not vendor real Cloud downloads — they are identifiable.
"""

from __future__ import annotations

import re
from pathlib import Path

SHAPE_MIN_OVERLAP = 0.9

CORE = ("timestampunix", "timestampiso", "participantfullid")

PREFERRED_COLUMNS = {
    "participantfullid": "participant_full_id",
    "timestampunix": "timestamp_unix",
    "timestampiso": "timestamp_iso",
    "missingvaluereason": "missing_value_reason",
}

SUBJECT_CANON = ("participantfullid", "subjectid", "participantid")

NOT_SUBJECT = {"missingvaluereason"}

NOT_VALUES = {
    "timestampunix",
    "timestampiso",
    "missingvaluereason",
    "participantfullid",
}

# Filename suffix (after the date) → slug. Screenshot dumps include ``acticounts``
# alongside ``activity-counts``; keep them distinct until a file proves they match.
FILENAME_SLUGS = {
    "accelerometers-std": "accelerometers_std",
    "actigraphy-counts": "actigraphy_counts",
    "acticounts": "acticounts",
    "activity-classification": "activity_classification",
    "activity-counts": "activity_counts",
    "activity-intensity": "activity_intensity",
    "body-position": "body_position",
    "double-support": "double_support",
    "eda": "eda",
    "gait-speed": "gait_speed",
    "met": "met",
    "mets": "met",
    "prv": "prv",
    "pulse-rate": "pulse_rate",
    "respiratory-rate": "respiratory_rate",
    "sleep-detection": "sleep_detection",
    "spo2": "spo2",
    "stance-time": "stance_time",
    "stance-time-asymmetry": "stance_time_asymmetry",
    "step-counts": "step_counts",
    "step-length": "step_length",
    "step-length-asymmetry": "step_length_asymmetry",
    "step-time": "step_time",
    "step-time-asymmetry": "step_time_asymmetry",
    "step-time-std": "step_time_std",
    "step-time-variance": "step_time_variance",
    "stride-length": "stride_length",
    "stride-time": "stride_time",
    "swing-time": "swing_time",
    "swing-time-asymmetry": "swing_time_asymmetry",
    "temperature": "temperature",
    "wearing-detection": "wearing_detection",
}

# Distinctive value columns (canonical) for each shape. Core headers are required too.
SHAPES: dict[str, dict] = {
    "embrace_accelerometers_std": {"any": {"accelerometersstdg"}},
    "embrace_actigraphy_counts": {"any": {"countxaxis", "vectormagnitude"}},
    "embrace_acticounts": {"any": {"acticounts"}},
    "embrace_activity_classification": {"any": {"activityclass"}},
    "embrace_activity_counts": {"any": {"activitycounts"}},
    "embrace_activity_intensity": {"any": {"activityintensity"}},
    "embrace_body_position": {"any": {"bodypositionleft", "bodypositionright"}},
    "embrace_double_support": {"any": {"doublesupportingait"}},
    "embrace_eda": {"any": {"edasclusiemens"}},
    "embrace_gait_speed": {"any": {"gaitspeedmps"}},
    "embrace_met": {"any": {"met"}},
    "embrace_prv": {"any": {"prvrmssdms"}},
    "embrace_pulse_rate": {"any": {"pulseratebpm"}},
    "embrace_respiratory_rate": {"any": {"respiratoryratebrpm"}},
    "embrace_sleep_detection": {"any": {"sleepdetectionstage"}},
    "embrace_spo2": {"any": {"spo2percentage"}},
    "embrace_stance_time": {"any": {"stancetimes"}},
    "embrace_stance_time_asymmetry": {"any": {"stancetimeasymmetrys"}},
    "embrace_step_counts": {"any": {"stepcounts"}},
    "embrace_step_length": {"any": {"steplengthm"}},
    "embrace_step_length_asymmetry": {"any": {"steplengthasymmetrym"}},
    "embrace_step_time": {"any": {"steptimes"}},
    "embrace_step_time_asymmetry": {"any": {"steptimeasymmetrys"}},
    "embrace_step_time_std": {"any": {"steptimestds"}},
    "embrace_step_time_variance": {"any": {"steptimevariances"}},
    "embrace_stride_length": {"any": {"stridelengthm"}},
    "embrace_stride_time": {"any": {"stridetimes"}},
    "embrace_swing_time": {"any": {"swingtimes"}},
    "embrace_swing_time_asymmetry": {"any": {"swingtimeasymmetrys"}},
    "embrace_temperature": {"any": {"temperaturecelsius"}},
    "embrace_wearing_detection": {"any": {"wearingdetectionpercentage"}},
}

_CLOUD_NAME = re.compile(
    r"^(?P<study>[^-]+)-(?P<site>[^-]+)-(?P<participant>[^_]+)_"
    r"(?P<date>\d{4}-\d{2}-\d{2})_(?P<biomarker>.+)\.csv$",
    re.I,
)


def canonicalize_header(header: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(header or ""))
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def parse_cloud_filename(name: str) -> dict | None:
    """Parse ``1-1-P001_2026-10-08_eda.csv``. None if the name is not Cloud-style."""
    m = _CLOUD_NAME.match(Path(name).name)
    if not m:
        return None
    biomarker = m.group("biomarker").lower()
    return {
        "study": m.group("study"),
        "site": m.group("site"),
        "participant": m.group("participant"),
        "date": m.group("date"),
        "biomarker": biomarker,
        "slug": FILENAME_SLUGS.get(biomarker) or re.sub(r"[^a-z0-9]+", "_", biomarker).strip("_"),
    }


def matched_shape(headers: list[str], filename: str | None = None) -> str | None:
    """Core Cloud headers plus a distinctive biomarker column."""
    canon = {canonicalize_header(h) for h in headers}
    if sum(1 for c in CORE if c in canon) / len(CORE) < SHAPE_MIN_OVERLAP:
        parsed = parse_cloud_filename(filename or "")
        if parsed:
            return f"embrace_{parsed['slug']}"
        return None
    parsed = parse_cloud_filename(filename or "")
    if parsed:
        named = f"embrace_{parsed['slug']}"
        spec = SHAPES.get(named)
        if spec and spec.get("any") and (spec["any"] & canon):
            return named
        if named in SHAPES:
            return named
    best = None
    best_n = 0
    for name, spec in SHAPES.items():
        hints = spec.get("any") or set()
        n = len(hints & canon)
        if n and n > best_n:
            best, best_n = name, n
    return best


def keep_row(headers: list[str], cells: list[str]) -> bool:
    return bool(cells) and any(str(c).strip() for c in cells)


def discover_csv_files(data_dir) -> list[Path]:
    """Cloud ``aggregated_per_minute`` trees, else Cloud-named CSVs, else top-level ``*.csv``."""
    root = Path(data_dir)
    nested = sorted(root.rglob("aggregated_per_minute/*.csv"))
    if nested:
        return nested
    named = sorted(
        p for p in root.rglob("*.csv") if parse_cloud_filename(p.name) and p.name != "manifest.yaml"
    )
    if named:
        return named
    return sorted(root.glob("*.csv"))
