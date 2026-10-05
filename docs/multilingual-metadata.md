# Multilingual Metadata (COAR)

[🇬🇷 Ελληνικά](multilingual-metadata.el.md)

COAR's recommendations for repositories managing multilingual and non-English
content ([source page](https://coar-repositories.org/what-we-do/multilingual-and-non-english-content/),
accessed 2026-10-05) ask a repository to:

> Declare the language of the resource at the item level · Declare the language of
> the metadata (e.g. `xml:lang`) · Use standard (two-letter or three-letter)
> language codes (ISO 639) · Enable UTF-8 support and use the original alphabet /
> the writing system whenever possible · If it is necessary to transliterate
> metadata, use recognized standards · Include keywords in many languages ·
> Ensure that language codes can consistently be used across the repository
> collection.

Here is how each of those is met, and where the enforcement lives.

## Where the codes live

| need | field | code system | enforced by |
|---|---|---|---|
| a source's own language | `language` (source file) | ISO 639-1 | `source.schema.json` + `check_language_codes()` |
| the same language for repository metadata | `language_iso639_2b` | ISO 639-2/B | same check — the pair must agree |
| the language a quote is written in | `evidence[].quote_language` | ISO 639-1 or -2/B | `check_quote_languages()` |
| the dataset's languages | README metadata block, `i18n/languages.json` | both | `tests/test_coar.py` |
| a human-readable field | `{el, en}` object | keys *are* the tags | `check_bilingual_fields()` |

`i18n/languages.json` is the only place a code pair is written. Nothing else in
the repo carries a language table, so a source cannot claim `el`/`fra`.

**Why two systems.** ISO 639-1 is what humans and file names use (`summary.el.md`);
ISO 639-2/B is the bibliographic code repository software and OAI-PMH expose. The
`language` field feeds reports and the quote rules; `language_iso639_2b` feeds
repository metadata. `scripts/i18n.py` converts in both directions
(`to_iso639_2b`, `to_iso639_1`), and `scripts/migrate_language_codes.py` writes
the -2/B code from the -1 code so they cannot drift apart by hand.

## Original script, not transliteration

Quotes are stored **in the alphabet of the source**: an ONS table in English, an
INSTAT table in English, a Destatis table in German (`quote_language: de`), a
government statement in Greek. No transliteration happens anywhere in the data —
the only ASCII in a Greek sentence is the technical tokens (`source_ref`, `null`).
A machine-readable string must be ASCII to be greppable and stable in diffs; that
is why IDs, enums and file names are English (AGENTS.md), while everything a
person reads, and every quote, keeps its own script.

## COAR recommendation → implementation

| recommendation | this dataset |
|---|---|
| declare the language of each resource | every `sources/**/*.yaml` has `language` **and** `language_iso639_2b`; every quote has `quote_language` |
| declare the language of the metadata | the README metadata block declares `inLanguage: ["eng","ell"]`; bilingual fields are keyed by language rather than relying on an attribute |
| use standard ISO 639 codes | both systems, from one registry, validated at commit time |
| UTF-8 + original alphabet | every file UTF-8; quotes in original script (Greek quotes stay in Greek) |
| transliterate only with standards | we do not transliterate text; only identifiers are ASCII, by convention, and that convention is documented here |
| keywords in many languages | the metadata block carries `keywords` in `en` and `el` |
| consistent codes across the collection | `validate.py` fails on an unregistered code or a mismatched pair; `migrate_language_codes.py --check` proves no file drifted |

## Adding a language

Four steps, and the tests tell you if you missed one:

1. `i18n/languages.json` — one entry: `iso639_1`, `iso639_2b`, `name_native`,
   `name_en`, `direction`, `script`, `report_suffix`, `ui`.
2. `i18n/<code>.json` — UI strings, the same key set as the others
   (`tests/test_i18n.py` compares key sets, not counts).
3. `i18n/<code>.md` — the static legal/methodology text.
4. Every bilingual `{…}` field gains the new key. There is no migration script
   for this step and none is pretended: the validator refuses any bilingual field
   that misses a key (`check_bilingual_fields()`), so the missing ones are listed
   file by file until they are filled. `python scripts/validate.py` is the tool.

Reports pick the language up automatically: `scripts/report.py` and
`scripts/report_flows.py` iterate `i18n.ui_langs()` and name files through
`i18n.report_suffix()`, so no report script hard-codes a language list.

The migrations that do exist are `scripts/migrate_sources_v2.py` (independence and
publication blocks) and `scripts/migrate_language_codes.py` (the ISO 639-2/B code);
both take `--check` and are run from the pre-commit hook.
