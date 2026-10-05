#!/usr/bin/env python3
"""Migrate sources to schema v2: retrieved_at -> publication block, add independence.

Structural half of the v2 migration (idempotent). The meta table below records,
per source, the facts established during the evidence pass (see
docs/evidence-and-verification.md): who collected the raw data, what a source
derives from, verified publication dates, and the URL/scope corrections found
by first-hand fetching on 2026-10-05.

Usage:
    python scripts/migrate_sources_v2.py          # apply
    python scripts/migrate_sources_v2.py --check  # exit 1 if drift
"""
from __future__ import annotations
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"

RETRIEVED = "2026-10-05"

# id -> meta gathered during the 2026-10-05 evidence pass.
#  primary: collected the raw data itself
#  derives: source ids whose data this source re-publishes
#  published_at: date the figure was published (verified first-hand where set)
#  url: corrected canonical URL (replaces TODO or wrong URL)
#  scope: corrected definition (fixes known mis-scopes)
#  robots: robots.txt permits fetching from this machine (probed 2026-10-05)
META: dict[str, dict] = {
    "abs-au-2021": dict(primary=True, robots=True,
        url="https://www.abs.gov.au/statistics/people/people-and-communities/cultural-diversity-census/2021",
        published_at="2022-06-28"),
    "destatis-de-2022": dict(primary=True, robots=True,
        url="https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Migration-Integration/Tabellen/auslaendische-bevoelkerung-staatsangehoerigkeit-jahre.html"),
    "ons-uk-2021": dict(primary=True, robots=True,
        url="https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/internationalmigration/datasets/populationoftheunitedkingdombycountryofbirthandnationality/july2020tojune2021"),
    "statcan-ca-2021": dict(primary=True, robots=True,
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=9810033801",
        published_at="2022-10-26"),
    "us-acs-2023": dict(primary=True, robots=True,
        url="https://data.census.gov/table/ACSDT1Y2023.B04006"),
    "instat-al-2023": dict(primary=True, robots=True,
        url="https://www.instat.gov.al/en/publications/books/2024/albanian-population-and-housing-census-2023/",
        published_at="2024-06-28"),
    "greece-in-figures-2023": dict(primary=True, robots=False),
    "oecd-review-greek-emigrants": dict(primary=False, robots=True, scope="greek-born",
        derives=["destatis-de-2022", "ons-uk-2021", "statcan-ca-2021", "abs-au-2021", "us-acs-2023"],
        published_at="2026-07-03"),
    "greekcitytimes-brain-drain-2024": dict(primary=False, robots=True,
        url="https://greekcitytimes.com/2024/07/31/greeces-efforts-to-reverse-brain-drain-amid-continued-emigration/",
        published_at="2024-07-31",
        derives=["greek-ministry-finance-brain-drain"]),
    "greek-ministry-finance-brain-drain": dict(primary=True, robots=False),
    "omonoia-al-2013": dict(primary=True, robots=True, published_at="2013-12-11"),
    "fa-de-2006": dict(primary=False, robots=False),
    "independent-uk-2009": dict(primary=False, robots=True, published_at="2009-04-03"),
    "ausgreeknet-2006": dict(primary=False, robots=False),
    "community-estimate-de-2024": dict(primary=True, robots=False),
    "community-estimate-uk-2024": dict(primary=True, robots=False),
    "community-estimate-us-2024": dict(primary=True, robots=False),
    "community-estimate-ca-2024": dict(primary=True, robots=False),
    "community-estimate-au-2024": dict(primary=True, robots=False),
}


def migrate_doc(doc: dict) -> dict:
    sid = doc.get("id")
    meta = META.get(sid)
    if meta is None:
        raise SystemExit(f"migrate_sources_v2: no meta for source id '{sid}' — add it to META")

    pub = doc.get("publication") or {}
    if "retrieved_at" in doc:
        pub.setdefault("retrieved_at", str(doc.pop("retrieved_at")))
    pub.setdefault("retrieved_at", RETRIEVED)
    if meta.get("published_at"):
        pub["published_at"] = meta["published_at"]
    doc["publication"] = pub

    ind = doc.get("independence") or {}
    ind["primary_data_collector"] = meta["primary"]
    if meta.get("derives"):
        ind["derives_from"] = meta["derives"]
    doc["independence"] = ind

    if meta.get("url"):
        doc["url"] = meta["url"]
    if meta.get("scope"):
        doc["scope"] = meta["scope"]
    doc["robots_txt_allows_fetch"] = meta["robots"]

    order = ["id", "title", "publisher", "country", "year", "url", "classification",
             "type", "scope", "reliability", "publication", "independence",
             "agency", "robots_txt_allows_fetch", "language", "language_iso639_2b", "notes"]
    return {k: doc[k] for k in order if k in doc}


def main() -> int:
    check = "--check" in sys.argv
    drift = 0
    for folder in ("confirmed", "hypothetical"):
        for f in sorted((SOURCES / folder).glob("*.yaml")):
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            migrated = migrate_doc(doc)
            text = yaml.safe_dump(migrated, allow_unicode=True, sort_keys=False, width=100)
            if f.read_text(encoding="utf-8") != text:
                drift += 1
                if check:
                    print(f"DRIFT {f}")
                else:
                    f.write_text(text, encoding="utf-8")
                    print(f"✓ migrated {f}")
    if check and drift:
        print(f"{drift} source file(s) need migration.")
        return 1
    print("✓ sources v2" + (" (no drift)" if check else " migration done"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
