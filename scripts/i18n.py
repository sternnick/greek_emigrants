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
