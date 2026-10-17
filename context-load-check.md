# Context load check — K 5.W.1

The repository instructions are in root `AGENTS.md` (four sections, 20 lines). Verification used a newly started, ephemeral Codex CLI session with this repository as its working root. The probe did not ask the session to open the file.

## Fresh-session probe

Prompt: list the four instruction headings, state the allowed data source, and state the minimum Python version.

## Result

Passed on 2026-10-17. Session `01a14bac-dbaa-7783-8e2f-c8c1239d18f4` returned: Project context; Conventions; Utilities to prefer; Escalation gates; synthetic data only; Python 3.11. This confirms the fresh session loaded the repository context.
