"""VCH CLI - Command line interface for VCH harness."""

import click
from pathlib import Path
import json
import sys

from vch.orchestrator import HarnessOrchestrator
from vch.config import Config


@click.group()
@click.version_option(version="0.1.0")
def main():
    """VCH: Verifiable Contextual Harness for DeepAgents SDK."""
    pass


@main.command()
@click.argument("repo", default=".")
@click.option("--max-sprints", default=3, help="Maximum number of sprints")
@click.option("--max-repair-attempts", default=3, help="Maximum repair attempts per sprint")
def init(repo: str, max_sprints: int, max_repair_attempts: int):
    """Initialize VCH harness in a repository."""
    from vch.agents.initializer import Initializer

    repo_path = Path(repo).absolute()
    if not repo_path.exists():
        click.echo(f"Error: Repository not found: {repo_path}", err=True)
        sys.exit(1)

    initializer = Initializer(str(repo_path))
    run_state = initializer.invoke("")

    click.echo(f"Initialized VCH harness in {repo_path}")
    click.echo(f"Run ID: {run_state.run_id}")


@main.command()
@click.argument("task")
@click.argument("repo", default=".")
@click.option("--max-sprints", default=3, help="Maximum number of sprints")
@click.option("--max-repair-attempts", default=3, help="Maximum repair attempts per sprint")
@click.option("--run-id", default=None, help="Continue existing run")
@click.option("--llm-backend", default="deterministic", help="LLM backend: deterministic|openai|minimax|openai-compatible")
@click.option("--model", default="gpt-4.1", help="LLM model name when using an LLM backend")
def plan(
    task: str,
    repo: str,
    max_sprints: int,
    max_repair_attempts: int,
    run_id: str,
    llm_backend: str,
    model: str,
):
    """Generate feature spec and roadmap for a task."""
    from vch.agents.planner import Planner
    from vch.gates.plan_feasibility import PlanFeasibilityGate

    repo_path = Path(repo).absolute()
    harness_dir = repo_path / ".harness"

    # Check if initialized
    if not harness_dir.exists():
        click.echo("Error: VCH not initialized. Run 'vch init' first.", err=True)
        sys.exit(1)

    planner = Planner(str(repo_path), llm_backend_name=llm_backend, model=model)
    spec = planner.invoke(task)

    # Run feasibility gate
    gate = PlanFeasibilityGate()
    result = gate.validate(spec)

    click.echo(f"\nFeasibility Score: {result.score}")
    click.echo(f"Recommendation: {result.recommendation}")

    if result.issues:
        click.echo("\nIssues:")
        for issue in result.issues:
            prefix = "[ERROR]" if issue.severity == "error" else "[WARN]"
            click.echo(f"  {prefix} {issue.category}: {issue.message}")


@main.command()
@click.argument("task")
@click.argument("repo", default=".")
@click.option("--max-sprints", default=3, help="Maximum number of sprints")
@click.option("--max-repair-attempts", default=3, help="Maximum repair attempts per sprint")
@click.option("--llm-backend", default="deterministic", help="LLM backend: deterministic|openai|minimax|openai-compatible")
@click.option("--model", default="gpt-4.1", help="LLM model name when using an LLM backend")
def run(
    task: str,
    repo: str,
    max_sprints: int,
    max_repair_attempts: int,
    llm_backend: str,
    model: str,
):
    """Run VCH harness for a task."""
    repo_path = Path(repo).absolute()

    orchestrator = HarnessOrchestrator(
        repo_root=str(repo_path),
        max_sprints=max_sprints,
        max_repair_attempts=max_repair_attempts,
        llm_backend=llm_backend,
        llm_model=model,
    )

    run_state = orchestrator.run(task)

    click.echo(f"\nRun completed: {run_state.run_id}")
    click.echo(f"Status: {run_state.status}")
    click.echo(f"Sprints: {len(run_state.sprints)}")


@main.command("eval")
@click.argument("sprint_id")
@click.argument("repo", default=".")
def eval_sprint(sprint_id: str, repo: str):
    """Run evaluator for a specific sprint."""
    repo_path = Path(repo).absolute()
    harness_dir = repo_path / ".harness"
    sprint_dir = harness_dir / "sprints" / sprint_id
    contract_path = sprint_dir / "CONTRACT.yaml"

    if not contract_path.exists():
        click.echo(f"Error: Contract not found: {contract_path}", err=True)
        sys.exit(1)

    import yaml
    from vch.schemas.contract import Contract
    from vch.agents.evaluator import Evaluator

    with open(contract_path) as f:
        contract_data = yaml.safe_load(f)
    contract = Contract(**contract_data)

    evaluator = Evaluator(str(repo_path))
    git_base = "HEAD"
    git_head = "HEAD"

    eval_report = evaluator.invoke(sprint_id, contract, git_base, git_head)

    click.echo(f"\nSprint: {sprint_id}")
    click.echo(f"Status: {eval_report.overall_status}")
    click.echo(f"Summary: {eval_report.summary}")


