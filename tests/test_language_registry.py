"""The el+en rule, enforced. This dataset supports exactly two languages.

The repo rule is that the dataset speaks Greek and English and nothing else.
Before this file existed that rule was a convention: `i18n/` happened to hold two
catalogues, the generators happened to iterate `("en", "el")`, and nothing failed
when `i18n/languages.json` listed French and Albanian, or when an Arabic token
landed inside a Greek paragraph. Each test below is one way that rule can break.

Two vocabularies are kept apart on purpose:

* **dataset languages** — the languages the dataset itself is written in: `el`, `en`.
* **source languages** — the language an *external* document was published in,
  recorded per source in `language`. A source may be German; the dataset is not.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

DATASET_LANGS = {"el", "en"}
CATALOGUE_EXEMPT = {"languages"}  # i18n/languages.json is a registry, not strings
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".githooks"}
# Scripts that are neither Greek nor Latin: a hit here is a language leak, not styling.
FOREIGN_SCRIPT = re.compile(
    "[\u0600-\u06ff"      # Arabic
    "\u0590-\u05ff"       # Hebrew
    "\u0400-\u04ff"       # Cyrillic
    "\u3040-\u30ff"       # Kana
    "\u3400-\u4dbf\u4e00-\u9fff"  # CJK ideographs
    "\uac00-\ud7af"       # Hangul
    "\u0900-\u097f"       # Devanagari
    "\u0e00-\u0eff]"      # Thai
)
# Codes that must never appear anywhere: the retired fr/sq registrations and the
# ISO 639-2/B codes they would have had.
FORBIDDEN_CODE = re.compile(r"(?<![A-Za-z])(fr|sq|fra|sqi)(?![A-Za-z])")


def _i18n():
    spec = importlib.util.spec_from_file_location("i18n", ROOT / "scripts" / "i18n.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["i18n"] = mod
    spec.loader.exec_module(mod)
    return mod


i18n = _i18n()

# The language registry (i18n/languages.json) and the i18n.codes()/ui_langs() helpers that
# read it arrived together in the COAR commit. This test file is designed to run on either
# side of that: with no registry, the registry-backed assertions skip and the structural
# ones - the Arabic-token sweep above all - still run, so main gets regression protection
# without needing code that is not there yet. When both branches merge, everything runs.
HAS_REGISTRY = (ROOT / "i18n" / "languages.json").exists() and hasattr(i18n, "codes")
needs_registry = pytest.mark.skipif(
    not HAS_REGISTRY,
    reason="no language registry on this branch (i18n/languages.json + i18n.codes)")


def _text_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


def _source_docs():
    for path in sorted((ROOT / "sources").rglob("*.yaml")):
        yield path, yaml.safe_load(path.read_text(encoding="utf-8"))


def test_ui_catalogues_are_exactly_el_and_en():
    """i18n/ holds one string catalogue per dataset language, plus the registry."""
    found = {p.stem for p in (ROOT / "i18n").glob("*.json")} - CATALOGUE_EXEMPT
    assert found == DATASET_LANGS, f"i18n/ catalogues {sorted(found)} != {sorted(DATASET_LANGS)}"


@needs_registry
def test_registry_agrees_with_the_catalogues():
    """ui: true must mean exactly the dataset languages, and match ui_langs()."""
    codes = i18n.codes()
    ui = {c for c, m in codes.items() if m.get("ui")}
    assert ui == DATASET_LANGS, f"registry ui languages {sorted(ui)}"
    assert set(i18n.ui_langs()) == DATASET_LANGS
    catalogues = {p.stem for p in (ROOT / "i18n").glob("*.json")} - CATALOGUE_EXEMPT
    assert ui == catalogues, f"registry {sorted(ui)} vs catalogues {sorted(catalogues)}"


@needs_registry
def test_every_catalogue_key_is_registered_as_ui():
    codes = i18n.codes()
    for lang in DATASET_LANGS:
        assert codes[lang]["ui"] is True, f"{lang} is a dataset language but is not ui: true"
        assert codes[lang]["iso639_1"] == lang


@needs_registry
def test_non_ui_language_is_justified_by_a_real_source():
    """A registered non-dataset language must be the actual language of a source.

    This is the assertion that would have rejected fr and sq at the moment they
    were added: nothing in the dataset is published in French or Albanian, so a
    registry entry for them has no evidence behind it.
    """
    codes = i18n.codes()
    used = {doc["language"] for _, doc in _source_docs() if doc.get("language")}
    non_ui = {c for c, m in codes.items() if not m.get("ui")}
    unjustified = non_ui - used
    assert not unjustified, (
        f"registered as source language but no source uses it: {sorted(unjustified)}")
    undeclared = used - set(codes)
    assert not undeclared, f"source language not in the registry: {sorted(undeclared)}"


@needs_registry
def test_source_provenance_languages_stay_out_of_the_ui():
    """A source language kept for provenance must never be marked ui."""
    for code, meta in i18n.codes().items():
        if code not in DATASET_LANGS:
            assert meta.get("ui") is not True, f"{code} is a source language but marked ui"
    assert set(i18n.ui_langs()) == DATASET_LANGS


def test_generators_follow_the_language_list():
    """Reports must be driven by the language list, whichever form this branch is on.

    With a registry the generators must follow ui_langs(), so a new ui language is the
    only way a report language can change. Without one they must still iterate exactly
    the el/en pair literally - and on either branch, no generator may name any other
    language in its loop.
    """
    for name in ("report.py", "report_flows.py"):
        src = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        if HAS_REGISTRY:
            assert "for lang in i18n.ui_langs():" in src, f"{name} does not iterate ui_langs()"
        else:
            assert re.search(r'for lang in \("en", "el"\)', src), \
                f"{name} does not iterate the el/en pair"
        bad = re.findall(r'for lang in ([^)]*)\)', src)
        for clause in bad:
            stray = re.findall(r'"([a-z]{2})"', clause)
            assert set(stray) <= DATASET_LANGS, f"{name} iterates {sorted(set(stray))}"
        assert not re.search(r'reports?/.*\.(fr|de|sq)\.md', src), f"{name} emits a non-el/en report"


def test_generators_emit_only_el_and_en_files():
    """Whatever the reports directory holds must be el/en only. No subprocess here:
    a test that regenerates reports would dirty the working tree.
    """
    produced = {p.stem.split(".")[-1] for p in (ROOT / "reports").glob("*.md")
                if len(p.stem.split(".")) > 1}
    assert produced <= DATASET_LANGS, f"reports written in {sorted(produced)}"


def test_no_schema_enum_is_language_valued():
    """No enum may admit a language code outside the dataset languages.

    Runs on both branch shapes: the static {el, en} allowlist always, widened with the
    registry's own codes when this branch has one.
    """
    langs = set(DATASET_LANGS)
    if HAS_REGISTRY:
        langs |= {m["iso639_1"] for m in i18n.codes().values()}
        langs |= {m["iso639_2b"] for m in i18n.codes().values()}
    for path in sorted((ROOT / "schemas").glob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))

        def walk(node, trail):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "enum" and isinstance(v, list):
                        bad = [x for x in v
                               if isinstance(x, str) and x.lower() in langs]
                        assert not bad, f"{path.name}{trail}.enum holds language code(s) {bad}"
                    walk(v, f"{trail}.{k}")
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, f"{trail}[{i}]")

        walk(schema, "")


def test_bilingual_fields_use_only_dataset_languages():
    """Every {el, en} shaped object stays {el, en} shaped."""
    def walk(node, path, trail):
        if isinstance(node, dict):
            if node and ({"el", "en"} & set(node)) and all(
                    re.fullmatch(r"[a-z]{2}", str(k)) for k in node):
                assert set(node) <= DATASET_LANGS, f"{path}{trail}: keys {sorted(node)}"
            for k, v in node.items():
                walk(v, path, f"{trail}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path, f"{trail}[{i}]")

    for path, doc in _source_docs():
        walk(doc, path.name, "")
    for sub in ("data/countries", "data/flows"):
        for path in sorted((ROOT / sub).rglob("*.yaml")):
            walk(yaml.safe_load(path.read_text(encoding="utf-8")), path.name, "")


def test_no_forbidden_language_code_appears_anywhere():
    """fr and sq are gone entirely — including in prose and 639-2/B form.

    This file is exempt: it names the codes in order to forbid them, and any
    other way of writing the check would hide the rule from a reader.
    """
    here = Path(__file__).resolve()
    hits = []
    for path, text in _text_files():
        if path.resolve() == here:
            continue
        for m in FORBIDDEN_CODE.finditer(text):
            hits.append(f"{path.relative_to(ROOT)}:{text[:m.start()].count(chr(10)) + 1} "
                        f"{m.group(0)!r}")
    assert not hits, "retired language code present:\n" + "\n".join(hits)


def test_no_text_uses_a_script_outside_greek_and_latin():
    """The Arabic-token class of defect: a foreign script inside an el or en file."""
    hits = []
    for path, text in _text_files():
        for m in FOREIGN_SCRIPT.finditer(text):
            hits.append(f"{path.relative_to(ROOT)}:"
                        f"{text[:m.start()].count(chr(10)) + 1} {m.group(0)!r}")
    assert not hits, "non-el/en script found:\n" + "\n".join(hits)


def test_readme_and_docs_come_in_exactly_two_languages():
    """Every translatable document is either the en original or its .el pair."""
    for path in sorted(list((ROOT / "docs").glob("*.md")) + list(ROOT.glob("*.md"))):
        name = path.name
        if name.endswith(".el.md"):
            stem = name[: -len(".el.md")]
            assert (path.parent / f"{stem}.md").exists(), f"{name} has no English original"
        else:
            assert ".el." not in name and ".en." not in name, f"unexpected locale in {name}"
