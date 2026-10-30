"""Setup check: planned manifest matches Cloud-tree CSV headers."""

import csv
import re
import shutil
from pathlib import Path

import pytest
import yaml

from w4h_embraceplus_csv_file_importer.manifest import write_manifest
from w4h_embraceplus_csv_file_importer.mapping import plan_directory

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_TOP_LEVEL = ("vendor", "format", "version", "title", "signals")
REQUIRED_SIGNAL_KEYS = ("slug", "file", "columns", "geomts_mapping")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@pytest.fixture(scope="module")
def data_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("planned")
    shutil.copytree(REPO_ROOT / "tests" / "fixtures", root, dirs_exist_ok=True)
    write_manifest(root, plan_directory(root))
    return root


@pytest.fixture(scope="module")
def manifest(data_root):
    path = data_root / "manifest.yaml"
    assert path.is_file()
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_manifest_has_required_top_level_keys(manifest):
    missing = [k for k in REQUIRED_TOP_LEVEL if k not in manifest]
    assert not missing
    assert manifest["signals"]


def test_signals_have_required_keys_and_unique_slugs(manifest):
    slugs = []
    for signal in manifest["signals"]:
        missing = [k for k in REQUIRED_SIGNAL_KEYS if k not in signal]
        assert not missing, f"signal {signal.get('slug')!r} is missing keys: {missing}"
        assert IDENT.match(signal["slug"])
        slugs.append(signal["slug"])
    assert len(slugs) == len(set(slugs))


def test_geomts_mapping_references_declared_columns(manifest):
    for signal in manifest["signals"]:
        declared = {c["name"] for c in signal["columns"]}
        mapping = signal["geomts_mapping"]
        assert mapping["signal_type"] == signal["slug"]
        referenced = [mapping["subject"]]
        if mapping.get("time"):
            referenced += mapping["time"].get("combine") or [mapping["time"]["column"]]
        referenced += [v["source"] for v in mapping.get("values") or []]
        unknown = [c for c in referenced if c not in declared]
        assert not unknown, f"{signal['slug']}: {unknown}"


def test_csv_files_exist_and_headers_match_manifest(manifest, data_root):
    for signal in manifest["signals"]:
        path = data_root / signal["file"]
        assert path.is_file(), f"{signal['slug']}: missing {path}"
        with path.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f), None)
        expected = [c.get("source", c["name"]) for c in signal["columns"] if not c.get("injected")]
        assert header == expected, f"{signal['slug']}: {header} != {expected}"


