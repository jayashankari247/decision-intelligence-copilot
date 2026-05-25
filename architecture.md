# Decision Intelligence Co-Pilot — Architecture & Design

---

## 1. Overview

The Decision Intelligence Co-Pilot is a multi-agent AI system for retail operations. A single natural language question is classified by intent, routed in parallel to one or more specialist agents, and synthesized into a unified streamed recommendation. Five specialist agents cover customer sentiment, pricing, product catalog, inventory, and campaign planning — each backed by purpose-built data retrieval and validated structured output.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit UI  (ui/app.py)                   │
└────────────────────────┬────────────────────────────────────────┘
                         │  natural language query
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator  (orchestrator/)                 │
│                                                                  │
│  1. Intent Classifier  — Claude API call → routing JSON          │
│     { agents: [...], mode: "search|summary", article_id }       │
│                                                                  │
│  2. Parallel Dispatcher — ThreadPoolExecutor fan-out             │
│     one future per agent, results collected as completed         │
│                                                                  │
│  3. Synthesizer — client.messages.stream() with prompt cache    │
│     streams token-by-token to the UI                            │
└───┬──────────┬──────────┬──────────┬──────────┬────────────────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌──────────┐
│  CV   │ │  PP   │ │  PD   │ │  IS   │ │    CI    │
│ Agent │ │ Agent │ │ Agent │ │ Agent │ │  Agent   │
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └────┬─────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌───────────────────┐ ┌──────────────────────────┐
│ ChromaDB │ │      SQLite       │ │  inventory_snapshot.csv  │
│ (reviews │ │ price_points      │ │  (warehouse stock levels)│
│  + prods)│ │ demand_daily      │ └──────────────────────────┘
└──────────┘ │ demand_summary    │
             └───────────────────┘
