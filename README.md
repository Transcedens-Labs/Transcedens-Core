# 🧬 Transcedens Core: The Architecture of Becoming

**Transcedens Core** is a state-of-the-art cognitive architecture designed to power truly autonomous characters in games. By implementing a "Thinking, Fast and Slow" dual-process system, it balances sub-second reactions with deep, intentional planning and long-term personality evolution.

## 🏗️ Architecture: The 2-Tier Open Core

Transcedens Core provides the "Body" and "Mind" of your NPC, optimized for high-performance execution and narrative depth.

### 1. ⚡ The Reflex (System 1)
* **Latency**: < 100ms (Local) / < 1s (API)
* **Purpose**: Instant, persona-appropriate reactions to player stimuli.
* **Logic**: Bypasses heavy retrieval; utilizes **Persona DNA** and a **Warm State Cache** in Redis for sub-second responses.

### 2. 🧠 The Mind (System 2)
* **Cycle**: Event-driven or periodic "Heartbeat".
* **Purpose**: Short-term goal setting, tactical planning, and environmental awareness.
* **Logic**: Uses **Agentic RAG** to query relational context (Neo4j) and episodic memories (Qdrant).
* **The Transcedens Effect**: Automatically emits a `{"event": "cognitive_pause"}` signal to trigger "thinking" animations in-game during heavy System 2 processing.

---

## 🚀 Quick Start (Lite Mode)

Transcedens is **local-first** and **infra-agnostic**. You can run the engine in "Lite" mode with zero external databases for rapid prototyping.

### 1. Install via `uv` (Recommended)
```bash
# Fastest setup using the uv package manager
uv pip install -e .
```

### 2. Configure Environment
Create a `.env` file:
```env
LLM_PROVIDER=google_genai
GOOGLE_API_KEY=your_key_here
DB_MODE=LITE # Enables Zero-Infra mode
```

### 3. Basic Usage
```python
from core.reflex_api import process_stimulus

# Instant reaction via the System 1 Reflex tier
response = process_stimulus(npc_id="guard_01", text="Stop right there!")
print(response.speech) 
```

### 4. Running the Server (Open API)
To expose the engine as a web service, use the standalone API:
```bash
# Start the FastAPI server on port 8000 using uv
uv run uvicorn core.api:app --reload
```
You can then hit the endpoints:
- **Reflex (System 1)**: `POST /api/v1/reflex/stream`
- **Mind (System 2)**: `POST /api/v1/mind/heartbeat`

---

## ☄️ Advanced Logic Hooks (The Soul)

Transcedens Core includes a **Reflection Hook** (`reflection_hook.py`) that manages the handover of raw logs to an advanced "Soul" layer for deep memory distillation and persona evolution.

* **Standard Implementation**: The core maintains local logs and state persistence.
* **Proprietary Integration**: Supports `SAAS_REFLECTION_URL` for remote distillation services (A.U.D.N. logic).

> **Note**: A hosted "Soul" service for automated character evolution is currently in early access.

---

## 🤝 Contributing & License

We welcome contributions to the cognitive graphs, repository abstractions, and engine-specific adapters (Unity/Unreal).

* **License**: This project is licensed under the **Apache-2.0 License**.
* **Contact**: [Transcedens Labs](transcedens.labs@proton.me)
* **Laboratory**: [GitHub.com/Transcedens-Labs](https://GitHub.com/Transcedens-Labs)
