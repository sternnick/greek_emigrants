#!/usr/bin/env python3
"""Aggregate country records into worldwide.yaml — grouped by definition."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "aggregate" / "worldwide.yaml"


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_latest(records: list[dict], classification: str) -> dict | None:
    subset = [
        r for r in records
        if r.get("classification") == classification and r.get("count") is not None
    ]
    if not subset:
        return None
    return max(subset, key=lambda r: r["year"])


def main() -> None:
    continents: dict[str, dict] = {}
    # totals[classification][definition] = sum
    totals: dict[str, dict[str, int]] = {
        "confirmed": defaultdict(int),
        "hypothetical": defaultdict(int),
    }

    for f in sorted((DATA / "countries").rglob("*.yaml")):
        doc = load_yaml(f)
        cont_id = doc["continent"]
        bucket = continents.setdefault(
            cont_id,
            {"countries": [], "totals": {"confirmed": defaultdict(int),
                                        "hypothetical": defaultdict(int)}},
        )

        latest_conf = pick_latest(doc["records"], "confirmed")
        latest_hyp = pick_latest(doc["records"], "hypothetical")

        entry = {
            "id": doc["id"],
            "iso_alpha2": doc["iso_alpha2"],
            "name": doc["name"],
            "confirmed": None,
            "hypothetical": None,
        }

        if latest_conf:
            entry["confirmed"] = {
                "count": latest_conf["count"],
                "year": latest_conf["year"],
                "source_ref": latest_conf["source_ref"],
                "definition": latest_conf["definition"],
                "population_type": latest_conf["population_type"],
            }
            bucket["totals"]["confirmed"][latest_conf["definition"]] += latest_conf["count"]
            totals["confirmed"][latest_conf["definition"]] += latest_conf["count"]

        if latest_hyp:
            entry["hypothetical"] = {
                "count": latest_hyp["count"],
                "year": latest_hyp["year"],
                "source_ref": latest_hyp["source_ref"],
                "definition": latest_hyp["definition"],
                "population_type": latest_hyp["population_type"],
            }
            bucket["totals"]["hypothetical"][latest_hyp["definition"]] += latest_hyp["count"]
            totals["hypothetical"][latest_hyp["definition"]] += latest_hyp["count"]

        bucket["countries"].append(entry)

    # convert defaultdicts to plain dicts
    for cont in continents.values():
        for cls in ("confirmed", "hypothetical"):
            cont["totals"][cls] = dict(cont["totals"][cls])

    out_doc = {
        "generated_by": "scripts/aggregate.py",
        "totals_by_definition": {
            "confirmed": dict(totals["confirmed"]),
            "hypothetical": dict(totals["hypothetical"]),
        },
        "continents": continents,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(out_doc, f, allow_unicode=True, sort_keys=False)
    print(f"✓ Wrote {OUT}")


if __name__ == "__main__":
    main()
