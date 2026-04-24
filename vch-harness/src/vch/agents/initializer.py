"""Initializer agent - initializes repository and harness."""

from pathlib import Path
from typing import Optional
import subprocess
import json
from datetime import datetime

from vch.schemas.run_state import RunState


class Initializer:
    """
    Initializes the VCH harness and environment.

    Responsibilities:
    - Create .harness/ directory structure
    - Generate ENV_REPORT.md
    - Generate REPO_MAP.md
    - Generate RUN_STATE.json
    - Check git status
    - Detect package manager and test runner
    """

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)

    def invoke(self, user_task: str) -> RunState:
        """
        Initialize the harness.

        Args:
            user_task: The user's task description

        Returns:
            RunState object
        """
        harness_dir = self.repo_root / ".harness"
        self._create_directory_structure(harness_dir)

        env_report = self._generate_env_report()
        self._save_env_report(env_report, harness_dir)

        repo_map = self._generate_repo_map()
        self._save_repo_map(repo_map, harness_dir)

        self._generate_protocol_files(harness_dir, user_task)
        run_state = self._create_run_state(user_task)
        self._save_run_state(run_state, harness_dir)

        self._generate_memory_files(harness_dir)

        return run_state

    def _create_directory_structure(self, harness_dir: Path) -> None:
        """Create the .harness directory structure."""
        dirs = [
            "sprints",
            "logs",
            "memory",
        ]
        for d in dirs:
            (harness_dir / d).mkdir(parents=True, exist_ok=True)

    def _generate_env_report(self) -> dict:
        """Generate environment report."""
        report = {
            "detected_stack": self._detect_stack(),
            "verified_commands": {},
            "problems": [],
            "recommended_init_command": None,
        }

        # Verify commands
        report["verified_commands"] = self._verify_commands()

        return report

    def _detect_stack(self) -> dict:
        """Detect the tech stack."""
        stack = {
            "language": None,
            "framework": None,
            "package_manager": None,
            "test_runner": None,
            "build_command": None,
            "dev_server_command": None,
        }

        # Check for package.json
        if (self.repo_root / "package.json").exists():
            stack["language"] = "JavaScript/TypeScript"
            stack["package_manager"] = self._detect_package_manager()
            stack["test_runner"] = self._detect_test_runner()
            try:
                import json
                with open(self.repo_root / "package.json") as f:
                    pkg = json.load(f)
                    stack["framework"] = pkg.get("name", "Unknown")
                    scripts = pkg.get("scripts", {})
                    stack["build_command"] = scripts.get("build")
                    stack["dev_server_command"] = scripts.get("dev") or scripts.get("start")
            except Exception:
                pass

        # Check for Python
        elif (self.repo_root / "pyproject.toml").exists() or (self.repo_root / "requirements.txt").exists():
            stack["language"] = "Python"
            stack["package_manager"] = "pip"
            if (self.repo_root / "pytest.ini").exists() or (self.repo_root / "pyproject.toml").exists():
                stack["test_runner"] = "pytest"

        return stack

    def _detect_package_manager(self) -> str:
        """Detect which package manager is used."""
        if (self.repo_root / "pnpm-lock.yaml").exists():
            return "pnpm"
        elif (self.repo_root / "yarn.lock").exists():
            return "yarn"
        elif (self.repo_root / "package-lock.json").exists():
            return "npm"
        return "npm"

    def _detect_test_runner(self) -> str:
        """Detect which test runner is used."""
        if (self.repo_root / "playwright.config.ts").exists() or (self.repo_root / "playwright.config.js").exists():
            return "playwright"
        elif (self.repo_root / "vitest.config.ts").exists() or (self.repo_root / "vitest.config.js").exists():
            return "vitest"
        elif (self.repo_root / "jest.config.js").exists():
            return "jest"
        return "unknown"

    def _verify_commands(self) -> dict:
        """Verify which commands work."""
        verified = {}

        commands = {
            "install": self._get_install_command(),
            "build": self._get_build_command(),
            "test": self._get_test_command(),
        }

        for name, cmd in commands.items():
            if cmd:
                try:
                    result = subprocess.run(
                        cmd,
                        cwd=self.repo_root,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    verified[name] = result.returncode == 0
                except Exception:
                    verified[name] = False
            else:
                verified[name] = False

        return verified

    def _get_install_command(self) -> Optional[list]:
        """Get the install command."""
        if (self.repo_root / "package.json").exists():
            pkg_manager = self._detect_package_manager()
            if pkg_manager == "pnpm":
                return ["pnpm", "install"]
            elif pkg_manager == "yarn":
                return ["yarn", "install"]
            elif pkg_manager == "npm":
                return ["npm", "install"]
        return None

    def _get_build_command(self) -> Optional[list]:
        """Get the build command."""
        if (self.repo_root / "package.json").exists():
            return ["npm", "run", "build"]
        return None

    def _get_test_command(self) -> Optional[list]:
        """Get the test command."""
        if (self.repo_root / "package.json").exists():
            test_runner = self._detect_test_runner()
            if test_runner == "playwright":
                return ["npx", "playwright", "test"]
            elif test_runner in ("vitest", "jest"):
                return ["npm", "test"]
        return None

    def _generate_repo_map(self) -> dict:
        """Generate repository map."""
        map_data = {
            "entry_points": [],
            "important_directories": [],
            "routing": [],
            "test_files": [],
            "likely_extension_points": [],
        }

        # Find entry points
        for pattern in ["src/index.*", "src/main.*", "app.*", "index.*"]:
            matches = list(self.repo_root.glob(pattern))
            map_data["entry_points"].extend([str(m) for m in matches])

        # Find important directories
        for pattern in ["src/**", "app/**", "lib/**", "tests/**"]:
            matches = list(self.repo_root.glob(pattern))
            dirs = [str(m.parent) for m in matches if m.is_dir()]
            map_data["important_directories"].extend(list(set(dirs))[:10])

        # Find test files
        for pattern in ["**/*.test.*", "**/*.spec.*", "**/test_*.py"]:
            matches = list(self.repo_root.glob(pattern))
            map_data["test_files"].extend([str(m) for m in matches[:20]])

        return map_data

    def _save_env_report(self, report: dict, harness_dir: Path) -> None:
        """Save environment report."""
        content = ["# Environment Report", "", "## Detected stack"]

        stack = report.get("detected_stack", {})
        for key, value in stack.items():
            if value:
                content.append(f"- {key}: {value}")

        content.append("")
        content.append("## Verified commands")
        for name, passed in report.get("verified_commands", {}).items():
            content.append(f"- [{'x' if passed else ' '}] {name}")

        content.append("")
        content.append("## Problems")
        problems = report.get("problems", [])
        if problems:
            for problem in problems:
                content.append(f"- {problem}")
        else:
            content.append("- None detected")

        content.append("")
        content.append("## Recommended init command")
        init_command = report.get("recommended_init_command")
        content.append("```bash")
        content.append(init_command or "# No install command detected")
        content.append("```")

        (harness_dir / "ENV_REPORT.md").write_text("\n".join(content))

    def _save_repo_map(self, map_data: dict, harness_dir: Path) -> None:
        """Save repository map."""
        content = ["# Repo Map", "", "## Entry points"]
        for ep in map_data.get("entry_points", []):
            content.append(f"- {ep}")

        content.append("")
        content.append("## Important directories")
        for d in map_data.get("important_directories", []):
            content.append(f"- {d}")

        content.append("")
        content.append("## Routing / API / state locations")
        for route in map_data.get("routing", []):
            content.append(f"- {route}")
        if not map_data.get("routing"):
            content.append("- None detected")

        content.append("")
        content.append("## Test files")
        for t in map_data.get("test_files", []):
            content.append(f"- {t}")
        if not map_data.get("test_files"):
            content.append("- None detected")

        content.append("")
        content.append("## Likely extension points")
        for path in map_data.get("likely_extension_points", []):
            content.append(f"- {path}")
        if not map_data.get("likely_extension_points"):
            content.append("- None detected")

        (harness_dir / "REPO_MAP.md").write_text("\n".join(content))

    def _generate_protocol_files(self, harness_dir: Path, user_task: str) -> None:
        """Create baseline artifact protocol files."""
        files = {
            "RUN.md": f"# VCH Run\n\n## User Task\n{user_task or '[not provided]'}\n",
            "REQUIREMENTS.md": f"# Requirements\n\n{user_task or '[not provided]'}\n",
            "FEATURE_LEDGER.json": '{\n  "project_goal": "",\n  "features": []\n}\n',
            "PROGRESS.md": "# Progress\n\nNo feature spec has been generated yet.\n",
            "GLOBAL_CONSTRAINTS.md": (
                "# Global Constraints\n\n"
                "- Do not modify files outside the active sprint contract.\n"
                "- Do not declare final success without a passing EVAL_REPORT.json.\n"
                "- Preserve user changes unless explicitly instructed otherwise.\n"
            ),
        }
        for name, content in files.items():
            path = harness_dir / name
            if not path.exists():
                path.write_text(content)

        log_files = {
            "tool_calls.jsonl": "",
            "commands.jsonl": "",
            "app.log": "",
            "test.log": "",
            "evaluator.log": "",
            "trace_index.json": "{}\n",
        }
        logs_dir = harness_dir / "logs"
        for name, content in log_files.items():
            path = logs_dir / name
            if not path.exists():
                path.write_text(content)

    def _create_run_state(self, user_task: str) -> RunState:
        """Create initial run state."""
        run_id = f"{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}-vch"

        # Get git info
        git_base = None
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                git_base = result.stdout.strip()
        except Exception:
            pass

        return RunState(
            run_id=run_id,
            status="initialized",
            current_phase="initializer",
            current_sprint=None,
            max_repair_attempts=3,
            started_at=datetime.now().isoformat(),
            repo_root=str(self.repo_root),
            git_base_commit=git_base,
            sprints=[],
            last_error=None,
        )

    def _save_run_state(self, state: RunState, harness_dir: Path) -> None:
        """Save run state to JSON."""
        with open(harness_dir / "RUN_STATE.json", "w") as f:
            json.dump(state.model_dump(), f, indent=2)

    def _generate_memory_files(self, harness_dir: Path) -> None:
        """Generate initial memory files."""
        memory_dir = harness_dir / "memory"

        files = {
            "PROJECT_RULES.md": "# Project Rules\n\n## TBD\n",
            "ARCHITECTURE_NOTES.md": "# Architecture Notes\n\n## TBD\n",
            "DECISIONS.md": "# Decisions\n\n## TBD\n",
            "KNOWN_FAILURES.md": "# Known Failures\n\n## None yet\n",
        }

        for name, content in files.items():
            (memory_dir / name).write_text(content)
