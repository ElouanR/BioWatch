# Annotation guidelines

Annotate from the title and summary only. Do not use outside knowledge
and do not look at the model's output.

## Interventions

Include: drugs, biologics, vaccines, devices, procedures, behavioural
therapies that the trial *tests or gives*.

Exclude: blood draws, questionnaires, scans (tests used only to measure).
Exception: if the study's purpose is to evaluate, compare or validate
a test, scan or measurement device itself (a diagnostic study), that
tool is the intervention. In a study where participants are only
observed, sampled or scanned and receive no treatment, otherwise
leave `interventions` empty.

Normalisation:
- Drop dosage and schedule: "pembrolizumab 200 mg" -> "pembrolizumab".
- Write the name as it appears in the text. Do not translate brand
  names yourself ("Tarceva" stays "Tarceva"). If the text gives
  both a brand or code name and the generic name, keep the
  generic name.
- When both the full term and its acronym appear anywhere in the
  title or summary, write the full term ("non-small cell lung
  cancer", not "NSCLC"). Keep an acronym only if no full term
  is given.
- If only a code name is given ("NN1250"), keep the code name.
- Placebo is not an intervention. It goes in `comparator`.
- If both a code name and a generic name appear, keep only the generic name.

## Conditions

The diseases or health problems the trial studies or targets.

- Use the name as written in the text, lower case, no abbreviations
  if the full name is given ("type 2 diabetes", not "T2DM").
- Include a condition only if the text names it. Do not infer it from
  the drug ("insulin" does not imply "diabetes").
- Symptoms count if they are the target ("chronic pain").
- Healthy volunteers are not a condition.
- Comorbidities that define the enrolled population (e.g. chronic
  kidney disease in a diabetes trial) count as conditions.
- A disease named in the text as the thing being prevented
  (e.g. HIV for a PrEP adherence app) counts.
- Stage, line of therapy and genetic markers ("metastatic",
  "BRAF V600E") are qualifiers of the population, not part of
  the condition name. Use the base disease name.
- A problem that is only measured as an outcome or side effect
  (e.g. hypoglycaemia episodes counted in a diabetes trial) is not
  a condition, unless the treatment is meant to target it.

## Population

One short phrase: who is enrolled, as stated in the text (age group,
sex, disease stage, clinical setting such as hospitalised patients).
Country or region where the trial runs is not part of the
population.

- "Stated" means the text says it explicitly. If it does not, the gold
  value is empty (null).
- A disease named only in the title or as background ("X in type 2
  diabetes") does not state who is enrolled. Leave it empty unless
  the text says who the participants are.
- It counts as stated when the aim or design sentence names the
  patients the intervention is for ("rehabilitation for patients
  with X").
- Keep it short: "adults with type 2 diabetes", not the full
  eligibility criteria.

## Comparator

What the tested intervention is compared against (placebo, usual
care, another drug, no treatment).

- If the trial has a single arm, or the text names no comparison,
  the gold value is empty (null).
- Placebo and usual care go here, never in `interventions`.
- If the trial compares two doses or regimens of the same drug,
  the comparator is "another regimen of <generic name>" and
  the drug is listed once in `interventions`.
- If the comparator is another active drug, write it here and also
  list it in `interventions` only if the trial gives it as part of
  the studied treatment.

## Empty values

An empty field is a valid answer. If the text does not say, the gold
value is empty. The model returning nothing in that case is a success.
