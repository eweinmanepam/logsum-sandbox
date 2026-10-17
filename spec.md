# logsum-sandbox specification

## Goal

Summarize synthetic event records into deterministic counts of normalized event groups. Each valid input data row represents one event.

## Inputs

- Read comma-delimited CSV with double-quote field quoting, encoded as UTF-8 without a BOM, from `--input`; default: `data/events.csv`.
- The header must contain the case-sensitive columns `timestamp`, `level`, `service`, and `message`, in any order. Extra columns are ignored; duplicate header names are invalid.
- Every nonblank parsed data record must have the same number of fields as the header. Blank records outside quoted fields are ignored.
- `timestamp` must be `YYYY-MM-DDTHH:MM:SS[.fraction](Z|±HH:MM)`. Seconds and an explicit timezone are required; the optional fraction has 1–6 digits.
- Runtime code uses the Python 3.11 standard library only. Use `ruff` and `pytest` for development checks when available; do not install them without asking.

## Outputs

- Write comma-delimited CSV with double-quote field quoting, encoded as UTF-8 without a BOM, to `--output`; default: `summary.csv`.
- Columns, in order: `level,service,message,count,first_seen,last_seen`.
- Write one row per group, sorted lexicographically ascending by the tuple `(normalized level, normalized service, normalized message)` using Python string ordering.
- Write a header even when there are no event rows. On successful processing, write no status text to stdout.
- Stage the complete output beside the destination and replace the destination only after the input is fully valid. A failure before replacement leaves any existing output unchanged. Never write over the input file.

## Normalisation rules

- Parse timestamps with their explicit timezone and convert them to UTC.
- Trim surrounding Unicode whitespace from `level`, then uppercase it. A blank level becomes `UNKNOWN`; other values are unrestricted.
- Trim surrounding Unicode whitespace from `service`, then apply Unicode case folding. A blank service remains empty.
- For `message`, trim surrounding Unicode whitespace and replace each run of Unicode whitespace with one ASCII space. Preserve case; a blank message remains empty.
- These normalized `level`, `service`, and `message` values are written to the summary and used for grouping.

## Grouping rule

The exact group key is `(normalized level, normalized service, normalized message)`. Timestamp is not part of the key. Grouping is exact after the normalization above; there is no fuzzy matching or removal of IDs or other message content.

## Aggregation

- `count` is the number of input rows in the group; duplicate rows count separately.
- `first_seen` is the earliest parsed timestamp in the group; `last_seen` is the latest. Both are UTC in `YYYY-MM-DDTHH:MM:SS[.ffffff]Z` form; include six fractional digits only when the fraction is nonzero.

## Edge cases

- A blank or whitespace-only `level` is valid and normalizes to `UNKNOWN`.
- Blank `timestamp`, a timestamp outside the accepted format, or an invalid calendar/time value is fatal. Report the 1-based CSV record number (the header is record 1), exit 1, and leave any existing output unchanged.
- A header-only file is valid and produces a header-only summary with exit 0. A zero-byte file is invalid because it has no header.
- A missing or unreadable input, missing required header, duplicate header, malformed CSV, or wrong-width record is an input error: report it to stderr, exit 1, and leave output unchanged.
- Blank `service` and `message` values are valid and group according to their normalized values.
- If input and output resolve to the same file, fail with exit 1 without changing it. Do not create a missing output parent directory; that is an output error.

## CLI

- Invocation: `logsum-sandbox [--input PATH] [--output PATH]`.
- Omitted flags use the defaults in Inputs and Outputs. Paths are interpreted relative to the current working directory.
- `--help` prints usage and exits 0. Invalid arguments print usage to stderr and exit 2.
- Successful processing, including header-only input, exits 0. Input, timestamp, or output failures print a diagnostic to stderr and exit 1.

## Out of scope

- Production or client data, network access, databases, JSON, stdin/stdout streaming, time-window grouping, fuzzy matching, and message redaction.
- Adding runtime or development dependencies without asking first.
- Changing or inferring event fields beyond the four required input columns.

## Signed off — Eben Weinman, 2026-10-17

## Implementation notes

The requested `python -m src.logsum INPUT OUTPUT` form uses positional paths. The module accepts that pair as a shorthand while retaining `--input` and `--output`; the two forms are mutually exclusive.
