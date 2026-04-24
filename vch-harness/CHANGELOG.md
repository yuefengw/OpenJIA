# Changelog

All notable project changes and verification results should be recorded here after each implementation pass.

## 2026-04-24

### Added

- Added article-derived harness design principles in `docs/HARNESS_DESIGN_PRINCIPLES.md`.
- Added end-to-end execution plan in `docs/END_TO_END_EXECUTION_PLAN.md`.
- Added `.env`, `.env.example`, `.gitignore`, and `python-dotenv` loading for safe local API configuration.
- Added MiniMax/OpenAI-compatible LLM backend and `vch llm-smoke`.
- Added feature ledger and progress artifacts.
- Added project bootstrapper for simple static web tasks.
- Added guarded filesystem writes.
- Added deterministic Todo/web generator path.
- Added LLM generator structured file-output path.
- Added Playwright E2E generation and evaluator evidence collection.
- Added README architecture diagram and project usage documentation.

### Changed

- Planner fallback now emits a usable feature/sprint/AC plan instead of an empty spec.
- Generator now writes real files and command-backed self-verification reports.
- Evaluator now records real command observations and test artifacts.
- MiniMax default base URL changed to `https://api.minimaxi.com/v1`.

### Verified

- `pytest -q` passed: 68 tests.
- `python -m compileall src tests` passed.
- `vch llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.
- End-to-end Todo run passed with Playwright browser verification.

### Documentation Pass

- Replaced README with project overview, Mermaid architecture diagram, setup, secrets, usage, current capabilities, and limits.
- Added this changelog as the required update log for future implementation passes.
- Re-ran verification after documentation changes:
  - `pytest -q` passed: 68 tests.
  - `python -m compileall src tests` passed.
  - `vch llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.
