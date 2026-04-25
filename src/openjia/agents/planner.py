"""Planner agent - generates feature specs and roadmaps."""

from pathlib import Path
from typing import Optional
import json
from pydantic import ValidationError

from openjia.schemas.feature_spec import FeatureSpec
from openjia.feature_ledger import build_ledger_from_spec, save_ledger, write_progress_markdown
from openjia.llm import LLMBackend, LLMConfigurationError, make_llm_backend
from openjia.prompts.loader import load_role_prompt


class Planner:
    """
    Planner agent - converts user requirements into verifiable task graphs.

    Inputs:
    - User task
    - ENV_REPORT.md
    - REPO_MAP.md
    - GLOBAL_CONSTRAINTS.md
    - KNOWN_FAILURES.md

    Outputs:
    - FEATURE_SPEC.json
    - ROADMAP.md
    """

    def __init__(
        self,
        repo_root: str,
        llm_backend: Optional[LLMBackend] = None,
        llm_backend_name: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.repo_root = Path(repo_root)
        self.llm_backend = llm_backend
        self.strict_llm = (llm_backend_name or "").lower() in {"deepagents", "deepagent"}
        if self.llm_backend is None and llm_backend_name:
            self.llm_backend = make_llm_backend(llm_backend_name, model)

    def invoke(
        self,
        user_task: str,
        env_report_path: Optional[str] = None,
        repo_map_path: Optional[str] = None,
        constraints_path: Optional[str] = None,
        failures_path: Optional[str] = None,
    ) -> FeatureSpec:
        """
        Generate a feature spec from user task.

        This is a stub implementation. In production, this would
        invoke a DeepAgent with the planner prompt.

        Args:
            user_task: User's task description
            env_report_path: Path to ENV_REPORT.md
            repo_map_path: Path to REPO_MAP.md
            constraints_path: Path to GLOBAL_CONSTRAINTS.md
            failures_path: Path to KNOWN_FAILURES.md

        Returns:
            FeatureSpec object
        """
        # Read input files
        env_report = ""
        if env_report_path and Path(env_report_path).exists():
            env_report = Path(env_report_path).read_text()

        repo_map = ""
        if repo_map_path and Path(repo_map_path).exists():
            repo_map = Path(repo_map_path).read_text()

        constraints = ""
        if constraints_path and Path(constraints_path).exists():
            constraints = Path(constraints_path).read_text()

        try:
            spec = self._generate_llm_spec(
                user_task=user_task,
                env_report=env_report,
                repo_map=repo_map,
                constraints=constraints,
            ) if self.llm_backend else self._generate_placeholder_spec(user_task)
        except (LLMConfigurationError, ValueError, json.JSONDecodeError) as error:
            if self.strict_llm:
                raise
            spec = self._generate_placeholder_spec(user_task)
            spec.assumptions.append(f"LLM planner failed; deterministic fallback used: {error}")

        self._normalize_spec(spec)

        # Save the spec
        harness_dir = self.repo_root / ".harness"
        harness_dir.mkdir(parents=True, exist_ok=True)
        self._save_feature_spec(spec, harness_dir)
        self._save_roadmap(spec, harness_dir)
        self._save_feature_ledger(spec, harness_dir)

        return spec

    def _normalize_spec(self, spec: FeatureSpec) -> None:
        """Apply harness safety normalization to model-authored plans."""
        existing_files = self._detect_extension_points()
        web_goal = self._looks_like_web_goal(spec.project_goal)
        if web_goal:
            existing_files = sorted(set(existing_files + self._default_web_write_candidates()))
        protected_files = self._protected_web_runtime_files() if web_goal and self.strict_llm else []
        if existing_files and (self.repo_root / "package.json").exists():
            for feature in spec.features:
                feature.estimated_files = self._normalize_file_list(
                    feature.estimated_files + existing_files,
                    canonicalize_web=web_goal,
                )
                if protected_files:
                    feature.estimated_files = [
                        path for path in feature.estimated_files if path not in protected_files
                    ]

        safe_commands = self._detect_verification_commands()
        for sprint in spec.sprints:
            commands = [
                command
                for command in sprint.verification_commands
                if self._is_executable_command(command)
                and not self._is_long_running_command(command)
            ]
            if not commands:
                commands = safe_commands
            elif (self.repo_root / "package.json").exists():
                for command in safe_commands:
                    if command not in commands:
                        commands.append(command)
            sprint.verification_commands = commands

            if existing_files and (self.repo_root / "package.json").exists():
                sprint.max_files_to_touch = max(sprint.max_files_to_touch, len(existing_files))
            if protected_files:
                sprint.must_not_touch = sorted(set(sprint.must_not_touch + protected_files))

    def _normalize_file_list(self, paths: list[str], canonicalize_web: bool = False) -> list[str]:
        """Normalize model-authored file paths to repository-relative paths."""
        web_path_map = {
            "app.js": "src/app.js",
            "script.js": "src/app.js",
            "main.js": "src/app.js",
            "style.css": "src/styles.css",
            "styles.css": "src/styles.css",
        }
        normalized = []
        for path in paths:
            clean = path.replace("\\", "/").lstrip("/")
            for prefix in ("workspace/", "./workspace/"):
                if clean.startswith(prefix):
                    clean = clean[len(prefix):]
            if canonicalize_web:
                clean = web_path_map.get(clean, clean)
            if clean and clean not in normalized:
                normalized.append(clean)
        return sorted(normalized)

    def _looks_like_web_goal(self, text: str) -> bool:
        """Detect web app tasks where absent app files should be creatable."""
        lowered = text.lower()
        return any(token in lowered for token in ("web", "app", "网站", "网页", "应用"))

    def _default_web_write_candidates(self) -> list[str]:
        """Candidate files a web-task generator may need to create."""
        return [
            "index.html",
            "src/app.js",
            "src/styles.css",
            "package.json",
            "playwright.config.mjs",
            "scripts/validate-app.mjs",
            "scripts/browser-e2e.mjs",
            "tests/acceptance.spec.mjs",
        ]

    def _protected_web_runtime_files(self) -> list[str]:
        """Runtime/evaluator scaffold files that DeepAgents should not rewrite."""
        return [
            "package.json",
            "playwright.config.mjs",
            "scripts/validate-app.mjs",
            "scripts/browser-e2e.mjs",
        ]

    def _is_long_running_command(self, command: str) -> bool:
        """Detect commands that start servers instead of terminating as verification."""
        lowered = command.lower()
        patterns = [
            "http.server",
            "npm run dev",
            "vite --host",
            "vite --",
            "next dev",
            "serve ",
        ]
        return any(pattern in lowered for pattern in patterns)

    def _is_executable_command(self, command: str) -> bool:
        """Keep shell commands and drop natural-language verification notes."""
        lowered = command.strip().lower()
        executable_prefixes = (
            "npm ",
            "node ",
            "python ",
            "pytest",
            "npx ",
            "uv ",
            "pnpm ",
            "yarn ",
            "bun ",
        )
        return lowered.startswith(executable_prefixes)

    def _generate_llm_spec(
        self,
        *,
        user_task: str,
        env_report: str,
        repo_map: str,
        constraints: str,
    ) -> FeatureSpec:
        """Generate a feature spec with an LLM backend."""
        assert self.llm_backend is not None
        instructions = self._load_prompt("planner.md")
        prompt = "\n\n".join([
            f"USER_TASK:\n{user_task}",
            f"ENV_REPORT.md:\n{env_report or '[missing]'}",
            f"REPO_MAP.md:\n{repo_map or '[missing]'}",
            f"GLOBAL_CONSTRAINTS.md:\n{constraints or '[missing]'}",
            "Return only JSON matching the provided FEATURE_SPEC schema.",
        ])
        schema = FeatureSpec.model_json_schema()
        data = self.llm_backend.generate_json(
            instructions=instructions,
            prompt=prompt,
            schema=schema,
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return self._validate_feature_spec_data(data)
            except (ValidationError, ValueError) as error:
                last_error = error
                repair_prompt = "\n\n".join([
                    "The previous planner response did not match the required FEATURE_SPEC schema.",
                    f"Repair attempt: {attempt + 1} of 3",
                    f"Validation error:\n{error}",
                    f"Invalid response JSON:\n{json.dumps(data, ensure_ascii=False, indent=2)}",
                    "Return one complete FEATURE_SPEC JSON object only.",
                    "The top-level JSON object must include exactly this shape:",
                    json.dumps({
                        "project_goal": "string",
                        "non_goals": ["string"],
                        "assumptions": ["string"],
                        "features": [{
                            "id": "F001",
                            "title": "string",
                            "user_value": "string",
                            "dependencies": [],
                            "risk": "low|medium|high",
                            "estimated_files": ["repo-relative file path"],
                            "acceptance_criteria": [{
                                "id": "AC001",
                                "description": "observable behavior",
                                "verification_type": "unit|integration|e2e|api|db|log|static_check",
                                "oracle": "specific pass condition",
                                "required_evidence": ["command_output"],
                            }],
                            "definition_of_done": ["string"],
                        }],
                        "sprints": [{
                            "id": "S001",
                            "goal": "string",
                            "features": ["F001"],
                            "max_files_to_touch": 8,
                            "must_not_touch": [".git/**", ".harness/**"],
                            "verification_commands": ["npm test"],
                            "rollback_strategy": "string",
                        }],
                    }, ensure_ascii=False, indent=2),
                    "Do not return JSON Schema fragments such as $ref, $defs, properties, or type.",
                    prompt,
                ])
                data = self.llm_backend.generate_json(
                    instructions=instructions,
                    prompt=repair_prompt,
                    schema=schema,
                )
        raise ValueError(f"Planner LLM did not return a valid FEATURE_SPEC after repairs: {last_error}")

    def _validate_feature_spec_data(self, data: dict) -> FeatureSpec:
        """Reject schema fragments and validate a complete feature spec."""
        schema_fragment_keys = {"$ref", "$defs", "properties", "type"}
        if schema_fragment_keys.intersection(data) and "project_goal" not in data:
            raise ValueError("Planner returned a JSON Schema fragment instead of FEATURE_SPEC data.")
        return FeatureSpec(**data)

    def _generate_placeholder_spec(self, user_task: str) -> FeatureSpec:
        """Generate a conservative deterministic feature spec."""
        commands = self._detect_verification_commands()
        command = commands[0]
        estimated_files = self._detect_extension_points()

        return FeatureSpec(
            project_goal=user_task,
            non_goals=[],
            assumptions=[
                "Generated by deterministic planner fallback because no LLM backend is configured.",
                "The implementation should stay within the listed estimated files unless the contract is revised.",
            ],
            features=[
                {
                    "id": "F001",
                    "title": self._title_from_task(user_task),
                    "user_value": user_task,
                    "dependencies": [],
                    "risk": "medium",
                    "estimated_files": estimated_files,
                    "acceptance_criteria": [
                        {
                            "id": "AC001",
                            "description": f"Implemented behavior satisfies the request: {user_task}",
                            "verification_type": "static_check" if command == "python -m compileall ." else "unit",
                            "oracle": "Required verification command exits with code 0 and evaluator finds no scope violations.",
                            "required_evidence": ["command_output", "eval_report"],
                        }
                    ],
                    "definition_of_done": [
                        "Contract is accepted before implementation.",
                        "Required commands pass.",
                        "EVAL_REPORT.json overall_status is pass.",
                    ],
                }
            ],
            sprints=[
                {
                    "id": "S001",
                    "goal": self._title_from_task(user_task),
                    "features": ["F001"],
                    "max_files_to_touch": min(max(len(estimated_files), 1), 8),
                    "must_not_touch": [
                        ".git/**",
                        ".harness/logs/**",
                        ".harness/RUN_STATE.json",
                    ],
                    "verification_commands": commands,
                    "rollback_strategy": "Revert files modified for this sprint and keep .harness evidence for review.",
                }
            ],
        )

    def _detect_verification_commands(self) -> list[str]:
        """Choose likely verification commands for deterministic mode."""
        package_json = self.repo_root / "package.json"
        if package_json.exists():
            try:
                package = json.loads(package_json.read_text())
            except json.JSONDecodeError:
                return ["npm test"]
            scripts = package.get("scripts", {})
            commands = []
            if "test" in scripts:
                commands.append("npm test")
            if "build" in scripts:
                commands.append("npm run build")
            if "test:e2e" in scripts:
                commands.append("npm run test:e2e")
            return commands or ["npm install"]

        if (self.repo_root / "pyproject.toml").exists():
            return ["python -m compileall ."]

        return ["python -m compileall ."]

    def _detect_extension_points(self) -> list[str]:
        """Pick narrow candidate files for the fallback sprint contract."""
        candidates = []
        for path in [
            "package.json",
            "index.html",
            "playwright.config.mjs",
            "src/app.js",
            "src/styles.css",
            "scripts/validate-app.mjs",
            "scripts/browser-e2e.mjs",
            "tests/acceptance.spec.mjs",
        ]:
            if (self.repo_root / path).exists():
                candidates.append(path)

        for pattern in [
            "scripts/*.mjs",
            "tests/*.mjs",
            "src/**/*.ts",
            "src/**/*.tsx",
            "src/**/*.js",
            "src/**/*.jsx",
            "src/**/*.css",
            "src/**/*.py",
            "*.py",
        ]:
            for path in self.repo_root.glob(pattern):
                relative = path.relative_to(self.repo_root).as_posix()
                if path.is_file() and relative not in candidates:
                    candidates.append(relative)
                if len(candidates) >= 8:
                    return candidates

        if candidates:
            return candidates
        if (self.repo_root / "package.json").exists():
            return ["package.json"]
        if (self.repo_root / "pyproject.toml").exists():
            return ["pyproject.toml"]
        return ["README.md"]

    def _title_from_task(self, user_task: str) -> str:
        """Create a compact sprint/feature title."""
        clean = " ".join(user_task.strip().split())
        return clean[:80] or "Implement requested change"

    def _load_prompt(self, name: str) -> str:
        """Load a role prompt."""
        prompt = load_role_prompt(name)
        return prompt or "You are the OpenJIA Planner. Return valid FEATURE_SPEC JSON."

    def _save_feature_spec(self, spec: FeatureSpec, harness_dir: Path) -> str:
        """Save feature spec to JSON."""
        path = harness_dir / "FEATURE_SPEC.json"
        with open(path, "w") as f:
            json.dump(spec.model_dump(), f, indent=2)
        return str(path)

    def _save_roadmap(self, spec: FeatureSpec, harness_dir: Path) -> None:
        """Save roadmap to markdown."""
        lines = ["# Roadmap", "", f"## Project Goal: {spec.project_goal}", ""]

        for sprint in spec.sprints:
            lines.append(f"## {sprint.id}: {sprint.goal}")
            lines.append("")
            lines.append("### Features")
            for fid in sprint.features:
                lines.append(f"- {fid}")
            lines.append("")
            lines.append("### Acceptance Criteria")
            for feature in spec.features:
                if feature.id not in sprint.features:
                    continue
                for ac in feature.acceptance_criteria:
                    lines.append(f"- {ac.id}: {ac.description}")
                    lines.append(f"  - Verification: {ac.verification_type}")
                    lines.append(f"  - Oracle: {ac.oracle}")
            lines.append("")
            lines.append("### Verification Commands")
            for cmd in sprint.verification_commands:
                lines.append(f"```bash\n{cmd}\n```")
            lines.append("")

        (harness_dir / "ROADMAP.md").write_text("\n".join(lines))

    def _save_feature_ledger(self, spec: FeatureSpec, harness_dir: Path) -> None:
        """Save feature ledger and progress markdown."""
        ledger = build_ledger_from_spec(spec)
        save_ledger(ledger, harness_dir / "FEATURE_LEDGER.json")
        write_progress_markdown(ledger, harness_dir / "PROGRESS.md")

