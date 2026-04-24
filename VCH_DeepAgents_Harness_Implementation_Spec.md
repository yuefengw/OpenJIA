# VCH: Verifiable Contextual Harness for DeepAgents SDK

> 面向 Claude Code 的实现说明文档  
> 目标：基于 DeepAgents SDK 实现一个用于长程软件开发任务的可验证 Harness 系统。  
> 核心原则：**不要优先修改 DeepAgents 源码；DeepAgents 作为 runtime，VCH 作为外层 Harness 协议与流程控制系统。**

---

## 0. 项目目标

本项目要实现一个基于 DeepAgents SDK 的长程任务 Harness，暂命名为：

```text
VCH: Verifiable Contextual Harness
```

它不是简单的 planner / generator / evaluator 多代理拼接，而是一个由 artifact、gate、context manifest、external evaluator、repair packet 和 trace log 约束的工程执行系统。

DeepAgents 负责：

```text
- agent runtime
- tool calling
- filesystem tools
- shell / sandbox execution
- subagents
- memory
- skills
- middleware
- context offloading / summarization
```

VCH 负责：

```text
- 长程任务状态机
- Planner 可行性约束
- Sprint Contract 协商
- Generator 上下文裁剪
- Evaluator 外部验证
- 日志与证据收集
- 失败分类与 Repair Loop
- 防止虚假完成、越界修改、doom loop
```

最终实现应满足：

```text
1. 用户给一个开发任务。
2. 系统初始化仓库和环境。
3. Planner 生成可验证的 feature spec 和 sprint roadmap。
4. Plan gate 检查计划是否可实现、可测试、可拆分。
5. 每个 sprint 前生成 contract。
6. Generator 只在当前 contract 和 context manifest 范围内实现。
7. Evaluator 独立运行测试、构建、日志检查、UI 验证。
8. 失败时生成最小 repair packet，交给 Generator 修复。
9. 通过后更新 progress、commit、进入下一 sprint。
10. 所有过程可从 .harness/ 目录和 logs 复盘。
```

---

## 1. 总体架构

推荐采用：

```text
确定性 Python Orchestrator + 多个 role-specific DeepAgents
```

不要把流程控制完全交给 LLM。LLM 负责复杂推理、写代码、分析日志；Python orchestrator 负责强制阶段顺序和 gate 条件。

### 1.1 高层流程

```text
User Task
  ↓
[0] Initializer
    - 初始化 .harness/
    - 检查仓库、依赖、启动方式、测试方式
    - 生成 ENV_REPORT.md / REPO_MAP.md / RUN_STATE.json
  ↓
[1] Planner
    - 生成 FEATURE_SPEC.json
    - 生成 ROADMAP.md
  ↓
[2] PlanFeasibilityGate
    - schema 检查
    - 可测试性检查
    - sprint 粒度检查
    - 环境可用性检查
  ↓
[3] SprintSelector
    - 选择当前最小可交付 sprint
  ↓
[4] ContractNegotiation
    - Generator 提出 CONTRACT_PROPOSAL.yaml
    - Evaluator 审查
    - 形成 CONTRACT.yaml
  ↓
[5] ContextCurator
    - 生成 CONTEXT_MANIFEST.yaml
    - 只收集当前 sprint 最相关上下文
  ↓
[6] Generator
    - 读取 contract + manifest
    - 修改 allowed files
    - 写 CHANGESET.md
    - 自测
  ↓
[7] SelfVerifyGate
    - 检查是否运行 required commands
    - 检查是否保存日志
  ↓
[8] Evaluator
    - 独立运行 build/test/lint/e2e/log check
    - 生成 EVAL_REPORT.json
  ↓
[9] EvaluationGate
    - pass: commit + progress update + next sprint
    - fail: FailureClassifier → REPAIR_PACKET.md → Generator repair
    - ambiguous: QA / Planner / human arbitration
  ↓
[10] FinalQA
    - 全局回归
    - 文档检查
    - 最终报告
```

### 1.2 架构图

```text
                    ┌──────────────────────┐
                    │      User Task        │
                    └──────────┬───────────┘
                               │
                               v
                    ┌──────────────────────┐
                    │     Initializer       │
                    │ env / repo / memory   │
                    └──────────┬───────────┘
                               │
                               v
                    ┌──────────────────────┐
                    │       Planner         │
                    │ feature spec / roadmap│
                    └──────────┬───────────┘
                               │
                               v
                    ┌──────────────────────┐
                    │ Plan Feasibility Gate │
                    └──────────┬───────────┘
                               │
                               v
        ┌────────────────────────────────────────────┐
        │              Sprint Loop                    │
        │                                            │
        │  ┌──────────────┐      ┌──────────────┐    │
        │  │  Generator   │<────>│  Evaluator   │    │
        │  │ contract prop│      │ contract chk │    │
        │  └──────┬───────┘      └──────┬───────┘    │
        │         │ agreed CONTRACT      │            │
        │         v                      │            │
        │  ┌──────────────┐              │            │
        │  │ContextCurator│              │            │
        │  └──────┬───────┘              │            │
        │         v                      │            │
        │  ┌──────────────┐              │            │
        │  │  Generator   │              │            │
        │  │ implement    │              │            │
        │  └──────┬───────┘              │            │
        │         v                      │            │
        │  ┌──────────────┐              │            │
        │  │ Self Verify  │              │            │
        │  └──────┬───────┘              │            │
        │         v                      │            │
        │  ┌──────────────┐              │            │
        │  │  Evaluator   │──────────────┘            │
        │  │ tests/log/UI │                           │
        │  └──────┬───────┘                           │
        │         │ pass / fail                       │
        │         v                                  │
        │  ┌──────────────┐                           │
        │  │ RepairPacket │─── fail ──> Generator     │
        │  └──────────────┘                           │
        └────────────────────────────────────────────┘
                               │
                               v
                    ┌──────────────────────┐
                    │       Final QA        │
                    │ regression / docs     │
                    └──────────────────────┘
```

