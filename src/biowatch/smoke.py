from biowatch.llm import call_llm

res = call_llm(
    system="You are a concise assistant.",
    user="In one sentence: what is a phase 3 clinical trial?",
    component="smoke"
)

print(res.text)
print(f"in={res.input_tokens} out={res.output_tokens} "
      f"latency={res.latency_s:.2f}s cost={res.cost:.5f}")
