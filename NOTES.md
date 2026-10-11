# Notes

## Step 1 — Setup
- `llm.py` wraps every LLM call and logs tokens, latency and cost to `logs/llm_calls.jsonl`.
- Haiku 5.5 takes no temperature/top_p/top_k. `effort` controls thinking.
- Type error on `output_config`: `effort` needed a `Literal[...]` type, not `str`.
- Select response blocks by `type`, never by position (a thinking block can come first).
- First smoke call: 38 in / 69 out tokens, 1.4s, $0.00004.

## Step 2 — Data collection
- `collect.py` fetches trials from the ClinicalTrials.gov API v2 (paginated with `nextPageToken`), caches raw JSON in `data/raw/<group>.json`, flattens to one row per trial and saves `data/processed/trials.parquet`.
- Raw data is kept separate from processed data: a bug in `flatten()` is fixed and re-run without calling the API again.
- Parquet keeps list columns (`phases`, `conditions`, `interventions`); CSV would turn them into text.
- Always use `.get(key, default)`: many trials lack fields (no phase, no start date).
- `df[mask]` made the type checker think the result could be a Series; `df.loc[mask]` fixes it.
- Missing `src/biowatch/__init__.py` only broke the build once `pyproject.toml` changed and `uv` rebuilt the package.
- Line length set to 79 (PEP 8) in `[tool.ruff]`.

### Exploration (300 trials, 100 per group, 300 unique `nct_id`)
- **Per phase:** NA 91, none 57, PHASE2 56, PHASE1 35, PHASE3 23, PHASE4 22, PHASE1+PHASE2 8, EARLY_PHASE1 5, PHASE2+PHASE3 3.
- **Per sponsor class:** OTHER 197, INDUSTRY 89, NIH 8, OTHER_GOV 3, NETWORK 2, FED 1.
- **Summary length (words):** min 5, median 66, max 666.
- **Missing values:** phases 19.0% (empty list), interventions 8.0% (empty list), start_date 0.7%. Every other column 0%.
- No trial was dropped for an empty summary, and no duplicate `nct_id` appeared across groups.
- Worth remembering for step 3: very short summaries (5 words) leave the LLM little to extract, and `NA` phase (not applicable) is a real value, different from a missing phase.
