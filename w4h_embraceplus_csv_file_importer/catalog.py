"""EmbracePlus column descriptions. Fills empty fields only."""

from .shapes import canonicalize_header

TITLE = "EmbracePlus CSV import"
DESCRIPTION = (
    "Empatica EmbracePlus Health Monitoring Platform per-minute digital biomarker "
    "CSVs from an Empatica Cloud dump. Not Empatica E4 Connect. Review each "
    "signal before importing. Do not commit real Cloud downloads."
)

_SOURCE = "https://www.empatica.com/"

_COLUMNS = {
    "participantfullid": {"description": "Organization, study, site, and participant id."},
    "participant_full_id": {"description": "Organization, study, site, and participant id."},
    "timestampunix": {"description": "Unix time in milliseconds.", "unit": "ms"},
    "timestamp_unix": {"description": "Unix time in milliseconds.", "unit": "ms"},
    "timestampiso": {"description": "UTC sample time (ISO 8601)."},
    "timestamp_iso": {"description": "UTC sample time (ISO 8601)."},
    "missingvaluereason": {"description": "Why this minute has no biomarker value, when empty."},
    "missing_value_reason": {"description": "Why this minute has no biomarker value, when empty."},
}

_VALUES = {
    "embrace_accelerometers_std": {
        "accelerometersstdg": {"name": "accelerometers_std_g", "description": "Accelerometer magnitude SD", "unit": "g"},
    },
    "embrace_actigraphy_counts": {
        "countxaxis": {"name": "count_x_axis", "description": "Actigraphy counts X", "unit": "counts"},
        "countyaxis": {"name": "count_y_axis", "description": "Actigraphy counts Y", "unit": "counts"},
        "countzaxis": {"name": "count_z_axis", "description": "Actigraphy counts Z", "unit": "counts"},
        "vectormagnitude": {"name": "vector_magnitude", "description": "Actigraphy vector magnitude", "unit": "counts"},
    },
    "embrace_activity_counts": {
        "activitycounts": {"name": "activity_counts", "description": "Activity counts", "unit": "counts"},
    },
    "embrace_eda": {
        "edasclusiemens": {"name": "eda_scl_usiemens", "description": "EDA skin conductance level", "unit": "µS"},
    },
    "embrace_gait_speed": {
        "gaitspeedmps": {"name": "gait_speed_mps", "description": "Gait speed", "unit": "m/s"},
    },
    "embrace_met": {
        "met": {"name": "met", "description": "Metabolic equivalent of task", "unit": "MET"},
    },
    "embrace_prv": {
        "prvrmssdms": {"name": "prv_rmssd_ms", "description": "PRV RMSSD", "unit": "ms"},
    },
    "embrace_pulse_rate": {
        "pulseratebpm": {"name": "pulse_rate_bpm", "description": "Pulse rate", "unit": "bpm"},
    },
    "embrace_respiratory_rate": {
        "respiratoryratebrpm": {"name": "respiratory_rate_brpm", "description": "Respiratory rate", "unit": "brpm"},
    },
    "embrace_spo2": {
        "spo2percentage": {"name": "spo2_percentage", "description": "SpO2", "unit": "%"},
    },
    "embrace_step_counts": {
        "stepcounts": {"name": "step_counts", "description": "Step count", "unit": "counts"},
    },
    "embrace_temperature": {
        "temperaturecelsius": {"name": "temperature_celsius", "description": "Skin temperature", "unit": "°C"},
    },
    "embrace_wearing_detection": {
        "wearingdetectionpercentage": {
            "name": "wearing_detection_percentage",
            "description": "Wearing detection",
            "unit": "%",
        },
    },
    "embrace_sleep_detection": {
        "sleepdetectionstage": {"name": "sleep_detection_stage", "description": "Sleep stage code"},
    },
}

