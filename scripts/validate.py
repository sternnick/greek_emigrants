#!/usr/bin/env python3
"""Validate all YAML files against schemas and cross-file rules."""
from __future__ import annotations
import sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"
DATA = ROOT / "data"
SOURCES = ROOT / "sources"

errors: list[str] = []
warnings: list[str] = []


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_validator(schema_file: str) -> Draft202012Validator:
    schema_path = SCHEMAS / schema_file
    schema = load_yaml(schema_path)
    store = {s.name: load_yaml(s) for s in SCHEMAS.glob("*.json")}
    store[schema_file] = schema
    resolver = RefResolver(base_uri=SCHEMAS.as_uri() + "/", referrer=schema, store=store)
    return Draft202012Validator(schema, resolver=resolver)


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
            expected_class = folder
            if doc.get("classification") != expected_class:
                errors.append(
                    f"[CLASS-MISMATCH] {f}: classification={doc.get('classification')} "
                    f"but folder is '{expected_class}'"
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


def check_source_refs(countries: dict[str, Path], sources: dict[str, Path]) -> None:
    for cid, path in countries.items():
        doc = load_yaml(path)
        seen: set[tuple[str, int]] = set()
        for rec in doc.get("records", []):
            ref = rec.get("source_ref")
            if ref not in sources:
                errors.append(f"[MISSING-SOURCE] {path}: source_ref '{ref}' not found")
            key = (ref, rec.get("year"))
            if key in seen:
                errors.append(f"[DUP-RECORD] {path}: duplicate (source_ref,year)={key}")
            seen.add(key)
            if rec.get("count") is None:
                warnings.append(f"[NULL-COUNT] {path}: record '{rec.get('record_id')}' has count=null")


def check_continent_refs(countries: dict[str, Path]) -> None:
    for f in (DATA / "continents").glob("*.yaml"):
        doc = load_yaml(f)
        for cid in doc.get("countries", []):
            if cid not in countries:
                errors.append(f"[MISSING-COUNTRY] {f}: continent lists '{cid}' but no file")
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
    country_validator = build_validator("country.schema.json")
    continent_validator = build_validator("continent.schema.json")
    source_validator = build_validator("source.schema.json")

    for f in (DATA / "countries").rglob("*.yaml"):
        validate_file(f, country_validator)
    for f in (DATA / "continents").glob("*.yaml"):
        validate_file(f, continent_validator)
    for f in SOURCES.rglob("*.yaml"):
        validate_file(f, source_validator)

    sources = collect_sources()
    countries = collect_countries()
    check_source_refs(countries, sources)
    check_continent_refs(countries)

    for w in warnings:
        print(f"⚠  {w}")
    if errors:
        for e in errors:
            print(f"✗  {e}")
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"✓ All checks passed ({len(countries)} countries, {len(sources)} sources, "
          f"{len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
