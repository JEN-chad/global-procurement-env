# Jenish (P1) — Day 2 Instructions
**Role:** Env Core | **Theme:** Wire everything into the main environment class

> ⚠️ **Today's Critical Gate:** `env.reset()` followed by 100 random steps must complete without any Python exception. Reward values must vary across steps.

---

## 🔗 Cross-Team Dependency — What You Need From Jeswin Today

Before you can test `constraint_engine.py` with real data, you need Jeswin's actual policy JSON files:
- `policies/india_policy.json`
- `policies/eu_policy.json`
- `policies/usa_policy.json`
- `data/suppliers.json`

**Coordinate with Jeswin in the morning.** If his files aren't ready yet, use your Day 1 stub JSONs to keep moving — you can swap in the real files as soon as they arrive. The field names were agreed upon in yesterday's sync, so the swap should be seamless.

You also need Jeswin to have his task configs (`task1_easy.py`, `task2_medium.py`, `task3_hard.py`) ready by afternoon so you can confirm your `reset(task, seed)` accepts the right parameters.

---

## Phase 1 — Write the Main Environment Class (`global_procurement_env.py`)

**What you're building:** The single class that wraps everything you built on Day 1. This is the front door of the simulation — it must conform exactly to the **OpenEnv interface spec**. The three methods must return **typed Pydantic models**, not plain dicts. Judges run `openenv validate` which checks this.

**OpenEnv contract (hard requirement):**
- `reset(task, seed) → Observation` — a Pydantic `Observation` instance
- `step(action: Action) → tuple[Observation, Reward, bool, dict]` — a 4-tuple, NOT a dict
- `state() → Observation` — a Pydantic `Observation` instance

**File:** `env/global_procurement_env.py`

First, define your Pydantic models in `api/schemas.py` (coordinate with Jamal, since he owns that file). The `Observation`, `Action`, and `Reward` classes must be Pydantic `BaseModel` subclasses:

```python
# api/schemas.py — Jamal's file, but Jenish must agree on these shapes

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

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
    action: int  # 0-6

class Reward(BaseModel):
    value: float
    compliance: float
    cost_efficiency: float
    delivery_speed: float
    carbon_score: float
```

Then write the environment class:

```python
import random
import json
import os
from api.schemas import Observation, Action, Reward, SupplierObservation
from env.supply_chain_sim import SupplyChainState, apply_action
from env.constraint_engine import load_policy, validate_action
from env.disruption_engine import DisruptionEngine

class GlobalProcurementEnv:
    def __init__(self):
        self.state: SupplyChainState | None = None
        self.task: int = 1
        self.seed: int = 42
        self.disruption_engine: DisruptionEngine | None = None
        self.is_done: bool = False
        self.current_task: int = 1

    def reset(self, task: int = 1, seed: int = 42) -> Observation:
        """
        Returns: Observation (Pydantic model) — NOT a dict.
        CRITICAL: Always self.state = SupplyChainState(...) — never .clear() a list.
        """
        self.task = task
        self.current_task = task
        self.seed = seed
        self.is_done = False
        random.seed(seed)   # ← Must be first — makes every run with same seed identical

        self.state = SupplyChainState(
            budget=200000.0,
            suppliers=self._load_suppliers_for_task(task),
            inventory={"steel": 0.0, "chips": 0.0, "fabric": 0.0},
            lead_days=0,
            carbon=0.0,
            step_count=0,
            violations=0
        )
        self.disruption_engine = DisruptionEngine(task=task, seed=seed)
        return self._build_observation()

    def step(self, action: int) -> tuple:
        """
        Returns: (Observation, Reward, bool, dict) — a 4-tuple per OpenEnv spec.
        NOT a dict. The bool is done. The dict is info.
        """
        # Step 1: disruption check
        active = self.disruption_engine.check(self.state.step_count)
        available_suppliers = self._apply_disruptions(active)

        # Step 2: apply action
        result = apply_action(self.state, action, available_suppliers)

        # Step 3: validate against policy
        policy = {}
        if result.get("selected_supplier"):
            policy = load_policy(result["selected_supplier"]["country"])
        is_valid, soft_penalty, vtype = validate_action(
            self.state, result.get("selected_supplier", {}), policy
        )

        # Step 4: hard violation → episode ends immediately
        if not is_valid:
            self.state.violations += 1
            self.is_done = True
            obs = self._build_observation()
            reward = Reward(value=-1.0, compliance=0.0, cost_efficiency=0.0,
                           delivery_speed=0.0, carbon_score=0.0)
            return obs, reward, True, {"violation": vtype}

        # Step 5: compute reward
        reward_obj = self._compute_reward(soft_penalty)
        done = self.state.step_count >= self._get_max_steps()
        self.is_done = done

        return self._build_observation(), reward_obj, done, {}

    def state(self) -> Observation:
        """Returns current state as Pydantic Observation — does not advance."""
        return self._build_observation()

    def _build_observation(self) -> Observation:
        supplier_obs = [
            SupplierObservation(
                id=s["id"], country=s["country"],
                price_usd=s["price_usd"], lead_days=s["lead_days"],
                carbon_tons=s["carbon_tons"], available=s["available"],
                applied_duty_rate=s.get("applied_duty_rate", 0.0)
            )
            for s in self.state.suppliers
        ]
        return Observation(
            step=self.state.step_count,
            budget_remaining=self.state.budget,
            inventory=self.state.inventory,
            suppliers=supplier_obs,
            active_disruptions=[],
            policy_violations_this_episode=self.state.violations,
            current_task=self.task,
            grader_score=None
        )
```

