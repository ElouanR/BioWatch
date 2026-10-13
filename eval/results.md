# Evaluation results

Extraction of `interventions` and `conditions` from clinical-trial
title + summary, `claude-haiku-5-5`. Gold set: 30 trials (15 dev, 15 test),
annotated with `eval/guidelines.md`. Split ids in `data/gold/split.json`.

## Metric

- List fields, micro precision / recall / F1, summed over all trials.
- Greedy one-to-one fuzzy matching, `rapidfuzz.token_sort_ratio >= 90`.
- Before comparing: lower case, hyphens to spaces, text in parentheses
  removed, extra spaces collapsed. (Removing parentheses was added after
  v1 was first scored; v1 was re-scored with the final metric.)
- A trial with no usable prediction counts as an empty prediction.
- `population` and `comparator` are **not scored yet** (need hand judging).

## Prompts

| version | change |
|---|---|
| v1 | first prompt (names "exactly as written") |
| v2 | names without dosage / acronyms in parentheses, generic name if given; base disease name only; only studied conditions and given interventions |
| v3 | v2 + diagnostic tools evaluated by the trial count as interventions |
| v4 | v2 + empty interventions if participants are only observed, sampled or scanned, unless the study evaluates the method itself |

## Dev results (n = 15 trials)

All at `effort=low` unless stated. Mean over the number of runs shown (the
model has no temperature, so the same prompt gives different outputs).

| prompt | runs | interventions P / R / F1 | conditions F1 |
|---|---|---|---|
| v1 | 1 | 0.54 / 0.72 / 0.62 | 0.64 |
| v2 | 3 | 0.77 / 0.74 / 0.75 | 0.93 |
| v3 | 3 | 0.69 / 0.81 / 0.75 | 0.95 |
| v4 | 8 | 0.77 / 0.87 / 0.82 | 0.96 |
| v4, effort=medium | 8 | 0.84 / 0.91 / 0.87 | 0.95 |

- Run-to-run spread of interventions F1 (same prompt, same data): v2 0.74
  to 0.78 (3 runs), v4 low 0.68 to 0.87 and v4 medium 0.82 to 0.92 (8 runs
  each). Three runs under-estimated the noise: low and medium looked equal
  after 3 runs, and medium came out ahead after 8.
- v3 vs v2: same F1, different balance (v3 higher recall, lower precision).
- v2 to v4: the gain in interventions F1 is larger than the run-to-run
  spread. The conditions numbers moved although no rule targeted
  conditions, so they are not attributable to a prompt change.

Files in `data/processed/` are single sample runs (`extractions_v2_dev`,
`v3_dev`, `v4_dev` at medium, `v4_test`; `v1` covers all 300 trials). The
tables report means over several runs, so re-scoring one file with
`evaluate.py <name> dev` gives one draw of that distribution.

## Effort comparison (v4, dev, 8 runs per level)

| | low | medium |
|---|---|---|
| interventions F1, mean (range) | 0.82 (0.68 to 0.87) | 0.87 (0.82 to 0.92) |
| interventions F1, std dev | about 0.06 | about 0.03 |
| conditions F1, mean | 0.96 | 0.95 |
| output tokens per trial | about 405 | about 505 |
| latency per trial | about 2.5 s | about 2.9 s |
| cost per trial | about $0.00032 | about $0.00037 |

Choice: `medium`. About 16% more cost per trial, a higher mean and half the
run-to-run spread on interventions; no difference on conditions.

## Test result (run once)

v4, `effort=medium`, 15 test trials, one run.

| field | precision | recall | F1 | n |
|---|---|---|---|---|
| interventions | 0.71 | 0.88 | 0.79 | 15 trials |
| conditions | 1.00 | 1.00 | 1.00 | 15 trials |

Interventions F1 is about 0.08 below the dev mean for the same setting
(0.87), the expected drop after tuning on dev, and within the run-to-run
spread.

## Error analysis

### v1, conditions, dev (11 extra, 6 missed items, 9 trials)

| category | extra | missed |
|---|---|---|
| qualifier kept in the name (stage, "metastatic", marker) | 5 | 4 |
| related condition not targeted (background / outcome) | 4 | 0 |
| too general (`diabetes mellitus` for `type 2 diabetes`) | 1 | 1 |
| metric failure (`(MCI)` in parentheses) | 1 | 1 |

Every missed item had a matching extra item: the model found the
condition and wrote it differently.

### v1, interventions, dev (12 extra, 6 missed items, 7 trials; metric before the parentheses fix)

