# CI notes

## Gate

`.github/workflows/ci.yml` runs on pushes to `main` and pull requests with Python 3.11. It installs `ruff` and `pytest`, then runs `ruff check .` and `pytest -v`.

## Input test evidence

The K 5.W.4 fallback test-state note reports independently authored tests, an initial missing-level failure, and a fix that kept the test intact. `test-notes.md` records the local suite result as 42 passed with Python 3.12.10 and pytest 9.1.1. That is local evidence, not a GitHub Actions result.

## GitHub Actions result

Repository: https://github.com/eweinmanepam/logsum-sandbox

PR and Actions result: pending. The initial PR revision will expose the missing-level regression in the implementation. The expected correction restores the `UNKNOWN` fallback without changing the tests. Record the PR URL and both Actions run results here after the failing run and the corrected run complete.