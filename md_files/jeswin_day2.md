# Jeswin (P2) — Day 2 Instructions
**Role:** Data & Tasks | **Theme:** Write task configs, build all 3 graders

> ⚠️ **Today's Critical Gate:** All 3 graders must return a float between 0.0 and 1.0 when given a completed episode dict. The value must not be constant across different inputs.

---

## 🔗 Cross-Team Dependency — What You Need Today

**From Jenish (morning):** The `SupplyChainState` field names and the structure of the observation dict that `env.step()` returns. Your task configs and graders depend on knowing what a completed "episode log" looks like — specifically what keys are in each step result (e.g. does it call the violations field `"violations"` or `"policy_violations_this_episode"`?). Confirm this with Jenish before you write the graders.

**From Jamal (afternoon):** Once Jamal has the FastAPI routes running locally, you'll call the `/reset` and `/step` endpoints with curl to get a real episode log you can feed into your graders for testing. Until then, construct a mock episode dict for Phase 4 testing.

---

## Phase 1 — Write Task 1 Config (`env/tasks/task1_easy.py`)

**What you're building:** A configuration module that defines the rules of Task 1 — the "easy" mode. Jenish's `GlobalProcurementEnv` will import this config when `reset(task=1)` is called. Think of the task config as the referee's rulebook for one specific game mode — it tells the environment how many steps to allow, which suppliers to include, and what actions are valid.

**File:** `env/tasks/task1_easy.py`

```python
"""
Task 1 — Easy Mode
India-only suppliers, 3 active suppliers, 20 steps maximum.
Actions 0-3 only (no negotiate, no split, no escalate).
No disruptions.
Teaches the agent basic cost/speed/carbon trade-offs.
"""

TASK_ID = 1
TASK_NAME = "easy_india_only"

MAX_STEPS = 20
VALID_ACTIONS = [0, 1, 2, 3]  # approve_cheapest, approve_fastest, approve_greenest, reject_all
SUPPLIER_COUNTRIES = ["India"]
NUM_SUPPLIERS = 3  # Use only 3 of the 4 India suppliers (randomly selected at reset)
DISRUPTIONS_ENABLED = False
STARTING_BUDGET = 200000.0

# Grader weights for Task 1 — simpler scoring, compliance matters most
GRADER_WEIGHTS = {
    "compliance_rate": 0.50,
    "delivery_rate": 0.30,
    "cost_rate": 0.20
}
```

**Why limit to India and 3 suppliers?** Task 1 is deliberately simple so the agent can first learn the basic loop: observe, act, receive reward. Introducing EU carbon rules and USA OFAC checks before the agent understands the fundamentals would make learning extremely slow. The difficulty ramps up progressively.

### ✅ Pitstop Audit — Phase 1

```python
import importlib
task1 = importlib.import_module("env.tasks.task1_easy")

assert task1.MAX_STEPS == 20
assert task1.DISRUPTIONS_ENABLED == False
assert set(task1.VALID_ACTIONS) == {0, 1, 2, 3}
assert "India" in task1.SUPPLIER_COUNTRIES
print("✅ Task 1 config valid")
```
**All assertions pass → Phase 1 complete.**

---

## Phase 2 — Write Task 2 and Task 3 Configs

Both follow the same pattern as Task 1. Write them in `env/tasks/task2_medium.py` and `env/tasks/task3_hard.py`.

**Task 2 (`task2_medium.py`):** India + EU, 6 suppliers (all 4 India + all 3 EU), 50 max steps, actions 0–5 (adds `negotiate_price` and `split_order`), 1 disruption enabled (port strike at step 8 only).

**Task 3 (`task3_hard.py`):** All 3 countries, all 10 suppliers, 100 max steps, all 7 actions including `escalate`, all 3 disruptions enabled.

```python
# task2_medium.py
TASK_ID = 2
MAX_STEPS = 50
VALID_ACTIONS = [0, 1, 2, 3, 4, 5]
SUPPLIER_COUNTRIES = ["India", "EU"]
NUM_SUPPLIERS = 6
DISRUPTIONS_ENABLED = True
ACTIVE_DISRUPTIONS = ["port_strike_india"]  # Only one in Task 2
STARTING_BUDGET = 200000.0

# task3_hard.py
TASK_ID = 3
MAX_STEPS = 100
VALID_ACTIONS = [0, 1, 2, 3, 4, 5, 6]
SUPPLIER_COUNTRIES = ["India", "EU", "USA"]
NUM_SUPPLIERS = 10
DISRUPTIONS_ENABLED = True
ACTIVE_DISRUPTIONS = ["port_strike_india", "war_reroute_eu", "protest_france"]
STARTING_BUDGET = 200000.0
```

### ✅ Pitstop Audit — Phase 2

```python
import importlib

for task_num, expected_max_steps, expected_actions in [(2, 50, 6), (3, 100, 7)]:
    mod = importlib.import_module(f"env.tasks.task{task_num}_{'medium' if task_num==2 else 'hard'}")
    assert mod.MAX_STEPS == expected_max_steps
    assert len(mod.VALID_ACTIONS) == expected_actions
    print(f"✅ Task {task_num} config valid")
```
**Both tasks load and have correct step/action counts → Phase 2 complete.**

---

## Phase 3 — Understand the Grader Contract (Read This Carefully)

Before writing any grader code, you need to understand exactly what the graders are expected to receive and return, because this contract is what the hackathon judges rely on.

Each grader receives a single argument: a dictionary called `episode_log` that represents everything that happened during one completed run of that task. The structure looks like this:

