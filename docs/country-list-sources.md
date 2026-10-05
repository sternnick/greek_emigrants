# Country List Sources

[🇬🇷 Ελληνικά](country-list-sources.el.md)

The dataset covers every sovereign state, so the country list itself is a
source with provenance — not an act of memory.

## Cross-check sources: probed 2026-10-05, both dropped

| source | probe | verdict |
|---|---|---|
| `mytravelmaps.org` | robots.txt `Allow: /`; `/` → 200, 51,432 B; `/countries-visited-map` → 200, 13,364 B. Both responses are Next.js shells (11 `_next/static/chunks/*` references, 0 `<tr>`, **zero country names anywhere in the HTML**) | **dropped — JS-rendered** |
| `guessthecountry.org` | robots.txt `Allow: /`, `Disallow: /api/ /admin/`; `/` → 200, 13,623 B (game page, no country list); `/countries/` → **404**; `sitemap.xml` lists 17 URLs, all blog posts + the root | **dropped — publishes no country list** |

Both were kept as candidates because earlier probes suggested plain HTML tables;
measured again with the real fetch, neither serves its list without JavaScript.
A cross-check that needs a browser is not a cross-check, so the list is built
from primary code authorities instead.

## What the list is built from

| column | source | fetched |
|---|---|---|
| codes, subregions, continent | UN M49 country-code table, `unstats.un.org/unsd/methodology/m49/overview/` (robots allows it; the English table is the first of six) | 2026-10-05 |
| `iso_name_en`, `name_en` | ISO 3166-1 names via the `iso-codes` package | local |
| `name_el` | the ISO 3166-1 Greek locale catalog (248/249 translated) — the "CLDR if available, else static mapping" fallback, bundled so builds never depend on this machine | local |

`scripts/build_country_list.py` regenerates `data/lists/country-list.csv` from
these and **refuses to write** unless the count is exactly 195 sovereign states
and no slug collides. 247 M49 entries remain after dropping Antarctica (a
continent, not a country); 52 are dependencies with the reason recorded in the
`note` column of the CSV, so nothing is silently deleted — it is just not
scaffolded.

## The one judgement call: the Americas

M49 puts Mexico, Central America and the Caribbean in a *socio-economic* group
called "Latin America and the Caribbean", which is not a continent. Since this
repo's field is `continent`, the Americas are split geographically at the Isthmus
of Panama: M49 intermediate regions Northern America (021), Central America
(013) and Caribbean (029) → `north-america`; South America (005) →
`south-america`. Result: 23 / 12. Set `SPLIT_AT_ISTHMUS = False` in
`scripts/build_country_list.py` and re-run to get literal M49 subregions (2 / 33).

## Verification: 10 random countries against the M49 table

| country | ISO | M49 | assigned |
|---|---|---|---|
| Angola | `AO` | Africa / Sub-Saharan Africa (inter. 017) | africa |
| Argentina | `AR` | Americas / Latin America and the Caribbean (inter. 005) | south-america |
| Burkina Faso | `BF` | Africa / Sub-Saharan Africa (inter. 011) | africa |
| Czechia | `CZ` | Europe / Eastern Europe | europe |
| Guatemala | `GT` | Americas / Latin America and the Caribbean (inter. 013) | north-america |
| Laos | `LA` | Asia / South-eastern Asia | asia |
| Poland | `PL` | Europe / Eastern Europe | europe |
| Syria | `SY` | Asia / Western Asia | asia |
| Tunisia | `TN` | Africa / Northern Africa | africa |
| Zimbabwe | `ZW` | Africa / Sub-Saharan Africa (inter. 014) | africa |

All ten agree. The Caribbean assignment (Guatemala-like cases) is the documented
isthmus rule above, not an error.

## The `status` field

| status | meaning | records |
|---|---|---|
| `stub` | scaffolded placeholder, nothing researched | `[]` (the only case where empty is legal) |
| `partial` | confirmed figures only | ≥ 1 |
| `complete` | confirmed and hypothetical both present | ≥ 1 |
| `disputed` | sources disagree on material facts (takes precedence over `complete`) | ≥ 1 |

`status` is required on every country file; `validate.py` rejects a `stub` that
carries records, a `complete` missing either classification, and a `disputed`
with no `status: disputed` record inside it. A `stub` is a place to fill in —
it is not a claim, and the report counts them separately instead of printing
189 rows of dashes.
