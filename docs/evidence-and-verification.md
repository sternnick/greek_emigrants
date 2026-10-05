# Evidence & Verification

[🇬🇷 Ελληνικά](evidence-and-verification.el.md)

Every record carries an **evidence chain** and a **verification block**. The
rule that drives both: *no number without evidence — if the page or table that
produced a number cannot be located, the count is `null` with a note.*

## The citation chain

```
record (a number)
 └─ source_ref            → sources/<classification>/<id>.yaml  (who published it)
     └─ independence       → did they collect the raw data, or re-publish others'?
         └─ derives_from    → the upstream source ids (transitive)
 └─ evidence[]             → one citation per consulted edition of the source
     ├─ url                 canonical, https where possible
     ├─ archive_url         web.archive.org snapshot (required for media,
     │                      recommended for government pages that rotate)
     ├─ accessed_at         when we read it
     ├─ published_at        when THEY published the figure
     ├─ page_or_table       "Table 4.2", "row Greece, column 2022", "p. 75"
     ├─ quote               ≤ 500 chars, VERBATIM, in the original language
     └─ quote_language      ISO 639-1 of the quote
```

**Quote convention.** `quote` is an `{el,en}` object because every human field
in this repo is bilingual — but quotes are never translated. The verbatim
original string is placed in BOTH `el` and `en` slots and `quote_language`
records the real language. Translation belongs in `notes`.

**Updated sources are new evidence entries.** If a source publishes a new
edition, append another `evidence[]` item (with its own `published_at`); never
overwrite. The evidence list is a time series, by design.

**Dead pages.** If the live page is gone, `url` keeps the original address and
`archive_url` gets the snapshot. No snapshot and no reachable page →
`count: null` and a `dispute_note` describing the search trail.

## What "independent" means

Two sources are independent **iff neither lists the other in `derives_from`
(transitively)**. A news article quoting a ministry is NOT independent from
that ministry. Eurostat/OECD/UN tables that state "based on national
statistics" are NOT independent from the national offices — they carry
`primary_data_collector: false` and their upstream ids in `derives_from`.
Wikipedia is never a primary source: cite what its footnotes cite.

`validate.py` enforces:

- `independent_sources = len(corroborating_refs) + 1` if the record's primary
  source has `primary_data_collector: true` (else `+ 0`);
- `confidence` must match the count: **1 → `single-source`, 2 →
  `corroborated`, ≥3 → `well-established`** (0 is labelled `single-source` —
  it is still one unsourced claim, honestly marked);
- every `derives_from` id must exist and the graph must be acyclic;
- every `evidence[].source_ref` must be either the record's `source_ref` or a
  `verification.corroborating_refs` entry;
- `evidence[].url` must be https (http is a warning).

Warnings (not errors): missing `archive_url`, missing `published_at`, missing
`quote` — things we must fix, but that must not block a commit that documents
the gap in a note.

## Worked examples

### 1. Confirmed, ×3 — well-established *(pattern, not yet in the data)*

A future record on Greeks in Germany cites `destatis-de-2022`
(`primary_data_collector: true`) and adds to `corroborating_refs` two sources
that are NOT derived from Destatis (e.g. a Labour Force Survey microsample and
the Central Register of Foreigners annual report, each collected independently).
`independent_sources: 3`, `confidence: well-established`. Note what does NOT
count: adding a Eurostat table that says "based on national statistics" —
it would sit in `derives_from: [destatis-de-2022]` and add 0 independence.

### 2. Confirmed, ×1 — single-source *(real: Albania)*

`al-2023-census-minority`, count 23,485, cites `instat-al-2023`
(`primary_data_collector: true`) with a verbatim quote from the census PDF
(Table 14): `Greke | Greek 23 485 12 063 11 422`, `published_at: 2024-06-28`.
No independent peer → `independent_sources: 1`, `confidence: single-source`.
Honest and sufficient — official, traceable, alone.

### 3. Hypothetical — community estimate *(real: Albania, Omonoia)*

`al-2013-omonoia-census`, count 287,000 — a self-report by a minority
organisation; the original press carrier now returns 410. The record keeps the
number (the organisation did publish it), states the chain in notes, quotes the
carrier text, and is labelled `single-source`, `reliability: low`. It is never
merged with the census figure.

## When sources disagree

List both. Never average. The record gets a `dispute_note` (bilingual) that
states each value, where each was published, and what the owner must decide.
A record whose own figure cannot be found in its cited page keeps its count
only if at least one published value is quotable — otherwise `count: null`
with the same style of note. Nulling a count is not deleting the record: the
record, its definition, and its search trail stay in the file.