```python
episode_log = {
    "task_id": 1,
    "seed": 42,
    "steps": [
        {"step": 1, "action": 0, "reward": 0.71, "done": False,
         "compliance": 1.0, "cost_usd": 38000, "lead_days": 7, "carbon_tons": 3.5},
        {"step": 2, "action": 3, "reward": 0.55, "done": False, ...},
        # ... more steps ...
        {"step": 20, "action": 1, "reward": 0.62, "done": True, ...},
    ],
    "total_violations": 0,
    "final_budget": 122000.0,
    "total_carbon": 14.2,
    "total_lead_days": 47
}
```

The grader must return a single float between 0.0 and 1.0. Three things will get your submission disqualified by the automated judge: returning `None`, returning `NaN`, or returning a value outside `[0.0, 1.0]`. A fourth disqualification is returning the same constant value for every possible episode — this tells the judges the grader isn't actually measuring anything.

---

## Phase 4 — Write the Three Graders

**File: `graders/grader1.py`**

Task 1 grading is relatively simple — it weights compliance and delivery, with a small cost component:

```python
def grade(episode_log: dict) -> float:
    """
    Returns a float in [0.0, 1.0] representing Task 1 performance.
    Disqualification checks:
    - If episode_log is empty or has 0 steps → return 0.0 (don't crash)
    - Never return NaN or None
    """
    steps = episode_log.get("steps", [])

    # Handle edge case: done=True at step 1 (immediate hard violation)
    if not steps:
        return 0.0

    total_steps = len(steps)
    violations = episode_log.get("total_violations", total_steps)  # default to worst case

    # compliance_rate: fraction of steps with no violation
    compliance_rate = max(0.0, 1.0 - (violations / max(total_steps, 1)))

    # delivery_rate: inverse of average lead days normalised to max (30 days)
    total_lead = episode_log.get("total_lead_days", 30 * total_steps)
    avg_lead = total_lead / max(total_steps, 1)
    delivery_rate = max(0.0, 1.0 - (avg_lead / 30.0))

    # cost_rate: how much budget remains (higher = better)
    starting_budget = 200000.0
    final_budget = episode_log.get("final_budget", 0.0)
    cost_rate = max(0.0, final_budget / starting_budget)

    score = 0.50 * compliance_rate + 0.30 * delivery_rate + 0.20 * cost_rate

    # Final safety clamp — never return outside [0, 1]
    return round(max(0.0, min(1.0, score)), 4)
```

**Files: `graders/grader2.py` and `graders/grader3.py`**

Use the same structure as grader1, but adjust the weights to reflect the harder tasks. For Task 2, add a carbon component (the EU carbon rules matter now). For Task 3, weigh compliance even higher because OFAC violations are catastrophic:

```python
# grader2.py — Task 2 adds carbon scoring
def grade(episode_log: dict) -> float:
    steps = episode_log.get("steps", [])
    if not steps:
        return 0.0

    # ... same compliance, delivery, cost calculations ...

    # Carbon rate (new in Task 2 — EU carbon rules apply)
    total_carbon = episode_log.get("total_carbon", 50.0)
    carbon_rate = max(0.0, 1.0 - (total_carbon / 50.0))

    score = 0.40 * compliance_rate + 0.25 * delivery_rate + 0.20 * cost_rate + 0.15 * carbon_rate
    return round(max(0.0, min(1.0, score)), 4)

# grader3.py — Task 3 maximises compliance weight (OFAC violations = immediate failure)
def grade(episode_log: dict) -> float:
    steps = episode_log.get("steps", [])
    if not steps:
        return 0.0

    # ... compliance, delivery, cost, carbon ...

    score = 0.45 * compliance_rate + 0.25 * delivery_rate + 0.15 * cost_rate + 0.15 * carbon_rate
    return round(max(0.0, min(1.0, score)), 4)
```

### ✅ Pitstop Audit — Phase 4 (Day 2 Critical Gate)

Build three mock episode logs and test all graders. The most important test is confirming graders don't crash when `done=True` happens at step 1:

```python
from graders.grader1 import grade as grade1
from graders.grader2 import grade as grade2
from graders.grader3 import grade as grade3

# Test 1: Good episode — should score well (near 1.0)
good_ep = {
    "task_id": 1, "seed": 42,
    "steps": [{"step": i, "action": 0, "reward": 0.7, "done": i==19}
              for i in range(1, 21)],
    "total_violations": 0,
    "final_budget": 140000.0,
    "total_lead_days": 50,
    "total_carbon": 10.0
}

# Test 2: Bad episode — immediate hard violation at step 1
bad_ep = {
    "task_id": 1, "seed": 42,
    "steps": [{"step": 1, "action": 0, "reward": -1.0, "done": True}],
    "total_violations": 1,
    "final_budget": 200000.0,
    "total_lead_days": 0,
    "total_carbon": 0.0
}

# Test 3: Empty episode (edge case)
empty_ep = {"task_id": 1, "seed": 42, "steps": [], "total_violations": 0}

for grader_fn in [grade1, grade2, grade3]:
    good_score = grader_fn(good_ep)
    bad_score = grader_fn(bad_ep)
    empty_score = grader_fn(empty_ep)

    assert isinstance(good_score, float), "Score must be float"
    assert 0.0 <= good_score <= 1.0, f"Good score out of range: {good_score}"
    assert 0.0 <= bad_score <= 1.0, f"Bad score out of range: {bad_score}"
    assert empty_score == 0.0, f"Empty episode should return 0.0, got {empty_score}"
    assert good_score != bad_score, "Grader returns same score for different episodes!"
    print(f"  Good: {good_score:.4f}, Bad: {bad_score:.4f}, Empty: {empty_score:.4f}")

print("✅ All graders pass critical gate checks")
```
**All 3 graders return floats in [0, 1], differ between good and bad episodes, and handle empty episodes gracefully → Day 2 critical gate cleared.**
