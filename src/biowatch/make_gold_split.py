import json
from pathlib import Path

import pandas as pd

df = pd.read_parquet("data/processed/trials.parquet")
sample = df.sample(30, random_state=0)
ids = sample["nct_id"].tolist()

split = {"dev": ids[:15], "test": ids[15:]}

Path("data/gold").mkdir(parents=True, exist_ok=True)
Path("data/gold/split.json").write_text(json.dumps(split, indent=2))
print(sample["condition_group"].value_counts())