---

## 2. 推荐项目结构

建议新增一个独立项目，不要 fork DeepAgents 源码。

```text
vch-harness/
  pyproject.toml
  README.md
  src/
    vch/
      __init__.py
      cli.py
      orchestrator.py
      config.py

      agents/
        __init__.py
        initializer.py
        planner.py
        generator.py
        evaluator.py
        qa.py
        trace_analyzer.py

      gates/
        __init__.py
        plan_feasibility.py
        self_verify.py
        evaluation_gate.py
        contract_gate.py
        scope_gate.py

      context/
        __init__.py
        curator.py
        repo_index.py
        relevance.py
        manifest.py

      schemas/
        __init__.py
        feature_spec.py
        contract.py
        eval_report.py
        run_state.py
        repair_packet.py

      middleware/
        __init__.py
        context_manifest.py
        pre_completion_checklist.py
        scope_guard.py
        eval_gate.py
        loop_detection.py
        log_collector.py

      tools/
        __init__.py
        shell.py
        git.py
        testing.py
        playwright.py
        logs.py
        filesystem.py

      prompts/
        initializer.md
        planner.md
        generator.md
        evaluator.md
        qa.md
        contract_reviewer.md
        repair_generator.md

      templates/
        AGENTS.md
        PROJECT_RULES.md
        init.sh
        playwright.config.template.ts

  tests/
    unit/
      test_plan_feasibility.py
      test_context_curator.py
      test_eval_report_schema.py
      test_failure_classifier.py
    integration/
      test_simple_bugfix_flow.py
      test_contract_negotiation.py
      test_repair_loop.py
    fixtures/
      todo_app/
      broken_counter_app/
      simple_api_project/
```

---

## 3. `.harness/` 工作目录协议

每次运行 VCH 时，在目标 repo 根目录创建：

```text
.harness/
  RUN.md
  RUN_STATE.json
  ENV_REPORT.md
  REPO_MAP.md
  REQUIREMENTS.md
  FEATURE_SPEC.json
  ROADMAP.md
  GLOBAL_CONSTRAINTS.md

  sprints/
    S001/
      SPRINT_GOAL.md
      CONTRACT_PROPOSAL.yaml
      CONTRACT_REVIEW.md
      CONTRACT.yaml
      CONTEXT_MANIFEST.yaml
      GENERATOR_PLAN.md
      CHANGESET.md
      SELF_VERIFY_REPORT.md
      EVAL_PLAN.yaml
      EVAL_REPORT.json
      BUG_REPORT.md
      REPAIR_PACKET.md
      REPAIR_REPORT.md
      LOG_INDEX.md
      ARTIFACTS/
        screenshots/
        traces/
        command_outputs/
        playwright/
        coverage/

  logs/
    tool_calls.jsonl
    commands.jsonl
    app.log
    test.log
    evaluator.log
    trace_index.json

  memory/
    PROJECT_RULES.md
    ARCHITECTURE_NOTES.md
    DECISIONS.md
    KNOWN_FAILURES.md
```

### 3.1 `RUN_STATE.json`

```json
{
  "run_id": "2026-04-24T10-00-00-vch",
  "status": "running",
  "current_phase": "planner",
  "current_sprint": null,
  "max_repair_attempts": 3,
  "started_at": "2026-04-24T10:00:00-07:00",
  "repo_root": "/path/to/repo",
  "git_base_commit": "abc123",
  "sprints": [],
  "last_error": null
}
```

### 3.2 `ENV_REPORT.md`

必须包含：

```text
# Environment Report

## Detected stack
- Language:
- Framework:
- Package manager:
- Test runner:
- Build command:
- Dev server command:

## Verified commands
- [ ] install
- [ ] build
- [ ] unit test
- [ ] lint
- [ ] typecheck
- [ ] e2e

## Problems
- ...

## Recommended init command
```bash
...
```
```

### 3.3 `REPO_MAP.md`

必须包含：

```text
# Repo Map

## Entry points
- ...

## Important directories
- src/
- tests/
- app/

## Routing / API / state locations
- ...

## Test files
- ...

## Likely extension points
- ...
```

---

## 4. Planner 设计

Planner 的目标不是生成漂亮计划，而是生成**可验证任务图**。

### 4.1 Planner 输入

Planner 只允许读取：