**The most important rule about `reset()`:** Always `self.state = SupplyChainState(...)` as a full new object. Never `self.state.violations = 0` or `self.state.inventory.clear()`. Reusing the old object silently corrupts every grader score — this is the #1 silent bug in RL environments.

### ✅ Pitstop Audit — Phase 1

```python
from env.global_procurement_env import GlobalProcurementEnv
from api.schemas import Observation, Reward

env = GlobalProcurementEnv()
obs = env.reset(task=1, seed=42)

# reset() must return a Pydantic Observation — not a dict
assert isinstance(obs, Observation), f"reset() must return Observation, got {type(obs)}"
assert obs.step == 0
assert obs.budget_remaining == 200000.0
assert obs.current_task == 1

# step() must return a 4-tuple: (Observation, Reward, bool, dict)
result = env.step(0)
assert isinstance(result, tuple) and len(result) == 4, "step() must return a 4-tuple"
obs2, reward, done, info = result
assert isinstance(obs2, Observation), "First element must be Observation"
assert isinstance(reward, Reward), "Second element must be Reward"
assert isinstance(done, bool), "Third element must be bool"
assert isinstance(info, dict), "Fourth element must be dict"

# Same seed produces identical initial observations
obs_a = env.reset(task=1, seed=42)
obs_b = env.reset(task=1, seed=42)
assert obs_a.budget_remaining == obs_b.budget_remaining
print("✅ Phase 1 pitstop passed — correct Pydantic return types")
```
**All assertions pass → Phase 1 complete.**

---

## Phase 2 — Implement the Reward Formula

**What you're building:** The scoring function that runs after every single action. This is what teaches the RL agent what "good procurement" looks like.

Add this method to `GlobalProcurementEnv`:

```python
def _compute_reward(self, soft_penalty: float = 0.0) -> float:
    """
    Reward = 0.35×compliance + 0.25×cost + 0.25×speed + 0.15×carbon
    Each component is normalised to [0, 1].
    """
    MAX_BUDGET = 200000.0
    MAX_LEAD_DAYS = 30
    MAX_CARBON = 50.0
    MAX_VIOLATIONS = 10

    # Compliance: fewer violations = better
    compliance = max(0.0, 1.0 - (self.state.violations / MAX_VIOLATIONS))

    # Cost efficiency: more budget remaining = we spent less = better
    cost_efficiency = max(0.0, self.state.budget / MAX_BUDGET)

    # Delivery speed: fewer accumulated lead days = better
    delivery_speed = max(0.0, 1.0 - (self.state.lead_days / MAX_LEAD_DAYS))

    # Carbon: less carbon used = better
    carbon_score = max(0.0, 1.0 - (self.state.carbon / MAX_CARBON))

    reward = (
        0.35 * compliance +
        0.25 * cost_efficiency +
        0.25 * delivery_speed +
        0.15 * carbon_score
    ) + soft_penalty  # soft_penalty is negative (e.g. -0.2)

    return round(max(-1.0, min(1.0, reward)), 4)  # clamp to [-1, 1]
```

