# Architecture Diagrams

Render these in VS Code with the **Markdown Preview Mermaid Support** extension,
or view directly on GitHub (Mermaid renders natively in GitHub markdown).

---

## Reference Architecture — Raw Anthropic SDK (pre-migration)

```mermaid
flowchart TD
    UI["🖥️ Streamlit UI\nui/app.py"]

    subgraph ORC["Orchestrator — orchestrator.py"]
        IC["Intent Classifier\n① Claude API call → routing JSON"]
        DISP["Parallel Dispatcher\n② ThreadPoolExecutor"]
        SYNTH["Synthesizer\n③ Claude streaming"]
    end

    subgraph AGENTS["Specialist Agents"]
        CV["Customer Voice\nagent.py"]
        PP["Pricing & Profit\nagent.py"]
        PD["Product Discovery\nagent.py"]
        IS["Inventory & Supply\nagent.py"]
        CI["Campaign Intelligence\nagent.py"]
    end

    subgraph DATA["Data Layer"]
        CHROMA1["ChromaDB\nReviews index\n23K reviews"]
        CHROMA2["ChromaDB\nArticles index\n10K products"]
        SQLITE["SQLite — retail.db\nprice_points\ndemand_summary\ndemand_daily"]
        SNAP["CSV\ninventory_snapshot.csv"]
    end

    subgraph SHARED["Shared Infrastructure"]
        SCHEMA["Pydantic Schemas\nshared/schemas.py\ncase-normalised enums"]
        LOGGER["JSON Logger\nshared/logger.py\nlogs/agent_calls.jsonl"]
    end

    UI -->|"natural language query"| IC
    IC -->|"agents list + mode + article_id"| DISP
    DISP -->|"parallel"| CV
    DISP -->|"parallel"| PP
    DISP -->|"parallel"| PD
    DISP -->|"parallel"| IS
    DISP -->|"parallel"| CI
    CV & PP & PD & IS & CI --> SYNTH
    SYNTH -->|"streamed recommendation"| UI

    CV <--> CHROMA1
    PD <--> CHROMA2
    PP <--> SQLITE
    IS <--> SQLITE
    CI <--> SQLITE
    IS <--> SNAP
    CI <--> SNAP

    CV & PP & PD & IS & CI -. "validate()" .-> SCHEMA
    ORC -. "log()" .-> LOGGER
```

---

## Current Architecture — LangGraph

```mermaid
flowchart TD
    UI["🖥️ Streamlit UI"]

    subgraph GRAPH["LangGraph StateGraph"]
        direction TB
        IC["classify_intent\nnode"]

        subgraph PAR["Parallel agent nodes\n(Send API — fan-out)"]
            CV["customer_voice\nnode"]
            PP["pricing_profit\nnode"]
            PD["product_discovery\nnode"]
            IS["inventory_supply\nnode"]
            CI["campaign_intelligence\nnode"]
        end

        SYNTH["synthesize\nnode"]
        ENDNODE(["END"])
    end

    subgraph STATE["RetailState — TypedDict"]
        S1["query: str"]
        S2["intent: dict"]
        S3["agent_results: dict"]
        S4["formatted: str"]
        S5["agent_timings: dict"]
    end

    subgraph OBS["LangSmith Observability"]
        LS["Visual trace per run\nPer-node latency\nInput + output per step\nError replay"]
    end

    UI -->|"query"| IC
    IC -->|"conditional edges\nroute_to_agents()"| CV & PP & PD & IS & CI
    CV & PP & PD & IS & CI --> SYNTH
    SYNTH --> ENDNODE
    ENDNODE -->|"RetailState.formatted"| UI

    GRAPH <-. "state flows\nthrough nodes" .-> STATE
    GRAPH <-. "auto-traced\nby LangSmith" .-> OBS
```

---

## What changed in the migration

| Concept | Raw SDK (reference) | LangGraph (current) |
|---|---|---|
| Routing logic | `if/elif` in `orchestrator.py` | Conditional edges on the graph |
| Parallel dispatch | `ThreadPoolExecutor` | LangGraph `Send` API (fan-out) |
| State passing | Plain `dict` returned from `run()` | Typed `RetailState` TypedDict with merge reducers |
| Observability | `print()` + JSONL log file | LangSmith visual trace |
| Agent code | ✅ Unchanged | ✅ Unchanged |
| Prompts | ✅ Unchanged | ✅ Unchanged |
| Tests | 26 passing | 25 passing |

## What stayed the same

All 5 `agents/*/agent.py` files — the actual business logic, data access,
and Claude API calls — were not touched. LangGraph wraps the orchestration
layer only. The agents became nodes; their existing methods are called
from within those nodes.
