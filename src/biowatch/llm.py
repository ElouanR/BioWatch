import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv

load_dotenv()
MODEL = os.environ["LLM_MODEL"]
PRICE_IN = float(os.getenv("PRICE_INPUT_PER_M", "0"))
PRICE_OUT = float(os.getenv("PRICE_OUTPUT_PER_M", "0"))
LOG = Path("logs/llm_calls.jsonl")
LOG.parent.mkdir(exist_ok=True)

client = anthropic.Anthropic(api_key=os.environ["LLM_API_KEY"])

Effort = Literal["low", "medium", "high", "xhigh", "max"]

@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    cost: float
    model: str
    stop_reason: str | None

def call_llm(
    system: str, 
    user: str, 
    effort: Effort = "low", 
    max_tokens: int = 2048,
    component: str = "misc"
) -> LLMResult:
    start = time.perf_counter()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort},
    )
    latency = time.perf_counter() - start

    text = "".join(b.text for b in resp.content if b.type == "text")
    in_tok, out_tok = resp.usage.input_tokens, resp.usage.output_tokens

    cost = (in_tok * PRICE_IN + out_tok * PRICE_OUT) / 1_000_000
    res = LLMResult(text, in_tok, out_tok, latency, cost, MODEL, resp.stop_reason)
    with LOG.open("a") as f:
        log = {k: v for k, v in asdict(res).items() if k != "text"}
        f.write(json.dumps({"ts": time.time(), "component": component,
                            "effort": effort, **log}) + "\n")
    return res
