# Harness Improvement Plan

This plan adapts the project toward the harness principles described in:

- OpenAI, Harness engineering: leveraging Codex in an agent-first world
- Anthropic, Effective harnesses for long-running agents
- Anthropic, Harness design for long-running application development

## Design Principles

The harness should be a durable engineering control plane, not just a wrapper around a planner, generator, and evaluator.

- Keep plans, requirements, progress, evidence, failures, and final decisions in files that humans and agents can inspect.
- Use small, verifiable feature units with acceptance criteria before implementation begins.
- Separate roles: planner proposes, generator changes code, evaluator decides pass/fail, QA arbitrates ambiguity.
- Make context explicit through manifests so long-running tasks do not drift into stale logs or unrelated history.
- Track feature state across the run so skipped tests, false completion, and partial work are visible.
- Prefer external, evidence-based evaluation over generator self-attestation.
- Feed repairs only the minimal failure packet: failed AC, observed/expected, evidence, likely files, forbidden changes, and required commands.
- Treat harness improvements themselves as measurable: command execution rate, evidence completeness, false completion rate, and out-of-scope diffs.

## Current State Assessment

The project has a useful deterministic skeleton:

- `.harness/` initialization
- Pydantic schemas
- plan, contract, self-verify, and evaluation gates
- context manifest schema and basic curator
- CLI entry points
- unit tests for core gates

Important gaps remain:

- Planner currently emits an empty placeholder plan.
- There is no durable feature ledger or progress artifact.
- Contract negotiation can only work if `FeatureSpec` is already populated.
- Generator and evaluator are still deterministic stubs.
- Required command logging exists in evaluator but not as a reusable command ledger.
- Repair loop does not persist repeated failure fingerprints.
- Final completion is not yet tied to all feature states.

## Implementation Order

### 1. Feature Ledger and Progress Artifacts

Goal: make work state visible and auditable across long-running runs.

- Add `FEATURE_LEDGER.json` and `PROGRESS.md`.
- Track every feature, AC, sprint, status, evidence, and latest failure.
- Initialize ledger from `FEATURE_SPEC.json`.
- Update ledger from `EVAL_REPORT.json`.
- Include ledger paths in context manifests and final QA.

Done when:

- Initializer creates empty artifacts.
- Planner writes ledger after feature spec generation.
- EvaluationGate or orchestrator updates AC status after each eval.
- Tests cover pass/fail status transitions.

### 2. Usable Deterministic Planner Fallback

Goal: avoid an empty plan when no LLM/DeepAgents backend is connected.

- Generate at least one feature and sprint from the user task.
- Derive verification commands from `ENV_REPORT.md`.
- Use conservative `estimated_files` from `REPO_MAP.md`.
- Emit acceptance criteria with oracle and required evidence.

Done when:

- `openjia plan "..."` produces a gate-passing `FEATURE_SPEC.json`.
- `ROADMAP.md` includes feature and AC details.
- Tests cover non-empty fallback plan generation.

### 3. Contract and Context Tightening

Goal: make contract-before-code real.

- Generate `CONTRACT.yaml` from selected feature ACs.
- Reject empty allowed files unless the sprint is explicitly documentation-only.
- Include `FEATURE_LEDGER.json`, `PROGRESS.md`, `CONTRACT.yaml`, and relevant files in `CONTEXT_MANIFEST.yaml`.
- Ensure repair manifests contain only latest failure context.

Done when:

- ContractGate catches empty criteria, empty commands, and overbroad scope.
- Context manifests contain the active state artifacts.

### 4. Command Ledger and Evidence Completeness

Goal: make command execution and evidence auditable.

- Add a reusable command runner that writes command output and appends `.harness/logs/commands.jsonl`.
- Evaluator uses the command runner.
- SelfVerifyGate verifies command outputs exist and are not placeholders.
- Evaluation reports record evidence paths for command output.

Done when:

- Every required command has exit code and log path in `commands.jsonl`.
- EVAL_REPORT evidence includes command output logs.

### 5. Repair Loop Memory

Goal: prevent unbounded repeated repair attempts.

- Persist repair attempts in `FEATURE_LEDGER.json` or `RUN_STATE.json`.
- Fingerprint failed criteria and command errors.
- If the same AC or command fails twice, require RCA fields in `REPAIR_PACKET.md`.
- On max attempts, write `BLOCKER_REPORT.md`.

Done when:

- Tests cover repeated failure detection and blocked sprint output.

### 6. DeepAgents Integration Boundary

Goal: connect role-specific agents without weakening the harness.

- Keep Python orchestrator as the source of phase order and gate decisions.
- Inject prompts, contract, manifest, ledger, and repair packets into role agents.
- Do not let generator declare final pass.
- Add adapter interfaces so local deterministic mode remains testable.

Done when:

- Planner/Generator/Evaluator can be swapped between deterministic and DeepAgents backends.

## Immediate Work This Pass

This pass will implement sections 1 and 2 first, then tighten section 3 where feasible.

Priority rationale:

- A feature ledger and non-empty fallback planner make the harness usable immediately.
- Stronger contracts and context are only useful once there is real feature state to carry through the run.
- DeepAgents integration should come after deterministic gates are trustworthy.