```text
1. 用户原始需求
2. .harness/ENV_REPORT.md
3. .harness/REPO_MAP.md
4. .harness/GLOBAL_CONSTRAINTS.md
5. .harness/memory/KNOWN_FAILURES.md
```

不要把完整历史对话给 Planner。

### 4.2 Planner 输出：`FEATURE_SPEC.json`

```json
{
  "project_goal": "string",
  "non_goals": ["string"],
  "assumptions": ["string"],
  "features": [
    {
      "id": "F001",
      "title": "string",
      "user_value": "string",
      "dependencies": [],
      "risk": "low|medium|high",
      "estimated_files": ["path"],
      "acceptance_criteria": [
        {
          "id": "AC001",
          "description": "string",
          "verification_type": "unit|integration|e2e|manual_review|static_check|api|db|log",
          "oracle": "string",
          "required_evidence": ["screenshot", "trace", "log", "test_output"]
        }
      ],
      "definition_of_done": ["string"]
    }
  ],
  "sprints": [
    {
      "id": "S001",
      "goal": "string",
      "features": ["F001"],
      "max_files_to_touch": 6,
      "must_not_touch": ["glob"],
      "verification_commands": ["command"],
      "rollback_strategy": "string"
    }
  ]
}
```

### 4.3 Planner prompt 要点

写入 `src/vch/prompts/planner.md`：

```text
你是 VCH Planner。
你的任务不是直接写代码，而是把用户需求拆成可验证、可实现、可分阶段交付的任务图。

强制规则：
1. 每个 feature 必须有 acceptance criteria。
2. 每个 acceptance criterion 必须有 verification_type、oracle、required_evidence。
3. 每个 sprint 必须足够小，能在一次实现循环内完成。
4. 每个 sprint 必须列出 must_not_touch，防止范围扩张。
5. 不能写“优化体验”“完善功能”这种不可验证目标，除非给出具体 oracle。
6. 如果信息不足，写入 assumptions，而不是自行扩大需求。
7. 输出必须是合法 JSON，符合 FEATURE_SPEC schema。
```

---

## 5. PlanFeasibilityGate

实现位置：

```text
src/vch/gates/plan_feasibility.py
```

### 5.1 检查项

```text
Schema Validity:
  - JSON 能 parse
  - 必填字段完整
  - id 唯一

Atomicity:
  - 每个 sprint feature 数量不能太多
  - max_files_to_touch 不能超过配置上限，默认 8

Testability:
  - 每个 AC 必须有 verification_type
  - 每个 AC 必须有 oracle
  - 每个 AC 必须有 required_evidence

Dependency:
  - feature dependencies 无环
  - sprint 顺序满足依赖

Environment:
  - verification_commands 在当前项目中合理
  - package manager 和命令匹配

Scope:
  - sprint 不允许修改 GLOBAL_CONSTRAINTS 禁止的路径

Risk:
  - high risk sprint 必须有 spike 或 rollback_strategy
```

### 5.2 评分

```python
feasibility_score = (
    0.25 * testability
    + 0.20 * atomicity
    + 0.20 * dependency_clarity
    + 0.15 * environment_readiness
    + 0.10 * context_size_fit
    + 0.10 * rollback_safety
)
```

规则：

```text
score >= 0.8: pass
0.6 <= score < 0.8: require planner revision
score < 0.6: fail and ask planner to regenerate
```

### 5.3 单元测试

```text
test_rejects_missing_oracle
test_rejects_missing_evidence
test_rejects_too_large_sprint
test_detects_dependency_cycle
test_accepts_valid_plan
```

---

## 6. Contract Negotiation

Generator 写代码前，必须先和 Evaluator 对齐“什么叫完成”。

### 6.1 输出文件

```text
.harness/sprints/S001/CONTRACT_PROPOSAL.yaml
.harness/sprints/S001/CONTRACT_REVIEW.md
.harness/sprints/S001/CONTRACT.yaml
```

### 6.2 `CONTRACT.yaml` schema

```yaml
sprint_id: S001
goal: string

scope:
  include:
    - string
  exclude:
    - string

allowed_files:
  - path_or_glob

forbidden_files:
  - path_or_glob

acceptance_criteria:
  - id: AC001
    behavior: string
    verification:
      type: unit|integration|e2e|api|db|log|static_check
      steps:
        - string
      oracle:
        - string
      required_evidence:
        - screenshot
        - trace
        - log
        - command_output

required_commands:
  - command

pass_threshold:
  all_acceptance_criteria_must_pass: true
  build_must_pass: true
  no_console_error: true
  no_type_error: true

repair_policy:
  max_repair_attempts: 3
  if_same_error_twice: ask_planner_or_change_approach
```

### 6.3 Contract reviewer 规则

Evaluator 或 ContractReviewer 必须拒绝：

```text
- 没有 oracle 的 AC
- 没有 required evidence 的 AC
- allowed_files 过宽，例如整个 src/**
- scope 里混入下一个 sprint 的内容
- required_commands 为空
- 测试方式与项目技术栈不匹配
```

### 6.4 单元测试

