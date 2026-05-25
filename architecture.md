# Decision Intelligence Co-Pilot — Architecture & Design Document

**Version:** 0.1 (Learning Project)
**Last Updated:** 2026-05-03

---

## 1. Overview

The Decision Intelligence Co-Pilot is a multi-agent, multimodal AI system that helps business users make better decisions across customer experience, inventory, pricing, product, and marketing domains. Users interact through natural language; the system routes questions to specialized agents, synthesizes their outputs, and returns a unified recommendation.

---

## 2. System Goals

- Answer complex cross-domain business questions from a single natural language prompt
- Analyze multimodal inputs (text, images, behavioral signals)
- Produce structured, explainable recommendations — not just answers
- Serve as a learning platform for AI-native system design

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│              (Streamlit / Gradio / CLI)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │  Natural language query + optional
                         │  multimodal inputs (images, files)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator Agent                          │
│                                                                 │
│  • Parses and classifies the intent of the user query           │
│  • Decomposes complex queries into sub-tasks                    │
│  • Routes sub-tasks to one or more specialist agents            │
│  • Collects agent responses                                     │
│  • Synthesizes a unified recommendation                         │
└──┬──────────┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐
│  CV  │  │  IS  │  │  PP  │  │  PD  │  │   CI     │
│Agent │  │Agent │  │Agent │  │Agent │  │  Agent   │
└──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  └────┬─────┘
   │          │          │          │           │
   └──────────┴──────────┴──────────┴───────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Shared Context  │
              │  & Memory Store  │
              └──────────────────┘
