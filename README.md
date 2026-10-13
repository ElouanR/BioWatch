# BioWatch

Extract structured information from clinical-trial descriptions with an LLM,
and measure how good the extraction is.

From the **title and brief summary** of a trial registered on
[ClinicalTrials.gov](https://clinicaltrials.gov), `claude-haiku-5-5` returns a
validated JSON object:

| field | meaning |
|---|---|
| `interventions` | drugs, devices, therapies the trial tests or gives |
| `conditions` | diseases the trial studies or treats |
| `population` | who is enrolled, if stated |
| `comparator` | what the intervention is compared against, if stated |

The focus of this repository is the **evaluation**: a written annotation
guideline, a 30-trial gold set split into dev and test, field-level precision
and recall with fuzzy matching, an error analysis, four prompt versions, and
a test number measured once.

## Pipeline

1. `collect.py` fetches 300 trials from the ClinicalTrials.gov API v2 (100
   each for lung cancer, Alzheimer's disease and type 2 diabetes), caches the
   raw JSON and flattens it to `data/processed/trials.parquet`.
2. `extract.py` calls the model with a versioned prompt (`prompts/`),
   validates the answer with Pydantic (`schemas.py`, unknown keys rejected),
   retries once on invalid output, and writes one record per trial (raw
   output, parsed result, tokens, latency) to `data/processed/`.
3. `evaluate.py` scores the extractions against the gold set (or against the
   API fields) and lists the extra and missed items.
4. `llm.py` wraps every call and logs tokens, latency and cost.

## Run it

```bash
uv sync
cp .env.example .env
uv run python src/biowatch/collect.py
uv run python src/biowatch/extract.py dev
uv run python src/biowatch/evaluate.py v4 dev
uv run python src/biowatch/evaluate.py v4 dev interventions
```

`extract.py` writes `data/processed/extractions_<version>.jsonl`; the files
committed under `*_dev` / `*_test` / `*_all` are single sample runs kept for
re-scoring (for example `evaluate.py v4_dev dev`).

`PROMPT_VERSION` and `EFFORT` are read from the environment (see
`.env.example`). Cost: about $0.10 for the 300 trials at `effort=medium`.

## Results

Metric: micro precision / recall / F1 per field, greedy one-to-one fuzzy
matching (`rapidfuzz`, threshold 90) after lower-casing and removing hyphens
and text in parentheses. Details and caveats in
[`eval/results.md`](eval/results.md).

**Test set, final version (v4, `effort=medium`, one run, n = 15 trials)**

| field | precision | recall | F1 |
|---|---|---|---|
| interventions | 0.71 | 0.88 | 0.79 |
| conditions | 1.00 | 1.00 | 1.00 |

**Dev set, prompt versions (n = 15 trials, mean over several runs)**

| prompt | interventions F1 | conditions F1 |
|---|---|---|
| v1 (first prompt) | 0.62 | 0.64 |
| v2 (naming and "what to leave out" rules) | 0.75 | 0.93 |
| v3 (+ diagnostic tools count) | 0.75 | 0.95 |
| v4 (+ observed-only studies have no intervention), `effort=low` | 0.82 | 0.96 |
| v4, `effort=medium` | 0.87 | 0.95 |

The model has no temperature, so the same prompt gives different results on
each run. Three runs were not enough to tell `low` from `medium` effort;
eight runs showed `medium` ahead (and about half as variable) for about 16%
more cost per trial.

**Against the API fields (v4, 300 trials):** F1 0.35 (interventions) and 0.38
(conditions). This is not a quality measure: the registration's structured
fields describe more than the summary shows, and scoring the API fields
against the 30 gold trials gives F1 0.31 and 0.36, the same level of
disagreement.

## Main errors

- **Too much detail in names:** stage, "metastatic" or a genetic marker kept
  in a condition name; dosage, brand or acronym left in an intervention.
  Fixed largely by v2.
- **Items taken from the background text:** related diseases and measurement
  tests listed as conditions or interventions.
- **Measurement-only studies:** the model lists the imaging method or the
  sampling method as an intervention when nobody receives a treatment. v4
  reduced this and it still happens on test.
- **Granularity:** one programme split into its phases, or a therapy listed
  together with its sub-protocol.
- **Matching noise:** several remaining "errors" are the same item written
  with one extra word, which a fuzzy threshold cannot absorb.

## Limits

- 15 dev and 15 test trials, about 30 gold items per field: one item moves a
  score by several points. Differences under about 0.1 F1 cannot be resolved.
- Dev was used to write the rules and scored many times, so dev numbers are
  optimistic. The test number is a single run.
- Several gold decisions are judgement calls (see
  [`eval/guidelines.md`](eval/guidelines.md)), and one gold row was corrected
  after model outputs had been seen.
- `population` and `comparator` are extracted but not evaluated.
- The model reads only the title and brief summary; the detailed description
  and eligibility criteria are not used.
- One model (`claude-haiku-5-5`), three disease areas.

## Next steps

- Score `population` and `comparator` by hand.
- Give the model the detailed description and eligibility criteria, with a
  new gold set for those fields.
- Semantic search over the extracted fields, then retrieval-augmented
  question answering on top of it.

## Repository

```
src/biowatch/   collect, extract, evaluate, llm wrapper, schemas
prompts/        extract_v1.txt ... extract_v4.txt
eval/           guidelines.md, results.md
data/gold/      gold.jsonl, split.json (15 dev / 15 test)
data/processed/ trials.parquet and the extraction outputs
NOTES.md        working notes, lessons and decisions per step
```
