# W4H EmbracePlus CSV File Importer

Notebook + CLI to import **Empatica EmbracePlus Cloud per-minute biomarker CSVs** into W4H. Point it at an Empatica Health Monitoring Platform dump (the S3 tree with `v2 / <org> / <study> / <site> / participant_data / …`). It is **not** the Empatica **E4** importer (`w4h-data-recorder-csv-file-importer`).

**Publisher:** usc-infolab · **Kinds:** notebook, CLI · **Language:** Python

`plan` → review `manifest.yaml` → `import` / `sync` via `POST /datasets/:id/import/csv-batch`. Every payload sends `table_prefix: "embrace"`.

## Name

Repo: **`w4h-embraceplus-csv-file-importer`**. CLI: `w4h-embraceplus-csv-file-import`. Use this name so Contributions does not look like E4.

## What this is (vs E4)

| | This importer | E4 recorder |
|--|---------------|-------------|
| Device | **EmbracePlus** | Empatica **E4** |
| Source | Empatica Cloud / S3 dump | E4 Connect ZIP or headered research CSVs |
| Files | Headered `*_eda.csv`, `*_pulse-rate.csv`, … under `aggregated_per_minute` | Headerless `ACC.csv` (unix t0 + Hz) |
| Raw high-rate | Avro (`raw_data/`) — **not imported yet** | E4 Connect channel CSVs |

How people get these files: Empatica shares S3 access keys; you sync `v2/<org>/<study>/<site>/`. That layout is the standard Cloud hierarchy, not a rearranged export.

## Files it reads

```
participant_data/
  2026-10-08/
    P001-3YK9K1J2P4/
      digital_biomarkers/
        aggregated_per_minute/
          1-1-P001_2026-10-08_eda.csv
          1-1-P001_2026-10-08_pulse-rate.csv
          …
```

`--data-dir` can be the site folder, `participant_data`, or a single `aggregated_per_minute` folder. Same biomarker across **days and participants** becomes **one** table (e.g. every `*_eda.csv` → `embrace_eda`). Rows are keyed by `participant_full_id` + `timestamp_iso`. Sampling interval is 1 minute.

`reports/` and `digital_biomarkers/raw_data/*.avro` are ignored.

## Several subjects / new days / reimport

One `--data-dir` at the site (or `participant_data`) is enough. You do not run once per subject folder.

The importer does not watch the disk. After Empatica adds a date folder, **re-run `plan`** so `manifest.yaml` lists the new files, then `import`.

| Command | New minutes | Same minute again | Files you deleted from disk |
|---------|-------------|-------------------|-----------------------------|
| `import --mode append` (default) | Inserted | Skipped | Rows **stay** in the dataset |
| `import --mode replace` | Loaded after truncate | Table rebuilt from the current dump | **Removed** |

Use `append` for a growing dump. Use `replace` when the database should match the folder exactly.

Do not commit real Cloud downloads. `tests/fixtures/` is a tiny synthetic tree with the same headers.

## Who should do what

| Role | What to do |
|------|-----------|
| **Admin** | Ingest your Cloud CSVs into **your team's** catalog. CLI for cron. |
| **User** | Analyse loaded datasets. You cannot add datasets. |
| **Super admin** | Catalog this repo after it is on a git remote. |

## How it works

1. **Files** — In **Select importer…**, drop the Cloud zips (one for the site, or one per participant) or choose the unzipped `participant_data` folder. Every day and participant in that drop loads into the one dataset. The importer opens the zips and keeps the per-minute CSVs. Avro and reports are ignored. **Load example** uses the tiny fixtures in [`contribution.yaml`](contribution.yaml), not your export.
2. **Plan** — profiles locally, GeoMTS mapping, six checks, writes `manifest.yaml` when you pass `--data-dir`.
3. **Import** — 500-row chunks to `csv-batch` with `table_prefix: "embrace"`. `@@PROGRESS@@` lines for the in-app bar.

## Prerequisites

- Running **w4h-api** and a personal API key
- A dataset you can ingest into
- Python 3.10+

## Credentials

```bash
cp .env.example .env
# Edit .env — W4H_API_KEY only
```

## Install

```bash
pip install -e ".[dev,notebook]"
```

## Notebook

Open [`notebook/import_embraceplus_csv_file.ipynb`](notebook/import_embraceplus_csv_file.ipynb): **pick dataset → pick files → review mapping → import**. Prefer `--data-dir` on the unzipped Cloud tree so day folders stay intact.

## CLI

```bash
w4h-embraceplus-csv-file-import plan --data-dir /path/to/site-or-participant_data
export W4H_API_KEY=w4h_sk_...
w4h-embraceplus-csv-file-import import --dataset-id my-embrace --data-dir /path/to/site-or-participant_data --mode append
```

## One-command run (`run.sh`)

```bash
./run.sh plan
./run.sh import
```

## Tests

```bash
pytest tests/ -q -m "not integration"
```
