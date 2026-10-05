#!/usr/bin/env python3
"""Generate bilingual report for migration flows."""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n
from i18n import t  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FLOWS = ROOT / "data" / "flows"
REPORTS = ROOT / "reports"


def fmt(n: int | None, lang: str) -> str:
    if n is None:
        return t(lang, "report.no_data")
    sep = "." if lang == "el" else ","
    return f"{n:,}".replace(",", sep)


def label(lang: str, prefix: str, value: str) -> str:
    """Translate an enum value, falling back to the raw value when no key exists."""
    if not value:
        return ""
    key = f"{prefix}.{value}"
    text = t(lang, key)
    return text if text != key else value


def render(lang: str) -> str:
    lines: list[str] = [f"# {t(lang, 'flow.title')}", ""]
    lines.append(f"*{t(lang, 'report.generated')}: {date.today().isoformat()}*")
    lines.append("")
    lines.append(
        f"| {t(lang, 'flow.columns.direction')} "
        f"| {t(lang, 'flow.columns.year')} "
        f"| {t(lang, 'flow.columns.count')} "
        f"| {t(lang, 'flow.columns.citizenship')} "
        f"| {t(lang, 'flow.columns.education')} "
        f"| {t(lang, 'report.columns.source')} |"
    )
    lines.append("|---|---|---|---|---|---|")

    for f in sorted(FLOWS.rglob("*.yaml")):
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        direction = doc["direction"]
        dir_label = t(lang, f"flow.direction.{direction}")
        for rec in doc["records"]:
            year = str(rec["year"])
            if rec.get("period_end"):
                year = f"{year}–{rec['period_end']}"
            lines.append(
                f"| {dir_label} | {year} | {fmt(rec['count'], lang)} "
                f"| {label(lang, 'citizenship', rec.get('citizenship', ''))} "
                f"| {label(lang, 'education', rec.get('education', ''))} "
                f"| `{rec['source_ref']}` |"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    for lang in i18n.ui_langs():
        text = render(lang)
        out = REPORTS / f"flows.{i18n.report_suffix(lang)}.md"
        out.write_text(text, encoding="utf-8")
        print(f"✓ Wrote {out}")


if __name__ == "__main__":
    main()
