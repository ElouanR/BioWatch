import json
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz


def norm(s: str) -> str:
    s = re.sub(r"\([^)]*\)", " ", s)
    return " ".join(s.lower().replace("-", " ").split())


def diff_lists(
    pred: list[str], gold: list[str], threshold: int = 90
) -> tuple[list[str], list[str]]:
    gold_n = [norm(g) for g in gold]
    used: set[int] = set()
    extra = []

    for original in pred:
        p = norm(original)
        best_i, best_score = None, 0.0
        for i, g in enumerate(gold_n):
            if i in used:
                continue
            score = fuzz.token_sort_ratio(p, g)
            if score > best_score:
                best_i, best_score = i, score
        if best_i is not None and best_score >= threshold:
            used.add(best_i)
        else:
            extra.append(original)

    missed = [g for i, g in enumerate(gold) if i not in used]
    return extra, missed


def match_lists(
    pred: list[str], gold: list[str], threshold: int = 90
) -> tuple[int, int, int]:
    extra, missed = diff_lists(pred, gold, threshold)
    return len(pred) - len(extra), len(extra), len(missed)


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score_field(
    preds: dict, golds: dict, field: str
) -> tuple[float, float, float]:
    tp = fp = fn = 0

    for nct_id, gold in golds.items():
        pred = (preds.get(nct_id) or {}).get(field, [])
        a, b, c = match_lists(pred, gold[field])
        tp, fp, fn = tp + a, fp + b, fn + c

    return prf(tp, fp, fn)


def load_jsonl(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f]


def main(version: str, split: str) -> None:
    gold_rows = load_jsonl(Path("data/gold/gold.jsonl"))
    golds = {r["nct_id"]: r for r in gold_rows if r["split"] == split}
    pred_rows = load_jsonl(Path(f"data/processed/extractions_{version}.jsonl"))
    preds = {r["nct_id"]: r["parsed"] for r in pred_rows}
    print(f"{version} on {split} (n={len(golds)})")

    for field in ("interventions", "conditions"):
        p, r, f = score_field(preds, golds, field)
        print(f"{field:14} P={p:.2f} R={r:.2f} F1={f:.2f}")


def show_errors(version: str, split: str, field: str) -> None:
    gold_rows = load_jsonl(Path("data/gold/gold.jsonl"))
    golds = {r["nct_id"]: r for r in gold_rows if r["split"] == split}
    pred_rows = load_jsonl(Path(f"data/processed/extractions_{version}.jsonl"))
    preds = {r["nct_id"]: r["parsed"] for r in pred_rows}

    for nct_id, gold in golds.items():
        pred = (preds.get(nct_id) or {}).get(field, [])
        extra, missed = diff_lists(pred, gold[field])
        if extra or missed:
            print(nct_id)
            print(f"  extra : {extra}")
            print(f"  missed: {missed}")


if __name__ == "__main__":
    if len(sys.argv) == 4:
        show_errors(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        main(sys.argv[1], sys.argv[2])
