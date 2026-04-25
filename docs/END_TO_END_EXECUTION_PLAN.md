# End-to-End Execution Plan

Goal: after the harness is fully implemented, a user should be able to type a short task such as:

```bash
openjia run "Build a runnable Todo List website" --llm-backend minimax
```

and receive a runnable implementation with traceable planning, scoped generation, command evidence, evaluation, and repair artifacts under `.harness/`.

This plan is not tied to Todo List. Todo List is the first acceptance fixture because it is small, visual, testable, and representative of common app-building requests.

## Current Reality

What works now:

- `.env` can provide MiniMax API credentials.
- Planner can call MiniMax and produce `FEATURE_SPEC.json`.
- Planner and Generator can run through DeepAgents SDK with `--llm-backend deepagents`.
- Feature ledger and progress artifacts are written.
- PlanFeasibilityGate, ContractGate, SelfVerifyGate, EvaluationGate, and command logging exist.
- Evaluator can run shell commands and write command evidence.
- Empty simple web tasks can bootstrap a dependency-light static web app.
- Deterministic Generator can create a runnable Todo List app inside contract scope.
- Generator runs required commands and writes real self-verification logs.
- Browser E2E opens the generated Todo app and verifies add, complete, delete, and refresh persistence behavior.
- Evaluator collects evidence such as `test-results/todo-pass.png`.

What does not yet work:

- General-purpose DeepAgents generation is now available, but direct tool-use integration is still experimental.
- Repair loop does not persist repeated failure fingerprints or perform root-cause escalation.
- `openjia run` can create and verify the first static Todo app path, but does not yet start a persistent dev server or print a final URL.

## Target User Flow

1. User runs:

   ```bash
   openjia run "Build a runnable Todo List website with add, complete, delete, and persistence after refresh" --llm-backend minimax
   ```

2. Initializer creates `.harness/` and detects whether the target directory is empty, Python, JS, TS, Vite, React, or another supported stack.

3. Planner creates `FEATURE_SPEC.json`, `ROADMAP.md`, `FEATURE_LEDGER.json`, and `PROGRESS.md`.

4. PlanFeasibilityGate accepts only if every feature has testable acceptance criteria.

5. SprintSelector selects the smallest sprint, usually `S001`.

6. Contract negotiation writes `CONTRACT_PROPOSAL.yaml`, `CONTRACT_REVIEW.md`, and `CONTRACT.yaml`.

7. ContextCurator writes `CONTEXT_MANIFEST.yaml`.

8. Generator modifies only allowed files and writes code, tests, `GENERATOR_PLAN.md`, `CHANGESET.md`, and `SELF_VERIFY_REPORT.md`.

9. SelfVerifyGate blocks if required commands were not run, logs are missing, placeholders remain, or command exits are nonzero.

10. Evaluator runs build/test/e2e commands, collects evidence, checks scope, and writes `EVAL_REPORT.json`.

11. If failed, EvaluationGate writes `REPAIR_PACKET.md`; Generator repairs; Evaluator reruns.

12. If passed, FeatureLedger updates acceptance criteria to pass and FinalQA writes a summary.

13. CLI prints final status, run command, evidence paths, and failing artifacts if blocked.

## Implementation Milestones

### Milestone 1: Safe Configuration and Provider Readiness

Status: mostly complete.

Acceptance:

- `openjia llm-smoke --llm-backend minimax --model MiniMax-M2.7` returns valid JSON.
- `pytest -q` passes.
- `git check-ignore .env` confirms the secret file is ignored.

### Milestone 2: Stack-Aware Project Bootstrap

Status: complete for simple static web tasks.

Acceptance:

- Empty temp directory plus `openjia run "Build a runnable Todo List website"` produces app files.
- `npm run build` and browser checks are discoverable.
- Existing projects are not overwritten without contract scope.

### Milestone 3: LLM Generator Backend

Status: initial interface complete; general file generation is experimental.

Acceptance:

- Generator receives only `CONTRACT.yaml`, `CONTEXT_MANIFEST.yaml`, allowed file contents, and repair packets.
- Writes are applied through guarded filesystem checks.
- Forbidden file changes are blocked.
- `CHANGESET.md` lists actual changed files.

### Milestone 4: Command-Running Self Verification

Status: complete for current flow.

Acceptance:

- SelfVerifyGate fails if Generator does not run required commands.
- SelfVerifyGate passes when required commands produce logs and exit 0.

### Milestone 5: Browser Evaluator for Web Apps

Status: complete for Todo fixture.

Acceptance:

- Evaluator catches a UI that builds but cannot add a todo.
- Evaluator catches missing persistence when required.
- Evidence includes screenshot, command output, and log index paths.

### Milestone 6: Repair Loop That Learns

Status: pending.

Acceptance:

- Same failed acceptance criterion twice triggers RCA.
- Max attempts mark the sprint blocked with `BLOCKER_REPORT.md`.

### Milestone 7: Final App Run Report

Status: pending.

Acceptance:

- After a passing run, user can read the final command and URL from CLI output or `FINAL_REPORT.md`.

## First End-to-End Acceptance Fixture

Fixture command:

```bash
openjia run "Build a runnable Todo List website with add, complete, delete, and persistence after refresh" --llm-backend minimax
```

DeepAgents runtime fixture:

```bash
openjia run "Build a runnable Todo List website with add, complete, delete, and persistence after refresh" --llm-backend deepagents --model MiniMax-M2.7
```

Expected features:

- Add todo
- Mark todo complete/incomplete
- Delete todo
- Persist todos after refresh
- Responsive usable page

Expected verification:

- `npm run build`
- unit/static test
- browser add/toggle/delete/refresh test
- console log check
- screenshot evidence

Success condition:

- `EVAL_REPORT.json.overall_status == "pass"`
- all feature ledger acceptance criteria are `pass`
- final report contains app run instructions
