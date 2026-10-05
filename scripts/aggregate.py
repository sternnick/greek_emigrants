#!/usr/bin/env python3
"""Aggregate country records into worldwide.yaml."""
from __future__ import annotations
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "aggregate" / "worldwide.yaml"


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_latest(records: list[dict], classification: str) -> dict | None:
    subset = [r for r in records
              if r.get("classification") == classification and r.get("count") is not None]
    if not subset:
        return None
    return max(subset, key=lambda r: r["year"])


def main() -> None:
    continents: dict[str, dict] = {}
    totals = {"confirmed": 0, "hypothetical": 0}

    for f in sorted((DATA / "countries").rglob("*.yaml")):
        doc = load_yaml(f)
        cont = doc["continent"]
        bucket = continents.setdefault(cont, {"countries": [], "confirmed": 0, "hypothetical": 0})

        latest_conf = pick_latest(doc["records"], "confirmed")
        latest_hyp = pick_latest(doc["records"], "hypothetical")

        entry = {
            "id": doc["id"],
            "iso_alpha2": doc["iso_alpha2"],
            "name": doc["name"],
            "confirmed": (
                {"count": latest_conf["count"], "year": latest_conf["year"],
                 "source_ref": latest_conf["source_ref"],
                 "definition": latest_conf["definition"]}
                if latest_conf else None
            ),
            "hypothetical": (
                {"count": latest_hyp["count"], "year": latest_hyp["year"],
                 "source_ref": latest_hyp["source_ref"],
                 "definition": latest_hyp["definition"]}
                if latest_hyp else None
            ),
        }
        bucket["countries"].append(entry)
        if latest_conf:
            bucket["confirmed"] += latest_conf["count"]
            totals["confirmed"] += latest_conf["count"]
        if latest_hyp:
            bucket["hypothetical"] += latest_hyp["count"]
            totals["hypothetical"] += latest_hyp["count"]

    out_doc = {
        "generated_by": "scripts/aggregate.py",
        "totals": totals,
        "continents": continents,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(out_doc, f, allow_unicode=True, sort_keys=False)
    print(f"✓ Wrote {OUT}")


if __name__ == "__main__":
    main()
