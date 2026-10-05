"""Net figures are derived, must be marked as such, and must never be summed twice."""
import importlib.util
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
FLOWS = ROOT / "data" / "flows"


def _spec(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def flow_docs():
    return {p.name: yaml.safe_load(p.read_text(encoding="utf-8"))
            for p in sorted(FLOWS.rglob("*.yaml"))}


def test_net_exists_and_every_net_record_is_marked_computed():
    doc = flow_docs()["net.yaml"]
    assert doc["direction"] == "net"
    assert doc["records"], "net.yaml must carry the balance records"
    for rec in doc["records"]:
        assert rec.get("computed") is True, rec


def test_net_records_are_not_double_counted_in_the_totals():
    """worldwide.yaml's net_flows comes from the two directions, not net.yaml.

    If net.yaml were summed in as well, the balance would come out as the sum of
    the two net records (14,400 + 9,000) instead of returns minus departures.
    """
    agg = _spec("aggregate")
    totals = agg.net_flow_totals()
    assert "greece" in totals
    g = totals["greece"]
    outflow = max((r for r in flow_docs()["outflow.yaml"]["records"]
                   if r.get("classification") == "confirmed" and r.get("count") is not None
                   and r.get("citizenship") == "greek-citizens"), key=lambda r: r["year"])
    returns = max((r for r in flow_docs()["return.yaml"]["records"]
                   if r.get("classification") == "confirmed" and r.get("count") is not None
                   and r.get("citizenship") == "greek-citizens"), key=lambda r: r["year"])
    assert g["departures"] == outflow["count"]
    assert g["returns"] == returns["count"]
    assert g["net_return"] == max(0, returns["count"] - outflow["count"])
    assert g["net_emigration"] == max(0, outflow["count"] - returns["count"])

    net_sum = sum(r["count"] for r in flow_docs()["net.yaml"]["records"] if r["count"])
    assert g["net_return"] != net_sum, "net.yaml appears to be aggregated as if it were data"


def test_every_flow_record_has_evidence_and_verification():
    for name, doc in flow_docs().items():
        for rec in doc["records"]:
            assert rec.get("evidence"), f"{name} {rec['year']}: missing evidence"
            assert rec.get("verification"), f"{name} {rec['year']}: missing verification"
            assert rec["verification"]["independent_sources"] == (
                len(rec["verification"].get("corroborating_refs", []))
                + (1 if _primary(rec["source_ref"]) else 0)
            ), f"{name} {rec['year']}: independence count is not the computed one"


def _primary(source_ref: str) -> bool:
    for p in (ROOT / "sources").rglob(f"{source_ref}.yaml"):
        return bool(yaml.safe_load(p.read_text(encoding="utf-8"))
                    .get("independence", {}).get("primary_data_collector"))
    return False


def test_conflicting_values_are_kept_side_by_side_not_reconciled():
    """OECD and the national figures disagree for 2023; both must remain."""
    docs = flow_docs()
    ret_2023 = [r["count"] for r in docs["return.yaml"]["records"]
                if r["year"] == 2023 and r.get("count")]
    out_2023 = [r["count"] for r in docs["outflow.yaml"]["records"]
                if r["year"] == 2023 and r.get("count")]
    assert 47200 in ret_2023 and 46000 in ret_2023, ret_2023
    assert 32800 in out_2023 and 37000 in out_2023, out_2023
    disputed = [r for r in docs["return.yaml"]["records"] if r["year"] == 2023
                and r.get("dispute_note")]
    assert disputed, "the 46,000 vs 47,200 conflict needs a dispute_note"
