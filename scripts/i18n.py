"""Translation loader and helper."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N_DIR = ROOT / "i18n"

_CACHE: dict[str, dict] = {}


def load(lang: str) -> dict:
    if lang not in _CACHE:
        path = I18N_DIR / f"{lang}.json"
        _CACHE[lang] = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE[lang]


def t(lang: str, key: str, **kwargs) -> str:
    strings = load(lang)
    template = strings.get(key, key)
    return template.format(**kwargs) if kwargs else template


def bilingual(value: dict, lang: str) -> str:
    """Return the {el,en} field for a given lang, raising if missing."""
    if not isinstance(value, dict) or lang not in value:
        raise ValueError(f"Missing translation for '{lang}' in {value!r}")
    return value[lang]


REGISTRY: dict | None = None


def registry() -> dict:
    """The language-neutral registry (i18n/languages.json)."""
    global REGISTRY
    if REGISTRY is None:
        REGISTRY = json.loads((I18N_DIR / "languages.json").read_text(encoding="utf-8"))["languages"]
    return REGISTRY


def codes() -> dict[str, dict]:
    return registry()


def to_iso639_2b(iso639_1: str) -> str | None:
    for meta in registry().values():
        if meta["iso639_1"] == iso639_1:
            return meta["iso639_2b"]
    return None


def to_iso639_1(iso639_2b: str) -> str | None:
    for meta in registry().values():
        if meta["iso639_2b"] == iso639_2b:
            return meta["iso639_1"]
    return None


def get_lang_name(code: str, in_lang: str = "en") -> str:
    """Native name of a language, given its ISO 639-1 or ISO 639-2/B code."""
    for meta in registry().values():
        if code in (meta["iso639_1"], meta["iso639_2b"]):
            return meta["name_native"] if in_lang == meta["iso639_1"] else meta["name_en"]
    return code


def get_lang_metadata(code: str) -> dict | None:
    for meta in registry().values():
        if code in (meta["iso639_1"], meta["iso639_2b"]):
            return meta
    return None


def report_suffix(lang: str) -> str:
    meta = get_lang_metadata(lang)
    return meta["report_suffix"] if meta else lang


def ui_langs() -> list[str]:
    """The dataset's own languages — the ones every bilingual field must cover."""
    return [m["iso639_1"] for m in registry().values() if m.get("ui")]
