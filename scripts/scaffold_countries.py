#!/usr/bin/env python3
"""Scaffold one country file per sovereign state from the bundled list.

Every missing sovereign country in data/lists/country-list.csv gets
data/countries/<continent>/<slug>.yaml with `status: stub` and `records: []` —
a place to fill in, not a claim. Existing files are NEVER touched (reported as
skipped), so the six researched countries keep their records.

data/continents/<continent>.yaml is regenerated from what is actually on disk,
so membership can never drift from the files.

CROSS-CHECK SOURCES (measured 2026-10-05, see docs/country-list-sources.md):
both web cross-checks were dropped — mytravelmaps.org is a Next.js client-side
app (its HTML contains no country names) and guessthecountry.org has no
country-list page at all (its sitemap is blog posts only, /countries/ is 404).
The list therefore comes from UN M49 (authoritative for the continent column)
plus ISO 3166-1, with 10 random countries verified against the M49 table below.

Usage:
    python scripts/scaffold_countries.py --dry-run
    python scripts/scaffold_countries.py
    python scripts/scaffold_countries.py --check      # exit 1 if anything missing
"""
from __future__ import annotations
import argparse, csv, random, re, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "data" / "lists" / "country-list.csv"
COUNTRIES = ROOT / "data" / "countries"
CONTINENTS = ROOT / "data" / "continents"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_list() -> list[dict]:
    with LIST.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(line for line in fh if not line.startswith("#"))]
    return [r for r in rows if r["sovereign"] == "yes"]


def existing_by_iso() -> dict[str, Path]:
    """Index country files by their iso_alpha2, not by slug: the slug is derived
    from the ISO English name ("United States of America"), which is not always
    the slug an existing file happens to use ("united-states")."""
    out: dict[str, Path] = {}
    for p in COUNTRIES.rglob("*.yaml"):
        iso = yaml.safe_load(p.read_text(encoding="utf-8")).get("iso_alpha2")
        if not iso:
            sys.exit(f"{p}: country files must carry iso_alpha2 so the scaffolder can match them")
        out[iso] = p
    return out


def refresh_continents(countries: dict[str, Path], apply: bool,
                       planned: list[tuple[str, str]] = ()) -> list[tuple[str, list[str]]]:
    """Return (continent, [added slugs]) for each continent file that needs work.
    `planned` slugs are counted in --dry-run so the preview matches the run."""
    on_disk: dict[str, set[str]] = {}
    for path in countries.values():
        on_disk.setdefault(path.parent.name, set()).add(path.stem)
    for slug, cont in planned:
        on_disk.setdefault(cont, set()).add(slug)
    changes = []
    for cfile in sorted(CONTINENTS.glob("*.yaml")):
        doc = yaml.safe_load(cfile.read_text(encoding="utf-8"))
        want = sorted(on_disk.get(cfile.stem, set()))
        if sorted(doc.get("countries", [])) != want:
            added = [s for s in want if s not in set(doc.get("countries", []))]
            removed = [s for s in set(doc.get("countries", [])) if s not in want]
            if removed:
                print(f"⚠ continents/{cfile.stem}.yaml lists {removed} but no such file exists")
            changes.append((cfile.stem, added))
            if apply:
                doc["countries"] = want
                cfile.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
                                 encoding="utf-8")
    return changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.dry_run and args.check:
        sys.exit("--dry-run and --check are exclusive")

    rows = load_list()
    have = existing_by_iso()
    planned, skipped = [], []
    for r in rows:
        slug, cont = slugify(r["name_en"]), r["continent"]
        path = COUNTRIES / cont / f"{slug}.yaml"
        if r["iso_alpha2"] in have:
            found = have[r["iso_alpha2"]]
            skipped.append(found.stem)
            doc = yaml.safe_load(found.read_text(encoding="utf-8"))
            if doc.get("continent") != cont:
                print(f"⚠ {found.stem}: continent={doc.get('continent')} but M49 puts {r['name_en']} in {cont}")
            continue
        planned.append((slug, cont, path, r))

    mode = "would create" if (args.dry_run or args.check) else "created"
    for slug, cont, path, r in planned:
        print(f"  {mode} {path.relative_to(ROOT)}  ({r['name_en']} / {r['name_el']})")
        if not (args.dry_run or args.check):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump({
                "id": slug, "iso_alpha2": r["iso_alpha2"],
                "name": {"el": r["name_el"], "en": r["name_en"]},
                "continent": cont, "status": "stub", "records": [],
            }, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")

    countries = {p.stem: p for p in COUNTRIES.rglob("*.yaml")}
    cont_changes = refresh_continents(countries,
                                     apply=not (args.dry_run or args.check),
                                     planned=[(s, c) for s, c, _, _ in planned])
    for cont, added in cont_changes:
        shown = ", ".join(added[:6]) + (" …" if len(added) > 6 else "")
        print(f"  continents/{cont}.yaml: +{len(added)} member(s){': ' + shown if added else ''}")

    print(f"{'✓' if not planned or args.dry_run else '✓'} scaffold: "
          f"{len(planned)} missing, {len(skipped)} existing skipped, "
          f"{len(cont_changes)} continent file(s) to touch"
          + ("  [dry-run]" if args.dry_run or args.check else ""))
    if args.check and planned:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
