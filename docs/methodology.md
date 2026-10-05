# Methodology

[🇬🇷 Ελληνικά](methodology.el.md)

## What we count

Every record has a `definition`:

- `greek-citizens` — hold Greek nationality. Most reliable (registers, censuses).
- `greek-born` — born in Greece, whatever their nationality now (census country-of-birth tables; this is what the OECD reports).
- `greek-ethnic` — self-identified Greek ethnicity.
- `greek-origin` — ancestry of any generation (census "ancestry" question).
- `greek-language` — speak Greek at home.

**Never mix definitions in one record.**

## Coverage of countries

Every country file carries a `status` (`stub`, `partial`, `complete`,
`disputed`): a `stub` is a scaffolded placeholder with `records: []`, not a
claim. How the country list itself is built and cross-checked:
[country-list-sources.md](country-list-sources.md).

## Source classification

- `confirmed` — official censuses, national registers, Eurostat, UN, OECD, IOM.
- `hypothetical` — community estimates, media, academic extrapolations, self-reports.

A country file must include a `confirmed` record if one exists.

## Why the two numbers differ

An ancestry count can be 5–10× a nationality count. A nationality count can
miss 2nd/3rd generation descendants. Both are shown side by side, never merged.
