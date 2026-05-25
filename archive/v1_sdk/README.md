# Archive — v1 Raw SDK Orchestrator (Phase 6 final state)

This folder preserves the hand-written orchestration layer before the
Phase 7 migration to LangGraph.

## What is archived

| File | Description |
|---|---|
| `orchestrator.py` | Full orchestrator: intent classification, parallel agent dispatch via ThreadPoolExecutor, streaming synthesis, JSON logging |
| `intent_classifier.py` | Intent classifier: single Claude API call returns routing JSON with agent list + mode fields |

## Why this was archived

Phase 7 migrates the orchestration layer to LangGraph. The 5 specialist
agents (`agents/*/agent.py`) and all prompts are unchanged — only the
orchestrator and intent classifier are replaced.

This archive exists so the two designs can be compared directly:
- v1 (here): explicit Python, full control, no framework dependency
- v2 (LangGraph): graph-based, typed state, LangSmith observability

## Key design decisions in v1

- **Intent classification**: one Claude API call → JSON with `agents`, `mode`, `article_id` fields
- **Parallel dispatch**: `ThreadPoolExecutor` with one future per agent
- **Synthesis**: streaming via `client.messages.stream()` for multi-agent results
- **Logging**: append-only JSONL at `logs/agent_calls.jsonl` via `shared/logger.py`
- **Validation**: Pydantic schemas in `shared/schemas.py` with case-normalisation on string enums

## Phase completed

Phase 6 — all tests passing:
- 14 routing tests (no API calls)
- 12 integration tests (real API calls, all agents + orchestrator)