```text
test_contract_rejects_missing_required_commands
test_contract_rejects_overbroad_allowed_files
test_contract_rejects_unverifiable_acceptance_criterion
test_contract_accepts_valid_contract
```

---

## 7. Context Curator

Generator 必须拿到干净上下文。

实现位置：

```text
src/vch/context/curator.py
src/vch/context/manifest.py
src/vch/context/relevance.py
```

### 7.1 目标

每个 sprint / repair attempt 都新建一个 Generator invocation。上下文只来自 `CONTEXT_MANIFEST.yaml`。

### 7.2 `CONTEXT_MANIFEST.yaml`

```yaml
sprint_id: S001
git_base: abc123
git_head: def456

must_read:
  - .harness/sprints/S001/CONTRACT.yaml
  - .harness/GLOBAL_CONSTRAINTS.md
  - src/path/to/relevant_file.ts

may_read:
  - tests/relevant_test.spec.ts
  - package.json

forbidden_context:
  - "obsolete eval reports"
  - "old unrelated logs"

latest_failure:
  eval_report: .harness/sprints/S001/EVAL_REPORT.json
  failed_criteria:
    - AC002
  evidence:
    - .harness/sprints/S001/ARTIFACTS/command_outputs/playwright.log
    - .harness/sprints/S001/ARTIFACTS/screenshots/ac002.png

allowed_write_paths:
  - src/path/to/file.ts
  - tests/relevant_test.spec.ts
  - .harness/sprints/S001/CHANGESET.md
  - .harness/sprints/S001/REPAIR_REPORT.md
```

### 7.3 上下文分类

```text
A. Stable Context
   - AGENTS.md
   - PROJECT_RULES.md
   - 架构约束
   - coding style

B. Current Task Context
   - CONTRACT.yaml
   - 当前 sprint goal
   - 当前 acceptance criteria

C. Relevant Code Context
   - 相关文件
   - 相关 symbol
   - 相关测试
   - 相关路由/API/schema

D. Current Failure Context
   - 当前失败 AC
   - 最小 reproduction
   - 最新日志
   - 最新 screenshot / trace 索引

E. State Integrity Context
   - 当前 git commit hash
   - 当前 diff stat
   - allowed_files / forbidden_files
```

### 7.4 不应包含的上下文

```text
- 旧的失败日志，除非当前 failure 仍引用
- 上一轮 generator 的自夸总结
- 已修复 bug 的冗长历史
- 无关代码
- 用户闲聊历史
- evaluator 的长篇主观评价
```

### 7.5 relevance score

```python
def relevance_score(file):
    score = 0
    if file.explicitly_mentioned_in_contract:
        score += 5
    if file.appears_in_failing_stack_trace:
        score += 4
    if file.imports_or_is_imported_by_touched_file:
        score += 3
    if file.grep_hits_acceptance_keywords:
        score += 3
    if file.recently_modified_in_current_sprint:
        score += 2
    if file.test_references_file:
        score += 1
    if file.belongs_to_completed_sprint_without_current_failure_ref:
        score -= 5
    if file.is_obsolete_or_archived:
        score -= 10
    return score
```

### 7.6 测试

```text
test_manifest_includes_contract
test_manifest_includes_failing_stack_trace_files
test_manifest_excludes_obsolete_eval_reports
test_manifest_limits_allowed_write_paths
test_relevance_ranking_prefers_contract_files
```

---

## 8. Generator 设计

Generator 只负责实现当前 contract，不负责重新解释需求。

### 8.1 Generator 输入

```text
- CONTRACT.yaml
- CONTEXT_MANIFEST.yaml
- must_read 文件内容
- 当前 git diff stat
- 如果是修复轮，则加入 REPAIR_PACKET.md
```

### 8.2 Generator 输出

```text
- 修改代码
- .harness/sprints/S001/GENERATOR_PLAN.md
- .harness/sprints/S001/CHANGESET.md
- .harness/sprints/S001/SELF_VERIFY_REPORT.md
- 如果是 repair，则写 REPAIR_REPORT.md
```

### 8.3 Generator prompt 要点

写入 `src/vch/prompts/generator.md`：

```text
你是 VCH Generator。
你只能实现当前 CONTRACT.yaml 指定的 sprint。

强制规则：
1. 首先读取 CONTRACT.yaml 和 CONTEXT_MANIFEST.yaml。
2. 只修改 allowed_write_paths 中允许的文件。
3. 不要实现 contract exclude 中的功能。
4. 不要根据旧日志或旧评价扩大范围。
5. 如果需要读取 manifest 外文件，先写 CONTEXT_REQUEST.md 并说明原因。
6. 修改完成后必须运行 CONTRACT.yaml 中 required_commands。
7. 必须写 CHANGESET.md，说明改了什么、为什么改、影响哪些 AC。
8. 必须写 SELF_VERIFY_REPORT.md，记录每条命令 exit code 和日志路径。
9. 不能因为自己认为完成就结束；最终通过必须由 Evaluator 决定。
```

---

## 9. Evaluator 设计

Evaluator 必须独立验证，不相信 Generator 的自评。

### 9.1 Evaluator 必备能力

