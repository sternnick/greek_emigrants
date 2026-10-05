"""The status field must say what it means (docs/country-list-sources.md)."""
from pathlib import Path
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
STATUSES = {"stub", "partial", "complete", "disputed"}
COUNTRY_FILES = sorted((ROOT / "data" / "countries").rglob("*.yaml"))


def countries():
    return [(p, yaml.safe_load(p.read_text(encoding="utf-8"))) for p in COUNTRY_FILES]


@pytest.mark.parametrize("path", COUNTRY_FILES, ids=[p.stem for p in COUNTRY_FILES])
def test_status_field_is_valid(path):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["status"] in STATUSES, path


def test_stub_countries_have_no_records():
    for path, doc in countries():
        if doc["status"] == "stub":
            assert doc["records"] == [], path


def test_non_stub_countries_have_records():
    for path, doc in countries():
        if doc["status"] != "stub":
            assert doc["records"], path


def test_complete_countries_have_both_classifications():
    for path, doc in countries():
        if doc["status"] == "complete":
            classes = {r["classification"] for r in doc["records"]}
            assert {"confirmed", "hypothetical"} <= classes, path


def test_disputed_countries_point_at_a_disputed_record():
    for path, doc in countries():
        if doc["status"] == "disputed":
            assert any(r.get("status") == "disputed" for r in doc["records"]), path


def test_stub_records_field_exists_and_is_empty_list():
    """The stub convention is `records: []`, not a missing key."""
    for path, doc in countries():
        assert "records" in doc, path
