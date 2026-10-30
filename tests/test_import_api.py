"""Integration test against a running w4h-api. Run: pytest -m integration -q"""

import os

import pytest

from w4h_embraceplus_csv_file_importer.client import W4HClient


@pytest.mark.integration
def test_import_embraceplus_batch():
    if not os.environ.get("W4H_API_KEY", "").strip():
        pytest.skip("W4H_API_KEY not set")
    dataset_id = os.environ.get("W4H_DATASET_ID", "").strip()
    if not dataset_id:
        pytest.skip("W4H_DATASET_ID not set")
    result = W4HClient().import_csv_batch(
        dataset_id,
        {
            "signal": "pulse_rate_probe",
            "table_prefix": "embrace",
            "mode": "append",
            "dedupe_columns": ["participant_full_id", "timestamp_iso"],
            "columns": [
                {"name": "participant_full_id", "type": "text"},
                {"name": "timestamp_iso", "type": "timestamp"},
                {"name": "pulse_rate_bpm", "type": "double precision"},
            ],
            "mapping": {
                "signal_type": "pulse_rate_probe",
                "subject": "participant_full_id",
                "time": {"column": "timestamp_iso"},
                "values": [{"source": "pulse_rate_bpm", "name": "pulse_rate_bpm", "type": "double precision"}],
            },
            "rows": [
                {
                    "participant_full_id": "demo-1-1-P001",
                    "timestamp_iso": "2026-10-08T00:00:00Z",
                    "pulse_rate_bpm": "72",
                }
            ],
            "source_name": "EmbracePlus",
            "description": "integration test row",
        },
    )
    assert result.get("success") is True
