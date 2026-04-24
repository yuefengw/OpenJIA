# End-to-End Execution Plan

Goal: after this harness is fully implemented, a user should be able to type a short task such as:

```bash
vch run "实现一个运行 Todo List 网站" --llm-backend minimax
```

and receive a runnable implementation with traceable planning, scoped generation, command evidence, evaluation, and repair artifacts under `.harness/`.

This plan is intentionally not tied to Todo List. Todo List is the first acceptance fixture because it is small, visual, testable, and representative of common app-building requests.

## Current Reality

What works now:

- `.env` can provide MiniMax API credentials.
- Planner can call MiniMax and produce `FEATURE_SPEC.json`.
- Feature ledger and progress artifacts are written.
- PlanFeasibilityGate, ContractGate, SelfVerifyGate, EvaluationGate, and command logging exist.
- Evaluator can run shell commands and write command evidence.
- Empty simple web tasks can bootstrap a dependency-light static web app.
- Deterministic Generator can create a runnable Todo List app inside contract scope.
- Generator now runs required commands and writes real self-verification logs.

What does not yet work:

- Evaluator does not yet run browser checks, inspect UI state, or verify app-specific behavior.
- LLM Generator is not implemented yet; current real generation path is deterministic for simple web/Todo tasks.
- Repair loop does not persist repeated failure fingerprints or perform root-cause escalation.
- `vch run` can create and verify the first static Todo app path, but does not yet start a persistent dev server or print a final URL.

## Target User Flow

1. User runs:

   ```bash
   vch run "实现一个运行 Todo List 网站" --llm-backend minimax
   ```

2. Initializer creates `.harness/` and detects whether the target directory is empty, Python, JS, TS, Vite, React, or another supported stack.

3. Planner creates:

   - `FEATURE_SPEC.json`
   - `ROADMAP.md`
   - `FEATURE_LEDGER.json`
   - `PROGRESS.md`

4. PlanFeasibilityGate accepts only if every feature has testable ACs.

5. SprintSelector selects the smallest sprint, usually `S001`.

6. Contract negotiation writes:

   - `CONTRACT_PROPOSAL.yaml`
   - `CONTRACT_REVIEW.md`
   - `CONTRACT.yaml`

7. ContextCurator writes `CONTEXT_MANIFEST.yaml`.

8. Generator backend modifies only allowed files and writes:

   - code files
   - tests
   - `GENERATOR_PLAN.md`
   - `CHANGESET.md`
   - `SELF_VERIFY_REPORT.md`

9. SelfVerifyGate blocks if required commands were not run, logs are missing, or placeholders remain.

10. Evaluator runs build/test/e2e commands, collects evidence, checks scope, and writes `EVAL_REPORT.json`.

11. If failed, EvaluationGate writes `REPAIR_PACKET.md`, Generator repairs, Evaluator reruns.

12. If passed, FeatureLedger updates ACs to pass and FinalQA writes a summary.

13. CLI prints:

   - final status
   - how to run the app
   - dev server command
   - evidence paths
   - failing artifacts if blocked

## Implementation Milestones

### Milestone 1: Safe Configuration and Provider Readiness

Status: mostly complete.

Tasks:

- Keep real secrets in `.env`.
- Keep `.env` ignored by git.
- Commit `.env.example`.
- Load `.env` automatically.
- Support MiniMax via OpenAI-compatible API.
- Add `vch llm-smoke`.

Acceptance:

- `vch llm-smoke --llm-backend minimax --model MiniMax-M2.7` returns valid JSON.
- `pytest -q` passes.
- `git check-ignore .env` confirms the secret file is ignored.

### Milestone 2: Stack-Aware Project Bootstrap

Purpose: one-line app tasks often start in an empty or incomplete directory.

Tasks:

- Add a `ProjectBootstrapper`.
- Detect empty directory vs existing app.
- For empty web-app requests, scaffold a minimal Vite + React + TypeScript app or a static HTML app.
- Prefer the simplest stack that can satisfy the task.
- Generate `package.json`, `src/`, `tests/`, and Playwright config when needed.
- Record bootstrap decisions in `.harness/BOOTSTRAP_REPORT.md`.

Acceptance:

