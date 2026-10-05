#!/usr/bin/env python3
"""Validate all YAML files against schemas and cross-file rules."""
from __future__ import annotations
import sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator
import i18n  # noqa: E402
from referencing import Registry, Resource

import os

ROOT = Path(os.environ.get("DIASPORA_DATA_ROOT", Path(__file__).resolve().parent.parent))
SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"
DATA = ROOT / "data"
SOURCES = ROOT / "sources"

errors: list[str] = []
warnings: list[str] = []


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_registry() -> Registry:
    resources = []
    for f in SCHEMAS.glob("*.json"):
        doc = load_yaml(f)
        uri = doc.get("$id", f.as_uri())
        resources.append((uri, Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def make_validator(schema_file: str, registry: Registry) -> Draft202012Validator:
    schema = load_yaml(SCHEMAS / schema_file)
    return Draft202012Validator(schema, registry=registry)


def validate_file(path: Path, validator: Draft202012Validator) -> None:
    try:
        data = load_yaml(path)
    except Exception as e:
        errors.append(f"[YAML] {path}: {e}")
        return
    for err in validator.iter_errors(data):
        errors.append(f"[SCHEMA] {path}: {err.message} @ {list(err.path)}")


def collect_sources() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for folder in ("confirmed", "hypothetical"):
        for f in (SOURCES / folder).glob("*.yaml"):
            doc = load_yaml(f)
            sid = doc.get("id")
            if sid in found:
                errors.append(f"[DUP-SOURCE] id '{sid}' in {f} and {found[sid]}")
            found[sid] = f
            if doc.get("classification") != folder:
                errors.append(
                    f"[CLASS-MISMATCH] {f}: classification={doc.get('classification')} "
                    f"but folder is '{folder}'"
                )
    return found


def collect_countries() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for f in (DATA / "countries").rglob("*.yaml"):
        doc = load_yaml(f)
        cid = doc.get("id")
        if cid in found:
            errors.append(f"[DUP-COUNTRY] id '{cid}' in {f} and {found[cid]}")
        found[cid] = f
    return found


# The dimensions that make two rows with the same (source_ref, year) different facts.
# direction lives on the flow document, not on the record, so it is read from the doc.
DIMENSIONS = ("direction", "definition", "population_type", "citizenship", "education")


def collect_births_files() -> list[Path]:
    d = DATA / "births"
    return sorted(d.rglob("*.yaml")) if d.exists() else []


def load_source_meta() -> dict[str, dict]:
    """id -> {primary_data_collector, derives_from} for evidence-rule checks."""
    meta: dict[str, dict] = {}
    for folder in ("confirmed", "hypothetical"):
        d = SOURCES / folder
        if not d.exists():
            continue
        for f in d.glob("*.yaml"):
            doc = load_yaml(f)
            ind = doc.get("independence") or {}
            meta[doc.get("id")] = {
                "primary": bool(ind.get("primary_data_collector")),
                "derives": ind.get("derives_from") or [],
            }
    return meta


def check_language_codes(sources: dict[str, dict]) -> None:
    """COAR wants machine-readable language metadata: both ISO 639 systems, agreeing.

    `language` is the two-letter code the reports and quote rules use;
    `language_iso639_2b` is the bibliographic code a repository publishes. The
    mapping lives once, in i18n/languages.json, so a file cannot invent a pair.
    """
    try:
        langs = i18n.codes()
    except FileNotFoundError:
        errors.append("[LANGUAGES] i18n/languages.json is missing")
        return
    by1 = {m["iso639_1"]: m for m in langs.values()}
    for sid, path in sorted(sources.items()):
        doc = load_yaml(path) if isinstance(path, Path) else path
        lang = doc.get("language")
        b = doc.get("language_iso639_2b")
        if lang not in by1:
            errors.append(f"[LANG-CODE] sources/{sid}: language '{lang}' is not in i18n/languages.json")
            continue
        want = by1[lang]["iso639_2b"]
        if b != want:
            errors.append(f"[LANG-CODE] sources/{sid}: language '{lang}' needs "
                          f"language_iso639_2b '{want}', found {b!r}")


def check_quote_languages(files: list[Path]) -> None:
    """A quote must declare a language the registry knows."""
    try:
        known = {m["iso639_1"] for m in i18n.codes().values()} | {m["iso639_2b"] for m in i18n.codes().values()}
    except FileNotFoundError:
        return
    for f in files:
        doc = load_yaml(f)
        for rec in doc.get("records", []):
            for i, ev in enumerate(rec.get("evidence") or []):
                if not ev.get("quote"):
                    continue
                ql = (ev.get("quote") or {}).get("language") or ev.get("quote_language")
                if ql not in known:
                    errors.append(f"[QUOTE-LANG] {f.name} record {rec.get('record_id', rec.get('year'))} "
                                  f"evidence[{i}]: quote_language {ql!r} is not a registered ISO 639 code")


def check_derives(meta: dict[str, dict]) -> None:
    """derives_from ids must exist and the graph must be acyclic."""
    for sid, m in meta.items():
        for d in m["derives"]:
            if d not in meta:
                errors.append(f"[MISSING-DERIVES] source '{sid}': derives_from '{d}' not found")

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {sid: WHITE for sid in meta}

    def visit(sid: str, stack: list[str]) -> None:
        color[sid] = GRAY
        for d in meta.get(sid, {}).get("derives", []):
            if d not in meta:
                continue
            if color[d] == GRAY:
                errors.append(
                    f"[DERIVES-CYCLE] derives_from cycle: {' -> '.join(stack + [d])}"
                )
            elif color[d] == WHITE:
                visit(d, stack + [d])
        color[sid] = BLACK

    for sid in meta:
        if color[sid] == WHITE:
            visit(sid, [sid])


def check_verification(record: dict, path: Path, meta: dict[str, dict]) -> None:
    """Evidence + verification consistency for one country/births record."""
    where = f"{path} '{record.get('record_id', record.get('year'))}'"
    v = record.get("verification") or {}
    n = v.get("independent_sources")
    refs = v.get("corroborating_refs") or []
    confidence = v.get("confidence")
    own = meta.get(record.get("source_ref"), {})
    expected = len(refs) + (1 if own.get("primary") else 0)
    if isinstance(n, int) and n != expected:
        errors.append(
            f"[INDEP-COUNT] {where}: independent_sources={n} but computed "
            f"{expected} (corroborating_refs={len(refs)}, primary_data_collector="
            f"{bool(own.get('primary'))})"
        )
    if isinstance(n, int) and confidence:
        want = ("single-source" if n <= 1 else
                "corroborated" if n == 2 else "well-established")
        if confidence != want:
            errors.append(
                f"[CONFIDENCE] {where}: confidence '{confidence}' inconsistent "
                f"with independent_sources={n} (expected '{want}')"
            )
    for ref in refs:
        if ref not in meta:
            errors.append(f"[MISSING-CORROBORATION] {where}: corroborating_ref '{ref}' not found")

    allowed = {record.get("source_ref")} | set(refs)
    for ev in record.get("evidence") or []:
        evref = ev.get("source_ref")
        if evref not in allowed:
            errors.append(
                f"[EVIDENCE-REF] {where}: evidence source_ref '{evref}' is neither the "
                f"record's primary source nor a corroborating_ref"
            )
        url = ev.get("url", "")
        if url.startswith("http://"):
            warnings.append(f"[HTTP-URL] {where}: evidence url not https: {url}")
        if not ev.get("archive_url"):
            warnings.append(f"[NO-ARCHIVE] {where}: evidence for '{evref}' has no archive_url")
        if not ev.get("published_at"):
            warnings.append(f"[NO-PUBLISHED] {where}: evidence for '{evref}' has no published_at")
        if not ev.get("quote"):
            warnings.append(f"[NO-QUOTE] {where}: evidence for '{evref}' has no verbatim quote")


def check_status_semantics(country_files: list[Path]) -> None:
    """Country/record status must be consistent with the records present."""
    for path in country_files:
        doc = load_yaml(path)
        recs = doc.get("records", [])
        cstatus = doc.get("status")
        classes = {r.get("classification") for r in recs}
        if cstatus == "stub" and recs:
            errors.append(f"[STATUS-STUB] {path}: status=stub but {len(recs)} record(s) present")
        if cstatus == "complete" and not {"confirmed", "hypothetical"} <= classes:
            errors.append(
                f"[STATUS-COMPLETE] {path}: status=complete requires both a confirmed and "
                f"a hypothetical record (present: {sorted(c for c in classes if c)})"
            )
        if cstatus == "disputed" and not any(r.get("status") == "disputed" for r in recs):
            errors.append(
                f"[STATUS-DISPUTED] {path}: status=disputed requires at least one record "
                f"with record-level status: disputed"
            )
        for rec in recs:
            if rec.get("status") == "disputed" and not rec.get("dispute_note"):
                errors.append(
                    f"[DISPUTE-NOTE] {path} '{rec.get('record_id')}': record status=disputed "
                    f"requires a dispute_note"
                )


def check_source_refs(paths: list[Path], sources: dict[str, Path]) -> None:
    for path in paths:
        doc = load_yaml(path)
        direction = doc.get("direction")
        seen: set[tuple] = set()
        for rec in doc.get("records", []):
            ref = rec.get("source_ref")
            if ref not in sources:
                errors.append(f"[MISSING-SOURCE] {path}: source_ref '{ref}' not found")
            key = (ref, rec.get("year"), direction) + tuple(
                rec.get(d) for d in DIMENSIONS if d != "direction"
            ) + (rec.get("mother_origin"), rec.get("father_origin"))
            if key in seen:
                errors.append(f"[DUP-RECORD] {path}: duplicate {key}")
            seen.add(key)
            if rec.get("count") is None:
                warnings.append(
                    f"[NULL-COUNT] {path}: record '{rec.get('record_id', rec.get('year'))}' has count=null"
                )


def check_continent_refs(countries: dict[str, Path]) -> None:
    for f in (DATA / "continents").glob("*.yaml"):
        doc = load_yaml(f)
        for cid in doc.get("countries", []):
            if cid not in countries:
                errors.append(f"[MISSING-COUNTRY] {f}: lists '{cid}' but no file")
    for cid, path in countries.items():
        doc = load_yaml(path)
        cont = doc.get("continent")
        cont_file = DATA / "continents" / f"{cont}.yaml"
        if not cont_file.exists():
            errors.append(f"[MISSING-CONTINENT] {path}: continent '{cont}' file missing")
            continue
        cont_doc = load_yaml(cont_file)
        if cid not in cont_doc.get("countries", []):
            errors.append(f"[UNLISTED] {path}: '{cid}' not listed in {cont_file}")


def main() -> int:
    registry = build_registry()
    country_v = make_validator("country.schema.json", registry)
    continent_v = make_validator("continent.schema.json", registry)
    source_v = make_validator("source.schema.json", registry)
    flow_v = make_validator("flow.schema.json", registry)

    births_v = make_validator("births.schema.json", registry)

    country_files = list((DATA / "countries").rglob("*.yaml"))
    for f in country_files:
        validate_file(f, country_v)
    for f in (DATA / "continents").glob("*.yaml"):
        validate_file(f, continent_v)
    for f in SOURCES.rglob("*.yaml"):
        validate_file(f, source_v)

    births_files = collect_births_files()
    for f in births_files:
        validate_file(f, births_v)

    flow_files = list((DATA / "flows").rglob("*.yaml")) if (DATA / "flows").exists() else []
    for f in flow_files:
        validate_file(f, flow_v)

    sources = collect_sources()
    countries = collect_countries()
    check_source_refs(country_files + flow_files + births_files, sources)
    check_continent_refs(countries)

    meta = load_source_meta()
    check_derives(meta)
    check_language_codes(sources)
    check_quote_languages(country_files + flow_files)
    check_status_semantics(country_files)
    for f in country_files:
        for rec in load_yaml(f).get("records", []):
            check_verification(rec, f, meta)
    for f in births_files:
        for rec in load_yaml(f).get("records", []):
            check_verification(rec, f, meta)

    for w in warnings:
        print(f"⚠  {w}")
    if errors:
        for e in errors:
            print(f"✗  {e}")
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"✓ All checks passed ({len(countries)} countries, {len(sources)} sources, "
          f"{len(flow_files)} flow files, {len(births_files)} births files, "
          f"{len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
