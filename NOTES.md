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

## Step 3 — LLM extraction
- `schemas.py` defines `TrialInfo` (interventions, conditions, population, comparator). `prompts/extract_v1.txt` holds the rules. `extract.py` has `parse_json()` (strips Markdown fences, validates with Pydantic), `extract_one()` (one retry) and a thread pool (5 workers) that writes `data/processed/extractions_v1.jsonl`.
- Every record keeps `prompt_version`, `model`, `raw_output`, `parsed`, `error` and token counts, so a result can be traced and re-parsed without a new API call.
- Prompt file = prompt only. Explanations pasted into it would be sent to the model on every call.
- Row subsets use `df.sample(..., random_state=0)`, not `head`: the table is ordered by group.

### Silent failure found
- On the first full run, one trial (NCT05198830) came back with all fields empty and no error. The model had echoed the JSON schema instead of filling it in. Pydantic ignores unknown keys by default and every field has a default, so it was "valid".
- Fix: `model_config = ConfigDict(extra="forbid")` on `TrialInfo`. An echoed schema is now rejected and goes to the retry path (checked on a fake echoed schema).
- On the re-run the same trial was extracted correctly and no retry fired, so the guard has not been seen working on a real case yet. The model has no temperature, so the same prompt can fail on one run and pass on the next.
- Lesson: a valid output is not necessarily a correct output. Parse rate alone is not a quality measure; that is what step 4 is for.

### Results (v1, claude-haiku-5-5, effort=low, 300 trials)
- **Parsed:** 300/300 (100%), 0 retries, every call ended with `end_turn` (no truncation).
- **Tokens per trial:** 848 in, 174 out on average.
- **Cost:** about $0.05 for the run (about $0.11 spent in total so far, from the log). **Time:** 94 s with 5 workers; median call 1.2 s, max 4.9 s.
- **Empty or null:** comparator 205/300, population 37/300, interventions 32/300, conditions 20/300.

### First impressions (about 20 outputs read)
- No invented values spotted. When the text does not say, the model leaves the field empty (rule 1 works).
- Empty `conditions` mostly happens when the summary never names the disease (the API has more context than the summary). Reasonable.
- Differences with the API fields are mostly naming and granularity: `NN1250` vs `insulin degludec` (same drug), case differences, one program split into four interventions, long population phrases. Step 4 needs normalisation and fuzzy matching, not exact comparison.
- My prompt defines interventions as "drugs or therapies", narrower than the API's (blood draws, tests, devices). Candidate for a v2 prompt, but only after step 4 gives numbers.
- The API is not a perfect answer key either (it lists `surgery` for a retinal-thickness study).
- Output tokens vary a lot (68 to 488) for similar prompts: most of it is thinking tokens at `effort=low`.

## Step 4 — Evaluation
- Wrote `eval/guidelines.md` before annotating. Each unclear case found while annotating led to a new rule (outcomes are not conditions, country is not population, qualifiers belong to the population, same-drug regimens are a comparator, brand names are not translated, full term over acronym). Gold: `data/gold/gold.jsonl`, split in `data/gold/split.json` (seed 42, 15 dev / 15 test, saved ids so the split cannot move).
- `evaluate.py`: `norm()` then `diff_lists()` (greedy one-to-one fuzzy match, returns the extra and missed strings), `match_lists()` (counts), `prf()`, `score_field()` (sums the counts over trials, then computes the scores). Micro scores: add counts first, never average per-trial percentages.
- Loop over the gold ids, not the predictions, so a trial the model failed on still counts against it.
- Precision is about the model's list, recall is about the gold's list. A model that returns nothing has precision 1.0, recall 0 and F1 0.
- Some "errors" are the metric's fault, not the model's: `(MCI)` in parentheses, one extra word. Fix the metric once, then re-score every version, before comparing prompts.
- Prompt examples must be invented, never taken from dev trials.
- v2 fixed naming and extras but made a regression: an imaging trial went from found to empty. Always look at what got worse, not only at the mean.
- No temperature means run-to-run noise. 3 runs were not enough: low and medium effort looked equal, then 8 runs showed medium ahead with half the spread. Compare means over several runs and look at the range.
- Do not attribute a gain to a change that did not target that field (conditions moved while only an intervention rule changed).
- Editing a gold row after seeing model outputs biases the comparison. One row was corrected to follow the written rule and the effect is documented in `eval/results.md`.
- `extract.py` now takes `PROMPT_VERSION` and `EFFORT` from the environment (`.env` is loaded by `llm.py` before they are read; a variable set on the command line wins) and runs `dev` or `test` from the saved split.
- Final: v4 at `effort=medium`, test run once: interventions F1 0.79, conditions F1 1.00 (n=15). Dev mean for interventions was 0.87. Test file kept in `data/processed/extractions_v4_test.jsonl`.
- Not done yet: population/comparator scoring, the 300-trial API consistency check.
