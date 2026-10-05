# Contributing

[🇬🇷 Ελληνικά](CONTRIBUTING.el.md)

## Adding a country

1. Create `data/countries/<continent>/<country>.yaml` using the schema in `schemas/country.schema.json`.
2. Add at least one `confirmed` source in `sources/confirmed/`.
3. Optionally add `hypothetical` sources in `sources/hypothetical/`.
4. Register the country id in the matching `data/continents/<continent>.yaml`.
5. Run `python scripts/validate.py` — it must pass.

## Validation gate

The fast checks run in a commit hook; enable it once per clone:

```bash
git config core.hooksPath .githooks
```

It runs `validate.py` plus the two migration `--check`s (independence blocks and
ISO 639 language codes), so a file cannot drift from what the generator scripts
would write. The full suite is explicit: `python -m pytest tests/ -q`.

## Adding a source

1. Pick folder: `sources/confirmed/` or `sources/hypothetical/`.
2. Filename pattern: `<publisher-slug>-<country>-<year>.yaml`
3. Fill all fields. `url` must be a real link or `TODO` (validation warns).
4. `retrieved_at` in ISO format.

## Rules

- Never invent a number. If unknown, `count: null`.
- Never merge two `definition` values into one record.
- Never use Greek characters in ids, keys or filenames.
- Bilingual text is mandatory: `{el, en}`.
