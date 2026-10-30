# AGENTS.md — w4h-embraceplus-csv-file-importer

Importer module for **user-supplied Empatica EmbracePlus Cloud CSV files** (notebook + CLI + tests). Per-minute digital biomarkers from an Empatica Health Monitoring Platform dump (`participant_data/<date>/<participant>-<serial>/digital_biomarkers/aggregated_per_minute/`). **Not** Empatica E4 Connect (that is `w4h-data-recorder-csv-file-importer`). No bundled Cloud download. The notebook picks files with a chooser. In-app **Run** / `./run.sh` calls the CLI and loads the synthetic fixtures declared in `contribution.yaml`.

- API key via `W4H_API_KEY` in local `.env` only — never in git.
- Do not add direct Postgres / `to_sql` paths; use the W4H API (`POST /datasets/:id/import/csv-batch`).
- The module owns its mapping logic (`profile.py`, `mapping.py`, `reconcile.py`, `catalog.py`, `shapes.py`). Do not call any W4H API route except `csv-batch` and `GET /datasets` (notebook picker).
- Recurse Cloud trees; group same-biomarker files across days into one signal (`files:`). Do not flatten the dump in git.
- Official E4 Connect (unix t0 + Hz, no header) and EmbracePlus **Avro** raw (`digital_biomarkers/raw_data`) are out of scope here.
- Every `csv-batch` payload sends `table_prefix: "embrace"` (`config.TABLE_PREFIX`) — do not drop it.
- Progress: keep printing `@@PROGRESS@@ {json}` lines (contribution-runner.js parses them).
- Tests: `pytest tests/ -q -m "not integration"`. `contribution.yaml` is the test contract. `-m integration` tests need a running w4h-api.
