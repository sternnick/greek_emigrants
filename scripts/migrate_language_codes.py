#!/usr/bin/env python3
"""Add the ISO 639-2/B code beside every source file's ISO 639-1 language tag.

COAR multilingual compliance wants a bibliographic code a repository can publish;
`language` stays the two-letter code the report and quote rules use, and
`language_iso639_2b` is written next to it from the same registry, so the two can
never drift apart by hand.

  python scripts/migrate_language_codes.py            # fill missing/incorrect codes
  python scripts/migrate_language_codes.py --check    # report drift, write nothing
"""
from __future__ import annotations
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from i18n import to_iso639_2b  # noqa: E402


def files():
    for cls in ("confirmed", "hypothetical", "derived"):
        yield from sorted((ROOT / "sources" / cls).glob("*.yaml"))


def main() -> int:
    check = "--check" in sys.argv
    drift: list[Path] = []
    for f in files():
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        want = to_iso639_2b(doc.get("language", ""))
        if want is None:
            print(f"? {f}: unknown language '{doc.get('language')}'", file=sys.stderr)
            return 2
        if doc.get("language_iso639_2b") != want:
            drift.append(f)
            if not check:
                ordered = {}
                for k, v in doc.items():
                    ordered[k] = v
                    if k == "language":
                        ordered["language_iso639_2b"] = want
                if "language" not in ordered:
                    ordered["language"] = doc.get("language")
                    ordered["language_iso639_2b"] = want
                f.write_text(yaml.safe_dump(ordered, allow_unicode=True,
                                            sort_keys=False, width=100), encoding="utf-8")
                print(f"✓ {f}: language_iso639_2b = {want}")
    if check:
        if drift:
            print("DRIFT " + ", ".join(str(d) for d in drift))
            print(f"{len(drift)} source file(s) need the ISO 639-2/B code.")
            return 1
        print("✓ language codes v2 (no drift)")
        return 0
    print(f"{'fixed ' if drift else 'ok    '}{len(drift)} source file(s) touched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
