# DeepAgents SDK Integration

This document records how OpenJIA uses DeepAgents SDK and what still belongs to the OpenJIA harness layer.

## Source Notes

- DeepAgents exposes `create_deep_agent(...)` as the main runtime constructor.
- A deep agent can receive a chat model, tools, system prompt, middleware, subagents, permissions, memory, checkpointer, and `response_format`.
- DeepAgents is built on LangGraph/LangChain agent runtime concepts, so invocation uses message inputs and returns a graph state.
- For OpenAI-compatible providers such as MiniMax, OpenJIA creates a LangChain `ChatOpenAI` model with `base_url` and provider API key, then passes it to `create_deep_agent`.
- Models used through DeepAgents must support the tool/structured-output behavior needed by LangChain agents. OpenJIA validates this with `openjia llm-smoke --llm-backend deepagents`.

References:

- https://docs.langchain.com/oss/python/deepagents/quickstart
- https://docs.langchain.com/oss/python/deepagents/customization
- https://docs.langchain.com/oss/python/deepagents/subagents

## Current Integration Shape

OpenJIA keeps its planner-generator-evaluator harness as the outer control plane:

```text
OpenJIA Orchestrator
  -> Planner role
  -> Contract gate
  -> Context packet
  -> Generator role
  -> SelfVerify gate
  -> Evaluator role
  -> Evaluation gate
```

DeepAgents is now available as a runtime backend for JSON-producing role agents:

```text
Planner / Generator
  -> DeepAgentsJSONBackend.generate_json(...)
  -> deepagents.create_deep_agent(...)
  -> LangChain ChatOpenAI model
  -> MiniMax/OpenAI-compatible provider
```

This replaces direct provider-adapter calls when `--llm-backend deepagents` is selected.

## Configuration

Install the optional runtime dependencies:

```powershell
pip install -e ".[deepagents]"
```

MiniMax-backed DeepAgents:

```env
MINIMAX_API_KEY=your_minimax_api_key_here
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
OPENJIA_LLM_BACKEND=deepagents
OPENJIA_LLM_MODEL=MiniMax-M2.7
OPENJIA_DEEPAGENTS_PROVIDER=minimax
```

Smoke test:

```powershell
openjia llm-smoke --llm-backend deepagents --model MiniMax-M2.7
```

## Fallback Policy

The old deterministic generator remains available for offline fixtures and regression tests.

When `--llm-backend deepagents` is used:

- Planner failures are surfaced instead of silently using the deterministic planner.
- Generator failures are surfaced instead of using the deterministic Todo/Web file template.
- The evaluator and gates still decide completion from command/browser evidence.

This makes DeepAgents runs real runtime-agent attempts instead of disguised template runs.

## Boundary

OpenJIA still owns:

- sprint contracts
- allowed file scope
- context packets
- command logs
- evidence packets
- pass/fail gates
- repair packet protocol

DeepAgents owns:

- model runtime invocation
- structured agent execution
- future tool use, memory, subagents, and checkpointing

## Next Upgrade

The next deeper integration should expose OpenJIA tools directly to the DeepAgents Generator:

- guarded file read/write tool
- command runner tool
- evidence writer tool
- repair packet reader

That will let Generator perform multi-step tool use inside the runtime instead of returning all file contents in one structured JSON response.
