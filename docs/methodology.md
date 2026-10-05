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

## Net figures

`net = returns − departures`. It is never measured by anyone: it is arithmetic
over two flow records, so it lives in `data/flows/<country>/net.yaml` with
`computed: true` and `direction: net`.

Rules the pipeline enforces:

- Net records are **excluded from every total** — summing them would count each
  flow twice (`scripts/aggregate.py` reads only `outflow.yaml` and
  `return.yaml`; `tests/test_net_flows.py` proves it).
- A net record must name the source that published the components it was
  computed from, so the arithmetic is checkable from the evidence alone.
- Where two carriers disagree (national figures vs OECD), **both** balances are
  kept side by side with a `dispute_note`; the aggregate uses the national pair.
- **Stock and flow cannot be summed.** A diaspora stock (people living abroad in
  a given year) and a flow (people moving in a year) are different quantities
  over different denominators; a net balance explains how a stock changed, it
  never substitutes for one.


## Source classification

- `confirmed` — official censuses, national registers, Eurostat, UN, OECD, IOM.
- `hypothetical` — community estimates, media, academic extrapolations, self-reports.

A country file must include a `confirmed` record if one exists.

## Why the two numbers differ

An ancestry count can be 5–10× a nationality count. A nationality count can
miss 2nd/3rd generation descendants. Both are shown side by side, never merged.
