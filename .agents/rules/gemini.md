---
trigger: always_on
---

# Gemini Workspace Rules — GlobalProcurementEnv
# Primary IDE: Antigravity
# Read by: Gemini AI assistant inside Antigravity
# Purpose: Enforce every constraint, naming convention, and design rule
#          for this specific project so generated code never violates
#          hackathon submission requirements.
#
# ════════════════════════════════════════════════
# CRITICAL — READ BEFORE GENERATING ANY CODE
# ════════════════════════════════════════════════
# This project is submitted to the OpenEnv Hackathon (Round 1).
# Automated judges disqualify submissions that violate rules below.
# Treat every constraint here as a HARD requirement.
# ═══════════════════════════════════════════════════════════════

---

## 1. Project Identity

**Project name:** GlobalProcurementEnv
**Hackathon:** OpenEnv Hackathon Round 1 (deadline 8 April, 11:59 PM)
**Framework:** `openenv-core` — NOT raw Gym, NOT Gymnasium natively
**Team:**
- Jenish — Env Core (`env/`, root ML scripts, `inference.py`)
- Jeswin — Data & Tasks (`graders/`, `policies/`, `data/`, `disruptions/`, `README.md`)
- Jamal — Infra & Deploy (`api/`, `Dockerfile`, `requirements.txt`, `openenv.yaml`)

**What we are building:** An AI agent acts as a procurement officer buying materials from India, EU, and USA suppliers under real government trade policies and seeded supply-chain disruptions. Deployed as a FastAPI Docker app on Hugging Face Spaces, fully conforming to the OpenEnv spec.

---

## 2. OpenEnv Spec — Most Critical Section

The judges run an automated validator. Any deviation = automatic disqualification.

### 2a. Required Python Interface

`GlobalProcurementEnv` must implement exactly these three methods with **typed Pydantic models**:

```python
def reset() -> Observation
def step(action: Action) -> tuple[Observation, Reward, bool, dict]
def state() -> Observation
```

- `Observation`, `Action`, `Reward` must be **Pydantic `BaseModel` subclasses** — never plain dicts or dataclasses as return types.
- `step()` returns a **4-tuple**: `(observation, reward, done, info)` — not a dict.
- `reset()` and `state()` each return an `Observation` instance.

### 2b. Pydantic Models — Always Typed

Gemini must always generate typed Pydantic models. Never use `dict` as a return type for `step()`, `reset()`, or `state()`.

```python
from pydantic import BaseModel
from typing import List, Optional, Dict

class SupplierObservation(BaseModel):
    id: str
    country: str
    price_usd: float
    lead_days: int
    carbon_tons: float
    available: bool
    applied_duty_rate: float

class Observation(BaseModel):
    step: int
    budget_remaining: float
    inventory: Dict[str, float]
    suppliers: List[SupplierObservation]
    active_disruptions: List[str]
    policy_violations_this_episode: int
    current_task: int
    grader_score: Optional[float] = None

class Action(BaseModel):
    action: int  # integer 0-6

class Reward(BaseModel):
    value: float
    compliance: float
    cost_efficiency: float
    delivery_speed: float
    carbon_score: float
```

### 2c. `openenv.yaml` Required Fields

Must pass `openenv validate` (run by judges via `openenv-core` CLI). Required top-level keys: `name`, `version`, `description`, `tasks` (list of ≥ 3), `action_space`, `observation_space`, `reward_range`. Task IDs in YAML must exactly match the `TASK_ID` string constants in task config files.

### 2d. `inference.py` — MANDATORY File (Disqualification if Missing)

A file named exactly `inference.py` in the **project root** is required by the hackathon. Rules:
- Uses **OpenAI API client** for all LLM calls — no other HTTP client
- Reads credentials from env vars: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`
- Total runtime under **20 minutes**
- Must run on **2 vCPU, 8 GB RAM** — no GPU, no CUDA

```python
# CORRECT — always use this pattern in inference.py
from openai import OpenAI
import os

