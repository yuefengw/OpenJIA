from openjia.agents.planner import Planner
from openjia.schemas.feature_spec import AcceptanceCriterion, Feature, FeatureSpec, Sprint


class RepairingBackend:
    def __init__(self):
        self.calls = 0

    def generate_json(self, *, instructions, prompt, schema):
        self.calls += 1
        if self.calls == 1:
            return {"id": "S001", "goal": "Wrong shape", "features": ["F001"]}
        return {
            "project_goal": "Build app",
            "features": [
                {
                    "id": "F001",
                    "title": "App",
                    "user_value": "Useful",
                    "acceptance_criteria": [
                        {
                            "id": "AC001",
                            "description": "Works",
                            "verification_type": "static_check",
                            "oracle": "Command exits zero",
                        }
                    ],
                }
            ],
            "sprints": [
                {
                    "id": "S001",
                    "goal": "Build app",
                    "features": ["F001"],
                    "verification_commands": ["python -m compileall ."],
                }
            ],
        }


class FragmentThenValidBackend:
    def __init__(self):
        self.calls = 0

    def generate_json(self, *, instructions, prompt, schema):
        self.calls += 1
        if self.calls == 1:
            return {"$ref": "#/$defs/Sprint"}
        return {
            "project_goal": "Build app",
            "features": [
                {
                    "id": "F001",
                    "title": "App",
                    "user_value": "Useful",
                    "acceptance_criteria": [
                        {
                            "id": "AC001",
                            "description": "Works",
                            "verification_type": "static_check",
                            "oracle": "Command exits zero",
                        }
                    ],
                }
            ],
            "sprints": [
                {
                    "id": "S001",
                    "goal": "Build app",
                    "features": ["F001"],
                    "verification_commands": ["python -m compileall ."],
                }
            ],
        }


def test_planner_repairs_invalid_llm_schema(tmp_path):
    backend = RepairingBackend()
    planner = Planner(str(tmp_path), llm_backend=backend)

    spec = planner._generate_llm_spec(
        user_task="Build app",
        env_report="",
        repo_map="",
        constraints="",
    )

    assert backend.calls == 2
    assert spec.project_goal == "Build app"


def test_planner_repairs_schema_fragment_response(tmp_path):
    backend = FragmentThenValidBackend()
    planner = Planner(str(tmp_path), llm_backend=backend)

    spec = planner._generate_llm_spec(
        user_task="Build app",
        env_report="",
        repo_map="",
        constraints="",
    )

    assert backend.calls == 2
    assert spec.project_goal == "Build app"


def test_planner_normalizes_long_running_verification_commands(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"node scripts/validate-app.mjs","test:e2e":"node scripts/browser-e2e.mjs"}}',
        encoding="utf-8",
    )
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.js").write_text("", encoding="utf-8")
    planner = Planner(str(tmp_path))
    spec = FeatureSpec(
        project_goal="Build app",
        features=[
            Feature(
                id="F001",
                title="App",
                user_value="Useful",
                estimated_files=["index.html"],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC001",
                        description="Works",
                        verification_type="e2e",
                        oracle="Command exits zero",
                    )
                ],
            )
        ],
        sprints=[
            Sprint(
                id="S001",
                goal="Build app",
                features=["F001"],
                verification_commands=[
                    "Verify background animation is visible",
                    "python -m http.server 5173",
                ],
            )
        ],
    )

    planner._normalize_spec(spec)

    assert "python -m http.server 5173" not in spec.sprints[0].verification_commands
    assert "Verify background animation is visible" not in spec.sprints[0].verification_commands
    assert "npm run build" in spec.sprints[0].verification_commands
    assert "npm run test:e2e" in spec.sprints[0].verification_commands
    assert "src/app.js" in spec.features[0].estimated_files


def test_planner_adds_creatable_web_files_and_normalizes_paths(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"node scripts/validate-app.mjs"}}',
        encoding="utf-8",
    )
    planner = Planner(str(tmp_path))
    spec = FeatureSpec(
        project_goal="帮我做一个炫酷的todolist网站",
        features=[
            Feature(
                id="F001",
                title="Todo",
                user_value="Useful",
                estimated_files=["/index.html", "workspace/src/app.js"],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC001",
                        description="Works",
                        verification_type="e2e",
                        oracle="Command exits zero",
                    )
                ],
            )
        ],
        sprints=[
            Sprint(
                id="S001",
                goal="Build todo",
                features=["F001"],
                verification_commands=["npm run build"],
            )
        ],
    )

    planner._normalize_spec(spec)

    assert "/index.html" not in spec.features[0].estimated_files
    assert "workspace/src/app.js" not in spec.features[0].estimated_files
    assert "index.html" in spec.features[0].estimated_files
    assert "src/app.js" in spec.features[0].estimated_files
    assert "src/styles.css" in spec.features[0].estimated_files


def test_planner_canonicalizes_common_root_web_assets(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"node scripts/validate-app.mjs"}}',
        encoding="utf-8",
    )
    planner = Planner(str(tmp_path))
    spec = FeatureSpec(
        project_goal="Build a todo web app",
        features=[
            Feature(
                id="F001",
                title="Todo",
                user_value="Useful",
                estimated_files=["app.js", "style.css", "index.html"],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC001",
                        description="Todo works",
                        verification_type="e2e",
                        oracle="Command exits zero",
                    )
                ],
            )
        ],
        sprints=[
            Sprint(
                id="S001",
                goal="Build todo",
                features=["F001"],
                verification_commands=["npm run build"],
            )
        ],
    )

    planner._normalize_spec(spec)

    assert "app.js" not in spec.features[0].estimated_files
    assert "style.css" not in spec.features[0].estimated_files
    assert "src/app.js" in spec.features[0].estimated_files
    assert "src/styles.css" in spec.features[0].estimated_files
    assert "tests/acceptance.spec.mjs" in spec.features[0].estimated_files


def test_deepagents_planner_protects_web_runtime_scaffold(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"node scripts/validate-app.mjs","test:e2e":"node scripts/browser-e2e.mjs"}}',
        encoding="utf-8",
    )
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "validate-app.mjs").write_text("", encoding="utf-8")
    (tmp_path / "scripts" / "browser-e2e.mjs").write_text("", encoding="utf-8")
    planner = Planner(str(tmp_path), llm_backend=FragmentThenValidBackend(), llm_backend_name="deepagents")
    spec = FeatureSpec(
        project_goal="Build a todo web app",
        features=[
            Feature(
                id="F001",
                title="Todo",
                user_value="Useful",
                estimated_files=[
                    "index.html",
                    "src/app.js",
                    "scripts/browser-e2e.mjs",
                    "scripts/validate-app.mjs",
                    "package.json",
                ],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC001",
                        description="Todo works",
                        verification_type="e2e",
                        oracle="Command exits zero",
                    )
                ],
            )
        ],
        sprints=[
            Sprint(
                id="S001",
                goal="Build todo",
                features=["F001"],
                verification_commands=["npm run build", "npm run test:e2e"],
            )
        ],
    )

    planner._normalize_spec(spec)

    assert "index.html" in spec.features[0].estimated_files
    assert "src/app.js" in spec.features[0].estimated_files
    assert "scripts/browser-e2e.mjs" not in spec.features[0].estimated_files
    assert "scripts/validate-app.mjs" not in spec.features[0].estimated_files
    assert "package.json" not in spec.features[0].estimated_files
    assert "scripts/browser-e2e.mjs" in spec.sprints[0].must_not_touch
