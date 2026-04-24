# Harness Design Principles

This document records the source principles that should guide VCH changes. Future implementation work should update the harness in alignment with these constraints rather than adding agent complexity for its own sake.

Sources:

- OpenAI, Harness engineering: leveraging Codex in an agent-first world  
  https://openai.com/index/harness-engineering/
- Anthropic, Effective harnesses for long-running agents  
  https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, Harness design for long-running application development  
  https://www.anthropic.com/engineering/harness-design-long-running-apps

## 1. Humans Steer, Agents Execute

The human role moves upward: define intent, constraints, architecture, acceptance criteria, and feedback loops. The agent role is to perform bounded work inside that system.

Implications for VCH:

- Keep Python orchestration deterministic and non-LLM-owned.
- Use LLMs for reasoning, planning, critique, and implementation suggestions.
- Do not let any role agent decide final success.
- Final success requires evaluator evidence and passing gates.

## 2. The Repository Is the System of Record

Agent-legible state must live in the repository. If a fact only exists in chat history, an external note, or a previous context window, future agents effectively cannot rely on it.

Implications for VCH:

- Store run state under `.harness/`.
- Maintain `FEATURE_SPEC.json`, `FEATURE_LEDGER.json`, `PROGRESS.md`, `CONTRACT.yaml`, `EVAL_REPORT.json`, and repair artifacts.
- Keep `AGENTS.md` and prompts short, with links to deeper docs.
- Prefer structured JSON/YAML schemas over prose-only state.

## 3. Context Must Be Curated, Not Dumped

Long-running agents fail when handed stale logs, giant manuals, or unrelated history. They need a small map and current task evidence.

Implications for VCH:

- Every role invocation should receive a context manifest.
- Generator context should include current contract, ledger/progress, relevant files, and latest failure only.
- Old eval reports and unrelated logs should be forbidden context unless explicitly requested.
- Add context requests as artifacts instead of silently broadening context.

## 4. Work Must Be Incremental and Feature-Led

Long tasks should be broken into feature-sized units so agents do not one-shot a project or falsely declare it complete after partial progress.

Implications for VCH:

- Planner expands a short user task into features, ACs, and sprints.
- Feature ledger starts pessimistically: ACs are pending/failing until proven otherwise.
- Each sprint should have a narrow contract and file scope.
- Progress must be visible across context resets.

## 5. Contract Before Code

Generator and evaluator should agree on what "done" means before implementation begins.

Implications for VCH:

- Each sprint must produce `CONTRACT_PROPOSAL.yaml`, `CONTRACT_REVIEW.md`, and `CONTRACT.yaml`.
- ContractGate rejects missing oracle, missing evidence, empty commands, or overbroad write scope.
- Generator can only operate inside `allowed_files` and `allowed_write_paths`.

## 6. External Evaluation Beats Self-Attestation

Generators tend to be optimistic about their own work. A separate evaluator, tuned to be skeptical, is a stronger control point.

Implications for VCH:

- `SELF_VERIFY_REPORT.md` is necessary but insufficient.
- `EVAL_REPORT.json` is the only source of final pass/fail.
- Evaluator must run commands, inspect logs, check scope, and verify ACs.
- For UI apps, evaluator should eventually use Playwright and screenshots/traces.

## 7. Evidence Is the Interface Between Roles

Repair should not receive a vague critique. It should receive minimal, concrete evidence: failed AC, observed vs expected, reproduction, logs, screenshots, traces, likely files, and forbidden changes.

Implications for VCH:

- Every command must have exit code and log path.
- Every AC result must include evidence paths.
- Repair packets should be small and current.
- Repeated failures must trigger root cause analysis, not blind retry.

## 8. Make the App and Harness Legible to Agents

Agents improve when they can directly inspect the application, logs, metrics, traces, DOM snapshots, and test results.

Implications for VCH:

- Command logs and trace indexes are first-class artifacts.
- UI evaluation should produce screenshots and Playwright traces.
- Logs should be searchable and summarized in `LOG_INDEX.md`.
- Harness failures should be classified separately from app failures.

## 9. Enforce Invariants Mechanically

Documentation guides agents, but tests, schemas, linters, and gates enforce boundaries.

Implications for VCH:

- Schemas should reject invalid planner, contract, eval, and repair artifacts.
- ScopeGuard and diff-scope checks must catch forbidden file changes.
- Pre-completion checks must reject TODO placeholders.
- CI should run unit tests for every gate.

## 10. Keep the Harness as Simple as the Model Allows

Every harness component encodes an assumption about what the model cannot do alone. Those assumptions should be tested and simplified over time.

Implications for VCH:

- Maintain deterministic mode for tests.
- Add LLM backends behind adapters.
- Measure which gates and roles improve outcomes.
- Remove or simplify components that become unnecessary.

## Standing Rule

DeepAgents or any LLM runtime is the execution substrate. VCH is the harness protocol: artifacts, gates, evidence, state transitions, and repair loops.