- Programme phases or components listed as separate interventions.
- Code name, acronym or brand next to the generic name.
- Dosage and settings left in the name.
- Measurement tools and food listed as interventions.
- Tested diagnostic technologies missed.

### What the prompts fixed
- v2 fixed qualifiers, naming and most background extras (rules 2, 4, 5)
  but also caused a regression: an imaging trial went from found (v1) to
  empty (v2), because "tests used only to measure" hid a tool that was
  itself under test.
- v4 fixed that regression and the measurement-only trials on dev.

### v4, interventions, test (5 trials with errors)

| trial | extra | missed | type |
|---|---|---|---|
| NCT05292222 | `intermittent theta burst stimulation` | | sub-protocol next to the therapy |
| NCT03320512 | `P3` | `P3 smartphone app` | naming |
| NCT00106899 | `brain imaging technology` | | measurement-only study |
| NCT04700813 | `systematic genetic diagnosis` | | measurement-only study (debatable) |
| NCT06284681 | `YMCA membership`, `group fitness classes` | `YMCA membership with group fitness classes` | granularity |

Three of five are naming or granularity mismatches where the gold choice
is arbitrary; two are measurement-only studies where rule 5 still fails.

## Consistency check against the API fields (300 trials)

v4, `effort=medium`, all 300 trials (300/300 parsed, $0.10, 149 s), compared
with the `interventions` and `conditions` columns of ClinicalTrials.gov.
Same metric. This is **not ground truth**: the API fields describe the whole
registration, not only the summary the model sees. Output:
`data/processed/extractions_v4_all.jsonl`.

| field | precision | recall | F1 | n |
|---|---|---|---|---|
| interventions | 0.43 | 0.29 | 0.35 | 300 trials |
| conditions | 0.53 | 0.30 | 0.38 | 300 trials |

- Calibration: using the API fields as if they were a model, scored against
  the 30 hand-annotated trials, gives F1 0.31 (interventions) and 0.36
  (conditions). The API disagrees with the hand gold about as much as the
  model disagrees with the API, so the low numbers say the API is a poor
  answer key for this task, not that the model is poor (test F1 0.79 / 1.00).
- The API lists more items (1.96 interventions and 2.55 conditions per trial,
  against 1.31 and 1.43 for the model) and never has an empty `conditions`
  field, while the model returns an empty `conditions` list for 22 trials
  whose summary names no disease.
- Typical disagreements: the API keeps dosage, brand and formulation in the
  name (`Pembrolizumab 50 MG Injection [Keytruda]`), lists `Placebo` as an
  intervention, lists `Radiotherapy` or `Immunotherapy` as conditions, and
  lists disease subtypes or comorbidities the summary does not mention
  (`Mesothelioma`, `Obesity, Morbid`).
- By group, agreement is best for lung cancer interventions (F1 0.48) and
  Alzheimer's conditions (F1 0.50), and worst for lung cancer conditions
  (F1 0.29), where the API lists many subtypes.

## Input scope

The model reads the title and the brief summary only (median 66 words).
`detailedDescription` (missing for 108 of 300 trials, median 101 words) and
`eligibilityCriteria` (median 195 words) are not used, and neither are the
structured arm groups. Adding the free text would raise the median input to
about 475 words, would break the current gold set (annotated from title and
summary only) and is the main candidate for improving `population` and
`comparator`.

## Limits

- 15 dev and 15 test trials, about 30 gold items per field: one item moves
  a score by several points. Report `n` with every number.
- Dev was used to write the rules and was scored many times, so dev numbers
  are optimistic. The test number is the honest one, and it is a single run.
- The metric choices (threshold 90, parentheses removed) change the
  numbers (about +0.04 to +0.05 F1 on v1) and can hide real differences.
- One gold row (NCT05234281, `mixed anxiety/depression` changed to
  `anxiety/depression`) was corrected after model outputs had been seen, to
  follow the written rule on qualifiers. It favoured v2/v4 over v1.
- Several gold decisions are judgement calls (related conditions, whether a
  population's comorbidities count, measurement-only studies).
- `population` and `comparator` are not evaluated.

## Conclusions

- What works: short rules about *what to leave out* (qualifiers, background
  items, measured tests) raised interventions precision a lot, and the
  condition names are now almost always right.
- What doesn't: the model still splits one programme into parts, adds
  sub-protocols, and lists methods in measurement-only studies; some of the
  remaining "errors" are naming choices the metric cannot absorb.
- Next: score `population` and `comparator` text by hand, try the
  detailed description and eligibility criteria as input (with a new gold set
  for those two fields), and use a larger gold set before trusting any number
  to the second decimal.
