# Project context
- `logsum-sandbox` is a small Python CLI that reads synthetic `events.csv` logs and writes a counted summary.
- The kata series builds it through context setup, spec, implementation, independent tests, CI, refactor review, async agent work, code Q&A, and a by-hand vs agent comparison.
- Support Python 3.11 or newer. Use synthetic data only; never use production or client data.

# Conventions
- Keep the CLI deterministic, small, and easy to inspect; follow the current kata spec for behavior.
- Keep sample inputs synthetic and checked in only when useful; do not commit generated output unless a kata requires it.
- Prefer clear names, type hints for public functions, and focused tests for behavior changes.
- Preserve privacy boundaries in examples, logs, fixtures, and documentation.

# Utilities to prefer
- Prefer the Python standard library: `argparse`, `csv`, `pathlib`, `collections.Counter`, and `json` where suitable.
- Use `python -m` entry points and the repository's chosen test and CI commands; avoid unnecessary dependencies.
- Generate fixtures locally from invented values; do not fetch real datasets or identifiers.

# Escalation gates
- Stop and ask before using or importing any production/client data, credentials, or sensitive identifiers.
- Ask before sending data outside this repository, publishing a package/release, or changing repository visibility.
- Ask when a kata spec leaves input schema, output format, or destructive behavior materially ambiguous.