_DESCRIPTIONS = {
    "embrace_accelerometers_std": "EmbracePlus 1-minute accelerometer magnitude standard deviation.",
    "embrace_actigraphy_counts": "EmbracePlus 1-minute actigraphy counts (x/y/z and vector magnitude).",
    "embrace_acticounts": "EmbracePlus Cloud file named acticounts (keep separate from activity-counts).",
    "embrace_activity_classification": "EmbracePlus 1-minute activity class.",
    "embrace_activity_counts": "EmbracePlus 1-minute activity counts.",
    "embrace_activity_intensity": "EmbracePlus 1-minute activity intensity.",
    "embrace_body_position": "EmbracePlus 1-minute body position (left/right wrist columns).",
    "embrace_double_support": "EmbracePlus 1-minute double-support gait fractions.",
    "embrace_eda": "EmbracePlus 1-minute electrodermal activity (skin conductance level).",
    "embrace_gait_speed": "EmbracePlus 1-minute gait speed.",
    "embrace_met": "EmbracePlus 1-minute metabolic equivalent of task.",
    "embrace_prv": "EmbracePlus 1-minute pulse-rate variability (RMSSD).",
    "embrace_pulse_rate": "EmbracePlus 1-minute pulse rate.",
    "embrace_respiratory_rate": "EmbracePlus 1-minute respiratory rate.",
    "embrace_sleep_detection": "EmbracePlus 1-minute sleep stage.",
    "embrace_spo2": "EmbracePlus 1-minute SpO2.",
    "embrace_stance_time": "EmbracePlus 1-minute stance time.",
    "embrace_stance_time_asymmetry": "EmbracePlus 1-minute stance-time asymmetry.",
    "embrace_step_counts": "EmbracePlus 1-minute step counts.",
    "embrace_step_length": "EmbracePlus 1-minute step length.",
    "embrace_step_length_asymmetry": "EmbracePlus 1-minute step-length asymmetry.",
    "embrace_step_time": "EmbracePlus 1-minute step time.",
    "embrace_step_time_asymmetry": "EmbracePlus 1-minute step-time asymmetry.",
    "embrace_step_time_std": "EmbracePlus 1-minute step-time standard deviation.",
    "embrace_step_time_variance": "EmbracePlus 1-minute step-time variance.",
    "embrace_stride_length": "EmbracePlus 1-minute stride length.",
    "embrace_stride_time": "EmbracePlus 1-minute stride time.",
    "embrace_swing_time": "EmbracePlus 1-minute swing time.",
    "embrace_swing_time_asymmetry": "EmbracePlus 1-minute swing-time asymmetry.",
    "embrace_temperature": "EmbracePlus 1-minute skin temperature.",
    "embrace_wearing_detection": "EmbracePlus 1-minute wearing detection.",
}

SHAPES: dict[str, dict] = {
    name: {
        "description": desc,
        "source_url": _SOURCE,
        "sampling_interval": "1min",
        "columns": _COLUMNS,
        "values": _VALUES.get(name, {}),
    }
    for name, desc in _DESCRIPTIONS.items()
}


def apply_catalog(manifest: dict) -> None:
    """Fill empty title/description/units from the catalog, in place."""
    if not manifest.get("title"):
        manifest["title"] = TITLE
    if not manifest.get("description"):
        manifest["description"] = DESCRIPTION
    for signal in manifest.get("signals", []):
        sdef = SHAPES.get(signal.get("matched_shape") or "") or {}
        for key in ("description", "source_url", "sampling_interval"):
            if not signal.get(key) and sdef.get(key):
                signal[key] = sdef[key]
        for col in signal.get("columns", []):
            canon = canonicalize_header(col["name"])
            meta = sdef.get("columns", {}).get(canon)
            if not meta:
                continue
            if not col.get("description") and meta.get("description"):
                col["description"] = meta["description"]
            if not col.get("unit") and meta.get("unit"):
                col["unit"] = meta["unit"]
        for v in signal.get("geomts_mapping", {}).get("values") or []:
            meta = sdef.get("values", {}).get(canonicalize_header(v["source"]))
            if not meta:
                continue
            if meta.get("name") and v.get("name") == v.get("source"):
                v["name"] = meta["name"]
            if not v.get("description") and meta.get("description"):
                v["description"] = meta["description"]
            if not v.get("unit") and meta.get("unit"):
                v["unit"] = meta["unit"]
