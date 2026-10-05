# Greek Diaspora Dataset

[🇬🇷 Ελληνικά](README.el.md)

Open dataset of Greeks living permanently abroad, organized by
**continent** → **country** → **record**, with every figure tied to a
**source** and classified as **confirmed** or **hypothetical**.

## Structure

- `data/continents/` — continent index files
- `data/countries/<continent>/<country>.yaml` — one file per country
- `data/lists/country-list.csv` — the bundled country list (regenerate with `scripts/build_country_list.py`)
- `sources/confirmed/` — official censuses, registers, Eurostat, UN, OECD
- `sources/hypothetical/` — community estimates, media, academic extrapolations
- `schemas/` — JSON Schemas for all YAML files
- `i18n/` — translations for reports and enum labels
- `scripts/` — validate, aggregate, report
- `docs/` — methodology, source classification, glossary

Coverage: **195** sovereign countries — 6 with records, 189 scaffolded as `status: stub`.

## Quick start

```bash
pip install -r requirements.txt
python scripts/scaffold_countries.py --dry-run   # which country files are missing
python scripts/validate.py
python scripts/aggregate.py
python scripts/report.py
```

Outputs:

- `data/aggregate/worldwide.yaml`
- `reports/summary.en.md`
- `reports/summary.el.md`

## Core rules

- Every number has a `source_ref`. No source, no number.
- Every human-readable field is bilingual: `{el: ..., en: ...}`.
- All IDs, enums and file names are English, lowercase, hyphenated.
- `confirmed` and `hypothetical` figures are never mixed into one record.
- Every country carries a `status`: `stub` (placeholder, `records: []`), `partial`, `complete`, `disputed`.
- `definition` (what counts as "Greek") is mandatory per record.

## Definitions

- `greek-citizens` — hold Greek nationality
- `greek-born` — born in Greece (birthplace; what the OECD reports)
- `greek-ethnic` — self-identified Greek ethnicity
- `greek-origin` — ancestry of any generation
- `greek-language` — speak Greek at home

## License

Data: CC BY 4.0. Code: MIT.