```text
- 构建检查：npm run build / pytest / cargo test / etc.
- 单元测试：npm test / pytest / go test / etc.
- lint/typecheck：按项目实际情况启用
- UI E2E：Playwright，若项目是前端或全栈应用
- API 检查：curl / httpx / pytest requests
- DB / persistence 检查：sqlite / localStorage / test DB
- 日志读取：app.log / console.log / test.log
- screenshot / trace 保存
- git diff scope check
```

### 9.2 Evaluator prompt 要点

写入 `src/vch/prompts/evaluator.md`：

```text
你是 VCH Evaluator。
你的职责是独立验证当前 sprint 是否满足 CONTRACT.yaml。

强制规则：
1. 不要相信 Generator 的完成声明。
2. 必须运行 CONTRACT.yaml 中 required_commands。
3. 必须逐条检查 acceptance criteria。
4. 每个 pass/fail 都必须有 evidence。
5. 如果是 UI 功能，必须尽量通过真实浏览器或 Playwright 验证。
6. 如果是 runtime 行为，必须检查日志和 console error。
7. 如果测试环境坏了，标记为 infrastructure_failure，不要误标 implementation_failure。
8. 不要把 contract 外的新需求当作失败，除非存在安全、数据损坏、严重回归。
9. 输出必须是合法 EVAL_REPORT.json。
```

### 9.3 `EVAL_REPORT.json` schema

```json
{
  "sprint_id": "S001",
  "overall_status": "pass|fail|blocked|infrastructure_failure",
  "summary": "string",
  "commands_run": [
    {
      "cmd": "npm run build",
      "exit_code": 0,
      "log_path": ".harness/sprints/S001/ARTIFACTS/command_outputs/build.log"
    }
  ],
  "criteria": [
    {
      "id": "AC001",
      "status": "pass|fail|blocked",
      "failure_type": "implementation_bug|test_bug|contract_gap|environment_failure|unknown|null",
      "evidence": ["path"],
      "observed": "string",
      "expected": "string",
      "likely_location": ["path"],
      "minimal_reproduction": ["step"],
      "repair_hint": "string"
    }
  ],
  "diff_scope_check": {
    "status": "pass|fail",
    "unexpected_files_modified": []
  },
  "logs": {
    "app_log": ".harness/logs/app.log",
    "console_log": ".harness/sprints/S001/ARTIFACTS/console.log"
  }
}
```

### 9.4 Evaluator 测试

```text
test_evaluator_fails_on_build_error
test_evaluator_fails_on_console_error
test_evaluator_detects_missing_persistence
test_evaluator_marks_infrastructure_failure_when_server_cannot_start
test_evaluator_does_not_fail_for_out_of_scope_feature
```

---

## 10. FailureClassifier 与 Repair Loop

实现位置：

```text
src/vch/gates/evaluation_gate.py
src/vch/schemas/repair_packet.py
```

### 10.1 失败分类

```text
implementation_bug:
  Generator 实现错误。进入 repair。

test_bug:
  Evaluator 测试错误或 oracle 错误。进入 evaluator correction 或 QA arbitration。

contract_gap:
  Contract 本身不完整或不可测。回到 contract negotiation。

plan_impossible:
  当前 sprint 不可行。回到 Planner re-scope。

environment_failure:
  环境启动、依赖、sandbox 出错。回到 Initializer。

ambiguous:
  进入 QA 或 human-in-the-loop。
```

### 10.2 `REPAIR_PACKET.md`

```text
# Repair Packet for S001

## Current status
Evaluator failed AC002.

## You must fix
- 刷新后项目状态丢失。

## You must not change
- 不要新增权限系统。
- 不要修改 auth/billing。
- 不要重写路由系统。
- 不要删除已有测试。

## Evidence
- Playwright log: .harness/sprints/S001/ARTIFACTS/command_outputs/playwright.log
- Screenshot: .harness/sprints/S001/ARTIFACTS/screenshots/ac002-after-reload.png
- Console log: .harness/sprints/S001/ARTIFACTS/console.log

## Likely files
- src/lib/projectStore.ts
- src/pages/ProjectEditor.tsx

## Required commands after fix
- npm run build
- npx playwright test tests/project-create.spec.ts

## Completion condition
You may stop only after:
1. AC002 passes.
2. Previously passing AC001 still passes.
3. You update REPAIR_REPORT.md.
```

### 10.3 Repair loop 规则

```text
max_repair_attempts = 3

if same AC fails twice:
  require Root Cause Analysis
  require at least two alternative fixes

if same command fails with same error twice:
  trigger LoopDetectionMiddleware

if same file edited more than N times:
  trigger LoopDetectionMiddleware

if three repair attempts fail:
  mark sprint blocked
  write BLOCKER_REPORT.md
  return to Planner or human
```

---

## 11. Middleware 设计

### 11.1 `ContextManifestMiddleware`

目的：每次 Generator/Evaluator 调用前注入当前上下文边界。

规则：

```text
- 必须先读 CONTRACT.yaml
- 必须先读 CONTEXT_MANIFEST.yaml
- manifest 外文件不能直接读，除非写 CONTEXT_REQUEST.md
- 写入路径必须在 allowed_write_paths 内
```

### 11.2 `ScopeGuardMiddleware`

