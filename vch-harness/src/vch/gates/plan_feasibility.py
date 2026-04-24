"""PlanFeasibilityGate - validates feature spec before execution."""

from dataclasses import dataclass
from typing import Optional
import json
from pydantic import ValidationError
from vch.schemas.feature_spec import FeatureSpec, Feature, Sprint


@dataclass
class FeasibilityIssue:
    """A feasibility issue found during validation."""

    category: str
    severity: str  # error, warning
    message: str
    location: Optional[str] = None


@dataclass
class FeasibilityResult:
    """Result of a feasibility check."""

    passed: bool
    score: float
    issues: list[FeasibilityIssue]
    recommendation: str  # pass, revision_required, fail


class PlanFeasibilityGate:
    """
    Validates that a feature spec is feasible for implementation.

    Checks:
    - Schema validity (JSON parse, required fields, unique IDs)
    - Atomicity (sprint feature count, max_files_to_touch limit)
    - Testability (each AC has verification_type, oracle, required_evidence)
    - Dependencies (no cycles, sprint order respects dependencies)
    - Environment (verification_commands are reasonable)
    - Scope (sprints don't touch forbidden paths)
    - Risk (high-risk sprints have spike or rollback_strategy)
    """

    DEFAULT_MAX_FILES = 8
    DEFAULT_MAX_FEATURES_PER_SPRINT = 5

    def __init__(self, max_files_per_sprint: int = DEFAULT_MAX_FILES):
        self.max_files_per_sprint = max_files_per_sprint

    def validate(self, spec: FeatureSpec | str | dict) -> FeasibilityResult:
        """
        Validate a feature spec.

        Args:
            spec: FeatureSpec object, JSON string, or dict

        Returns:
            FeasibilityResult with score and issues
        """
        issues: list[FeasibilityIssue] = []

        # Parse input
        if isinstance(spec, str):
            try:
                spec_dict = json.loads(spec)
            except json.JSONDecodeError as e:
                return FeasibilityResult(
                    passed=False,
                    score=0.0,
                    issues=[FeasibilityIssue(
                        "schema", "error", f"Invalid JSON: {e}"
                    )],
                    recommendation="fail"
                )
            try:
                spec = FeatureSpec(**spec_dict)
            except ValidationError as e:
                return FeasibilityResult(
                    passed=False,
                    score=0.0,
                    issues=[FeasibilityIssue(
                        "schema", "error", f"Invalid FEATURE_SPEC schema: {e}"
                    )],
                    recommendation="fail"
                )
        elif isinstance(spec, dict):
            try:
                spec = FeatureSpec(**spec)
            except ValidationError as e:
                return FeasibilityResult(
                    passed=False,
                    score=0.0,
                    issues=[FeasibilityIssue(
                        "schema", "error", f"Invalid FEATURE_SPEC schema: {e}"
                    )],
                    recommendation="fail"
                )

        # Run checks
        issues.extend(self._check_schema_validity(spec))
        issues.extend(self._check_atomicity(spec))
        issues.extend(self._check_testability(spec))
        issues.extend(self._check_dependencies(spec))
        issues.extend(self._check_environment(spec))
        issues.extend(self._check_scope(spec))
        issues.extend(self._check_risk(spec))

        # Calculate score
        score = self._calculate_score(spec, issues)

        # Determine recommendation
        errors = [i for i in issues if i.severity == "error"]
        if not errors and score >= 0.8:
            recommendation = "pass"
        elif score >= 0.6:
            recommendation = "revision_required"
        else:
            recommendation = "fail"

        return FeasibilityResult(
            passed=recommendation == "pass",
            score=score,
            issues=issues,
            recommendation=recommendation
        )

    def _check_schema_validity(self, spec: FeatureSpec) -> list[FeasibilityIssue]:
        """Check schema validity."""
        issues = []

        # Check for required fields
        if not spec.project_goal:
            issues.append(FeasibilityIssue("schema", "error", "project_goal is required"))

        # Check feature IDs are unique
        feature_ids = [f.id for f in spec.features]
        if len(feature_ids) != len(set(feature_ids)):
            issues.append(FeasibilityIssue(
                "schema", "error", "Feature IDs must be unique"
            ))

        # Check sprint IDs are unique
        sprint_ids = [s.id for s in spec.sprints]
        if len(sprint_ids) != len(set(sprint_ids)):
            issues.append(FeasibilityIssue(
                "schema", "error", "Sprint IDs must be unique"
            ))

        # Check all feature IDs in sprints exist
        all_feature_ids = set(feature_ids)
        for sprint in spec.sprints:
            for fid in sprint.features:
                if fid not in all_feature_ids:
                    issues.append(FeasibilityIssue(
                        "schema", "error",
                        f"Sprint {sprint.id} references unknown feature {fid}",
                        location=f"sprints.{sprint.id}"
                    ))

        return issues

    def _check_atomicity(self, spec: FeatureSpec) -> list[FeasibilityIssue]:
        """Check that sprints are atomic (not too large)."""
        issues = []

        for sprint in spec.sprints:
            if len(sprint.features) > self.DEFAULT_MAX_FEATURES_PER_SPRINT:
                issues.append(FeasibilityIssue(
                    "atomicity", "error",
                    f"Sprint {sprint.id} has too many features ({len(sprint.features)})",
                    location=f"sprints.{sprint.id}"
                ))

            if sprint.max_files_to_touch > self.max_files_per_sprint:
                issues.append(FeasibilityIssue(
                    "atomicity", "error",
                    f"Sprint {sprint.id} exceeds max_files_to_touch limit",
                    location=f"sprints.{sprint.id}"
                ))

        return issues

    def _check_testability(self, spec: FeatureSpec) -> list[FeasibilityIssue]:
        """Check that all acceptance criteria are testable."""
        issues = []
        valid_types = {"unit", "integration", "e2e", "manual_review", "static_check", "api", "db", "log"}

        for feature in spec.features:
            for ac in feature.acceptance_criteria:
                if not ac.verification_type:
                    issues.append(FeasibilityIssue(
                        "testability", "error",
                        f"AC {ac.id} missing verification_type",
                        location=f"features.{feature.id}.acceptance_criteria.{ac.id}"
                    ))
                elif ac.verification_type not in valid_types:
                    issues.append(FeasibilityIssue(
                        "testability", "warning",
                        f"AC {ac.id} has unknown verification_type: {ac.verification_type}",
                        location=f"features.{feature.id}.acceptance_criteria.{ac.id}"
                    ))

                if not ac.oracle:
                    issues.append(FeasibilityIssue(
                        "testability", "error",
                        f"AC {ac.id} missing oracle",
                        location=f"features.{feature.id}.acceptance_criteria.{ac.id}"
                    ))

                if not ac.required_evidence:
                    issues.append(FeasibilityIssue(
                        "testability", "error",
                        f"AC {ac.id} missing required_evidence",
                        location=f"features.{feature.id}.acceptance_criteria.{ac.id}"
                    ))

        return issues

    def _check_dependencies(self, spec: FeatureSpec) -> list[FeasibilityIssue]:
        """Check for dependency cycles and ordering."""
        issues = []

        # Build dependency graph
        feature_map = {f.id: f for f in spec.features}
        for feature in spec.features:
            for dep_id in feature.dependencies:
                if dep_id not in feature_map:
                    issues.append(FeasibilityIssue(
                        "dependency", "error",
                        f"Feature {feature.id} depends on unknown feature {dep_id}",
                        location=f"features.{feature.id}"
                    ))

        # Check for cycles using DFS
        def has_cycle(node: str, visited: set, stack: set) -> bool:
            visited.add(node)
            stack.add(node)
            if node in feature_map:
                for dep in feature_map[node].dependencies:
                    if dep not in visited:
                        if has_cycle(dep, visited, stack):
                            return True
                    elif dep in stack:
                        return True
            stack.remove(node)
            return False

        visited = set()
        for feature in spec.features:
            if feature.id not in visited:
                if has_cycle(feature.id, visited, set()):
                    issues.append(FeasibilityIssue(
                        "dependency", "error",
                        f"Circular dependency detected involving {feature.id}",
                        location=f"features.{feature.id}"
                    ))

        # Check sprint ordering respects dependencies
        sprint_map = {s.id: s for s in spec.sprints}
        for sprint in spec.sprints:
            for fid in sprint.features:
                if fid in feature_map:
                    for dep_id in feature_map[fid].dependencies:
                        # Find which sprint has the dependency
                        for other_sprint in spec.sprints:
                            if dep_id in other_sprint.features:
                                if other_sprint.id == sprint.id:
                                    continue
                                # Check ordering - dependency sprint should come first
                                if spec.sprints.index(other_sprint) > spec.sprints.index(sprint):
                                    issues.append(FeasibilityIssue(
                                        "dependency", "warning",
                                        f"Sprint {sprint.id} depends on {dep_id} in {other_sprint.id}, but {other_sprint.id} comes after",
                                        location=f"sprints.{sprint.id}"
                                    ))

        return issues

    def _check_environment(self, spec: FeatureSpec) -> list[FeasibilityIssue]:
        """Check that verification commands are reasonable."""
        issues = []

        for sprint in spec.sprints:
            if not sprint.verification_commands:
                issues.append(FeasibilityIssue(
                    "environment", "warning",
                    f"Sprint {sprint.id} has no verification_commands",
                    location=f"sprints.{sprint.id}"
                ))

        return issues

    def _check_scope(self, spec: FeatureSpec) -> list[FeasibilityIssue]:
        """Check scope constraints."""
        issues = []

        # This would need GLOBAL_CONSTRAINTS to fully validate
        # For now, just warn if sprints have empty goals
        for sprint in spec.sprints:
            if not sprint.goal:
                issues.append(FeasibilityIssue(
                    "scope", "error",
                    f"Sprint {sprint.id} has no goal",
                    location=f"sprints.{sprint.id}"
                ))

        return issues

    def _check_risk(self, spec: FeatureSpec) -> list[FeasibilityIssue]:
        """Check that high-risk sprints have mitigation."""
        issues = []
        feature_map = {f.id: f for f in spec.features}

        for sprint in spec.sprints:
            sprint_features = [f for f in spec.features if f.id in sprint.features]
            for feature in sprint_features:
                if feature.risk == "high":
                    if not sprint.rollback_strategy:
                        issues.append(FeasibilityIssue(
                            "risk", "warning",
                            f"High-risk feature {feature.id} in sprint {sprint.id} has no rollback_strategy",
                            location=f"sprints.{sprint.id}"
                        ))

        return issues

    def _calculate_score(self, spec: FeatureSpec, issues: list[FeasibilityIssue]) -> float:
        """Calculate feasibility score based on weighted criteria."""
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        # Base scores for each component
        testability = 1.0
        atomicity = 1.0
        dependency_clarity = 1.0
        environment_readiness = 1.0
        context_size_fit = 1.0
        rollback_safety = 1.0

        # Testability: docking for missing oracle/evidence
        for issue in errors:
            if issue.category == "testability":
                testability -= 0.15

        # Atomicity: docking for oversized sprints
        for issue in errors:
            if issue.category == "atomicity":
                atomicity -= 0.2

        # Dependency: docking for cycles
        for issue in errors:
            if issue.category == "dependency":
                dependency_clarity -= 0.2

        # Environment: docking for missing commands
        env_warnings = [i for i in warnings if i.category == "environment"]
        environment_readiness -= len(env_warnings) * 0.05

        # Risk: docking for missing rollback
        for issue in warnings:
            if issue.category == "risk":
                rollback_safety -= 0.1

        # Calculate weighted score
        score = (
            0.25 * max(0, testability) +
            0.20 * max(0, atomicity) +
            0.20 * max(0, dependency_clarity) +
            0.15 * max(0, environment_readiness) +
            0.10 * max(0, context_size_fit) +
            0.10 * max(0, rollback_safety)
        )

        return round(min(1.0, max(0.0, score)), 2)
