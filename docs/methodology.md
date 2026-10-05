# Methodology

[🇬🇷 Ελληνικά](methodology.el.md)

## What we count

Every record has a `definition`:

- `greek-citizens` — hold Greek nationality. Most reliable (registers, censuses).
- `greek-ethnic` — self-identified Greek ethnicity.
- `greek-origin` — ancestry of any generation (census "ancestry" question).
- `greek-language` — speak Greek at home.

**Never mix definitions in one record.**

## Source classification

- `confirmed` — official censuses, national registers, Eurostat, UN, OECD, IOM.
- `hypothetical` — community estimates, media, academic extrapolations, self-reports.

A country file must include a `confirmed` record if one exists.

## Why the two numbers differ

An ancestry count can be 5–10× a nationality count. A nationality count can
miss 2nd/3rd generation descendants. Both are shown side by side, never merged.
