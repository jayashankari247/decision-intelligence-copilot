# Decision Intelligence Co-Pilot — Phase-wise Learning Plan

**Version:** 0.1
**Last Updated:** 2026-05-03
**Approach:** Build to learn. Every phase produces working code, not just theory.

---

## Background & Mental Model Shift

Coming from a mainframe world, here is how the key concepts map:

| Mainframe Concept | Modern Equivalent |
|---|---|
| Subroutine call within a program | API call to an external service |
| JCL orchestrating job steps | Python orchestrator coordinating agents |
| Fixed-length record (VSAM, flat file) | JSON — flexible, readable, key-value pairs |
| STEPLIB / JOBLIB for library isolation | Python virtual environment (`venv`) |
| Batch job with defined inputs/outputs | Agent — takes input, produces structured output |
| Operator console / job monitor | Logging + observability layer |
| Multi-step batch pipeline | Multi-agent pipeline |

---

## Phase 1 — Environment & Foundations
**Duration:** 2–3 weeks
**Goal:** Get your development environment running and understand the core building blocks before writing any agent code.

### Week 1 — Setup & First API Call

**What to install:**
- Python (latest stable release) from [python.org/downloads](https://www.python.org/downloads/) — click the big green Download button; avoid anything labelled "pre-release", "alpha", or "beta". Check "Add Python to PATH" during install.
- VS Code Python extension (by Microsoft)

**What to learn:**
- Virtual environments — isolated package containers per project
- `pip` — Python's package installer
- `.env` files — keeping secrets (API keys) out of your code
- What an API call actually is

**Step-by-step tasks:**
1. Install Python → verify with `python --version` in PowerShell
2. Create project virtual environment:
   ```
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install first packages:
   ```
   pip install anthropic python-dotenv
   ```
4. Get Anthropic API key from [console.anthropic.com](https://console.anthropic.com) → save in `.env` file
5. Write and run `hello_claude.py` — one question to Claude, print the answer

**Milestone:** `python hello_claude.py` prints Claude's response in your terminal.

**Reading:**
- [Python Tutorial — Chapters 1–5](https://docs.python.org/3/tutorial/) — syntax refresher
- [What is an API?](https://www.mulesoft.com/resources/api/what-is-an-api) — 15 mins
- [JSON intro](https://www.w3schools.com/js/js_json_intro.asp) — 10 mins
- [Anthropic SDK Quickstart](https://docs.anthropic.com/en/docs/quickstart) — read after first call works

---

### Week 2 — Python Refresher (Focused on What You'll Actually Use)

You don't need to re-learn all of Python. You need these specific constructs:

**What to learn:**
- Functions and return values
- Dictionaries (Python's version of JSON — key/value pairs)
- Lists and loops
- f-strings (string formatting)
- Importing libraries (`import`, `from x import y`)
- Reading/writing files
- Basic error handling (`try / except`)

**Exercises to write:**
1. A function that takes a product name and returns a dict with name, price, and category
2. A function that reads a CSV file of customer reviews and prints each row
3. A function that catches an error gracefully and prints a helpful message

**Reading:**
- [Automate the Boring Stuff with Python — Chapters 1–8](https://automatetheboringstuff.com/) — free, practical, not academic
- [Real Python — Python Dicts](https://realpython.com/python-dicts/) — dicts are everywhere in this project

---

### Week 3 — The Agent Loop Pattern

This is the most important conceptual week. Everything in AI agents comes back to this loop:

```
1. Receive input (user query or another agent's output)
2. Build a prompt (combine system instructions + input + context)
3. Call the LLM (send the prompt, get a response)
4. Parse the output (extract the structured data from the response)
5. Return the result (or loop back if more steps needed)
```

**What to learn:**
- `system` vs `user` messages in the Claude API — what each one is for
- Structured output — how to instruct Claude to return JSON
- Parsing JSON in Python (`json.loads()`)
- What "tool use" is (Claude can call functions you define — covered deeper in Phase 3)

**Exercises to write:**
1. A function `ask_claude(question: str) -> str` that wraps the API call
2. A function that asks Claude to analyze a review and return structured JSON (sentiment, themes)
3. A function that validates Claude's output matches the expected schema

**Reading:**
- [Anthropic Docs — Messages API](https://docs.anthropic.com/en/api/messages)
- [Anthropic Docs — System Prompts](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts)
- [Anthropic Docs — Tool Use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) — read to understand, don't implement yet

**Phase 1 Milestone:** You can write a Python function that sends a prompt to Claude and gets back a structured JSON response that you can work with in code.

---

## Phase 2 — Customer Voice Agent (End-to-End)
**Duration:** 2–3 weeks
**Goal:** Build one complete specialist agent — real data in, structured JSON out, tested.

**Why Customer Voice first?**
It's the most concrete. Input = text (reviews, tickets). Output = sentiment + themes. No external math libraries needed. Good for learning the full agent pattern cleanly.

### What to build:
- `agents/customer_voice/agent.py` — the agent class
- `agents/customer_voice/prompts.py` — the system prompt
- A test file with 5 known review inputs and expected outputs

### Concepts introduced:
- **Agent as a class** — how to structure a reusable agent in Python (OOP basics)
- **System prompt engineering** — how to write a system prompt that reliably produces structured output
- **Pydantic for output validation** — define a schema, validate Claude's JSON against it
- **Synthetic data** — create a small CSV of sample reviews to work with

### Step-by-step:
1. Write the system prompt for the Customer Voice Agent
2. Write the `CustomerVoiceAgent` class with a single method: `analyze(reviews: list[str]) -> dict`
3. Test it on 5 hardcoded reviews
4. Load reviews from a CSV file instead of hardcoding
5. Validate the output schema with Pydantic
6. Write `pytest` tests for 5 known cases

**New packages to install:**
```
pip install pydantic pytest
```

**Reading:**
- [Real Python — Object-Oriented Python](https://realpython.com/python3-object-oriented-programming/) — understand classes before writing the agent class
- [Pydantic Docs — Getting Started](https://docs.pydantic.dev/latest/concepts/models/) — output validation
- [Anthropic Cookbook — Structured Output](https://github.com/anthropics/anthropic-cookbook) — practical examples

**Phase 2 Milestone:** `pytest agents/customer_voice/tests/` passes. The agent takes a list of reviews and reliably returns valid JSON matching the schema defined in `architecture.md`.

---

## Phase 3 — Orchestrator + Two Agents
**Duration:** 2–3 weeks
**Goal:** Learn multi-agent routing and synthesis. A natural language question gets routed to the right agent(s) and a unified answer comes back.

### What to build:
- `orchestrator/orchestrator_agent.py` — routes queries, collects responses
- `orchestrator/intent_classifier.py` — classifies the query domain
- `agents/pricing_profit/agent.py` — second specialist agent
- `shared/message_schema.py` — the `AgentMessage` dataclass
- `shared/context_store.py` — session-level shared context

### Concepts introduced:
- **Intent classification** — Claude reads the user's question and decides which agent(s) to call
- **Dataclasses** — lightweight Python data containers (like a struct)
- **Sequential vs parallel agent calls** — when to wait vs when to run simultaneously
- **Response synthesis** — how the orchestrator merges two agents' JSON into one coherent answer
- **Tool use (properly)** — define Python functions as tools so Claude can call them with structured arguments

### Step-by-step:
1. Build the Pricing & Profit Agent (same pattern as Customer Voice)
2. Write the intent classifier — given a query, returns `["customer_voice"]`, `["pricing"]`, or both
3. Build the orchestrator — takes a query, classifies it, calls agent(s), synthesizes
4. Test with 10 queries — some route to one agent, some to both
5. Add the `AgentMessage` schema so agent calls are logged and traceable

**Reading:**
- [Anthropic Docs — Tool Use Deep Dive](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Python Dataclasses](https://realpython.com/python-dataclasses/) — simple data containers
- [Anthropic Blog — Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)

**Phase 3 Milestone:** The query "What do customers think about product X and what price should we charge?" routes to both agents and returns a synthesized answer.

---

## Phase 4 — Multimodal: Product Discovery Agent
**Duration:** 2–3 weeks
**Goal:** Handle image inputs alongside text. Build the most technically complex agent.

### What to build:
- `agents/product_discovery/agent.py`
- `agents/product_discovery/embeddings.py` — vector embeddings for similarity search
- `shared/multimodal_handler.py` — normalize image + text inputs before agent call

### Concepts introduced:
- **Multimodal inputs** — sending images to Claude alongside text
- **Embeddings** — converting text/images into vectors of numbers that capture meaning
- **Vector similarity** — "find products similar to this one" = find vectors that are close together
- **Vector database (ChromaDB)** — store and query embeddings locally

### New packages to install:
```
pip install sentence-transformers chromadb Pillow
```

**Reading:**
- [Anthropic Docs — Vision](https://docs.anthropic.com/en/docs/build-with-claude/vision) — how to send images to Claude
- [What are Embeddings?](https://www.cloudflare.com/learning/ai/what-are-embeddings/) — conceptual explainer
- [ChromaDB Getting Started](https://docs.trychroma.com/getting-started)

**Phase 4 Milestone:** Pass a product image + description to the agent and get back a list of similar products from the catalog, plus trend signals.

---

## Phase 5 — All 5 Agents + Full Integration
**Duration:** 3–4 weeks
**Goal:** Complete the remaining two agents and run the full pipeline end-to-end.

### Before starting Phase 5 — Dataset Decision
Current open datasets are from different sources and cannot be joined on a shared product ID. Before building the remaining agents, evaluate whether to:
1. **Use a unified paid/commercial dataset** — a single retailer dataset where one product ID appears across customer reviews, inventory, pricing, catalog, and marketing data. Candidates: Snowflake Data Marketplace, Nielsen/IRI retail data, or a rich Kaggle competition dataset (Instacart, Walmart).
2. **Generate a synthetic unified dataset** — use Claude to generate a realistic but fictional retail dataset with consistent product IDs across all domains. Fast and free, good enough for a demo.
3. **Continue with fragmented open datasets** — acceptable for learning agent patterns but limits the orchestrator demo to single-agent queries.

**Recommendation:** Decide on option 1 or 2 before writing the remaining agents. A unified dataset transforms the UI demo from "5 separate tools" into a genuine Decision Intelligence Co-Pilot.

### What to build:
- `agents/inventory_supply/agent.py` + `forecaster.py`
- `agents/campaign_intelligence/agent.py` + `trend_analyzer.py`
- Full orchestrator routing to all 5 agents
- `ui/app.py` — Streamlit interface

### Concepts introduced:
- **Time-series forecasting** — Prophet library for demand prediction
- **Streamlit** — build a simple web UI in pure Python (no HTML/CSS needed)
- **End-to-end integration testing** — one query through all 5 agents

### New packages to install:
```
pip install prophet streamlit pandas
```

**Reading:**
- [Prophet Quickstart](https://facebook.github.io/prophet/docs/quick_start.html)
- [Streamlit Getting Started](https://docs.streamlit.io/get-started)

**Phase 5 Milestone:** You can open a browser, type a business question, and receive a synthesized recommendation drawn from all relevant agents.

---

## Phase 6 — Harden, Observe, Evaluate
**Duration:** Ongoing
**Goal:** Make the system trustworthy — logged, tested, and observable.

### What to build:
- Structured JSON logging for every agent call
- `pytest` golden test suites for all agents
- Pydantic validation on all agent outputs
- A simple log viewer or summary in the Streamlit UI

### Concepts introduced:
- **Structured logging** — logs as JSON, not free text
- **pytest fixtures** — reusable test setup
- **Evaluation methodology** — how to measure if an AI agent is working correctly

**Reading:**
- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [pytest — Getting Started](https://docs.pytest.org/en/stable/getting-started.html)
- [Anthropic Docs — Evals](https://docs.anthropic.com/en/docs/test-and-evaluate/eval-tool)

**Phase 6 Milestone:** Every agent call is logged. Running `pytest` gives you a green/red signal on whether the system is working. You can explain exactly why any recommendation was made.

---

## Phase 7 — Migrate to LangChain / LangGraph
**Duration:** 2–3 weeks
**Goal:** Rebuild the orchestration layer using LangGraph now that you understand what it's abstracting.

**Why this is Phase 7 and not Phase 1:**
You will have already built the orchestrator, agent routing, state management, and tool use by hand. Every LangGraph concept will map directly to something you wrote manually. This is the right time — abstractions you understand are tools; abstractions you don't understand are magic you can't debug.

### What changes:
- The orchestrator's routing logic → a **LangGraph graph** (nodes = agents, edges = routing conditions)
- Hand-written state dict → **LangGraph state management**
- Manual tool call handling → **LangChain `@tool` decorators**
- Custom logging → **LangSmith** tracing (LangChain's observability platform)

### What stays the same:
- All 5 agent business logic (`agent.py` files) — untouched
- All prompts — untouched
- All tests — still pass

### New packages:
```
pip install langchain langchain-anthropic langgraph langsmith
```

### Concepts introduced:
- **LangGraph** — stateful, graph-based agent orchestration
- **Nodes and edges** — agents are nodes, routing conditions are edges
- **LangSmith** — visual tracing of every agent call, great for debugging
- **LangChain tool decorators** — cleaner way to define tools Claude can call

### Reading:
- [LangGraph — Introduction](https://langchain-ai.github.io/langgraph/)
- [LangGraph vs raw agents — Why LangGraph?](https://langchain-ai.github.io/langgraph/concepts/why-langgraph/)
- [LangSmith Tracing](https://docs.smith.langchain.com/)

**Phase 7 Milestone:** The full pipeline runs through a LangGraph orchestrator. LangSmith shows a visual trace of every agent call for a given query. All existing tests still pass.

---

## Phase 8 — Advanced Reasoning & Adaptive Learning
**Duration:** 3–4 weeks
**Goal:** Make agents explainable and self-improving. This is where the system starts feeling genuinely intelligent rather than just functional.

### 15.1 Chain of Thought (CoT) — Start here
**What it is:** Instruct Claude to show its reasoning steps before giving a final answer. Like asking an analyst to "show your work."

**Why it matters:** Without CoT, Claude gives you an answer but you can't see why. With CoT, every recommendation comes with a reasoning trace — you can audit it, trust it more, and debug it when it's wrong.

**Implementation:** A one-line change to each agent's system prompt:
```
"Think step by step before answering. Show your reasoning, then output the final JSON."
```

### 15.2 Tree of Thought (ToT)
**What it is:** Claude explores multiple competing approaches before selecting the best one. Useful for the Pricing Agent (compare 3 pricing strategies) or Inventory Agent (compare reorder options).

**Implementation:** Prompt Claude to generate and evaluate multiple candidate answers before committing to one.

### 15.3 Adaptive Learning — Agents That Improve With Use
Three progressive levels:

1. **Feedback logging** — record every recommendation + whether the user accepted or rejected it
2. **Dynamic few-shot examples** — inject past accepted recommendations into the prompt so the agent learns your preferences over time
3. **RLHF (longer term)** — full fine-tuning loop using accepted/rejected recommendations to update the model

### Concepts introduced:
- **Chain of Thought prompting** — structured reasoning in prompts
- **Few-shot examples** — showing Claude examples of good outputs to calibrate its responses
- **Feedback loops** — capturing user signals to improve future responses
- **Prompt versioning** — tracking which prompt version produced which output

**Reading:**
- [Anthropic — Chain of Thought](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/chain-of-thought)
- [Tree of Thoughts paper](https://arxiv.org/abs/2305.10601)
- [Few-shot prompting](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-examples)

**Phase 8 Milestone:** At least two agents use CoT reasoning. Accepted recommendations are logged and fed back as few-shot examples in subsequent calls. Response quality measurably improves after 20+ interactions.

---

## Guiding Principles for This Journey

1. **Build first, perfect later.** A working rough agent beats a theoretical perfect one.
2. **Read the error message.** Every error tells you exactly what went wrong — learn to read them, not just Google them.
3. **One concept at a time.** Don't try to learn tool use, async, and embeddings in the same week.
4. **Keep a log.** Write a sentence each session about what you learned and what confused you. It compounds.
5. **Ask why.** Before copying any code, make sure you can explain what each line does.

---

## Quick Reference — Key Commands

```powershell
# Activate virtual environment (run this every session)
.\venv\Scripts\Activate.ps1

# Install a package
pip install <package-name>

# See installed packages
pip list

# Run a Python file
python filename.py

# Run tests
pytest

# Start Streamlit UI (Phase 5+)
streamlit run ui/app.py
```

---

## Current Status

| Phase | Status |
|---|---|
| Phase 1 — Environment & Foundations | Complete |
| Phase 2 — Customer Voice Agent | Complete |
| Phase 3 — Orchestrator + 2 Agents | Complete |
| Phase 4 — Product Discovery (Multimodal) | Complete |
| Phase 5 — All 5 Agents + UI | Complete |
| Phase 6 — Harden & Evaluate | Complete |
| Phase 7 — Migrate to LangChain / LangGraph | Not started |
| Phase 8 — Advanced Reasoning & Adaptive Learning | Not started |
