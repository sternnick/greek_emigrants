"""The scaffolder must produce a complete, self-consistent country set."""
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
COUNTRIES = ROOT / "data" / "countries"
CONTINENTS = ROOT / "data" / "continents"


def country_files():
    return {p.stem: p for p in COUNTRIES.rglob("*.yaml")}


def test_scaffold_is_complete_and_idempotent():
    """--check exits 0 only when every sovereign country already has a file."""
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "scaffold_countries.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_country_sits_under_a_continent_directory():
    for slug, path in country_files().items():
        assert path.parent.name in {"africa", "asia", "europe",
                                    "north-america", "oceania", "south-america"}, slug
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert doc["continent"] == path.parent.name, slug


def test_continent_membership_matches_the_files_on_disk():
    on_disk = {p.stem: {q.stem for q in (COUNTRIES / p.stem).glob("*.yaml")}
               for p in CONTINENTS.glob("*.yaml")}
    for cfile in CONTINENTS.glob("*.yaml"):
        doc = yaml.safe_load(cfile.read_text(encoding="utf-8"))
        assert sorted(doc["countries"]) == sorted(on_disk[cfile.stem]), cfile.stem


def test_no_country_is_listed_by_two_continents():
    seen: dict[str, str] = {}
    for cfile in CONTINENTS.glob("*.yaml"):
        for slug in yaml.safe_load(cfile.read_text(encoding="utf-8"))["countries"]:
            assert slug not in seen, f"{slug} in both {seen.get(slug)} and {cfile.stem}"
            seen[slug] = cfile.stem


def test_bundled_list_has_195_sovereign_states():
    import csv
    with (ROOT / "data" / "lists" / "country-list.csv").open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(line for line in fh if not line.startswith("#"))]
    sovereigns = [r for r in rows if r["sovereign"] == "yes"]
    assert len(sovereigns) == 195
    assert len({r["iso_alpha2"] for r in sovereigns}) == 195
    for r in sovereigns:
        assert r["name_en"] and r["name_el"] and r["continent"]
