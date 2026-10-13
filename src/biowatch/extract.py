import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from biowatch.llm import MODEL, call_llm
from biowatch.schemas import TrialInfo

PROMPT_VERSION = "v1"
SYSTEM = Path(f"prompts/extract_{PROMPT_VERSION}.txt").read_text()
SCHEMA = json.dumps(TrialInfo.model_json_schema())


def parse_json(text: str) -> TrialInfo:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return TrialInfo.model_validate_json(cleaned)


def extract_one(nct_id: str, title: str, summary: str) -> dict:
    user = (
        f"Title: {title}\n\nSummary:\n{summary}\n\n"
        f"Return only a JSON object matching this schema:\n{SCHEMA}"
    )
    res = call_llm(SYSTEM, user, component="extract")
    record = {
        "nct_id": nct_id,
        "prompt_version": PROMPT_VERSION,
        "model": MODEL,
        "raw_output": res.text,
        "parsed": None,
        "error": None,
        "input_tokens": res.input_tokens,
        "output_tokens": res.output_tokens,
        "latency_s": res.latency_s,
    }

    try:
        record["parsed"] = parse_json(res.text).model_dump()
    except ValueError as e:
        retry = call_llm(
            SYSTEM,
            user + f"\n\nYour previous answer was invalid ({e}). "
            "Return valid JSON only.",
            component="extract",
        )
        record["raw_output"] = retry.text
        record["input_tokens"] += retry.input_tokens
        record["output_tokens"] += retry.output_tokens
        record["latency_s"] += retry.latency_s
        try:
            record["parsed"] = parse_json(retry.text).model_dump()
        except ValueError as e2:
            record["error"] = str(e2)

    return record


TRIALS = Path("data/processed/trials.parquet")
OUT = Path(f"data/processed/extractions_{PROMPT_VERSION}.jsonl")


def run(limit: int | None = None, workers: int = 5) -> list[dict]:
    df = pd.read_parquet(TRIALS)

    if limit:
        df = df.sample(limit, random_state=0)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(
            pool.map(
                lambda r: extract_one(r.nct_id, r.title, r.summary),
                df.itertuples(),
            )
        )

    with OUT.open("w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    return records


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    start = time.perf_counter()
    records = run(limit)
    elapsed = time.perf_counter() - start

    ok = sum(r["parsed"] is not None for r in records)
    in_tok = sum(r["input_tokens"] for r in records)
    out_tok = sum(r["output_tokens"] for r in records)
    print(f"parsed: {ok}/{len(records)} ({ok / len(records):.0%})")
    print(
        f"avg tokens per trial: {in_tok / len(records):.0f} in, "
        f"{out_tok / len(records):.0f} out"
    )
    print(f"total time: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
