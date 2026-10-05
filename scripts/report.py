#!/usr/bin/env python3
"""Generate bilingual Markdown summaries from worldwide.yaml."""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n import t  # noqa: E402

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
    totals = doc["totals_by_definition"]

    lines: list[str] = []
    lines.append(f"# {t(lang, 'report.title')}")
    lines.append("")
    lines.append(f"*{t(lang, 'report.generated')}: {date.today().isoformat()}*")
    lines.append("")

    # Totals by definition
    lines.append(f"## {t(lang, 'report.totals')}")
    lines.append("")
    for cls in ("confirmed", "hypothetical"):
        cls_label = t(lang, f"classification.{cls}")
        lines.append(f"### {cls_label}")
        lines.append("")
        items = totals.get(cls, {})
        if not items:
            lines.append(f"- {t(lang, 'report.no_data')}")
        for definition, count in sorted(items.items()):
            def_label = t(lang, f"definition.{definition}")
            lines.append(f"- **{def_label}**: {fmt(count, lang)}")
        lines.append("")

    # Coverage by status
    by_status = doc.get("totals_by_status", {})
    lines.append(f"## {t(lang, 'report.status_summary')}")
    lines.append("")
    lines.append(f"| {t(lang, 'report.status')} | {t(lang, 'report.countries')} |")
    lines.append("|---|---|")
    for st in ("stub", "partial", "complete", "disputed"):
        if by_status.get(st):
            lines.append(f"| {t(lang, f'status.{st}')} | {by_status[st]} |")
    lines.append(f"| **{t(lang, 'report.total')}** | **{sum(by_status.values())}** |")
    if by_status.get("stub"):
        lines.append("")
        lines.append(
            f"_{t(lang, 'report.stub_note').replace('{n}', fmt(by_status['stub'], lang))}_"
        )
    lines.append("")

    # Main table
    lines.append(f"## {t(lang, 'report.columns.country')}")
    lines.append("")
    lines.append(
        f"| {t(lang, 'report.columns.continent')} "
        f"| {t(lang, 'report.columns.country')} "
        f"| {t(lang, 'report.columns.confirmed')} "
        f"| {t(lang, 'report.columns.year')} "
        f"| {t(lang, 'report.columns.definition')} "
        f"| {t(lang, 'report.columns.hypothetical')} "
        f"| {t(lang, 'report.columns.year')} "
        f"| {t(lang, 'report.columns.definition')} "
        f"| {t(lang, 'report.columns.source')} |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")

    for cont_id in sorted(continents):
        cont = continents[cont_id]
        cont_label = t(lang, f"continent.{cont_id}")
        for c in sorted(cont["countries"], key=lambda x: x["id"]):
            conf = c["confirmed"]
            hyp = c["hypothetical"]
            if not conf and not hyp:
                # status: stub — scaffolded placeholder, nothing to report
                continue
            conf_cell = fmt(conf["count"], lang) if conf else t(lang, "report.no_data")
            conf_year = str(conf["year"]) if conf else ""
            conf_def = t(lang, f"definition.{conf['definition']}") if conf else ""
            hyp_cell = fmt(hyp["count"], lang) if hyp else t(lang, "report.no_data")
            hyp_year = str(hyp["year"]) if hyp else ""
            hyp_def = t(lang, f"definition.{hyp['definition']}") if hyp else ""
            src = conf["source_ref"] if conf else (hyp["source_ref"] if hyp else "")
            lines.append(
                f"| {cont_label} | {c['name'][lang]} "
                f"| {conf_cell} | {conf_year} | {conf_def} "
                f"| {hyp_cell} | {hyp_year} | {hyp_def} "
                f"| `{src}` |"
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
