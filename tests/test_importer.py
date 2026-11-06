"""Unit tests for profiling, mapping, and chunked import — no network."""

import json
import shutil
from pathlib import Path

from w4h_embraceplus_csv_file_importer.__main__ import main
from w4h_embraceplus_csv_file_importer.csv_import import CHUNK_SIZE, import_all, import_signal
from w4h_embraceplus_csv_file_importer.manifest import load_manifest
from w4h_embraceplus_csv_file_importer.mapping import plan_directory
from w4h_embraceplus_csv_file_importer.profile import infer_type
from w4h_embraceplus_csv_file_importer.reconcile import reconcile_manifest

FIXTURES = Path(__file__).parent / "fixtures"


class FakeClient:
    def __init__(self):
        self.imports = []

    def import_csv_batch(self, dataset_id, payload):
        self.imports.append((dataset_id, payload))
        n = len(payload["rows"])
        return {"inserted": n, "skipped": 0, "physical_schema": "ds_t", "physical_table": payload["signal"]}


def _signal(manifest, slug):
    return next(s for s in manifest["signals"] if s["slug"] == slug)


def test_infer_type():
    assert infer_type(["72", "74"]) == "integer"
    assert infer_type(["0.21", "0.24"]) == "double precision"
    assert infer_type(["2026-10-08T00:00:00.000Z"]) == "timestamp"
    assert infer_type(["1728360000000"]) == "bigint"


def test_plan_directory_reads_participant_zips(tmp_path):
    import zipfile

    first = tmp_path / "participant-a.zip"
    second = tmp_path / "participant-b.zip"
    csvs = sorted(FIXTURES.rglob("*.csv"))
    with zipfile.ZipFile(first, "w") as archive:
        archive.write(csvs[0], csvs[0].relative_to(FIXTURES).as_posix())
        archive.writestr("participant_data/2026-10-08/P001-SN0001/digital_biomarkers/raw_data/x.avro", b"avro")
        archive.writestr("../evil.csv", "nope\n")
    with zipfile.ZipFile(second, "w") as archive:
        for csv in csvs[1:]:
            archive.write(csv, csv.relative_to(FIXTURES).as_posix())
    manifest = plan_directory(tmp_path)
    assert {s["slug"] for s in manifest["signals"]} == {"eda", "pulse_rate", "temperature"}
    assert not list(tmp_path.rglob("*.avro"))
    assert len(list(tmp_path.rglob("aggregated_per_minute/*.csv"))) == 4
    assert not (tmp_path.parent / "evil.csv").exists()


def test_plan_cloud_tree_groups_days():
    manifest = plan_directory(FIXTURES)
    assert manifest["vendor"] == "embraceplus"
    eda = _signal(manifest, "eda")
    assert eda["matched_shape"] == "embrace_eda"
    assert eda["sampling_interval"] == "1min"
    assert eda["geomts_mapping"]["subject"] == "participant_full_id"
    assert eda["geomts_mapping"]["time"] == {"column": "timestamp_iso", "zone": "UTC"}
    assert [v["name"] for v in eda["geomts_mapping"]["values"]] == ["eda_scl_usiemens"]
    assert len(eda["files"]) == 2
    pr = _signal(manifest, "pulse_rate")
    assert pr["matched_shape"] == "embrace_pulse_rate"
    assert pr["geomts_mapping"]["values"][0]["name"] == "pulse_rate_bpm"
    assert reconcile_manifest(manifest)["errors"] == []


def test_import_uses_embrace_prefix_and_all_eda_days():
    manifest = plan_directory(FIXTURES)
    client = FakeClient()
    import_signal(client, "ds", _signal(manifest, "eda"), FIXTURES, mode="replace")
    assert client.imports[0][1]["table_prefix"] == "embrace"
    assert [p["mode"] for _, p in client.imports] == ["replace", "append"]
    rows = [row for _, p in client.imports for row in p["rows"]]
    assert len(rows) == 5
    assert rows[0]["participant_full_id"] == "demo-1-1-P001"
    assert rows[0]["timestamp_iso"].startswith("2026-10-08")


def test_import_progress_marker(capsys):
    manifest = plan_directory(FIXTURES)
    temp = _signal(manifest, "temperature")
    import_all(FakeClient(), "ds", {"signals": [temp]}, FIXTURES)
    line = next(l for l in capsys.readouterr().out.splitlines() if l.startswith("@@PROGRESS@@ "))
    progress = json.loads(line.split(" ", 1)[1])
    assert progress["signal"] == "temperature" and progress["rows_total"] == 2


def test_plan_command_writes_manifest(tmp_path):
    dest = tmp_path / "dump"
    shutil.copytree(FIXTURES, dest)
    assert main(["plan", "--data-dir", str(dest)]) == 0
    manifest = load_manifest(dest)
    assert {s["slug"] for s in manifest["signals"]} == {"eda", "pulse_rate", "temperature"}


def test_import_chunks_prefix(tmp_path):
    n = CHUNK_SIZE * 2 + 1
    body = "\n".join(
        f"{1728360000000 + i * 60000},2026-10-08T00:{i // 60:02d}:{i % 60:02d}.000Z,demo-1-1-P001,{60 + (i % 5)},"
        for i in range(n)
    )
    folder = tmp_path / "aggregated_per_minute"
    folder.mkdir()
    (folder / "1-1-P001_2026-10-08_pulse-rate.csv").write_text(
        "timestamp_unix,timestamp_iso,participant_full_id,pulse_rate_bpm,missing_value_reason\n" + body + "\n"
    )
    manifest = plan_directory(tmp_path)
    client = FakeClient()
    result = import_signal(client, "ds", manifest["signals"][0], tmp_path, mode="replace")
    assert [p["mode"] for _, p in client.imports] == ["replace", "append", "append"]
    assert all(p["table_prefix"] == "embrace" for _, p in client.imports)
    assert result["inserted"] == n
