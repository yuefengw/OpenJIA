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

### Context And Evaluation Self-Check

- Added `GeneratorPacketBuilder` to create auditable, minimal generator context packets.
- Generator packets include contract, context manifest, allowed file contents, must/may read lists, forbidden context, and optional repair packet.
- Added `EvaluationEvidenceCollector` to persist command records, command logs, git diff data, self-verify report, changeset, and Playwright/test artifacts into `EVIDENCE_PACKET.json`.
- Added `AcceptanceCoverageGate` to prevent false pass when AC results are missing, failing, lacking evidence, lacking concrete observations, command logs, or diff-scope pass.
- Wired generator packet creation, evidence collection, and acceptance coverage into `HarnessOrchestrator`.
- Added unit coverage for generator packet boundaries, evidence collection, and acceptance coverage gate behavior.
- Re-ran verification:
  - `pytest -q` passed: 72 tests.
  - `python -m compileall src tests` passed.
  - `vch llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.

### Three-Layer Prompt Architecture

- Added `src/vch/prompts/common_protocol.md` as the shared VCH protocol layer for all role prompts.
- Rewrote planner, generator, and evaluator prompts into:
  - Layer 1: universal VCH protocol.
  - Layer 2: role methodology.
  - Layer 3: output contract.
- Added `src/vch/prompts/loader.py` so role prompt loading automatically prepends the common protocol.
- Wired Planner and Generator to the shared prompt loader.
- Added tests proving core role prompts include all three layers.
- Fixed the generated zero-dependency browser E2E script to connect to the page-level Chrome DevTools Protocol websocket.
- Re-ran verification:
  - `pytest -q` passed: 74 tests.
  - In-memory Python source compilation passed for 61 files. `compileall` was avoided because locked Windows `__pycache__` files prevented `.pyc` writes.
  - `vch llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.