```

**Agent key:** CV = Customer Voice, PP = Pricing & Profit, PD = Product Discovery, IS = Inventory & Supply, CI = Campaign Intelligence

---

## 3. Orchestration Layer

### 3.1 Intent Classifier (`orchestrator/intent_classifier.py`)

A single Claude API call converts the user's natural language query into a structured routing decision:

```json
{
  "agents": ["pricing_profit", "customer_voice"],
  "mode": "search",
  "article_id": "0108775015",
  "reasoning": "Query asks for price recommendation and customer sentiment on a specific article."
}
```

The classifier returns the minimal agent set required — single-agent queries invoke one agent, compound queries fan out to multiple. Prompt caching is applied to the classifier system prompt.

### 3.2 Parallel Dispatcher (`orchestrator/orchestrator.py`)

For multi-agent queries, agents run concurrently via `ThreadPoolExecutor`. Each agent executes in its own thread; results are collected as futures complete. Per-agent wall-clock timing is recorded for observability.

### 3.3 Streaming Synthesizer

For multi-agent results, synthesis uses `client.messages.stream()` with the system prompt under `cache_control: {"type": "ephemeral"}`. Tokens are yielded to the Streamlit UI via `st.write_stream()` as they arrive, eliminating the wait for full completion before the user sees output.

---

## 4. Specialist Agents

Each agent follows the same internal pattern:
1. Retrieve relevant data (vector search or SQL query)
2. Build a structured context block from retrieved data
3. Call the Claude API (with prompt caching on the system prompt)
4. Parse the JSON response
5. Validate and normalise output via `shared/schemas.py`

### 4.1 Customer Voice Agent (`agents/customer_voice/`)

| Property | Detail |
|---|---|
| Data | 23,000 women's clothing reviews indexed in ChromaDB |
| Embedding model | `all-MiniLM-L6-v2` (sentence-transformers) |
| Modes | `search` — specific article sentiment; `summary` — portfolio-wide themes |
| Output | Sentiment score, supporting evidence, themes, unmet needs, recommendation |

**Search mode** performs semantic similarity retrieval against the review index and returns direct-answer JSON. **Summary mode** samples across the full index and returns theme clusters, top positives/negatives, and an executive summary.

```json
{
  "direct_answer": "string",
  "sentiment": "positive | neutral | negative",
  "relevant_review_count": 0,
  "supporting_evidence": ["quote 1", "quote 2"],
  "recommendation": "string"
}
```

### 4.2 Pricing & Profit Agent (`agents/pricing_profit/`)

| Property | Detail |
|---|---|
| Data | SQLite `price_points` table (article_id, price, txn_count, total_rev) |
| Fallback | Transactions CSV if SQLite unavailable |
| Output | Price elasticity, current best price, recommended price, revenue scenarios |

The agent aggregates historical price-volume data per article, constructs price-demand curves, and prompts Claude to reason over elasticity and recommend an optimal price point with scenario comparisons.

```json
{
  "article_id": "string",
  "price_elasticity": "elastic | inelastic | unit_elastic",
  "current_best_price": 0.0,
  "recommended_price": 0.0,
  "recommendation_rationale": "string",
  "revenue_scenarios": [
    { "label": "string", "price": 0.0, "projected_units": 0, "projected_revenue": 0.0 }
  ],
  "confidence": "low | medium | high"
}
```

### 4.3 Product Discovery Agent (`agents/product_discovery/`)

| Property | Detail |
|---|---|
| Data | 10,000 H&M articles indexed in ChromaDB |
| Embedding model | `all-MiniLM-L6-v2` (sentence-transformers) |
| Modes | `search` — semantic catalog search; `summary` — catalog composition analysis |
| Output | Matching products, colour/style variety, coverage assessment, catalog gaps |

Product metadata (name, type, colour, department, description) is concatenated into a text document per article and embedded at index build time. Queries use semantic similarity to surface the closest matches.

### 4.4 Inventory & Supply Agent (`agents/inventory_supply/`)

| Property | Detail |
|---|---|
| Data | SQLite `demand_summary` (daily demand rates per article) + `inventory_snapshot.csv` (warehouse stock) |
| Supporting module | `forecaster.py` — computes days-until-stockout and recommended order quantities |
| Modes | Article-specific replenishment; portfolio risk summary |
| Output | Replenishment status, days until stockout, order quantity, order date, risk factors |

The forecaster divides current stock by demand rate to project stockout dates, then Claude reasons over lead times and risk factors to produce a replenishment recommendation.

```json
{
  "replenishment_status": "CRITICAL | AT_RISK | HEALTHY",
  "days_until_stockout": 0,
  "recommended_order_quantity": 0,
  "recommended_order_date": "YYYY-MM-DD",
  "rationale": "string",
  "risk_factors": ["string"],
  "confidence": "low | medium | high"
}
```

### 4.5 Campaign Intelligence Agent (`agents/campaign_intelligence/`)

| Property | Detail |
|---|---|
| Data | SQLite `demand_daily` (transaction counts by date) + `inventory_snapshot.csv` |
| Supporting module | `trend_analyzer.py` — computes demand trend and change percentage |
| Modes | Article-specific promotion decision; portfolio promotion candidates |
| Output | Promotion recommendation, discount percentage, campaign type and timing, risk of inaction |

The trend analyzer compares recent vs earlier transaction periods to classify demand direction. Claude combines demand trend with inventory pressure to recommend whether and how to promote.

```json
{
  "promotion_recommendation": "PROMOTE_NOW | MONITOR | HOLD",
  "suggested_discount_pct": 0,
  "campaign_type": "PRICE_DISCOUNT | BUNDLE | SEASONAL_CLEARANCE | LOYALTY_OFFER | NONE",
  "demand_trend": "DECLINING | STABLE | GROWING",
  "demand_change_pct": 0.0,
  "campaign_timing": "string",
  "rationale": "string",
  "risk_of_inaction": "string"
}
```

---

## 5. Data Layer

| Store | Contents | Used by |
|---|---|---|
| ChromaDB — reviews collection | 23K review embeddings + metadata | Customer Voice |
| ChromaDB — products collection | 10K article embeddings + metadata | Product Discovery |
| SQLite `price_points` | Per-article price/volume aggregations | Pricing & Profit |
| SQLite `demand_daily` | Daily transaction counts per article | Campaign Intelligence |
| SQLite `demand_summary` | Daily demand rate per article | Inventory & Supply |
| `inventory_snapshot.csv` | Warehouse-level stock quantities | Inventory & Supply, Campaign Intelligence |

**ChromaDB** uses `PersistentClient` — indexes are built once on first run and reloaded from disk on every subsequent start. **SQLite** is pre-aggregated from the raw transactions CSV by `build_sqlite_db.py` (run once at setup). Both strategies eliminate per-query raw file scanning.

---

## 6. Shared Infrastructure

### 6.1 Output Validation (`shared/schemas.py`)

Pydantic v2 models for every agent output type. A shared `_Base` class applies a `model_validator(mode="before")` that normalises string enum fields — Claude occasionally varies capitalisation on values like `"High"` vs `"HIGH"` vs `"high"`; the validator enforces consistent casing before field validation runs.

Nine schema classes cover all agent modes:
`CustomerVoiceSearchOutput`, `CustomerVoiceSummaryOutput`, `PricingOutput`, `ProductDiscoverySearchOutput`, `ProductDiscoverySummaryOutput`, `InventoryArticleOutput`, `InventorySummaryOutput`, `CampaignArticleOutput`, `CampaignSummaryOutput`

### 6.2 Structured Logging (`shared/logger.py`)

`AgentLogger` appends a JSON entry to `logs/agent_calls.jsonl` on every orchestrator run:

```json
{
  "timestamp": "ISO8601",
  "query": "string",
  "agents_called": ["string"],
  "agent_timings": { "agent_name": 8.3 },
  "total_latency_sec": 12.1,
  "success": true
}
```

The last 10 log entries are surfaced in the Streamlit sidebar for real-time observability without leaving the UI.

---

## 7. Test Suite

26 tests across two files, separated by cost:

| File | Tests | Requires API | Scope |
|---|---|---|---|
| `tests/test_routing.py` | 14 | No | Intent classification accuracy across all 11 known query patterns |
| `tests/test_schemas.py` | 12 | Yes | Per-agent output schema validation + end-to-end orchestrator runs |

Routing tests use `@pytest.mark.parametrize` across all query types — single agent, multi-agent, summary, article-specific, and unknown query fallback. Integration tests are marked `@pytest.mark.integration` and can be excluded to keep CI fast.

---

## 8. UI (`ui/app.py`)

Streamlit application with an Amazon Seller Central-inspired design — light sidebar, navy/orange header, card-based agent insight panels.

**Key UI behaviours:**
- `@st.cache_resource` loads the orchestrator once; all subsequent queries reuse the cached instance with warm ChromaDB indexes
- Multi-agent queries stream the synthesis live via `st.write_stream()`; single-agent results render immediately
- Each agent's structured output is rendered into its own insight card with metrics, charts (Plotly), and evidence lists
- Per-agent timing is displayed alongside the agent tags on each result
- Last 10 query logs visible in the sidebar expander without leaving the app

---

## 9. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Parallel dispatch | `ThreadPoolExecutor` | Multi-agent queries run all agents simultaneously; a 3-agent query takes the time of the slowest agent, not the sum |
| Streaming synthesis | `client.messages.stream()` | Users see the recommendation building in real time rather than waiting for full completion |
| Prompt caching | `cache_control: ephemeral` on all system prompts | Repeated queries reuse cached prompt prefixes, reducing latency and API cost |
| SQLite pre-aggregation | One-time build via `build_sqlite_db.py` | Price and demand queries hit indexed tables in milliseconds rather than scanning 500MB+ CSVs |
| Pydantic validation | Per-agent schema on every response | Catches malformed outputs and normalises enum casing before the synthesizer or UI consume the data |
| Orchestration style | Centralised orchestrator, no framework | Explicit routing and state passing; the LangGraph migration (next) will replace this layer without touching any agent code |
| Archive pattern | `archive/v1_sdk/` preserves the pre-migration orchestrator | Direct comparison between raw-SDK and LangGraph designs; agent code is identical in both |

---

## 10. Technology Stack

| Layer | Technology |
|---|---|
| LLM | Anthropic Claude (`claude-sonnet-4-6`) |
| UI | Streamlit |
| Vector search | ChromaDB + sentence-transformers (`all-MiniLM-L6-v2`) |
| Structured data | SQLite via Python `sqlite3` |
| Output validation | Pydantic v2 |
| Structured logging | Append-only JSONL (`shared/logger.py`) |
| Testing | pytest with `integration` marker for API-call tests |
| Orchestration (next) | LangGraph |

