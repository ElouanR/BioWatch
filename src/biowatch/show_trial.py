import json
import sys

import pandas as pd

with open("data/gold/split.json") as f:
    split = json.load(f)
ids = split["dev"] + split["test"]
df = pd.read_parquet("data/processed/trials.parquet")

i = int(sys.argv[1])
row = df.loc[df["nct_id"] == ids[i]].iloc[0]
print(f"[{i + 1}/30] {row['nct_id']}\n")
print(f"Title: {row['title']}\n")
print(f"Summary:\n{row['summary']}")
