"""contribution.yaml test contract: in-repo synthetic Cloud tree, no real dump."""

from pathlib import Path

from w4h_embraceplus_csv_file_importer.contribution import (
    automated_sample_paths,
    live_sample_paths,
    load_contribution,
)
from w4h_embraceplus_csv_file_importer.mapping import plan_files
from w4h_embraceplus_csv_file_importer.reconcile import reconcile_manifest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_contribution_yaml_has_required_keys():
    doc = load_contribution()
    assert doc["slug"] == "w4h-embraceplus-csv-file-importer"
    assert doc["kind"] == "ingest"
    assert doc["tests"]["automated"]["sample"]["kind"] == "fixtures"
    assert doc["tests"]["live"]["sample"]["kind"] == "fixtures"
    keys = {item["key"] for item in doc["inputs"]}
    assert "dataset_id" in keys


def test_automated_sample_is_tiny_in_repo_fixtures():
    paths = automated_sample_paths()
    assert {p.name for p in paths} == {
        "1-1-P001_2026-10-08_eda.csv",
        "1-1-P001_2026-10-08_pulse-rate.csv",
        "1-1-P001_2026-10-08_temperature.csv",
        "1-1-P001_2026-10-09_eda.csv",
    }
    assert all(p.is_file() and REPO_ROOT / "tests" / "fixtures" in p.parents for p in paths)
    assert all(p.stat().st_size < 2000 for p in paths)


def test_live_sample_plans_without_mapping_errors():
    source, paths, root = live_sample_paths()
    assert source == "fixtures"
    manifest = plan_files(paths, data_dir=root)
    review = reconcile_manifest(manifest)
    assert review["errors"] == []
    assert {s["slug"] for s in manifest["signals"]} == {"eda", "pulse_rate", "temperature"}
    assert len(_signal(manifest, "eda")["files"]) == 2


def _signal(manifest, slug):
    return next(s for s in manifest["signals"] if s["slug"] == slug)
