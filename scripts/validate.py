#!/usr/bin/env python3
"""Validate all YAML files against schemas and cross-file rules."""
from __future__ import annotations
import sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"
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
            )
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

    country_files = list((DATA / "countries").rglob("*.yaml"))
    for f in country_files:
        validate_file(f, country_v)
    for f in (DATA / "continents").glob("*.yaml"):
        validate_file(f, continent_v)
    for f in SOURCES.rglob("*.yaml"):
        validate_file(f, source_v)

    flow_files = list((DATA / "flows").rglob("*.yaml")) if (DATA / "flows").exists() else []
    for f in flow_files:
        validate_file(f, flow_v)

    sources = collect_sources()
    countries = collect_countries()
    check_source_refs(country_files + flow_files, sources)
    check_continent_refs(countries)

    for w in warnings:
        print(f"⚠  {w}")
    if errors:
        for e in errors:
            print(f"✗  {e}")
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"✓ All checks passed ({len(countries)} countries, {len(sources)} sources, "
          f"{len(flow_files)} flow files, {len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
