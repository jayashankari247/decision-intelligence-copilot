# Decision Intelligence Co-Pilot

A multi-agent AI system that answers complex cross-domain retail business questions from a single natural language prompt, using the Anthropic Claude API.

---

## What it does

Type a business question in plain English. The system routes it to the right specialist agents, runs them in parallel, and synthesizes a single unified recommendation.

**Example queries:**
- *"What do customers think about article 0108775015 and what should we charge for it?"*
- *"Which products are at risk of stockout and need urgent replenishment?"*
- *"Which products should we run a promotion on?"*
- *"How many black tops do we stock across all categories?"*

---

## Architecture

```
Streamlit UI
    │
    ▼
Orchestrator  ──  Intent classifier (Claude API)
    │
    ├── Customer Voice Agent      ←─ ChromaDB (23K reviews)
    ├── Pricing & Profit Agent    ←─ SQLite (price_points, demand)
    ├── Product Discovery Agent   ←─ ChromaDB (10K products)
    ├── Inventory & Supply Agent  ←─ SQLite + inventory snapshot
    └── Campaign Intelligence Agent ←─ SQLite + inventory snapshot
    │
    ▼
Synthesizer  ──  Streaming Claude API call
    │
    ▼
Streamlit UI  (streamed recommendation + agent insight cards)
```

See [architecture_diagram.md](architecture_diagram.md) for Mermaid diagrams of the current and planned (LangGraph) architecture.

---

## Setup

### 1. Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)
- The H&M Personalization Challenge dataset (see Data section below)

### 2. Clone and create virtual environment

```bash
git clone https://github.com/jayashankari247/decision-intelligence-copilot.git
cd decision-intelligence-copilot
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY and data file paths
```

### 5. Obtain the dataset

This project uses the [H&M Personalization Challenge](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data) dataset from Kaggle.

Download and place files at the paths listed in `.env.example`:

| File | Destination |
|---|---|
| `articles.csv` | `data/product_discovery/articles.csv` |
| `transactions_train.csv` | `data/product_discovery/transactions_train.csv` |
| `Womens Clothing E-Commerce Reviews.csv` | `data/customer_reviews/` |

Generate the inventory snapshot:
```bash
python generate_inventory_snapshot.py
```

### 6. Build the SQLite database

```bash
python build_sqlite_db.py
```

This reads the transactions CSV and creates `data/retail.db` with pre-aggregated price, demand, and summary tables.

### 7. Run the UI

```bash
streamlit run ui/app.py
```

The ChromaDB vector indexes (reviews + products) are built automatically on first run. This takes a few minutes — subsequent starts are fast.

---

## Project structure

```
├── agents/
│   ├── customer_voice/         # Review sentiment + search
│   ├── pricing_profit/         # Price elasticity + revenue scenarios
│   ├── product_discovery/      # Catalog search + gap analysis
│   ├── inventory_supply/       # Stockout forecasting + replenishment
│   └── campaign_intelligence/  # Promotion + discount recommendations
├── orchestrator/
│   ├── orchestrator.py         # Parallel dispatch + streaming synthesis
│   └── intent_classifier.py   # Claude API → routing JSON
├── shared/
│   ├── schemas.py              # Pydantic output models (all 5 agents)
│   └── logger.py              # JSON structured logging → logs/
├── ui/
│   └── app.py                 # Streamlit UI (Amazon Seller Central-inspired)
├── tests/
│   ├── test_routing.py        # 14 routing tests (no API calls)
│   └── test_schemas.py        # 12 integration tests (real API calls)
├── archive/v1_sdk/            # Archived v1 orchestrator before LangGraph migration
├── build_sqlite_db.py         # One-time SQLite pre-aggregation script
├── generate_inventory_snapshot.py
├── architecture_diagram.md    # Mermaid diagrams: current + LangGraph target
├── architecture.md            # Full system design document
└── requirements.txt
```

---

## Running tests

```bash
# Fast routing tests only (no API calls, ~45s)
pytest tests/test_routing.py -v

# Full integration tests (real API calls, ~3-4 min)
pytest tests/test_schemas.py -v -m integration

# All tests
pytest -v
```

---

## Key design decisions

- **Parallel agent dispatch** via `ThreadPoolExecutor` — multi-agent queries run all agents simultaneously
- **Streaming synthesis** via `client.messages.stream()` — recommendation streams token by token to the UI
- **Prompt caching** on all system prompts — reduces latency and API cost on repeated queries
- **Pydantic validation** on all agent outputs — normalises case inconsistencies from Claude
- **SQLite pre-aggregation** — price and demand queries hit indexed tables, not raw CSV scans
- **ChromaDB PersistentClient** — vector indexes survive restarts; only built once

---

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Anthropic Claude (claude-sonnet-4-6) |
| UI | Streamlit |
| Vector search | ChromaDB + sentence-transformers (all-MiniLM-L6-v2) |
| Structured data | SQLite via Python sqlite3 |
| Output validation | Pydantic v2 |
| Testing | pytest |
| Orchestration (next) | LangGraph |