**Why clamp the reward?** SB3's PPO expects rewards in a predictable range. Unclamped rewards that spike or crash can destabilise training.

### ✅ Pitstop Audit — Phase 2

```python
env = GlobalProcurementEnv()
env.reset(task=1, seed=42)

# Take action 0 (approve cheapest)
result = env.step(0)
print(0.0 <= result["reward"] <= 1.0)  # True — reward should be in range
print(result["done"])  # False — episode shouldn't end on step 1 normally

# Take action 3 (reject all — minor penalty)
result2 = env.step(3)
print(result2["reward"] < result["reward"])  # True — rejection should score lower
```
**Reward is in [0,1] range and rejection scores lower than approval → Phase 2 complete.**

---

## Phase 3 — Write the Disruption Engine (`disruption_engine.py`)

**What you're building:** The engine that fires crisis events at pre-set step numbers. Because you use the same seed, the same disruption always fires at the same step — making the simulation reproducible for judging.

**File:** `env/disruption_engine.py`

```python
import json, os

class DisruptionEngine:
    def __init__(self, task: int, seed: int):
        self.task = task
        self.seed = seed
        self._load_scenarios()

    def _load_scenarios(self):
        path = os.path.join(os.path.dirname(__file__), "..", "disruptions", "scenarios.json")
        with open(path, "r") as f:
            self.scenarios = json.load(f)  # list of scenario dicts

    def check(self, step_count: int) -> list:
        """
        Returns a list of active disruption dicts for the current step.
        Task 1: no disruptions
        Task 2: disruption at step 8 only
        Task 3: all 3 disruptions
        """
        active = []
        for scenario in self.scenarios:
            if scenario["trigger_step"] == step_count:
                if self.task >= scenario.get("min_task", 1):
                    active.append(scenario)
        return active
```

The three scenarios (from `scenarios.json`, written by Jeswin) are:
- `port_strike_india` — fires at step 8 — makes `IN_02` and `IN_03` unavailable for 5 steps
- `war_reroute_eu` — fires at step 15 — multiplies all EU supplier lead times by 2.5x for 10 steps
- `protest_france` — fires at step 22 — adds 14 days to `FR_01`'s lead time for 3 steps

### ✅ Pitstop Audit — Phase 3

```python
from env.disruption_engine import DisruptionEngine

engine = DisruptionEngine(task=3, seed=42)

# Step 7: no disruptions yet
print(engine.check(7))  # []

# Step 8: port strike fires
disruptions = engine.check(8)
print(len(disruptions))  # 1
print(disruptions[0]["name"])  # "port_strike_india"
```
**Empty list at step 7, non-empty at step 8 → Phase 3 complete.**

---

## Phase 4 — The Full 100-Step Stress Test (Day 2 Critical Gate)

This is the gate you must pass before the end-of-day sync. Run 100 random episodes and verify the environment never crashes and reward varies:

```python
# test_100_steps.py
import random
from env.global_procurement_env import GlobalProcurementEnv

env = GlobalProcurementEnv()
rewards = []

for episode in range(10):  # 10 episodes
    obs = env.reset(task=1, seed=episode)
    done = False
    ep_reward = 0.0
    steps = 0

    while not done and steps < 20:  # Task 1 max_steps = 20
        action = random.randint(0, 3)  # Task 1 only has actions 0-3
        result = env.step(action)
        ep_reward += result["reward"]
        done = result["done"]
        steps += 1

    rewards.append(ep_reward)
    print(f"Episode {episode}: steps={steps}, total_reward={ep_reward:.3f}")

print(f"\nReward range: {min(rewards):.3f} to {max(rewards):.3f}")
print("✅ PASSED" if min(rewards) != max(rewards) else "❌ FAILED — rewards are constant")
```

### ✅ Pitstop Audit — Phase 4 (Day 2 Critical Gate)

The test passes if:
- No episode crashes (no Python exception)
- Reward values differ between episodes (not all the same number)
- `done` eventually becomes `True` in each episode

**All three conditions met → tell Jamal to start the FastAPI server.**