目的：防止越界修改。

伪代码：

```python
class ScopeGuardMiddleware:
    def before_tool_call(self, tool_name, args, state):
        if tool_name in {"edit_file", "write_file"}:
            path = args.get("path")
            if not is_allowed(path, state.allowed_write_paths):
                raise PermissionError(f"Path not allowed by contract: {path}")
```

注意：如果 Generator 用 shell 命令修改文件，文件工具层 guard 不一定能拦住。因此还要在每轮后跑：

```bash
git diff --name-only
```

并与 `allowed_write_paths` 对比。

### 11.3 `PreCompletionChecklistMiddleware`

目的：防止未验证就完成。

退出前检查：

```text
- required_commands 是否全部运行？
- 每条命令是否有 exit code 和 log path？
- CHANGESET.md 是否存在？
- SELF_VERIFY_REPORT.md 是否存在？
- 如果是 repair，REPAIR_REPORT.md 是否存在？
```

### 11.4 `EvalGateMiddleware`

目的：不允许 Generator 自己宣布最终完成。

规则：

```text
if generator says done:
  require evaluator report

if EVAL_REPORT.overall_status != pass:
  block final completion
```

### 11.5 `LoopDetectionMiddleware`

目的：防止 doom loop。

检测：

```text
- 同一文件编辑次数
- 同一命令相同错误重复次数
- 同一 repair hint 重复次数
- 连续失败但 diff 没有实质变化
```

动作：

```text
- 注入 step-back prompt
- 要求 root cause analysis
- 升级到 Planner / QA
```

---

## 12. 日志与可观测性

### 12.1 `commands.jsonl`

```jsonl
{"ts":"2026-04-24T10:01:00-07:00","phase":"generator","cmd":"npm run build","exit_code":0,"log_path":".harness/sprints/S001/ARTIFACTS/command_outputs/build.log"}
{"ts":"2026-04-24T10:02:00-07:00","phase":"evaluator","cmd":"npx playwright test","exit_code":1,"log_path":".harness/sprints/S001/ARTIFACTS/command_outputs/playwright.log"}
```

### 12.2 `tool_calls.jsonl`

```jsonl
{"ts":"...","phase":"generator","tool":"edit_file","path":"src/lib/projectStore.ts","status":"ok"}
{"ts":"...","phase":"evaluator","tool":"read_file","path":".harness/sprints/S001/CONTRACT.yaml","status":"ok"}
```

### 12.3 `LOG_INDEX.md`

```text
# S001 Log Index

## Commands
- build: ARTIFACTS/command_outputs/build.log
- unit test: ARTIFACTS/command_outputs/unit.log
- playwright: ARTIFACTS/command_outputs/playwright.log

## Runtime
- app log: ../../logs/app.log
- console log: ARTIFACTS/console.log

## Visual Evidence
- AC001 screenshot: ARTIFACTS/screenshots/ac001.png
- AC002 screenshot: ARTIFACTS/screenshots/ac002-after-reload.png

## Traces
- Playwright trace: ARTIFACTS/playwright/trace.zip
- LangSmith run id: <optional>
```

---

## 13. DeepAgents SDK 接入建议

### 13.1 推荐：多个 role-specific DeepAgents

伪代码：

```python
from deepagents import create_deep_agent


def make_planner_agent(model, backend):
    return create_deep_agent(
        model=model,
        tools=[repo_scan, read_file, grep, write_file],
        system_prompt=load_prompt("planner.md"),
        backend=backend,
    )


def make_generator_agent(model, backend, middleware):
    return create_deep_agent(
        model=model,
        tools=[read_file, grep, edit_file, write_file, execute],
        system_prompt=load_prompt("generator.md"),
        middleware=[
            ContextManifestMiddleware(),
            ScopeGuardMiddleware(),
            PreCompletionChecklistMiddleware(),
            LoopDetectionMiddleware(),
            *middleware,
        ],
        backend=backend,
    )


def make_evaluator_agent(model, backend):
    return create_deep_agent(
        model=model,
        tools=[read_file, write_file, execute, run_playwright, inspect_logs, git_diff],
        system_prompt=load_prompt("evaluator.md"),
        backend=backend,
    )
```

### 13.2 Orchestrator 伪代码

```python
class HarnessOrchestrator:
    def run(self, user_task: str):
        self.initializer.invoke(init_packet(user_task))

        feature_spec = self.planner.invoke(plan_packet(user_task))
        self.plan_gate.validate(feature_spec)

        for sprint in self.select_sprints(feature_spec):
            contract = self.negotiate_contract(sprint)
            self.context_curator.build_manifest(contract)

            for attempt in range(1, self.config.max_repair_attempts + 1):
                self.generator.invoke(generator_packet(contract, attempt))
                self.self_verify_gate.validate(sprint)

                eval_report = self.evaluator.invoke(eval_packet(contract))
                decision = self.evaluation_gate.decide(eval_report)

                if decision.kind == "pass":
                    self.commit_sprint(sprint, eval_report)
                    break

                if decision.kind == "implementation_bug":
                    self.write_repair_packet(eval_report)
                    self.context_curator.build_repair_manifest(eval_report)
                    continue

                if decision.kind == "contract_gap":
                    contract = self.renegotiate_contract(sprint, eval_report)
                    continue

                if decision.kind == "plan_impossible":
                    self.replan_from_blocker(sprint, eval_report)
                    break

                if decision.kind in {"environment_failure", "ambiguous"}:
                    self.escalate_to_qa_or_human(sprint, eval_report)
                    break

        self.final_qa.invoke(final_qa_packet())
```

