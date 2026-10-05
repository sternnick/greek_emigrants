#!/usr/bin/env python3
"""Regenerate data/lists/country-list.csv — the bundled country list the scaffolder reads.

PROVENANCE of every column
  iso_alpha2, iso_alpha3, numeric : UN M49 country-code table, fetched from
      https://unstats.un.org/unsd/methodology/m49/overview/  (robots.txt allows it;
      first fetched 2026-10-05). M49 also supplies continent/subregion.
  iso_name_en                     : ISO 3166-1 names from the local `iso-codes`
      package (/usr/share/iso-codes/json/iso_3166-1.json).
  name_el                         : the same ISO names translated through the
      system's Greek locale catalog (gettext domain iso_3166-1, 248/249
      translated). This is the "CLDR if available, else static mapping" fallback
      of the bilingual-metadata standard: the mapping is bundled, so builds never
      depend on this machine.
  name_en                         : ISO common name, else the ISO name without
      its formal tail ("Tanzania, United Republic of" -> "Tanzania"), plus the
      NAME_FIXES below where the shortening would collide.
  sovereign/dependent + note      : curated, documented in DEPENDENTS below; the
      count is verified against the UN figure of 195 (193 members + 2 observers).

CONTINENT RULE: M49 region, except that the Americas are split geographically at
the Isthmus of Panama (M49's "Latin America and the Caribbean" is a
socio-economic grouping, not a continent): Northern America + Central America +
the Caribbean -> north-america, the South America subregion -> south-america.
Set SPLIT_AT_ISTHMUS = False to fall back to literal M49 subregions.

Usage:
    python scripts/build_country_list.py [--offline /tmp/m49.html] [--out PATH]
"""
from __future__ import annotations
import argparse, csv, gettext, json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "lists" / "country-list.csv"
M49_URL = "https://unstats.un.org/unsd/methodology/m49/overview/"
UA = "greek_emigrants-dataset/1.0 (research dataset build; +https://github.com/sternnick/greek_emigrants)"
ISO_CODES_JSON = Path("/usr/share/iso-codes/json/iso_3166-1.json")

# Central America (013) + Caribbean (029) + Northern America (021) are the North
# American continent; South America (005) is the other one.
SPLIT_AT_ISTHMUS = True
NORTH_AMERICA_M49 = {"021", "013", "029"}

# Not sovereign states. Keyed by ISO alpha-2, value = why. Verified 2026-10-05:
# 247 M49 entries (Antarctica excluded as a continent, not a country) minus these
# 52 = 195 sovereign states.
DEPENDENTS = {
    "IO": "UK Indian Ocean territory", "TF": "French overseas territory",
    "YT": "French overseas department", "RE": "French overseas department",
    "SH": "UK overseas territory", "EH": "UN Non-Self-Governing Territory",
    "AI": "UK overseas territory", "AW": "constituent country of the Kingdom of the Netherlands",
    "BM": "UK overseas territory", "BQ": "special municipality of the Netherlands",
    "BV": "Norwegian dependency", "KY": "UK overseas territory",
    "CW": "constituent country of the Kingdom of the Netherlands", "FK": "UK overseas territory",
    "GF": "French overseas department", "GL": "constituent country of the Kingdom of Denmark",
    "GP": "French overseas department", "MQ": "French overseas department",
    "MS": "UK overseas territory", "PR": "US unincorporated territory",
    "BL": "French overseas collectivity", "MF": "French overseas collectivity",
    "PM": "French overseas collectivity", "SX": "constituent country of the Kingdom of the Netherlands",
    "GS": "UK overseas territory", "TC": "UK overseas territory",
    "VG": "UK overseas territory", "VI": "US unincorporated territory",
    "HK": "SAR of China", "MO": "SAR of China",
    "FO": "constituent country of the Kingdom of Denmark", "GI": "UK overseas territory",
    "IM": "Crown dependency", "JE": "Crown dependency", "GG": "Crown dependency",
    "AX": "autonomous region of Finland", "SJ": "Norwegian territory",
    "AS": "US unincorporated territory", "CX": "external territory of Australia",
    "CC": "external territory of Australia", "CK": "free state in association with New Zealand",
    "PF": "French overseas collectivity", "GU": "US unincorporated territory",
    "HM": "external territory of Australia", "MP": "US commonwealth",
    "NC": "French special collectivity", "NU": "self-governing state in association with New Zealand",
    "NF": "external territory of Australia", "PN": "UK overseas territory",
    "TK": "dependent territory of New Zealand", "UM": "US minor outlying islands",
    "WF": "French overseas collectivity",
}