client = OpenAI(
    base_url=os.getenv("API_BASE_URL"),
    api_key=os.getenv("HF_TOKEN") or os.getenv("API_KEY"),
)
model_name = os.getenv("MODEL_NAME")
```

Gemini must **never** use `requests`, `httpx`, or `aiohttp` for LLM calls in `inference.py`.

### 2e. `baseline.py` vs `inference.py` — Critical Distinction

| File | Uses LLM? | Agent Type | Required? |
|------|-----------|-----------|-----------|
| `baseline.py` | No | Random actions | Yes — judges run it |
| `inference.py` | Yes (OpenAI client) | LLM-driven | **Yes — disqualification if absent** |

Both must exist in the project root. Do not conflate them.

---

## 3. File Ownership — Never Cross Without Flagging

| Owner | Files They Own |
|-------|---------------|
| Jenish | `env/`, `baseline.py`, `train.py`, `trained_agent.py`, `inference.py` |
| Jeswin | `graders/`, `policies/`, `data/`, `disruptions/`, `README.md` |
| Jamal | `api/`, `Dockerfile`, `requirements.txt`, `openenv.yaml` |

When generating code, place it in the correct owner's file. If a cross-boundary change is needed, prepend: `⚠️ This touches [Owner]'s file — coordinate before merging.`

---

## 4. Approved Libraries — Use These Only

| Library | Pinned Version | Purpose |
|---------|---------------|---------|
| `openenv-core` | `>=0.2.2` | OpenEnv spec, validation CLI |
| `fastapi` | `==0.111.0` | API server |
| `uvicorn[standard]` | `==0.29.0` | ASGI server |
| `pydantic` | `==2.7.1` | All typed models |
| `openai` | `>=1.0.0` | LLM calls in `inference.py` |
| `stable-baselines3` | `==2.3.2` | PPO training |
| `gymnasium` | `==0.29.1` | Gym wrapper for SB3 |
| `torch` | `==2.3.0` | PyTorch for SB3 |
| `numpy` | `==1.26.4` | Numerical ops |

## 4b. Banned Libraries — Never Suggest These

| Library | Why Banned |
|---------|-----------|
| `requests` / `httpx` for LLM calls | Must use `openai.OpenAI` client |
| `flask` | Use FastAPI only |
| `gym` (old OpenAI Gym) | Use `gymnasium` only |
| `ray` / `rllib` | Exceeds 2 vCPU/8 GB constraint |
| `vllm` | Requires CUDA — judges run CPU-only |
| `bitsandbytes` | Requires CUDA |
| Any package not already in `requirements.txt` without adding a pinned entry first |

---

## 5. Hard Implementation Constraints

### Rule 1 — Typed Pydantic Returns Everywhere

`reset()`, `step()`, `state()` always return Pydantic instances:
```python
# CORRECT
def reset(self, task: int = 1, seed: int = 42) -> Observation:
    return Observation(step=0, budget_remaining=200000.0, ...)

# WRONG
def reset(self, task=1, seed=42) -> dict:
    return {"step": 0}
```

### Rule 2 — Fresh State on Every `reset()`

`self.state = SupplyChainState(...)` — never `.clear()`, `.update()`, or mutate the existing state object.

### Rule 3 — Deterministic Seeding

`random.seed(seed)` must be the first line in `reset()`. Same seed = identical episode. Judges verify reproducibility.

### Rule 4 — One Worker, One Lock

`--workers 1` in Dockerfile CMD. One `threading.Lock()` wraps `/reset` and `/step`. Never suggest multiple uvicorn workers.

### Rule 5 — Grader Robustness

All graders: return `float` in `[0.0, 1.0]`, return `0.0` for empty `steps`, never `None` or `float('nan')`. Final line always: `return round(max(0.0, min(1.0, score)), 4)`.

### Rule 6 — HTTP Errors Are 400, Never 500

All FastAPI routes except `/health` catch all exceptions → `HTTPException(status_code=400, detail=str(e))`. `/health` has no try/except, always returns 200.

### Rule 7 — `inference.py` Uses OpenAI Client Only

No exceptions. All LLM calls go through `openai.OpenAI(base_url=..., api_key=...)`.

### Rule 8 — Runtime Constraints for `inference.py`

Under 20 minutes total. 2 vCPU / 8 GB RAM. No GPU. Keep `MAX_STEPS` ≤ 20 per episode for safety.

### Rule 9 — Model File Size

Each PPO `.zip` under 150 MB. Use `model.save()` — no replay buffers.

### Rule 10 — Port 7860

`EXPOSE 7860` in Dockerfile. `--port 7860` in CMD. Port 8000 is only for local dev convenience.