- Empty temp directory + `vch run "实现一个运行 Todo List 网站"` produces app files.
- `npm install`, `npm run build`, and at least one test command are discoverable.
- Existing projects are not overwritten without contract scope.

### Milestone 3: LLM Generator Backend

Purpose: Generator must actually implement files.

Tasks:

- Add `GeneratorBackend` protocol.
- Add `LLMGeneratorBackend` for MiniMax/OpenAI-compatible models.
- Give Generator only:
  - `CONTRACT.yaml`
  - `CONTEXT_MANIFEST.yaml`
  - allowed file contents
  - current failure packet when repairing
- Require LLM output as structured file patches or full file writes.
- Apply writes through a guarded filesystem tool.
- Reject writes outside `allowed_write_paths`.
- Write tool call records to `.harness/logs/tool_calls.jsonl`.

Acceptance:

- Generator creates or edits real files for a simple app sprint.
- Forbidden file changes are blocked.
- `CHANGESET.md` lists actual changed files.
- Generator cannot mark final success.

### Milestone 4: Command-Running Self Verification

Purpose: Generator must not fake completion.

Tasks:

- Let Generator call the command runner for required commands.
- Save command outputs under sprint artifacts.
- Write numeric exit codes and log paths to `SELF_VERIFY_REPORT.md`.
- Block `[TODO]`, missing logs, missing commands, and nonzero exits.

Acceptance:

- SelfVerifyGate fails if Generator does not run commands.
- SelfVerifyGate passes when all required commands produce logs and exit 0.

### Milestone 5: Browser Evaluator for Web Apps

Purpose: "Todo List 网站" requires visual and behavioral verification, not only build success.

Tasks:

- Add Playwright dependency detection and bootstrap.
- Add evaluator support for:
  - starting dev server
  - opening page
  - checking no console errors
  - adding todo
  - toggling todo
  - deleting todo
  - refreshing page and checking persistence when requested
- Save screenshots and traces.
- Write `LOG_INDEX.md`.

Acceptance:

- Evaluator catches a UI that builds but cannot add a todo.
- Evaluator catches console errors.
- Evaluator catches missing persistence when contract requires persistence.
- Evidence includes screenshot, console log, command output, and trace path.

### Milestone 6: Repair Loop That Learns

Purpose: avoid blind repeated attempts.

Tasks:

- Fingerprint failed ACs and command errors.
- Persist repair attempts in `FEATURE_LEDGER.json` and `RUN_STATE.json`.
- If same AC fails twice, require RCA and two alternative fixes.
- If max attempts fail, write `BLOCKER_REPORT.md`.
- Keep repair context minimal.

Acceptance:

- One simple injected bug can be repaired.
- Same failure twice triggers RCA.
- Three failures mark sprint blocked.

### Milestone 7: Final App Run Report

Purpose: user should know how to run what was built.

Tasks:

- Add `FINAL_REPORT.md`.
- Include:
  - final status
  - run command
  - dev server URL if started
  - passed ACs
  - evidence paths
  - remaining limitations
- CLI prints the same essentials.

Acceptance:

- After a passing run, user can copy the dev command from final output and open the app.

## First End-to-End Acceptance Fixture

Fixture command:

```bash
vch run "实现一个运行 Todo List 网站，支持新增、完成、删除待办，并刷新后保留数据" --llm-backend minimax
```

Expected features:

- Add todo
- Mark todo complete/incomplete
- Delete todo
- Persist todos after refresh
- Responsive usable page

Expected verification:

- `npm run build`
- unit test or static test
- Playwright add/toggle/delete/refresh test
- console log check
- screenshot evidence

Success condition:

- `EVAL_REPORT.json.overall_status == "pass"`
- all feature ledger ACs are `pass`
- `FINAL_REPORT.md` contains app run instructions

## Development Priority

Implement in this order:

1. ProjectBootstrapper
2. Guarded filesystem write tool
3. LLMGeneratorBackend
4. Generator command self-verification
5. Web Evaluator with Playwright
6. Repair loop fingerprints
7. Final report and CLI run summary

This order turns the project from planner-only into a real runnable app harness as quickly as possible while preserving the safety and traceability principles.
