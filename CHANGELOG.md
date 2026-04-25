# Changelog

All notable project changes and verification results should be recorded here after each implementation pass.

## 2026-04-25

### DeepAgents SDK Runtime

- Added optional `deepagents` and `all` dependency extras.
- Added `DeepAgentsJSONBackend`, which runs role prompts through `deepagents.create_deep_agent(...)`.
- Added MiniMax-backed DeepAgents configuration through `OPENJIA_DEEPAGENTS_PROVIDER=minimax`.
- Added `docs/DEEPAGENTS_SDK_INTEGRATION.md` with integration notes, configuration, current boundary, and next upgrade path.
- Updated Planner and Generator so `--llm-backend deepagents` does not silently use deterministic fallbacks.
- Added Planner schema-repair retry for malformed LLM/DeepAgents structured output.
- Added Planner normalization for web project commands so long-running dev servers are not used as required verification commands.
- Expanded web contract normalization so DeepAgents Generator can edit existing app files under contract scope.
- Normalized DeepAgents virtual `workspace/...` file paths before applying guarded writes.

### Verified

- `openjia llm-smoke --llm-backend deepagents --model MiniMax-M2.7` passed.
- DeepAgents end-to-end Todo run passed without `GENERATOR_ERROR.md` or deterministic generator fallback.
- DeepAgents run self-verification passed `node scripts/validate-app.mjs`, `npm test`, `npm run build`, and `npm run test:e2e`.
- DeepAgents evaluator produced `EVAL_REPORT.json.overall_status == "pass"` and collected `test-results/todo-pass.html` plus `test-results/todo-pass.png`.
- Targeted DeepAgents/Planner tests passed: 6 tests.
- Full `pytest -q` passed: 80 tests.
- `openjia llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.
- Fixed Planner command normalization so natural-language verification notes are not executed as shell commands.
- Fixed browser E2E script to tolerate animated delete flows and report CDP browser exceptions clearly.
- Verified the generated `D:\Project\testOpenJia` app with `npm run build` and `npm run test:e2e`.

### OpenJIA Rename

- Renamed the Python package from `vch` to `openjia`.
- Renamed the console command from `vch` to `openjia`.
- Renamed the project directory from `vch-harness` to `openjia-harness`.
- Promoted OpenJIA project files from the nested harness directory to the repository root.
- Updated imports, prompts, templates, docs, tests, generated app metadata, and localStorage keys to use OpenJIA naming.
- Updated LLM configuration variables from `VCH_LLM_BACKEND` / `VCH_LLM_MODEL` to `OPENJIA_LLM_BACKEND` / `OPENJIA_LLM_MODEL`.
- Updated `.env.example` and the local ignored `.env` variable names without exposing secrets.
- Removed BOM bytes introduced during Windows text rewrites so Python and TOML parsing work normally.

### Verified

- `pip install -e ".[llm]"` passed and installed the `openjia` command.
- `openjia --help` passed and showed the OpenJIA command group.
- `pytest -q` passed: 74 tests.
- In-memory Python source compilation passed for 61 files.
- `openjia llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.

## 2026-04-24

### Added

- Added article-derived harness design principles in `docs/HARNESS_DESIGN_PRINCIPLES.md`.
- Added end-to-end execution plan in `docs/END_TO_END_EXECUTION_PLAN.md`.
- Added `.env`, `.env.example`, `.gitignore`, and `python-dotenv` loading for safe local API configuration.
- Added MiniMax/OpenAI-compatible LLM backend and `openjia llm-smoke`.
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
- `openjia llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.
- End-to-end Todo run passed with Playwright browser verification.

### Documentation Pass

- Replaced README with project overview, Mermaid architecture diagram, setup, secrets, usage, current capabilities, and limits.
- Added this changelog as the required update log for future implementation passes.
- Re-ran verification after documentation changes:
  - `pytest -q` passed: 68 tests.
  - `python -m compileall src tests` passed.
  - `openjia llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.

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
  - `openjia llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.

### Three-Layer Prompt Architecture

- Added `src/openjia/prompts/common_protocol.md` as the shared OpenJIA protocol layer for all role prompts.
- Rewrote planner, generator, and evaluator prompts into:
  - Layer 1: Universal OpenJIA Protocol.
  - Layer 2: role methodology.
  - Layer 3: output contract.
- Added `src/openjia/prompts/loader.py` so role prompt loading automatically prepends the common protocol.
- Wired Planner and Generator to the shared prompt loader.
- Added tests proving core role prompts include all three layers.
- Fixed the generated zero-dependency browser E2E script to connect to the page-level Chrome DevTools Protocol websocket.
- Re-ran verification:
  - `pytest -q` passed: 74 tests.
  - In-memory Python source compilation passed for 61 files. `compileall` was avoided because locked Windows `__pycache__` files prevented `.pyc` writes.
  - `openjia llm-smoke --llm-backend minimax --model MiniMax-M2.7` passed.
