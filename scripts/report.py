#!/usr/bin/env python3
"""Generate bilingual Markdown summaries from worldwide.yaml."""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n import t, load as load_i18n  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORLDWIDE = ROOT / "data" / "aggregate" / "worldwide.yaml"
REPORTS = ROOT / "reports"


def fmt(n: int | None, lang: str) -> str:
    if n is None:
        return t(lang, "report.no_data")
    sep = "." if lang == "el" else ","
    return f"{n:,}".replace(",", sep)


def render(lang: str, doc: dict) -> str:
    continents = doc["continents"]
    totals = doc["totals"]

    lines: list[str] = []
    lines.append(f"# {t(lang, 'report.title')}")
    lines.append("")
    lines.append(f"*{t(lang, 'report.generated')}: {date.today().isoformat()}*")
    lines.append("")
    lines.append(
        f"| {t(lang, 'report.columns.continent')} "
        f"| {t(lang, 'report.columns.country')} "
        f"| {t(lang, 'report.columns.confirmed')} "
        f"| {t(lang, 'report.columns.year')} "
        f"| {t(lang, 'report.columns.hypothetical')} "
        f"| {t(lang, 'report.columns.year')} "
        f"| {t(lang, 'report.columns.source')} |"
    )
    lines.append("|---|---|---|---|---|---|---|")

    for cont_id in sorted(continents):
        cont = continents[cont_id]
        cont_label = t(lang, f"continent.{cont_id}")
        for c in sorted(cont["countries"], key=lambda x: x["id"]):
            conf = c["confirmed"]
            hyp = c["hypothetical"]
            conf_cell = fmt(conf["count"], lang) if conf else t(lang, "report.no_data")
            conf_year = str(conf["year"]) if conf else ""
            hyp_cell = fmt(hyp["count"], lang) if hyp else t(lang, "report.no_data")
            hyp_year = str(hyp["year"]) if hyp else ""
            src = conf["source_ref"] if conf else (hyp["source_ref"] if hyp else "")
            lines.append(
                f"| {cont_label} | {c['name'][lang]} "
                f"| {conf_cell} | {conf_year} "
                f"| {hyp_cell} | {hyp_year} "
                f"| `{src}` |"
            )

    lines.append("")
    lines.append(f"## {t(lang, 'report.totals')}")
    lines.append("")
    lines.append(
        f"- **{t(lang, 'report.columns.confirmed')}**: {fmt(totals['confirmed'], lang)}"
    )
    lines.append(
        f"- **{t(lang, 'report.columns.hypothetical')}**: {fmt(totals['hypothetical'], lang)}"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    with WORLDWIDE.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    REPORTS.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "el"):
        text = render(lang, doc)
        out = REPORTS / f"summary.{lang}.md"
        out.write_text(text, encoding="utf-8")
        print(f"✓ Wrote {out}")


if __name__ == "__main__":
    main()
