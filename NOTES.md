# Notes

## Step 1 — Setup
- `llm.py` wraps every LLM call and logs tokens, latency and cost to `logs/llm_calls.jsonl`.
- Haiku 5.5 takes no temperature/top_p/top_k. `effort` controls thinking.
- Type error on `output_config`: `effort` needed a `Literal[...]` type, not `str`.
- Select response blocks by `type`, never by position (a thinking block can come first).
- First smoke call: 38 in / 69 out tokens, 1.4s, $0.00004.
