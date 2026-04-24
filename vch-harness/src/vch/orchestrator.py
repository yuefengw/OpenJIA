"""HarnessOrchestrator - main state machine for VCH."""

from pathlib import Path
from typing import Optional
import json
import subprocess
from datetime import datetime

from vch.schemas.feature_spec import FeatureSpec
from vch.schemas.contract import Contract
from vch.schemas.eval_report import EvalReport
from vch.schemas.run_state import RunState, SprintState
from vch.schemas.repair_packet import RepairPacket

from vch.agents.initializer import Initializer
from vch.agents.planner import Planner
from vch.agents.generator import Generator
from vch.agents.evaluator import Evaluator
from vch.agents.qa import QA

from vch.gates.plan_feasibility import PlanFeasibilityGate
from vch.gates.contract_gate import ContractGate
from vch.gates.evaluation_gate import EvaluationGate, EvaluationDecision, DecisionKind
from vch.gates.self_verify import SelfVerifyGate

from vch.context.curator import ContextCurator
from vch.context.manifest import ContextManifest
from vch.bootstrapper import ProjectBootstrapper

import yaml
from vch.feature_ledger import load_ledger, save_ledger, update_ledger_from_eval, write_progress_markdown


class HarnessOrchestrator:
    """
    Main orchestrator for the VCH harness.

    Coordinates the flow:
    1. Initialize
    2. Plan (with feasibility gate)
    3. Sprint loop (contract, generate, evaluate)
    4. Final QA
    """

    def __init__(
        self,
        repo_root: str,
        max_sprints: int = 3,
        max_repair_attempts: int = 3,
        llm_backend: str = "deterministic",
        llm_model: str = "gpt-4.1",
    ):
        self.repo_root = Path(repo_root)
        self.max_sprints = max_sprints
        self.max_repair_attempts = max_repair_attempts
        self.llm_backend = llm_backend
        self.llm_model = llm_model

        # Initialize components
        self.initializer = Initializer(str(self.repo_root))
        self.planner = Planner(
            str(self.repo_root),
            llm_backend_name=llm_backend,
            model=llm_model,
        )
        self.generator = Generator(str(self.repo_root))
        self.evaluator = Evaluator(str(self.repo_root))
        self.qa = QA(str(self.repo_root))

        # Initialize gates
        self.plan_gate = PlanFeasibilityGate()
        self.contract_gate = ContractGate()
        self.eval_gate = EvaluationGate(max_repair_attempts=max_repair_attempts)
        self.self_verify_gate = SelfVerifyGate()

        # Initialize context
        self.context_curator = ContextCurator()
        self.bootstrapper = ProjectBootstrapper(str(self.repo_root))

        # State
        self.run_state: Optional[RunState] = None
        self.feature_spec: Optional[FeatureSpec] = None

    def run(self, user_task: str) -> RunState:
        """
        Run the full VCH harness.

        Args:
            user_task: User's task description

        Returns:
            Final RunState
        """
        harness_dir = self.repo_root / ".harness"

        bootstrapped = self.bootstrapper.maybe_bootstrap(user_task)
        if bootstrapped:
            print("Bootstrapped a minimal static web project.")

        # Phase 0: Initialize
        print("=== Phase 0: Initialization ===")
        self.run_state = self.initializer.invoke(user_task)
        self._update_run_state(harness_dir, "planner")
        print(f"Initialized: {self.run_state.run_id}")

        # Phase 1: Planner
        print("\n=== Phase 1: Planning ===")
        feature_spec = self._run_planner(harness_dir, user_task)
        self.feature_spec = feature_spec

        # Plan Feasibility Gate
        print("\n=== Plan Feasibility Gate ===")
        result = self.plan_gate.validate(feature_spec)
        print(f"Feasibility score: {result.score}")
        print(f"Recommendation: {result.recommendation}")

        if result.recommendation == "fail":
            self.run_state.status = "failed"
            self.run_state.last_error = "Plan failed feasibility check"
            self._save_run_state(harness_dir)
            return self.run_state

        # Phase 2: Sprint Loop
        print("\n=== Phase 2: Sprint Loop ===")
        self._run_sprint_loop(harness_dir)

        # Phase 3: Final QA
        print("\n=== Phase 3: Final QA ===")
        self._run_final_qa(harness_dir)

        self.run_state.status = "completed"
        self._save_run_state(harness_dir)

        return self.run_state

    def _run_planner(self, harness_dir: Path, user_task: str) -> FeatureSpec:
        """Run the planner."""
        env_report_path = harness_dir / "ENV_REPORT.md"
        repo_map_path = harness_dir / "REPO_MAP.md"

        # Check for global constraints
        constraints_path = harness_dir / "GLOBAL_CONSTRAINTS.md"
        if not constraints_path.exists():
            constraints_path = None

        failures_path = harness_dir / "memory" / "KNOWN_FAILURES.md"

        spec = self.planner.invoke(
            user_task=user_task,
            env_report_path=str(env_report_path) if env_report_path.exists() else None,
            repo_map_path=str(repo_map_path) if repo_map_path.exists() else None,
            constraints_path=str(constraints_path) if constraints_path else None,
            failures_path=str(failures_path) if failures_path.exists() else None,
        )

        self.run_state.current_phase = "contract"
        return spec

    def _run_sprint_loop(self, harness_dir: Path) -> None:
        """Run the sprint loop."""
        if not self.feature_spec or not self.feature_spec.sprints:
            print("No sprints to run")
            return

        for sprint in self.feature_spec.sprints[:self.max_sprints]:
            print(f"\n--- Sprint {sprint.id}: {sprint.goal} ---")

            sprint_dir = harness_dir / "sprints" / sprint.id
            sprint_dir.mkdir(parents=True, exist_ok=True)

            # Save sprint goal
            (sprint_dir / "SPRINT_GOAL.md").write_text(f"# {sprint.id}\n\n{sprint.goal}")

            # Add to run state
            sprint_state = SprintState(
                id=sprint.id,
                status="in_progress",
                started_at=datetime.now().isoformat()
            )
            self.run_state.sprints.append(sprint_state)
            self.run_state.current_sprint = sprint.id
            self._save_run_state(harness_dir)

            # Contract negotiation
            print(f"Contract negotiation for {sprint.id}...")
            contract = self._negotiate_contract(sprint, sprint_dir)

            # Context curation
            print(f"Building context manifest for {sprint.id}...")
            manifest = self._build_context_manifest(sprint, contract, harness_dir)

            # Generate
            print(f"Running generator for {sprint.id}...")
            self._run_generator(sprint, contract, manifest, sprint_dir)

            # Self verify
            print(f"Running self-verify gate for {sprint.id}...")
            self._run_self_verify(contract, sprint_dir)

            # Evaluate
            print(f"Running evaluator for {sprint.id}...")
            eval_report = self._run_evaluator(sprint, contract, harness_dir)

            # Evaluation gate decision
            print(f"Running evaluation gate for {sprint.id}...")
            decision = self._run_evaluation_gate(eval_report, sprint.id, sprint_dir)

            # Handle decision
            if decision.kind == DecisionKind.PASS:
                print(f"Sprint {sprint.id} PASSED")
                sprint_state.status = "passed"
                sprint_state.completed_at = datetime.now().isoformat()
                self._commit_sprint(sprint, harness_dir)
            elif decision.kind == DecisionKind.IMPLEMENTATION_BUG:
                print(f"Sprint {sprint.id} has implementation bug, attempting repair...")
                sprint_state = self._handle_repair(
                    sprint, contract, manifest, decision, sprint_state, harness_dir
                )
            else:
                print(f"Sprint {sprint.id} blocked or failed: {decision.message}")
                sprint_state.status = "blocked" if decision.kind == DecisionKind.PLAN_IMPOSSIBLE else "failed"

            self._save_run_state(harness_dir)

    def _negotiate_contract(self, sprint, sprint_dir: Path) -> Contract:
        """Negotiate contract for a sprint."""
        feature_map = {}
        if self.feature_spec:
            feature_map = {feature.id: feature for feature in self.feature_spec.features}

        acceptance_criteria = []
        estimated_files = []
        for feature_id in sprint.features:
            feature = feature_map.get(feature_id)
            if not feature:
                continue
            estimated_files.extend(feature.estimated_files)
            for ac in feature.acceptance_criteria:
                acceptance_criteria.append({
                    "id": ac.id,
                    "behavior": ac.description,
                    "verification": {
                        "type": ac.verification_type,
                        "steps": sprint.verification_commands,
                        "oracle": [ac.oracle],
                        "required_evidence": ac.required_evidence,
                    },
                })

        allowed_files = sorted(set(estimated_files))

        # Create contract proposal
        proposal = {
            "sprint_id": sprint.id,
            "goal": sprint.goal,
            "scope": {
                "include": allowed_files,
                "exclude": sprint.must_not_touch
            },
            "allowed_files": allowed_files,
            "forbidden_files": sprint.must_not_touch,
            "acceptance_criteria": acceptance_criteria,
            "required_commands": sprint.verification_commands,
            "pass_threshold": {
                "all_acceptance_criteria_must_pass": True,
                "build_must_pass": True,
                "no_console_error": True,
                "no_type_error": True
            },
            "repair_policy": {
                "max_repair_attempts": self.max_repair_attempts,
                "if_same_error_twice": "ask_planner_or_change_approach"
            }
        }

        proposal_path = sprint_dir / "CONTRACT_PROPOSAL.yaml"
        with open(proposal_path, "w") as f:
            yaml.dump(proposal, f)

        contract = Contract(**proposal)

        review = self.contract_gate.validate(contract)
        review_path = sprint_dir / "CONTRACT_REVIEW.md"
        with open(review_path, "w") as f:
            f.write(f"# Contract Review for {sprint.id}\n\n")
            f.write(f"Status: {'pass' if review.valid else 'fail'}\n\n")
            if review.issues:
                f.write("## Issues\n")
                for issue in review.issues:
                    f.write(f"- {issue.severity}: {issue.rule} - {issue.message}\n")
            else:
                f.write("No issues found.\n")

        if not review.can_proceed:
            messages = "; ".join(issue.message for issue in review.issues if issue.severity == "error")
            raise RuntimeError(f"Contract gate failed for {sprint.id}: {messages}")

        contract_path = sprint_dir / "CONTRACT.yaml"
        with open(contract_path, "w") as f:
            yaml.dump(contract.model_dump(), f)

        return contract

    def _build_context_manifest(
        self,
        sprint,
        contract: Contract,
        harness_dir: Path
    ) -> ContextManifest:
        """Build context manifest for a sprint."""
        git_base = self.run_state.git_base_commit or "HEAD"
        git_head = self._get_current_git_head()

        manifest = self.context_curator.build_manifest(
            sprint_id=sprint.id,
            contract=contract,
            git_base=git_base,
            git_head=git_head,
            repo_root=str(self.repo_root)
        )

        manifest_path = self.context_curator.save_manifest(manifest, str(harness_dir / "sprints" / sprint.id))
        print(f"Manifest saved to: {manifest_path}")

        return manifest

    def _run_generator(
        self,
        sprint,
        contract: Contract,
        manifest: ContextManifest,
        sprint_dir: Path
    ) -> None:
        """Run the generator."""
        result = self.generator.invoke(
            sprint_id=sprint.id,
            contract=contract,
            manifest=manifest.model_dump() if manifest else None
        )
        print(f"Generator completed: {result['status']}")

    def _run_self_verify(self, contract: Contract, sprint_dir: Path) -> None:
        """Run self-verify gate."""
        result = self.self_verify_gate.validate(
            required_commands=contract.required_commands,
            sprint_dir=str(sprint_dir)
        )

        for issue in result.issues:
            if issue.severity == "error":
                print(f"  [ERROR] {issue.rule}: {issue.message}")
            else:
                print(f"  [WARN] {issue.rule}: {issue.message}")

        if not result.passed:
            errors = "; ".join(issue.message for issue in result.issues if issue.severity == "error")
            raise RuntimeError(f"Self-verify gate failed: {errors}")

    def _run_evaluator(
        self,
        sprint,
        contract: Contract,
        harness_dir: Path
    ) -> EvalReport:
        """Run the evaluator."""
        git_base = self.run_state.git_base_commit or "HEAD"
        git_head = self._get_current_git_head()

        eval_report = self.evaluator.invoke(
            sprint_id=sprint.id,
            contract=contract,
            git_base=git_base,
            git_head=git_head
        )

        # Save eval report
        eval_report_path = harness_dir / "sprints" / sprint.id / "EVAL_REPORT.json"
        with open(eval_report_path, "w") as f:
            json.dump(eval_report.model_dump(), f, indent=2)

        self._update_feature_progress(harness_dir, eval_report)
        print(f"Eval status: {eval_report.overall_status}")
        return eval_report

    def _update_feature_progress(self, harness_dir: Path, eval_report: EvalReport) -> None:
        """Update run-level feature ledger from evaluator output."""
        ledger_path = harness_dir / "FEATURE_LEDGER.json"
        if not ledger_path.exists():
            return

        ledger = load_ledger(ledger_path)
        update_ledger_from_eval(ledger, eval_report)
        save_ledger(ledger, ledger_path)
        write_progress_markdown(ledger, harness_dir / "PROGRESS.md")

    def _run_evaluation_gate(
        self,
        eval_report: EvalReport,
        sprint_id: str,
        sprint_dir: Path
    ) -> EvaluationDecision:
        """Run the evaluation gate."""
        # Get current repair count
        sprint_state = next(
            (s for s in self.run_state.sprints if s.id == sprint_id),
            None
        )
        repair_count = sprint_state.repair_count if sprint_state else 0

        decision = self.eval_gate.decide(eval_report, repair_count)

        print(f"Decision: {decision.kind.value} - {decision.message}")

        return decision

    def _handle_repair(
        self,
        sprint,
        contract: Contract,
        manifest: ContextManifest,
        decision: EvaluationDecision,
        sprint_state: SprintState,
        harness_dir: Path
    ) -> SprintState:
        """Handle repair loop."""
        if not decision.repair_packet:
            sprint_state.status = "failed"
            return sprint_state

        sprint_dir = harness_dir / "sprints" / sprint.id
        repair_packet = decision.repair_packet

        # Save repair packet
        repair_packet_path = sprint_dir / "REPAIR_PACKET.md"
        with open(repair_packet_path, "w") as f:
            f.write(f"# Repair Packet for {sprint.id}\n\n")
            f.write(f"## Current status\n{repair_packet.current_status}\n\n")
            f.write(f"## Failed AC\n{repair_packet.failed_ac}\n\n")
            f.write(f"## Must fix\n")
            for item in repair_packet.must_fix:
                f.write(f"- {item}\n")
            f.write(f"\n## Must not change\n")
            for item in repair_packet.must_not_change:
                f.write(f"- {item}\n")
            f.write(f"\n## Evidence\n")
            for item in repair_packet.evidence:
                f.write(f"- {item}\n")
            f.write(f"\n## Completion condition\n")
            for item in repair_packet.completion_condition:
                f.write(f"- {item}\n")

        sprint_state.repair_count += 1

        # Run generator again with repair packet
        self.generator.invoke(
            sprint_id=sprint.id,
            contract=contract,
            manifest=manifest.model_dump() if manifest else None,
            repair_packet=repair_packet
        )

        # Re-evaluate
        eval_report = self._run_evaluator(sprint, contract, harness_dir)
        new_decision = self._run_evaluation_gate(eval_report, sprint.id, sprint_dir)

        if new_decision.kind == DecisionKind.PASS:
            sprint_state.status = "passed"
            sprint_state.completed_at = datetime.now().isoformat()
        elif sprint_state.repair_count >= self.max_repair_attempts:
            sprint_state.status = "blocked"
        else:
            sprint_state.status = "in_progress"

        return sprint_state

    def _commit_sprint(self, sprint, harness_dir: Path) -> None:
        """Commit sprint changes."""
        git_base = self.run_state.git_base_commit or "HEAD"
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_root,
                capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"VCH: Complete sprint {sprint.id}"],
                cwd=self.repo_root,
                capture_output=True
            )
            new_head = self._get_current_git_head()
            self.run_state.git_base_commit = new_head
        except Exception as e:
            print(f"Git commit failed: {e}")

    def _run_final_qa(self, harness_dir: Path) -> None:
        """Run final QA."""
        feature_spec_path = harness_dir / "FEATURE_SPEC.json"
        if not feature_spec_path.exists():
            print("No feature spec found for QA")
            return

        sprint_reports = []
        sprints_dir = harness_dir / "sprints"
        if sprints_dir.exists():
            for sprint_path in sprints_dir.iterdir():
                eval_report = sprint_path / "EVAL_REPORT.json"
                if eval_report.exists():
                    sprint_reports.append(str(eval_report))

        qa_report = self.qa.invoke(
            feature_spec_path=str(feature_spec_path),
            sprint_reports=sprint_reports
        )

        print(f"QA Status: {qa_report['overall_status']}")

    def _get_current_git_head(self) -> str:
        """Get current git head."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"

    def _update_run_state(self, harness_dir: Path, phase: str) -> None:
        """Update run state phase."""
        if self.run_state:
            self.run_state.current_phase = phase
            self._save_run_state(harness_dir)

    def _save_run_state(self, harness_dir: Path) -> None:
        """Save run state to file."""
        if self.run_state:
            self.run_state.last_updated = datetime.now().isoformat()
            with open(harness_dir / "RUN_STATE.json", "w") as f:
                json.dump(self.run_state.model_dump(), f, indent=2)
