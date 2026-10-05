"""COAR multilingual compliance: declared languages, standard codes, both scripts."""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


def _i18n():
    spec = importlib.util.spec_from_file_location("i18n", ROOT / "scripts" / "i18n.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["i18n"] = mod
    spec.loader.exec_module(mod)
    return mod


i18n = _i18n()


def test_registry_is_internally_consistent():
    codes = i18n.codes()
    ones = [m["iso639_1"] for m in codes.values()]
    twos = [m["iso639_2b"] for m in codes.values()]
    assert len(set(ones)) == len(ones) and len(set(twos)) == len(twos), "duplicate code"
    assert any(m.get("ui") for m in codes.values()), "no dataset language declared"
    for code, m in codes.items():
        assert code == m["iso639_1"], f"{code}: registry key must be the ISO 639-1 code"
        assert re.fullmatch(r"[a-z]{2}", m["iso639_1"])
        assert re.fullmatch(r"[a-z]{3}", m["iso639_2b"])
        assert m["direction"] in {"ltr", "rtl"}
        assert m["name_native"] and m["name_en"]


@pytest.mark.parametrize("path", sorted((ROOT / "sources").rglob("*.yaml")),
                         ids=lambda p: p.name)
def test_every_source_declares_both_language_codes(path):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    lang = doc.get("language")
    assert lang, f"{path.name}: no language"
    assert i18n.to_iso639_2b(lang), f"{path.name}: language '{lang}' is not registered"
    assert doc.get("language_iso639_2b") == i18n.to_iso639_2b(lang), \
        f"{path.name}: language_iso639_2b must be {i18n.to_iso639_2b(lang)!r}"


def test_every_quote_language_is_registered():
    known = {m["iso639_1"] for m in i18n.codes().values()} | {m["iso639_2b"] for m in i18n.codes().values()}
    for f in sorted((ROOT / "data").rglob("*.yaml")):
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for rec in doc.get("records", []):
            for ev in rec.get("evidence") or []:
                if ev.get("quote"):
                    assert ev.get("quote_language") in known, f"{f.name}: unregistered quote language"


def test_readme_declares_the_dataset_languages():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    block = re.search(r"```json\n(.*?)\n```", text, re.S)
    assert block, "README has no machine-readable metadata block"
    meta = json.loads(block.group(1))
    assert meta["@type"] == "Dataset"
    ui = sorted(i18n.to_iso639_2b(c) for c in i18n.ui_langs())
    assert sorted(meta["inLanguage"]) == ui, "README languages disagree with the registry"
    for entry in meta["languages"]:
        assert entry["iso639_2b"] == i18n.to_iso639_2b(entry["iso639_1"])
        assert entry["name_native"] == i18n.get_lang_metadata(entry["iso639_1"])["name_native"]
    assert set(meta["keywords"]) == set(i18n.ui_langs()), "keywords are not in every dataset language"
    assert meta["license"].startswith("https://")


def test_greek_readme_carries_the_same_metadata():
    """The block is language-neutral data, so it must not diverge between READMEs."""
    def block(path):
        m = re.search(r"```json\n(.*?)\n```", path.read_text(encoding="utf-8"), re.S)
        return json.loads(m.group(1)) if m else None
    assert block(ROOT / "README.el.md") == block(ROOT / "README.md")


def test_reports_take_their_languages_from_the_registry():
    for name in ("report.py", "report_flows.py"):
        src = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "i18n.ui_langs()" in src, f"{name} hard-codes a language list"
        assert '"en", "el"' not in src, f"{name} hard-codes a language list"


def test_language_code_migration_is_idempotent():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "migrate_language_codes.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("path", sorted((ROOT / "docs").glob("*.md")),
                         ids=lambda p: p.stem)
def test_documentation_has_a_greek_twin(path):
    if path.name.endswith(".el.md"):
        pytest.skip("this is the twin")
    twin = path.with_name(path.name[:-3] + ".el.md")
    assert twin.exists(), f"{path.name} has no Greek twin"


def test_the_two_migrations_do_not_fight_each_other(tmp_path):
    """Reordering a source file must not drop the language code another migration wrote.

    Measured: the independence migration rebuilt files from a canonical key order
    that predated `language_iso639_2b` and silently deleted the field, so
    `--check` reported drift on every file right after the language migration
    reported it clean.
    """
    import shutil
    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    for script in ("migrate_sources_v2.py", "migrate_language_codes.py"):
        r = subprocess.run([sys.executable, str(repo / "scripts" / script)],
                           capture_output=True, text=True)
        assert r.returncode == 0, f"{script}: {r.stdout}{r.stderr}"
    for script in ("migrate_sources_v2.py", "migrate_language_codes.py"):
        r = subprocess.run([sys.executable, str(repo / "scripts" / script), "--check"],
                           capture_output=True, text=True)
        assert r.returncode == 0, f"{script} --check after the other migration: {r.stdout}"
