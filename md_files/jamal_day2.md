# Jamal (P3) — Day 2 Instructions
**Role:** Infra & Deploy | **Theme:** Build the FastAPI layer that wraps the entire environment

> ⚠️ **Today's Critical Gate:** All API routes must respond correctly to curl commands on `localhost:8000`. `/reset` and `/step` must return 200 with valid JSON. `/health` must always return 200.

---

## 🔗 Cross-Team Dependency — What You Need Today

**From Jenish (morning):** The `GlobalProcurementEnv` class in `env/global_procurement_env.py` — specifically the method signatures for `reset(task, seed)`, `step(action)`, and the `state()` getter. Your `api/main.py` will import and call this class directly. If Jenish's class isn't ready yet, write your API against a stub mock class (see the stub at the end of Phase 2) and swap in the real one when it arrives.

**From Jeswin (any time):** The task IDs and action range for each task. You need to know that Task 1 accepts actions 0–3, Task 2 accepts 0–5, and Task 3 accepts 0–6 — your Pydantic request schema needs to validate these ranges.

---

## Phase 1 — Write the Pydantic Schemas (`api/schemas.py`)

**What you're building:** Two categories of Pydantic models live in this file:

1. **OpenEnv interface models** — `Observation`, `Action`, `Reward` — these are the typed models that the OpenEnv spec requires. `GlobalProcurementEnv.reset()` returns an `Observation`. `step()` returns a 4-tuple of `(Observation, Reward, bool, dict)`. Judges run `openenv validate` which checks these types exist and are correct.

