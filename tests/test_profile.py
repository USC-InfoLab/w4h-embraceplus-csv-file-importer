from w4h_embraceplus_csv_file_importer.profile import PREVIEW_ROWS, profile_csv


def test_profile_skips_leading_empty_values(tmp_path):
    """Leading 'device not recording' rows must not turn numeric columns into text."""
    rows = ["timestamp_unix,timestamp_iso,participant_full_id,pulse_rate_bpm,missing_value_reason"]
    for i in range(PREVIEW_ROWS * 3):
        rows.append(f"{1791417600000 + i * 60000},2026-10-08T00:{i % 60:02d}:00Z,1-1-P001,,device_not_recording")
    for i in range(5):
        rows.append(f"{1791428400000 + i * 60000},2026-10-08T03:{i:02d}:00Z,1-1-P001,{70 + i},")
    path = tmp_path / "1-1-P001_2026-10-08_pulse-rate.csv"
    path.write_text("\n".join(rows) + "\n")

    profile = profile_csv(path)
    types = dict(zip(profile["headers"], profile["inferred_types"]))
    assert types["pulse_rate_bpm"] == "integer"
    assert types["timestamp_unix"] == "bigint"
    assert types["missing_value_reason"] == "text"