# Where the formal-tail shortening collides, use these display names. Each keeps
# the Greek wording of the locale catalog, only reordered to natural Greek order.
NAME_FIXES = {
    "CD": ("DR Congo", "Λαϊκή Δημοκρατία του Κονγκό"),
    "CG": ("Congo", "Κονγκό"),
    "KR": ("South Korea", "Νότια Κορέα"),
    "KP": ("North Korea", "Βόρεια Κορέα"),
}


def fetch_m49(offline: str | None) -> str:
    if offline:
        return Path(offline).read_text(encoding="utf-8", errors="ignore")
    req = urllib.request.Request(M49_URL, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")


def parse_m49(html: str) -> list[dict]:
    """The English table is the first of six identical tables in other languages."""
    table = re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I)[0]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S | re.I)
    def cells(row):
        return [re.sub(r"<[^>]+>", "", c).strip()
                for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]
    out = []
    for r in rows[1:]:
        c = cells(r)
        if len(c) < 12 or not c[9].isdigit():
            continue
        out.append(dict(numeric=c[9], alpha2=c[10], alpha3=c[11], region=c[3],
                        subregion=c[5], intermediate=c[6], name_m49=c[8]))
    return out


def continent_of(entry: dict) -> str:
    region, sub, inter = entry["region"], entry["subregion"], entry["intermediate"]
    if region == "Americas":
        if SPLIT_AT_ISTHMUS:
            return "north-america" if (inter in NORTH_AMERICA_M49 or sub == "Northern America") else "south-america"
        return "north-america" if sub == "Northern America" else "south-america"
    return {"Africa": "africa", "Asia": "asia", "Europe": "europe", "Oceania": "oceania"}[region]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", help="path to a saved M49 overview page (skip the fetch)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    if not ISO_CODES_JSON.exists():
        sys.exit(f"missing {ISO_CODES_JSON}: install the iso-codes package or bundle the json")
    iso = {e["alpha_2"]: e for e in json.loads(ISO_CODES_JSON.read_text(encoding="utf-8"))["3166-1"]}
    translate = gettext.translation("iso_3166-1", languages=["el"]).gettext

    entries = parse_m49(fetch_m49(args.offline))
    if len(entries) < 240:
        sys.exit(f"M49 table looks truncated: {len(entries)} rows")

    rows = []
    for e in entries:
        a2 = e["alpha2"]
        if a2 == "AQ":                      # Antarctica: a continent, not a country
            continue
        iso_name = iso.get(a2, {}).get("name", e["name_m49"])
        common = iso.get(a2, {}).get("common_name")
        name_en = NAME_FIXES[a2][0] if a2 in NAME_FIXES else (common or iso_name.split(",")[0].strip())
        name_el = NAME_FIXES[a2][1] if a2 in NAME_FIXES else translate(iso_name).split(",")[0].strip()
        if not name_el:
            sys.exit(f"{a2}: no Greek name")
        rows.append({
            "iso_alpha2": a2, "iso_alpha3": e["alpha3"], "numeric": e["numeric"],
            "name_en": name_en, "name_el": name_el, "iso_name_en": iso_name,
            "continent": continent_of(e), "m49_region": e["region"], "m49_subregion": e["subregion"],
            "sovereign": "no" if a2 in DEPENDENTS else "yes",
            "note": DEPENDENTS.get(a2, ""),
        })

    sovereigns = [r for r in rows if r["sovereign"] == "yes"]
    if len(sovereigns) != 195:
        sys.exit(f"expected 195 sovereign states, built {len(sovereigns)} (rows {len(rows)})")
    slugs = [re.sub(r"[^a-z0-9]+", "-", r["name_en"].lower()).strip("-") for r in sovereigns]
    if len(set(slugs)) != len(slugs):
        dupes = {s for s in slugs if slugs.count(s) > 1}
        sys.exit(f"slug collision: {sorted(dupes)}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        fh.write("# Bundled country list — DO NOT hand-edit; regenerate with scripts/build_country_list.py\n")
        fh.write(f"# Sources: UN M49 {M49_URL} ; ISO 3166-1 via iso-codes ; el names via the ISO 3166-1 Greek locale catalog\n")
        fh.write(f"# Americas split at the Isthmus of Panama: SPLIT_AT_ISTHMUS = {SPLIT_AT_ISTHMUS}\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(f"✓ wrote {out.relative_to(ROOT)}: {len(rows)} rows, {len(sovereigns)} sovereign")
    print("  sovereign per continent:", dict(Counter(r["continent"] for r in sovereigns)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