```

**Agent Key:** CV = Customer Voice, IS = Inventory & Supply, PP = Pricing & Profit, PD = Product Discovery, CI = Campaign Intelligence

---

## 4. Agent Specifications

### 4.1 Orchestrator Agent

| Property | Detail |
|---|---|
| Role | Central coordinator and synthesizer |
| Input | Natural language query + user context + optional files/images |
| Output | Structured final recommendation with citations from specialist agents |
| Model | Claude Sonnet 4.6 (claude-sonnet-4-6) |

**Responsibilities:**
- Intent classification: identify which domain(s) are relevant
- Query decomposition: break compound questions into sub-tasks
- Agent dispatch: call one or more specialist agents (sequentially or in parallel)
- Response synthesis: merge specialist outputs into a coherent recommendation
- Conflict resolution: surface disagreements between agents rather than silently hiding them

**System Prompt Design Principles:**
- Define a clear decision-making persona (business advisor, not just a summarizer)
- Instruct it to always cite which agent produced which insight
- Require it to flag uncertainty and missing data explicitly

---

### 4.2 Customer Voice Agent

| Property | Detail |
|---|---|
| Role | Interpret customer signals and surface unmet needs |
| Input | Text reviews, support tickets, survey responses, behavioral logs, product images |
| Output | Sentiment scores, theme clusters, top unmet needs, urgency flags |
| Model | Claude Sonnet 4.6 (vision-enabled for image inputs) |
| Key Techniques | Sentiment analysis, topic modeling, multimodal signal fusion |

**Data Sources:**
- Women's Clothing E-Commerce Reviews (Kaggle) — general clothing sentiment, thematically aligned with H&M product categories
- H&M article mapping (`article_review_map.csv`) — category-based mapping from review Clothing IDs to H&M article IDs, enabling product-level demo queries
- Note: H&M's open dataset contains no customer review text; the review dataset is a category-level proxy, not H&M-specific data

**Output Schema (JSON):**
```json
{
  "overall_sentiment": "negative | neutral | positive",
  "sentiment_score": 0.0,
  "themes": [
    { "theme": "string", "frequency": 0, "sentiment": "string", "example_quotes": [] }
  ],
  "unmet_needs": ["string"],
  "urgency_flags": ["string"],
  "data_sources_used": ["string"]
}
```

---

### 4.3 Inventory & Supply Agent

| Property | Detail |
|---|---|
| Role | Model demand patterns and surface supply risks |
| Input | Historical sales data, inventory levels, lead times, supplier data |
| Output | Demand forecast, stockout risk, reorder recommendations |
| Model | Claude Sonnet 4.6 + external forecasting library (Prophet / statsforecast) |
| Key Techniques | Time-series forecasting, anomaly detection, constraint optimization |

**Architecture Note:** Claude handles interpretation and recommendation; a Python forecasting library (Prophet or statsforecast) handles the numerical computation. Claude does not do time-series math directly.

**Output Schema (JSON):**
```json
{
  "forecast_horizon_days": 30,
  "demand_forecast": [{ "date": "YYYY-MM-DD", "predicted_units": 0 }],
  "stockout_risk": [{ "sku": "string", "risk_level": "low|medium|high", "days_until_stockout": 0 }],
  "reorder_recommendations": [{ "sku": "string", "reorder_quantity": 0, "reorder_by_date": "YYYY-MM-DD" }]
}
```

---

### 4.4 Pricing & Profit Agent

| Property | Detail |
|---|---|
| Role | Analyze price elasticity and recommend margin-optimal pricing |
| Input | H&M transaction history (article_id + normalized price per transaction) |
| Output | Elasticity estimates, scenario comparisons, recommended price points |
| Model | Claude Sonnet 4.6 |
| Key Techniques | Price elasticity modeling, scenario simulation, demand-at-price aggregation |

**Data Source:** H&M `transactions_train.csv` — same unified dataset as Inventory and Campaign agents. Prices are H&M normalized values (0.0–1.0 scale). Pre-aggregated on first call and cached in memory for the session.

**Output Schema (JSON):**
```json
{
  "current_price": 0.0,
  "recommended_price": 0.0,
  "estimated_margin_impact_pct": 0.0,
  "elasticity_estimate": 0.0,
  "scenarios": [
    { "label": "string", "price": 0.0, "projected_revenue": 0.0, "projected_margin": 0.0 }
  ],
  "confidence": "low|medium|high",
  "assumptions": ["string"]
}
```

---

### 4.5 Product Discovery Agent

| Property | Detail |
|---|---|
| Role | Identify emerging trends, product gaps, and adjacent opportunities |
| Input | Product catalog (text + images), market data, customer themes from CV Agent |
| Output | Trend signals, similar products, opportunity scores, visual cluster map |
| Model | Claude Sonnet 4.6 (vision) + embedding model |
| Key Techniques | Multimodal embeddings, semantic similarity search, trend detection |

**Architecture Note:**
- Use Claude vision to extract structured attributes from product images
- Use a text+image embedding model (e.g., OpenAI CLIP or `sentence-transformers`) to build a joint embedding space
- Store embeddings in a vector database (e.g., ChromaDB for local dev, Pinecone/Weaviate for scale)

**Output Schema (JSON):**
```json
{
  "trending_categories": [{ "category": "string", "trend_score": 0.0, "evidence": [] }],
  "similar_products": [{ "product_id": "string", "similarity_score": 0.0 }],
  "opportunity_areas": [{ "area": "string", "opportunity_score": 0.0, "rationale": "string" }]
}
```

---

### 4.6 Campaign Intelligence Agent

| Property | Detail |
|---|---|
| Role | Identify when and where to run promotions or price discounts based on demand signals |
| Input | Transaction history (demand trend), inventory levels, product metadata |
| Output | Promotion recommendation, suggested discount, campaign timing, risk of inaction |
| Model | Claude Sonnet 4.6 |
| Key Techniques | Demand trend analysis, inventory pressure scoring, seasonal pattern detection |

**Architecture Note:** Demand trends are computed from transaction history (recent vs earlier period). Claude reasons over the combined demand + inventory signal to recommend campaign type and timing. Pairs naturally with the Pricing Agent — inventory routes both when a query mentions both demand slowdown and optimal pricing.

**Output Schema (JSON):**
```json
{
  "article_id": "string",
  "demand_trend": "DECLINING | STABLE | GROWING",
  "demand_change_pct": 0.0,
  "inventory_status": "HIGH | NORMAL | LOW",
  "promotion_recommendation": "PROMOTE_NOW | MONITOR | HOLD",
  "suggested_discount_pct": 0,
  "campaign_type": "PRICE_DISCOUNT | BUNDLE | SEASONAL_CLEARANCE | LOYALTY_OFFER | NONE",
  "campaign_timing": "string",
  "rationale": "string",
  "risk_of_inaction": "string",
  "confidence": "HIGH | MEDIUM | LOW"
}
```

---

## 5. Inter-Agent Communication

### Message Format

All agents communicate via a shared message schema:

```python
@dataclass
class AgentMessage:
    source_agent: str          # e.g., "orchestrator", "customer_voice"
    target_agent: str
    task_id: str               # UUID, ties sub-tasks to a parent query
    query: str
    context: dict              # shared context window
    inputs: dict               # structured inputs for the target agent
    outputs: dict | None       # populated by the target agent on response
    status: str                # "pending" | "running" | "complete" | "failed"
    timestamp: str
