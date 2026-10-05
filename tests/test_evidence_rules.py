"""Evidence/status-rule enforcement tests: run validate.py against synthetic data trees."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VALIDATE = ROOT / "scripts" / "validate.py"

BASE_RECORD = {
    "record_id": "t-2022-census", "year": 2022, "count": 1000,
    "source_ref": "st-src", "classification": "confirmed", "method": "census",
    "definition": "greek-citizens", "population_type": "diaspora",
    "evidence": [{"source_ref": "st-src", "url": "https://example.com/t",
                  "accessed_at": "2026-10-05", "published_at": "2023-01-01",
                  "quote": {"el": "x", "en": "x"}, "quote_language": "en",
                  "archive_url": "https://web.archive.org/x"}],
    "verification": {"independent_sources": 1, "confidence": "single-source"},
}
BASE_HYPOTHETICAL = dict(
    BASE_RECORD, record_id="t-2022-community", source_ref="st2-src",
    classification="hypothetical", method="estimate", definition="greek-origin",
    evidence=[{"source_ref": "st2-src", "url": "https://example.com/h",
               "accessed_at": "2026-10-05", "published_at": "2022-06-01",
               "quote": {"el": "y", "en": "y"}, "quote_language": "en",
               "archive_url": "https://web.archive.org/y"}],
)


def make_tree(base: Path, record_extras=None, source_derives=None,
              country_status="partial", records=None):
    """Minimal valid repo tree: 1 continent, 1 country, 2 sources."""
    d = base
    (d / "data/continents").mkdir(parents=True)
    (d / "data/countries/europe").mkdir(parents=True)
    (d / "sources/confirmed").mkdir(parents=True)
    (d / "sources/hypothetical").mkdir(parents=True)

    (d / "data/continents/europe.yaml").write_text(yaml.safe_dump({
        "id": "europe", "name": {"el": "Ευρώπη", "en": "Europe"}, "countries": ["testland"]},
        allow_unicode=True), encoding="utf-8")

    rec = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
           for k, v in BASE_RECORD.items()}
    if record_extras:
        for k, v in record_extras.items():
            if v is None:
                rec.pop(k, None)
            elif k == "evidence":
                rec["evidence"] = v
            elif k == "verification":
                rec["verification"].update(v)
            else:
                rec[k] = v
    recs = records if records is not None else [rec]
    (d / "data/countries/europe/testland.yaml").write_text(yaml.safe_dump({
        "id": "testland", "iso_alpha2": "TL", "name": {"el": "Τ", "en": "Testland"},
        "continent": "europe", "status": country_status, "records": recs},
        allow_unicode=True), encoding="utf-8")

    src = {
        "id": "st-src", "title": {"el": "τ", "en": "t"}, "publisher": {"el": "τ", "en": "t"},
        "country": "testland", "year": 2022, "url": "https://example.com/t",
        "classification": "confirmed", "type": "census", "scope": "greek-citizens",
        "reliability": "high", "language": "en", "language_iso639_2b": "eng",
        "publication": {"retrieved_at": "2026-10-05"},
        "independence": {"primary_data_collector": True},
    }
    (d / "sources/confirmed/st-src.yaml").write_text(
        yaml.safe_dump(src, allow_unicode=True), encoding="utf-8")
    src2 = dict(src, id="st2-src", classification="hypothetical", type="media")
    if source_derives:
        src2["independence"] = {"primary_data_collector": False, "derives_from": source_derives}
    (d / "sources/hypothetical/st2-src.yaml").write_text(
        yaml.safe_dump(src2, allow_unicode=True), encoding="utf-8")
    return d


def run(d: Path):
    env = dict(os.environ, DIASPORA_DATA_ROOT=str(d))
    return subprocess.run([sys.executable, str(VALIDATE)], capture_output=True,
                          text=True, env=env)


def test_baseline_passes():
    with tempfile.TemporaryDirectory() as t:
        r = run(make_tree(Path(t)))
        assert r.returncode == 0, r.stdout + r.stderr


def test_independent_sources_must_match_computation():
    with tempfile.TemporaryDirectory() as t:
        d = make_tree(Path(t), record_extras={"verification": {"independent_sources": 3}})
        r = run(d)
        assert r.returncode == 1 and "[INDEP-COUNT]" in r.stdout


def test_derives_from_missing_id_and_cycle():
    with tempfile.TemporaryDirectory() as t:
        r = run(make_tree(Path(t), source_derives=["nope"]))
        assert "[MISSING-DERIVES]" in r.stdout
    with tempfile.TemporaryDirectory() as t:
        d = make_tree(Path(t))
        for sid, folder in (("st-src", "confirmed"), ("st2-src", "hypothetical")):
            p = d / f"sources/{folder}/{sid}.yaml"
            s = yaml.safe_load(p.read_text(encoding="utf-8"))
            s["independence"]["derives_from"] = ["st2-src" if sid == "st-src" else "st-src"]
            p.write_text(yaml.safe_dump(s, allow_unicode=True), encoding="utf-8")
        assert "[DERIVES-CYCLE]" in run(d).stdout


def test_evidence_source_ref_must_be_primary_or_corroborating():
    with tempfile.TemporaryDirectory() as t:
        d = make_tree(Path(t), record_extras={
            "evidence": [{"source_ref": "st2-src", "url": "https://example.com/x",
                          "accessed_at": "2026-10-05"}]})
        assert "[EVIDENCE-REF]" in run(d).stdout


def test_http_url_is_warning_not_error_and_missing_quote_warns():
    with tempfile.TemporaryDirectory() as t:
        d = make_tree(Path(t), record_extras={
            "evidence": [{"source_ref": "st-src", "url": "http://example.com/x",
                          "accessed_at": "2026-10-05"}]})
        r = run(d)
        assert r.returncode == 0
        assert "[HTTP-URL]" in r.stdout and "[NO-QUOTE]" in r.stdout and "[NO-ARCHIVE]" in r.stdout


def test_disputed_record_requires_dispute_note():
    with tempfile.TemporaryDirectory() as t:
        d = make_tree(Path(t), record_extras={"status": "disputed"})
        r = run(d)
        assert r.returncode == 1 and "[DISPUTE-NOTE]" in r.stdout
    with tempfile.TemporaryDirectory() as t:
        d = make_tree(Path(t), record_extras={
            "status": "disputed", "dispute_note": {"el": "x", "en": "x"}})
        assert run(d).returncode == 0


def test_disputed_country_requires_a_disputed_record():
    with tempfile.TemporaryDirectory() as t:
        d = make_tree(Path(t), country_status="disputed")
        assert "[STATUS-DISPUTED]" in run(d).stdout


def test_complete_country_requires_both_classifications():
    with tempfile.TemporaryDirectory() as t:
        d = make_tree(Path(t), country_status="complete")
        assert "[STATUS-COMPLETE]" in run(d).stdout
    with tempfile.TemporaryDirectory() as t:
        confirmed = {k: v for k, v in BASE_RECORD.items()}
        hypothetical = {k: v for k, v in BASE_HYPOTHETICAL.items()}
        d = make_tree(Path(t), country_status="complete", records=[confirmed, hypothetical])
        r = run(d)
        assert r.returncode == 0, r.stdout