---

## 14. CLI 设计

实现：

```text
vch init
vch plan "build a todo app with persistence"
vch run "build a todo app with persistence"
vch run-sprint S001
vch eval S001
vch repair S001
vch status
vch trace S001
```

### 14.1 `vch run`

```bash
vch run "Add login page and persistent session support" \
  --repo . \
  --max-sprints 3 \
  --max-repair-attempts 3 \
  --model claude-sonnet-4-5 \
  --backend local
```

### 14.2 `vch status`

输出：

```text
Run: 2026-04-24T10-00-00-vch
Status: running
Current phase: evaluator
Current sprint: S001
Last pass: AC001
Current failure: AC002 persistence after reload
Repair attempts: 1/3
Logs: .harness/sprints/S001/LOG_INDEX.md
```

---

## 15. 分阶段实现计划

### Phase 0：Baseline

目标：建立普通 DeepAgent 的对照。

实现：

```text
- 用 DeepAgents 直接完成几个 coding task
- 记录是否跳过测试、是否误报完成、是否越界改文件
```

产物：

```text
baseline_results.json
baseline_failure_taxonomy.md
```

### Phase 1：Initializer + Artifact Protocol

实现：

```text
- 创建 .harness/
- 生成 ENV_REPORT.md
- 生成 REPO_MAP.md
- 生成 RUN_STATE.json
- 检查 git 状态
- 检查 package manager / test runner
```

测试：

```text
- 空项目能初始化
- 已有项目能识别技术栈
- 缺依赖时能报告
- 环境失败不会进入 Generator
```

### Phase 2：受约束 Planner

实现：

```text
- Planner agent
- FEATURE_SPEC.json schema
- ROADMAP.md
- PlanFeasibilityGate
```

测试：

```text
- 一句话需求能拆成 feature spec
- 每个 feature 都有 AC
- 不可测 feature 被 gate 拒绝
- 超大 sprint 被拆小
- 依赖环被发现
```

### Phase 3：Contract Negotiation

实现：

```text
- CONTRACT_PROPOSAL.yaml
- CONTRACT_REVIEW.md
- CONTRACT.yaml
- ContractGate
```

测试：

```text
- Contract 必须包含 scope / non-scope
- Contract 必须包含 required_commands
- 每个 AC 必须有 evidence
- Evaluator 能拒绝不可测 contract
```

### Phase 4：Generator + SelfVerify

实现：

```text
- Generator agent
- ContextManifestMiddleware
- ScopeGuardMiddleware
- PreCompletionChecklistMiddleware
- CHANGESET.md
- SELF_VERIFY_REPORT.md
```

测试：

```text
- 不运行测试不能结束
- 修改 forbidden file 会被拦截
- build fail 时不能进入 pass
- self verify 日志必须保存
```

### Phase 5：Evaluator

实现：

```text
- build/test/lint/typecheck command runner
- Playwright runner
- log inspector
- EVAL_REPORT.json
- evidence artifact collector
```

测试：

```text
- 故意注入 UI bug，Evaluator 必须 fail
- 故意注入 console error，Evaluator 必须 fail
- 故意删除 persistence，Evaluator 必须 fail
- 测试环境坏时标 infrastructure_failure
- contract 外需求不能随便 fail
```

### Phase 6：Repair Loop

实现：

```text
- FailureClassifier
- REPAIR_PACKET.md
- Generator repair invocation
- Evaluator rerun
- LoopDetectionMiddleware
- max repair attempts
```

测试：

```text
- 一次可修 bug 能修复
- 同一错误重复两次后触发 RCA
- 三次失败后 blocked
- contract gap 会回到 renegotiation
```

### Phase 7：Context Curator

实现：

```text
- repo symbol scan
- grep acceptance keywords
- stack trace file extraction
- git diff analysis
- relevance scoring
- CONTEXT_MANIFEST.yaml
```

测试：

```text
- Generator 不看到旧 EVAL_REPORT
- Generator 只看到当前失败相关日志
- manifest 缺关键文件时能请求补充
- token 数下降但成功率不下降
```

### Phase 8：Trace Analyzer / Harness Optimizer

实现：

```text
- 汇总 logs / traces
- 按 failure type 聚类
- 输出 harness 改进建议
- 可选 train / holdout eval
```

测试：

```text
- 能发现经常不跑测试
- 能发现经常越界改文件
- 能发现 evaluator 漏测
- harness 改动不能只提升 train set
```

---

## 16. MVP 范围

第一版只做以下内容，不要一开始实现所有高级功能。

