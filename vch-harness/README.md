# VCH: Verifiable Contextual Harness

A harness system for DeepAgents SDK that ensures verifiable, constrained execution of long-running software development tasks.

## Installation

```bash
pip install -e .
```

## Usage

```bash
vch init
vch plan "build a todo app"
vch run "build a todo app"
```

## LLM Backend

The harness defaults to deterministic mode so tests and gates stay reproducible.

To use OpenAI for planner generation:

```bash
pip install -e ".[llm]"
$env:OPENAI_API_KEY="sk-..."
vch plan "build a todo app with persistence" --llm-backend openai --model gpt-4.1
```

To use MiniMax through its OpenAI-compatible API:

```bash
pip install -e ".[llm]"
$env:MINIMAX_API_KEY="your-minimax-key"
vch plan "build a todo app with persistence" --llm-backend minimax --model MiniMax-M2.7
```

By default this uses the China-region OpenAI-compatible endpoint:
`https://api.minimaxi.com/v1`. Override with `MINIMAX_BASE_URL` if your key belongs to another region.

The LLM only proposes structured planning artifacts. The harness still enforces schemas, gates, contracts, self-verification, evaluator reports, and feature ledger updates.

## Architecture

See `VCH_DeepAgents_Harness_Implementation_Spec.md` for full specification.
See `docs/HARNESS_DESIGN_PRINCIPLES.md` for the article-derived design principles.
