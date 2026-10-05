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

## Repository metadata (COAR)

Machine-readable description of this dataset, following COAR's recommendations for
multilingual and non-English content ([source](https://coar-repositories.org/what-we-do/multilingual-and-non-english-content/),
accessed 2026-10-05). Languages are declared in both ISO 639 systems because COAR
asks for "standard (two-letter or three-letter) language codes".

```json
{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": {
    "en": "Greek Diaspora Dataset",
    "el": "Δεδομένα Ελληνικής Διασποράς"
  },
  "inLanguage": ["eng", "ell"],
  "languages": [
    {
      "iso639_1": "en",
      "iso639_2b": "eng",
      "name_native": "English",
      "role": "dataset language",
      "direction": "ltr",
      "script": "Latn"
    },
    {
      "iso639_1": "el",
      "iso639_2b": "ell",
      "name_native": "Ελληνικά",
      "role": "dataset language",
      "direction": "ltr",
      "script": "Grek"
    }
  ],
  "additionalLanguage": [
    {
      "iso639_1": "de",
      "iso639_2b": "deu",
      "name_native": "Deutsch",
      "role": "language of a quoted source"
    }
  ],
  "keywords": {
    "en": ["Greek diaspora", "emigration", "return migration", "brain drain", "census", "migration statistics"],
    "el": ["ελληνική διασπορά", "μετανάστευση", "επιστροφή μεταναστών", "brain drain", "απογραφή", "μεταναστευτικά στατιστικά"]
  },
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "codeLicense": "MIT",
  "conformsTo": [
    "https://coar-repositories.org/what-we-do/multilingual-and-non-english-content/",
    "https://www.iso.org/standard/22109.html"
  ],
  "isPartOf": "https://github.com/sternnick/greek_emigrants",
  "creativeWorkStatus": "Draft — PRs open",
  "measurementTechnique": "documented secondary analysis of official statistics"
}
```

The same table, for humans:

| language | ISO 639-1 | ISO 639-2/B | native name | script | role here |
|---|---|---|---|---|---|
| English | `en` | `eng` | English | Latn | dataset language |
| Greek | `el` | `ell` | Ελληνικά | Grek | dataset language |
| German | `de` | `deu` | Deutsch | Latn | language of a quoted source |

How each COAR recommendation is met: [docs/multilingual-metadata.md](docs/multilingual-metadata.md).

## License

Data: CC BY 4.0. Code: MIT.
