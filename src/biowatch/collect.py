import json
from pathlib import Path

import pandas as pd
import requests

BASE = "https://clinicaltrials.gov/api/v2/studies"
RAW = Path("data/raw")


def fetch_studies(
    condition: str, max_studies: int = 100, page_size: int = 50
) -> list[dict]:
    studies, token = [], None

    while len(studies) < max_studies:
        params = {
            "query.cond": condition,
            "pageSize": page_size,
            "format": "json",
        }
        if token:
            params["pageToken"] = token
        r = requests.get(BASE, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        studies.extend(data.get("studies", []))
        token = data.get("nextPageToken")
        if not token:
            break

    return studies[:max_studies]


def flatten(study: dict) -> dict:
    p = study.get("protocolSection", {})
    ident = p.get("identificationModule", {})
    desc = p.get("descriptionModule", {})
    design = p.get("designModule", {})
    sponsor = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    conds = p.get("conditionsModule", {})
    arms = p.get("armsInterventionsModule", {})
    status = p.get("statusModule", {})

    return {
        "nct_id": ident.get("nctId"),
        "title": ident.get("briefTitle"),
        "summary": desc.get("briefSummary"),
        "phases": design.get("phases", []),
        "sponsor": sponsor.get("name"),
        "sponsor_class": sponsor.get("class"),
        "conditions": conds.get("conditions", []),
        "interventions": [
            i.get("name") for i in arms.get("interventions", [])
        ],
        "status": status.get("overallStatus"),
        "start_date": status.get("startDateStruct", {}).get("date"),
    }


def collect(groups: dict[str, str], per_group: int = 100) -> pd.DataFrame:
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []

    for group, query in groups.items():
        path = RAW / f"{group}.json"
        if path.exists():
            studies = json.loads(path.read_text())
        else:
            studies = fetch_studies(query, per_group)
            path.write_text(json.dumps(studies))
        rows.extend(
            [{**flatten(s), "condition_group": group} for s in studies]
        )

    df = pd.DataFrame(rows).drop_duplicates("nct_id")
    has_summary = df["summary"].notna() & (df["summary"].str.len() > 0)
    return df.loc[has_summary]


GROUPS = {
    "lung_cancer": "lung cancer",
    "alzheimer": "Alzheimer's disease",
    "diabetes": "type 2 diabetes",
}


def main() -> None:
    df = collect(GROUPS, per_group=100)
    out = Path("data/processed")
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "trials.parquet")
    print(f"{len(df)} trials saved")


if __name__ == "__main__":
    main()