---

## 6. JSON Data File Conventions

**`policies/*.json`:** Must have `country`, `import_duty_rate`, `carbon_levy_per_ton_usd`, `sanctioned_categories` (list), `hard_rules` (list of strings), `soft_rules` (list of strings). Hard rule strings must exactly match strings checked in `constraint_engine.py`.

**`data/suppliers.json`:** Array of objects, each with `id`, `name`, `country`, `price_usd`, `lead_days`, `carbon_tons`, `available`, `sanctioned_category`. Country must be `"India"`, `"EU"`, or `"USA"` — exact strings.

---

## 7. `requirements.txt` Rules

```
openenv-core>=0.2.2
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
openai>=1.0.0
stable-baselines3==2.3.2
gymnasium==0.29.1
torch==2.3.0
numpy==1.26.4
```

All versions pinned. Never add unversioned packages. Never add packages that conflict with the pinned SB3 + gymnasium + torch trio.

---

## 8. Disqualification Checklist — Gemini Must Prevent All of These

| Trigger | What to Avoid |
|---------|--------------|
| Space does not deploy | Dockerfile errors, missing COPY dirs, wrong port |
| `openenv validate` fails | Wrong YAML, missing typed models, wrong field names |
| Graders return constant score | Grader formulas with no variance |
| `inference.py` missing | Always include in repo root |
| `inference.py` uses wrong HTTP client | Only `openai.OpenAI`, never `requests` |
| Baseline not reproducible | Always `random.seed(seed)` before any randomness |
| Fewer than 3 tasks | Always task1, task2, task3 |
| HTTP 500 from routes | Always catch exceptions → 400 |
| Models over 150 MB | Keep timesteps reasonable |
| `step()` returns dict instead of tuple | Always return 4-tuple |

---

## 9. Testing Conventions (Pitstop Audits)

Gemini must always offer a pitstop audit alongside generated code. Minimum checks:

- **Pydantic models:** `.model_dump()` returns expected keys
- **Environment:** `reset()` returns `Observation` instance, `step()` returns 4-tuple `(Observation, Reward, bool, dict)`, `state()` returns `Observation`
- **Graders:** `[0, 1]` float for valid episode, `0.0` for empty, different scores for clearly different episodes
- **API routes:** 200 for valid requests, 400 (not 500) for invalid
- **`inference.py`:** dry-run with mock env to confirm it completes without error

---

## 10. Day-by-Day Scope

| Day | Focus | Gemini's Job |
|-----|-------|-------------|
| Day 1 | Independent modules | Build each person's piece; enforce typed Pydantic from the start |
| Day 2 | Integration + OpenEnv API | Verify `step()` returns 4-tuple; check schemas match routes |
| Day 3 | Docker + Deploy | Dockerfile COPY completeness, port 7860, import paths |
| Day 4 | Harden + `inference.py` | No new features; verify `inference.py` runs cleanly; final `openenv validate` |

---

## 11. Import Conventions

```python
# Always module-level — never sys.path manipulation
from env.global_procurement_env import GlobalProcurementEnv
from env.supply_chain_sim import SupplyChainState
from api.schemas import Observation, Action, Reward
from graders.grader1 import grade

# In inference.py — always OpenAI client
from openai import OpenAI
```

Import errors are fixed by adding `__init__.py` to package directories or fixing Dockerfile COPY — never `sys.path.insert()`.

---

## 12. `openenv.yaml` Canonical Template

```yaml
name: global-procurement-env
version: "1.0.0"
description: >
  AI procurement simulation: agent sources materials from India, EU, USA
  under real trade policies and supply-chain disruptions.
tasks:
  - id: task_1_easy
    name: "Easy — India Only"
    max_steps: 20
  - id: task_2_medium
    name: "Medium — India + EU"
    max_steps: 50
  - id: task_3_hard
    name: "Hard — All 3 Countries"
    max_steps: 100
action_space:
  type: Discrete
  n: 7
observation_space:
  type: Dict
  fields:
    - name: step
      type: int
    - name: budget_remaining
      type: float
    - name: inventory
      type: object
    - name: suppliers
      type: array
    - name: active_disruptions
      type: array
    - name: policy_violations_this_episode
      type: int
    - name: current_task
      type: int
reward_range: [-1.0, 1.0]
```