```

### Communication Patterns

| Pattern | When to use |
|---|---|
| Sequential | Agent B needs Agent A's output as input (e.g., CI Agent paired with Pricing Agent for discount optimization) |
| Parallel | Independent sub-tasks (e.g., CV + IS + PP all queried simultaneously for a complex question) |
| Broadcast | Orchestrator needs all agents to respond and then synthesizes |

---

## 6. Shared Context & Memory

```
┌─────────────────────────────────────────────┐
│             Shared Context Store            │
│                                             │
│  session_context:  { query, user, history } │
│  agent_outputs:    { agent_id → output }    │
│  working_memory:   { key facts this run }   │
└─────────────────────────────────────────────┘
```

- **Session context:** In-memory Python dict for the duration of one user query
- **Working memory:** Key facts extracted by agents that other agents may need
- **Persistent memory (future):** Store past decisions, user preferences, and learned patterns across sessions (SQLite or a simple JSON log for the learning phase)

---

## 7. Multimodal Input Handling

| Input Type | Accepted Formats | Handling |
|---|---|---|
| Text | Plain text, CSV, JSON | Direct to agent context |
| Images | PNG, JPG, WEBP | Base64-encoded, passed to Claude vision |
| Behavioral data | CSV / JSON event logs | Parsed into structured summary before agent call |
| Documents | PDF (future) | Extract text via pypdf, then treat as text |

All multimodal inputs are normalized into a structured `inputs` dict before being passed to an agent.

---

## 8. Technology Stack

### Core

| Component | Choice | Rationale |
|---|---|---|
| LLM | Claude Sonnet 4.6 (claude-sonnet-4-6) | Vision support, tool use, long context |
| Language | Python 3.11+ | Ecosystem for ML/data, typing support |
| API Client | `anthropic` Python SDK | Native Claude support, streaming, tool use |

### Data & ML

| Component | Choice | Notes |
|---|---|---|
| Forecasting | Prophet or statsforecast | Time-series for Inventory Agent |
| Embeddings | sentence-transformers / CLIP | Multimodal embeddings for Product Discovery |
| Vector DB | ChromaDB (dev) → Pinecone (scale) | Similarity search |
| Data manipulation | pandas | Standard tabular data |

### Infrastructure (Learning Phase)

| Component | Choice | Notes |
|---|---|---|
| UI | Streamlit | Fast to build, good for data apps |
| Config management | python-dotenv | API keys, environment vars |
| Logging | Python `logging` + JSON formatter | Structured logs for agent observability |
| Testing | pytest | One test file per agent |
| Storage | Local filesystem + SQLite | No cloud dependency for learning phase |

---

## 9. Project Folder Structure

```
Decision Intelligence Co-Pilot/
│
├── architecture.md                  # This document
│
├── orchestrator/
│   ├── orchestrator_agent.py        # Main orchestrator logic
│   ├── intent_classifier.py         # Route query to correct agents
│   └── synthesizer.py               # Merge agent outputs
│
├── agents/
│   ├── base_agent.py                # Abstract base class all agents inherit
│   ├── customer_voice/
│   │   ├── agent.py
│   │   ├── prompts.py
│   │   └── tests/
│   ├── inventory_supply/
│   │   ├── agent.py
│   │   ├── forecaster.py
│   │   ├── prompts.py
│   │   └── tests/
│   ├── pricing_profit/
│   │   ├── agent.py
│   │   ├── prompts.py
│   │   └── tests/
│   ├── product_discovery/
│   │   ├── agent.py
│   │   ├── embeddings.py
│   │   ├── prompts.py
│   │   └── tests/
│   └── campaign_intelligence/
│       ├── agent.py
│       ├── trend_analyzer.py
│       ├── prompts.py
│       └── tests/
│
├── shared/
│   ├── message_schema.py            # AgentMessage dataclass
│   ├── context_store.py             # Session context management
│   └── multimodal_handler.py        # Normalize images/docs/text inputs
│
├── data/
│   ├── synthetic/                   # Sample datasets for development
│   └── schemas/                     # Expected input data formats
│
├── ui/
│   └── app.py                       # Streamlit interface
│
├── notebooks/
│   └── exploration/                 # Jupyter notebooks for experimentation
│
├── .env.example                     # Template for API keys
└── requirements.txt
```

---

## 10. Key Design Decisions & Tradeoffs

| Decision | Choice | Tradeoff |
|---|---|---|
| Agent communication | Shared in-memory context dict | Simple to start; won't scale to distributed agents — acceptable for learning phase |
| LLM for all agents | Single Claude model | Consistent interface; some agents (forecasting) need external compute layers |
| Orchestration style | Centralized orchestrator | Easier to reason about; limits emergent multi-agent collaboration |
| Output format | Structured JSON per agent | Enables downstream synthesis; requires careful prompt engineering to enforce |
| Frameworks (current) | Raw Anthropic SDK, no LangChain/AutoGen | Forces understanding of fundamentals; more code, more learning |
| Frameworks (future) | LangGraph for orchestration, LangChain for tool/chain abstractions | Reduces boilerplate once fundamentals are solid; introduces after Phase 6 |

---

## 11. Observability & Evaluation

### Per-Agent Logging (every call)
```json
{
  "timestamp": "ISO8601",
  "agent": "customer_voice",
  "task_id": "uuid",
  "input_tokens": 0,
  "output_tokens": 0,
  "latency_ms": 0,
  "status": "complete | failed",
  "input_summary": "...",
  "output_summary": "..."
}
```

### Evaluation Strategy
- **Golden test set per agent:** 5–10 known input/output pairs, validated by hand
- **Orchestrator routing accuracy:** Does it route to the right agent(s) for known query types?
- **Output schema validation:** Use `pydantic` to validate every agent's JSON output
- **End-to-end integration test:** One full query through all 5 agents, assert non-empty synthesis

---

## 12. Build Sequence (Aligned to Learning Plan)

| Phase | What to Build | Milestone |
|---|---|---|
| 1 | Foundations — Claude API, agent loop, tool use | Single agent responds correctly to one query |
| 2 | Customer Voice Agent end-to-end | Structured JSON output from real review data |
| 3 | Orchestrator + 2 agents (CV + Pricing) | Query routed and synthesized correctly |
| 4 | Multimodal — Product Discovery Agent | Image + text input handled, embeddings working |
| 5 | All 5 agents + full orchestration | Full pipeline from NL query to unified recommendation |
| 6 | UI + observability + evals | Streamlit UI, logging in place, pytest suite passing |

---

## 13. Future Considerations (Post-Learning)

- **Streaming responses:** Stream agent outputs to UI in real-time rather than waiting for full completion
- **Async agent execution:** Run independent agents in parallel using `asyncio`
- **Persistent memory:** Store and retrieve past decisions and user preferences across sessions
- **Fine-tuning:** Consider fine-tuning on domain-specific data once baseline prompts are stable
- **Human-in-the-loop:** Add approval steps before high-stakes recommendations (e.g., pricing changes)
- **Agent self-evaluation:** Have agents rate their own confidence and flag low-confidence outputs for review

---

## 15. Advanced Reasoning & Adaptive Learning (Phase 8+)

These capabilities are intentionally deferred until the full pipeline is stable. Introducing them early adds complexity before the foundation is solid.

### 15.1 Deep Reasoning Mechanisms

**Chain of Thought (CoT)** — instruct Claude to reason step by step before producing its final JSON output. The reasoning trace is visible, making recommendations explainable.

```
Implementation: Add "Think step by step before answering. Show your reasoning,
then output the final JSON." to each agent's system prompt.
```

**Tree of Thought (ToT)** — Claude explores multiple reasoning paths in parallel before selecting the best one. Useful for complex decisions like pricing scenarios or inventory tradeoffs where there are competing options to evaluate.

```
Implementation: Prompt Claude to generate 3 candidate approaches,
evaluate each, then select and output the best one.
```

**When to introduce:**
- CoT: Phase 6 (hardening) — low effort, high explainability gain
- ToT: Phase 8 — after LangGraph migration, since ToT benefits from graph-based branching

### 15.2 Adaptive Learning — Agents That Improve Over Time

As users accept, reject, or refine agent recommendations, the system learns from that feedback.

**Approach 1 — Feedback logging (Phase 6+)**
Log every recommendation + user decision. Build a feedback store that agents can query: "Here are past recommendations the user accepted/rejected — use these to calibrate your output."

**Approach 2 — Dynamic few-shot examples (Phase 7+)**
Automatically build a library of good examples from accepted recommendations. Inject the most relevant ones into the prompt as few-shot examples. The agent's quality improves as the example library grows.

**Approach 3 — Reinforcement Learning from Human Feedback (RLHF, Phase 8+)**
Full fine-tuning loop where accepted/rejected recommendations are used to update model weights. This requires significant data volume and infrastructure — a longer-term goal.

| Mechanism | Complexity | When | What it gives you |
|---|---|---|---|
| Chain of Thought | Low | Phase 6 | Explainable reasoning |
| Tree of Thought | Medium | Phase 8 | Better decisions on complex tradeoffs |
| Feedback logging | Low | Phase 6 | Foundation for all learning |
| Dynamic few-shot | Medium | Phase 7 | Agents improve with use |
| RLHF fine-tuning | High | Phase 8+ | Deep model-level adaptation |

**Reading (save for later):**
- [Anthropic — Chain of Thought Prompting](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/chain-of-thought)
- [Tree of Thoughts paper](https://arxiv.org/abs/2305.10601)
- [Few-shot prompting guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-examples)

---

## 14. Framework Evolution Path (LangChain / LangGraph)

**When to introduce:** After Phase 6, once the full raw-SDK system is working end-to-end.

**Why wait:** LangChain and LangGraph are abstractions over the exact patterns you will have built by hand. Introducing them after you've felt the manual friction means every abstraction will make sense and you'll know when to use vs. bypass it.

### What LangChain/LangGraph replaces in this system

| Current (Raw SDK) | Future (LangChain/LangGraph) |
|---|---|
| Hand-written agent loop | `LangGraph` — stateful graph-based agent execution |
| Custom `AgentMessage` schema + routing | `LangGraph` nodes and edges |
| Manual tool call handling | `LangChain` tool decorators (`@tool`) |
| Custom context store (dict) | `LangGraph` state management |
| Custom prompt templates in `prompts.py` | `LangChain` `ChatPromptTemplate` |
| Manual retry/error handling | LangChain built-in retry wrappers |
| Custom logging | LangSmith — LangChain's observability platform |

### Migration approach (Phase 7)
1. Keep all 5 agent business logic unchanged
2. Replace the orchestrator's routing and state management with a LangGraph graph
3. Replace prompt template strings with `ChatPromptTemplate`
4. Add LangSmith for tracing and observability
5. Compare: same results, less orchestration code

### Packages to add at that point
```
pip install langchain langchain-anthropic langgraph langsmith
```

### Reading (save for Phase 7)
- [LangGraph — Introduction](https://langchain-ai.github.io/langgraph/)
- [LangGraph vs raw agents](https://langchain-ai.github.io/langgraph/concepts/why-langgraph/)
- [LangSmith — Tracing](https://docs.smith.langchain.com/)
