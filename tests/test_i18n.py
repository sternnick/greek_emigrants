"""i18n keys must match across languages."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_keys_match():
    en = json.loads((ROOT / "i18n" / "en.json").read_text(encoding="utf-8"))
    el = json.loads((ROOT / "i18n" / "el.json").read_text(encoding="utf-8"))
    assert set(en.keys()) == set(el.keys()), (set(en) ^ set(el))