```text
1. 支持 JavaScript/TypeScript 前端项目。
2. 支持 npm / pnpm 自动识别。
3. 支持 build / test / playwright 三类验证。
4. 支持 1 个 Planner、1 个 Generator、1 个 Evaluator。
5. 支持最多 3 个 sprint。
6. 支持每个 sprint 最多 3 次 repair。
7. 支持 .harness/ artifact protocol。
8. 支持 EVAL_REPORT.json 和 REPAIR_PACKET.md。
9. 支持 ScopeGuard 和 PreCompletionChecklist。
```

MVP 成功标准：

```text
- Generator 不再跳过测试。
- Evaluator 能发现人为注入的简单 bug。
- Repair packet 能让 Generator 修复简单失败。
- 每轮上下文可控，没有明显旧日志污染。
- 人类能从 .harness/ 复盘完整执行过程。
```

---

## 17. 实验与评估

### 17.1 对照组

```text
Baseline A：普通 DeepAgents，一条 prompt 完成任务。
Baseline B：DeepAgents + planner prompt。
Baseline C：DeepAgents + planner/generator/evaluator，但无 artifact gates。
Ours：完整 VCH。
```

### 17.2 指标

```text
- Task Success Rate
- First-pass Success Rate
- Repair Success Rate
- False Completion Rate
- Out-of-scope Modification Count
- Required Command Execution Rate
- Evidence Completeness Rate
- Average Repair Attempts
- Average Token Usage
- Irrelevant Context Ratio
- Regression Rate
```

### 17.3 Ablation

```text
- 去掉 PlanFeasibilityGate
- 去掉 ContractNegotiation
- 去掉 Evaluator
- 去掉 ContextManifest
- 去掉 RepairPacket，直接给完整 EVAL_REPORT
- 去掉 LoopDetection
- 去掉 logs / screenshot / trace
```

---

## 18. 实现注意事项

### 18.1 不要优先 fork DeepAgents

本项目应优先通过：

```text
- create_deep_agent
- custom tools
- custom prompts
- custom middleware
- custom backends / sandbox
- external orchestrator
```

完成。

只有当 SDK 扩展点无法满足以下需求时，才考虑改 DeepAgents 源码：

```text
- 无法调整关键 middleware 顺序
- 无法读取必要的 tool call trace
- 无法控制 subagent 上下文
- 无法替换默认 summarization / filesystem 行为
```

### 18.2 权限边界

文件工具层权限不等于 shell 命令权限。必须同时做：

```text
1. edit_file / write_file path guard
2. execute command allowlist
3. git diff scope check
4. forbidden file post-check
```

### 18.3 Generator 不能决定最终成功

最终成功只能来自：

```text
EVAL_REPORT.overall_status == "pass"
```

### 18.4 Evaluator 不能随便扩大需求

Evaluator 只能按 contract 验收。contract 外问题只在以下情况标记：

```text
- 安全问题
- 数据损坏
- 严重回归
- 应用无法启动
```

### 18.5 失败报告必须最小化

Repair 不要把全部历史塞给 Generator，只给：

```text
- failed AC
- observed vs expected
- minimal reproduction
- evidence paths
- likely files
- forbidden changes
- required commands
```

---

## 19. 推荐优先实现顺序

请 Claude Code 按以下顺序实现：

```text
1. 创建项目骨架和 schemas。
2. 实现 .harness/ artifact 初始化。
3. 实现 PlanFeasibilityGate 单元测试。
4. 实现 ContractGate 单元测试。
5. 实现 ContextManifest schema 和 curator 的基础版本。
6. 实现 Orchestrator 的状态机骨架。
7. 接入 DeepAgents Planner。
8. 接入 DeepAgents Generator。
9. 接入 DeepAgents Evaluator。
10. 实现 command runner 和 log collector。
11. 实现 EVAL_REPORT.json 生成与解析。
12. 实现 RepairPacket。
13. 实现 ScopeGuard / PreCompletionChecklist。
14. 用 fixtures/todo_app 做 integration test。
15. 再加入 Playwright。
16. 最后加入 TraceAnalyzer。
```

---

## 20. 给 Claude Code 的第一条执行指令建议

可以直接把下面这段作为实现起始 prompt：

```text
请基于本仓库实现 VCH: Verifiable Contextual Harness。

第一阶段不要接入真实 LLM，也不要调用 DeepAgents。
先实现 deterministic core：
1. .harness/ 目录初始化
2. Pydantic schemas
3. PlanFeasibilityGate
4. ContractGate
5. ContextManifest
6. EvaluationGate
7. FailureClassifier
8. Orchestrator 状态机骨架
9. 单元测试

要求：
- 不要修改 DeepAgents 源码。
- 所有状态文件都写入 .harness/。
- 所有 schema 都必须可 parse、可验证。
- 测试必须覆盖无效 plan、无效 contract、越界文件、eval fail 到 repair packet 的转换。

完成第一阶段后，再接入 DeepAgents SDK 的 Planner/Generator/Evaluator agent。
```

---

## 21. 最终原则

本系统的核心不是“多代理”，而是：

```text
artifact-gated execution
contract-before-code
clean context per step
evidence-based evaluation
minimal repair feedback
traceable state transition
```

一句话总结：

> DeepAgents is the runtime. VCH is the harness protocol.