@main.command("run-sprint")
@click.argument("sprint_id")
@click.argument("repo", default=".")
def run_sprint(sprint_id: str, repo: str):
    """Run the currently planned harness flow for a specific sprint."""
    repo_path = Path(repo).absolute()
    sprint_dir = repo_path / ".harness" / "sprints" / sprint_id
    if not sprint_dir.exists():
        click.echo(f"Error: Sprint not found: {sprint_dir}", err=True)
        sys.exit(1)

    click.echo(
        "run-sprint requires a persisted orchestrator sprint selector; "
        "use 'vch run' for the current deterministic MVP."
    )
    sys.exit(2)


@main.command("llm-smoke")
@click.option("--llm-backend", default="minimax", help="LLM backend: openai|minimax|openai-compatible")
@click.option("--model", default=None, help="LLM model name")
def llm_smoke(llm_backend: str, model: str):
    """Run a small JSON-only LLM connectivity check."""
    from vch.llm import LLMConfigurationError, make_llm_backend

    try:
        backend = make_llm_backend(llm_backend, model)
        if backend is None:
            click.echo("Error: deterministic backend does not call an LLM.", err=True)
            sys.exit(1)
        result = backend.generate_json(
            instructions="Return valid JSON only.",
            prompt="Return a JSON object with ok=true and provider='vch'.",
            schema={
                "title": "vch_smoke_test",
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "provider": {"type": "string"},
                },
                "required": ["ok", "provider"],
                "additionalProperties": True,
            },
        )
    except (LLMConfigurationError, ValueError) as error:
        click.echo(f"LLM smoke test failed: {error}", err=True)
        sys.exit(1)

    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@main.command()
@click.argument("repo", default=".")
def status(repo: str):
    """Show VCH status."""
    repo_path = Path(repo).absolute()
    harness_dir = repo_path / ".harness"
    run_state_path = harness_dir / "RUN_STATE.json"

    if not run_state_path.exists():
        click.echo("Error: VCH not initialized. Run 'vch init' first.", err=True)
        sys.exit(1)

    with open(run_state_path) as f:
        run_state = json.load(f)

    click.echo(f"Run: {run_state['run_id']}")
    click.echo(f"Status: {run_state['status']}")
    click.echo(f"Current phase: {run_state['current_phase']}")
    click.echo(f"Current sprint: {run_state['current_sprint']}")
    click.echo(f"Last error: {run_state.get('last_error', 'None')}")

    if run_state.get("sprints"):
        click.echo("\nSprints:")
        for sprint in run_state["sprints"]:
            click.echo(f"  {sprint['id']}: {sprint['status']}")


@main.command()
@click.argument("sprint_id")
@click.argument("repo", default=".")
def repair(sprint_id: str, repo: str):
    """Attempt repair for a failed sprint."""
    repo_path = Path(repo).absolute()
    harness_dir = repo_path / ".harness"
    sprint_dir = harness_dir / "sprints" / sprint_id
    eval_report_path = sprint_dir / "EVAL_REPORT.json"

    if not eval_report_path.exists():
        click.echo(f"Error: Eval report not found: {eval_report_path}", err=True)
        sys.exit(1)

    click.echo(f"Repair for sprint {sprint_id} not yet implemented.")
    click.echo("Use 'vch run' to restart the full harness.")


@main.command()
@click.argument("sprint_id")
@click.argument("repo", default=".")
def trace(sprint_id: str, repo: str):
    """Show trace information for a sprint."""
    repo_path = Path(repo).absolute()
    harness_dir = repo_path / ".harness"
    sprint_dir = harness_dir / "sprints" / sprint_id
    log_index_path = sprint_dir / "LOG_INDEX.md"

    if not log_index_path.exists():
        click.echo(f"Error: Log index not found: {log_index_path}", err=True)
        sys.exit(1)

    click.echo(log_index_path.read_text())


if __name__ == "__main__":
    main()