2. **FastAPI HTTP request models** — `ResetRequest`, `StepRequest` — these validate the JSON body coming from HTTP callers (the judges' automated system, `baseline.py`, `inference.py`).

**Coordinate with Jenish first** — he needs to import `Observation`, `Action`, and `Reward` from this file in his `global_procurement_env.py`. Agree on the field names before either of you writes the implementations.

**File:** `api/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any

# ─── OpenEnv Interface Models (returned by reset/step/state) ─────────────────
# These are NOT just HTTP schemas — they are the typed models that
# openenv validate checks. reset() returns Observation. step() returns
# (Observation, Reward, bool, dict). state() returns Observation.

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
    action: int = Field(ge=0, le=6, description="Action integer 0-6")

class Reward(BaseModel):
    value: float
    compliance: float
    cost_efficiency: float
    delivery_speed: float
    carbon_score: float

# ─── FastAPI HTTP Request Models (validate incoming JSON from callers) ────────

class ResetRequest(BaseModel):
    task: int = Field(default=1, ge=1, le=3,
                      description="Task ID: 1=easy, 2=medium, 3=hard")
    seed: int = Field(default=42, description="Random seed for reproducibility")

class StepRequest(BaseModel):
    action: int = Field(ge=0, le=6,
                        description="Action: 0=approve_cheapest … 6=escalate")

class HealthResponse(BaseModel):
    status: str = "ok"
```

**Why two categories?** The `ResetRequest` / `StepRequest` models are what FastAPI sees from HTTP callers. The `Observation` / `Reward` models are what the OpenEnv spec requires the environment to return internally. The FastAPI routes bridge the two: they receive `ResetRequest`, call `env.reset()`, get back an `Observation`, and serialize it as JSON.

### ✅ Pitstop Audit — Phase 1

```python
from api.schemas import Observation, Action, Reward, ResetRequest, StepRequest

# OpenEnv models instantiate correctly
obs = Observation(
    step=0, budget_remaining=200000.0,
    inventory={"steel": 0.0, "chips": 0.0, "fabric": 0.0},
    suppliers=[], active_disruptions=[],
    policy_violations_this_episode=0, current_task=1
)
assert "budget_remaining" in obs.model_dump()
print("✅ Observation model valid")

reward = Reward(value=0.71, compliance=1.0, cost_efficiency=0.8,
                delivery_speed=0.7, carbon_score=0.9)
assert reward.value == 0.71
print("✅ Reward model valid")

# HTTP request validation rejects invalid inputs
from pydantic import ValidationError
try:
    ResetRequest(task=9)
    assert False, "Should have raised ValidationError"
except ValidationError:
    print("✅ Invalid task correctly rejected")

try:
    StepRequest(action=9)
    assert False, "Should have raised ValidationError"
except ValidationError:
    print("✅ Invalid action correctly rejected")
```
**All 4 checks pass → Phase 1 complete. Share the Observation/Reward field names with Jenish.**

---

## Phase 2 — Write the FastAPI Application (`api/main.py`)

**What you're building:** The web application that wraps the environment. The key thing to understand: the environment's methods now return **Pydantic models and 4-tuples** (per the OpenEnv spec), not dicts. Your routes must unpack these correctly before returning JSON.

**The step() contract to remember:**
```python
# env.step() returns a 4-tuple:
observation, reward, done, info = env.step(action)
# observation: Observation (Pydantic)
# reward: Reward (Pydantic)
# done: bool
# info: dict
```

**File:** `api/main.py`

```python
import threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from api.schemas import (
    Observation, Action, Reward,
    ResetRequest, StepRequest, HealthResponse
)
from env.global_procurement_env import GlobalProcurementEnv

app = FastAPI(
    title="GlobalProcurementEnv",
    description="AI procurement simulation — OpenEnv Hackathon",
    version="1.0.0"
)

# ─── Single global env + thread lock ──────────────────────────────────────────
env = GlobalProcurementEnv()
lock = threading.Lock()
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    """Always returns 200. No try/except. Judges ping this first."""
    return HealthResponse(status="ok")

@app.post("/reset")
def reset(request: ResetRequest):
    """Calls env.reset() and returns Observation as JSON."""
    try:
        with lock:
            observation: Observation = env.reset(task=request.task, seed=request.seed)
        return observation.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/step")
def step(request: StepRequest):
    """
    Calls env.step() which returns a 4-tuple (Observation, Reward, bool, dict).
    Unpacks and returns a flat JSON combining observation + reward + done.
    """
    try:
        with lock:
            if env.state is None:
                raise ValueError("Call /reset before /step")
            if env.is_done:
                raise ValueError("Episode ended. Call /reset to start a new one.")

            # env.step() returns (Observation, Reward, bool, dict)
            observation, reward, done, info = env.step(action=request.action)

        # Merge observation + reward + done into one flat response
        response = observation.model_dump()
        response["reward"] = reward.value
        response["reward_breakdown"] = reward.model_dump()
        response["done"] = done
        response["info"] = info
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state")
def state():
    """Returns current Observation without advancing the episode."""
    try:
        with lock:
            observation: Observation = env.state()
        return observation.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Why `observation.model_dump()`?** FastAPI can serialise Pydantic models directly, but merging the observation with `reward` and `done` is easier if we work with a plain dict. `.model_dump()` converts the Pydantic model to a dict for this purpose.

**Stub for testing before Jenish's env is ready:**
```python
# Temporary stub — replace once Jenish delivers global_procurement_env.py
class GlobalProcurementEnv:
    state = None
    is_done = False
    current_task = 1

    def reset(self, task=1, seed=42):
        from api.schemas import Observation
        self.state = "initialized"
        self.is_done = False
        self.current_task = task
        return Observation(step=0, budget_remaining=200000.0,
                          inventory={"steel":0.0,"chips":0.0,"fabric":0.0},
                          suppliers=[], active_disruptions=[],
                          policy_violations_this_episode=0, current_task=task)

    def step(self, action=0):
        from api.schemas import Observation, Reward
        obs = Observation(step=1, budget_remaining=160000.0,
                         inventory={"steel":10.0,"chips":0.0,"fabric":0.0},
                         suppliers=[], active_disruptions=[],
                         policy_violations_this_episode=0, current_task=self.current_task)
        reward = Reward(value=0.5, compliance=1.0, cost_efficiency=0.8,
                       delivery_speed=0.7, carbon_score=0.6)
        return obs, reward, False, {}

    def state(self):
        return self.reset()
```

### ✅ Pitstop Audit — Phase 2

Start the server: `uvicorn api.main:app --host 0.0.0.0 --port 8000`

Then in a second terminal:

```bash
# Health — always 200, no env needed
curl -s http://localhost:8000/health
# Expected: {"status":"ok"}

# Reset — returns Observation JSON
curl -s -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task": 1, "seed": 42}'
# Expected: JSON with budget_remaining, suppliers, step, etc.

# Step — returns merged Observation + reward + done
curl -s -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": 0}'
# Expected: JSON with reward (float), done (bool), budget_remaining, etc.

# Verify step response has the required 4-tuple fields flattened correctly
curl -s -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": 0}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'reward' in d, 'reward missing'
assert 'done' in d, 'done missing'
assert 'reward_breakdown' in d, 'reward_breakdown missing'
assert isinstance(d['done'], bool), 'done must be bool'
print('✅ /step returns correct structure')
"

# Invalid task — must return 422 from Pydantic, not 500
curl -s -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task": 9}'
# Expected: HTTP 422 with Pydantic validation error detail
```

All 5 commands produce expected responses and no 500s → Phase 2 complete.

---

## Phase 3 — Update `openenv.yaml` with Real Values

Now that you've written the actual API, you know exactly what the observation fields are called and what the action space looks like. Replace the Day 1 placeholders with the real values:

Update the `observation_space.fields` section to exactly match the keys in your `StepResponse` Pydantic model. The field names in the YAML must match the JSON keys the API actually returns — this is what `openenv validate` checks. Also update the task `id` values to match the string IDs in the task config files Jeswin wrote.

### ✅ Pitstop Audit — Phase 3

Compare the YAML's observation field names against the actual JSON returned by `curl localhost:8000/state`. Every key in the JSON response should have a corresponding entry in `openenv.yaml`. Any field in the YAML that doesn't exist in the actual response is a validation failure.

**All YAML fields match actual API responses → Day 2 critical gate cleared. Tell Jenish and Jeswin the server is ready for their testing.**
