# Jenish (P1) — Day 1 Instructions
**Role:** Env Core | **Theme:** Build the simulation engine foundation independently

> ⚠️ **Today's Critical Gate:** Both `supply_chain_sim.py` and `constraint_engine.py` must run together without errors in a plain Python terminal. No Docker, no API, no teammates' files needed yet.

---

## 🔗 Cross-Team Dependency Note

Today you work **fully independently** — but the decisions you make, especially the field names in `SupplyChainState`, become the contract that Jeswin's JSON files and Jamal's API must conform to. **By end of day, you MUST share your field names, types, and defaults with the team.** This is the single most important handoff of the entire project.

---

## Phase 1 — Define the State Blueprint (`SupplyChainState`)

**What you're building:** A Python `dataclass` that represents a complete snapshot of the procurement world at any moment in time. This is the **internal state object** — it lives inside the environment class and is never directly exposed to the API. The API exposes Pydantic `Observation` models (defined in `api/schemas.py` and agreed upon with Jamal). Think of `SupplyChainState` as the engine's internals, and `Observation` as the dashboard readout.

> **Important distinction:**
> - `SupplyChainState` = internal Python dataclass, used only inside `env/`
> - `Observation` = Pydantic `BaseModel`, returned by `reset()`, `step()`, `state()` to the outside world
> 
> This day you build the dataclass. On Day 2 you wrap it in Pydantic. Today's job is to get the field names right — because Jeswin's JSON must use these same names.

**File:** `env/supply_chain_sim.py` (define the dataclass at the top of this file, or in a separate `state.py` — just be consistent)

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class SupplyChainState:
    inventory: Dict[str, float] = field(default_factory=lambda: {"steel": 0.0, "chips": 0.0, "fabric": 0.0})
    suppliers: List[Dict[str, Any]] = field(default_factory=list)
    budget: float = 200000.0
    lead_days: int = 0
    carbon: float = 0.0
    step_count: int = 0
    violations: int = 0
```

**Why each field matters:**
- `inventory` tracks the 3 raw materials the agent procures.
- `suppliers` is a list of available supplier dicts (populated by loading `suppliers.json`).
- `budget` is how much money is left — cost efficiency is scored against this.
- `lead_days` tracks cumulative delivery delay — delivery speed is scored against this.
- `carbon` tracks cumulative carbon footprint — carbon score is scored against this.
- `step_count` tracks which step we're on — disruptions fire at specific step numbers.
- `violations` counts policy rule breaks — compliance score is computed from this.

> 🔑 **The field names you choose here are the internal contract.** `carbon` is what your own `_compute_reward()` method will read. `violations` is what the grader scores against. `step_count` is what the disruption engine checks. Do not change these names after today without telling everyone.

### ✅ Pitstop Audit — Phase 1
Run this sanity check in your terminal before moving to Phase 2:

```python
# Quick test — paste this in a Python terminal
from supply_chain_sim import SupplyChainState
s = SupplyChainState()
print(s.budget)        # should print 200000.0
print(s.violations)    # should print 0
print(s.inventory)     # should print {'steel': 0.0, 'chips': 0.0, 'fabric': 0.0}
print(s.step_count)    # should print 0
```
**If all 4 lines print expected values → Phase 1 complete. If any fail → fix before proceeding.**

---

## Phase 2 — Build the Simulation Logic (`supply_chain_sim.py`)

**What you're building:** The "physics engine" of the simulation. When the agent picks an action (a number 0–6), this file decides what actually changes — inventory goes up, budget goes down, lead days accumulate, etc.

**File:** `env/supply_chain_sim.py`

You need to handle all **7 action types**. Think of each action as a different procurement decision the agent can make:

```python
def apply_action(state: SupplyChainState, action: int, available_suppliers: list) -> dict:
    """
    Applies an action to the state and returns a result dict with:
    - cost_incurred (float)
    - lead_days_added (int)
    - carbon_added (float)
    - action_label (str)
    - selected_supplier (dict or None)
    """
    if action == 0:   # approve_cheapest
        # Pick the supplier with the lowest price_usd from available_suppliers
        # Deduct cost from state.budget, add to state.inventory, add carbon, add lead_days
        pass

    elif action == 1: # approve_fastest
        # Pick supplier with fewest lead_days
        pass

    elif action == 2: # approve_greenest
        # Pick supplier with smallest carbon_tons
        pass

    elif action == 3: # reject_all
        # No supplier selected. Apply a minor cost penalty (e.g. -500 from budget)
        pass

    elif action == 4: # negotiate_price (Task 2 & 3 only)
        # Take cheapest supplier, apply 10% discount to price, then approve
        pass

    elif action == 5: # split_order (Task 2 & 3 only)
        # Split order 50/50 between two cheapest available suppliers
        pass

    elif action == 6: # escalate (Task 3 only)
        # Flag for human review. No purchase. Apply a soft penalty.
        pass

    state.step_count += 1
    return result
```

**Key rule:** Only increment `state.step_count` once, at the end of `apply_action`. This ensures disruption triggers (which fire at specific step numbers) are checked before the step count advances.

### ✅ Pitstop Audit — Phase 2

```python
# Test with a mock supplier list — no JSON files needed yet
mock_suppliers = [
    {"id": "IN_01", "country": "India", "price_usd": 40000, "lead_days": 5, "carbon_tons": 2.0, "available": True},
    {"id": "EU_01", "country": "EU", "price_usd": 60000, "lead_days": 3, "carbon_tons": 1.0, "available": True},
]
state = SupplyChainState(budget=200000.0)
result = apply_action(state, 0, mock_suppliers)  # approve_cheapest
print(state.budget)     # should be less than 200000
print(state.step_count) # should be 1
print(result["selected_supplier"]["id"])  # should be "IN_01" (cheapest)

result2 = apply_action(state, 3, mock_suppliers)  # reject_all
print(state.step_count) # should be 2
```
**All assertions pass → Phase 2 complete. Budget decreased and step_count incremented → proceed.**

---

## Phase 3 — Build the Rule Enforcer (`constraint_engine.py`)

**What you're building:** The policy checker. Before any action is approved, this engine loads the relevant country's JSON policy file and validates the action against the rules. It's the bridge between Jeswin's JSON data and your simulation logic.

**File:** `env/constraint_engine.py`

```python
import json
import os

POLICY_DIR = os.path.join(os.path.dirname(__file__), "..", "policies")

def load_policy(country: str) -> dict:
    """Loads the policy JSON for a given country (India, EU, USA)."""
    filename = f"{country.lower()}_policy.json"
    filepath = os.path.join(POLICY_DIR, filename)
    with open(filepath, "r") as f:
        return json.load(f)

def validate_action(state: SupplyChainState, selected_supplier: dict, policy: dict) -> tuple:
    """
    Returns (is_valid: bool, penalty: float, violation_type: str or None)
    
    Hard rule violation → is_valid=False, penalty=-1.0 (episode ends)
    Soft rule violation → is_valid=True, penalty=-0.2 (episode continues)
    No violation       → is_valid=True, penalty=0.0
    """
    penalty = 0.0
    
    # Hard rule: check sanctioned suppliers
    # Hard rule: check carbon limit per order (EU)
    # Hard rule: check OFAC sanctions (USA)
    # Soft rule: prefer low carbon
    # Soft rule: prefer domestic supplier
    
    return (True, penalty, None)
```

**Critical detail about hard vs soft rules:**
- A **hard rule** violation (like buying from a sanctioned entity) must immediately end the episode: set `done=True` and `reward=-1.0`. These are non-negotiable — they represent illegal actions in the real world.
- A **soft rule** violation (like not preferring a green supplier) subtracts 0.2 from the reward but lets the episode continue. Think of these as "not ideal but not illegal."

> ⚠️ **Important:** The policy files (`india_policy.json`, `eu_policy.json`, `usa_policy.json`) won't exist yet because Jeswin is writing them today. For Phase 3 testing, create **stub JSON files** with placeholder content matching the field names you expect. You and Jeswin will align these at the end-of-day sync.

### ✅ Pitstop Audit — Phase 3

```python
# Create a stub policies/india_policy.json with placeholder values first
# Then test:
from constraint_engine import load_policy, validate_action

policy = load_policy("India")
print(type(policy))  # should be dict
print("import_duty_rate" in policy)  # should be True

state = SupplyChainState()
supplier = {"id": "IN_01", "country": "India", "price_usd": 40000, "carbon_tons": 2.0}
is_valid, penalty, violation = validate_action(state, supplier, policy)
print(is_valid)   # should be True for a clean supplier
print(penalty)    # should be 0.0 or a small float
```
**Policy loads and returns a dict → validation runs without crashing → Phase 3 complete.**

---

## Phase 4 — Integration Test (Both Files Together)

Run Phases 2 and 3 together in a single test script to confirm they interact correctly:

```python
# test_day1.py — run this as: python test_day1.py
from supply_chain_sim import SupplyChainState, apply_action
from constraint_engine import load_policy, validate_action

state = SupplyChainState(budget=200000.0)
policy = load_policy("India")  # uses your stub JSON

mock_suppliers = [
    {"id": "IN_01", "country": "India", "price_usd": 40000, "lead_days": 5, "carbon_tons": 2.0, "available": True},
]

# Simulate 5 steps
for i in range(5):
    result = apply_action(state, 0, mock_suppliers)
    is_valid, penalty, vtype = validate_action(state, result["selected_supplier"], policy)
    print(f"Step {state.step_count}: budget={state.budget:.0f}, valid={is_valid}, penalty={penalty}")

print("✅ 5 steps completed without crash")
```

### ✅ Pitstop Audit — Phase 4 (Day 1 Critical Gate)

```
Expected output:
Step 1: budget=160000, valid=True, penalty=0.0
Step 2: budget=120000, valid=True, penalty=0.0
...
✅ 5 steps completed without crash
```

**If you see 5 lines of output and no Python exceptions → Day 1 critical gate passed.**

---

## 📤 End-of-Day Handoff (Mandatory)

Post this message in your team chat before the sync call:

```
JENISH — DAY 1 HANDOFF

SupplyChainState internal fields (dataclass — env only):
  - inventory: Dict[str, float] — keys: "steel", "chips", "fabric"
  - suppliers: List[Dict] — each dict has: id, country, price_usd, lead_days, carbon_tons, available
  - budget: float — default 200000.0
  - lead_days: int — default 0
  - carbon: float — default 0.0
  - step_count: int — default 0
  - violations: int — default 0

Pydantic Observation model (for OpenEnv API — coordinate with Jamal on Day 2):
  - step: int
  - budget_remaining: float
  - inventory: Dict[str, float]
  - suppliers: List[SupplierObservation]
  - active_disruptions: List[str]
  - policy_violations_this_episode: int
  - current_task: int
  - grader_score: Optional[float]

Constraint engine expects these keys in policy JSON:
  - import_duty_rate (float)
  - carbon_levy_per_ton_usd (float)
  - max_single_source_usd (float, India only)
  - max_carbon_tons_per_order (float, EU only)
  - sanctioned_categories (list of strings)
  - hard_rules (list of strings)
  - soft_rules (list of strings)
```

Jeswin must confirm JSON field names match. Jamal must confirm GitHub is pushed. Both must happen before anyone ends their workday.

> **Note for Day 2:** On Day 2 morning, sync with Jamal to finalise the Pydantic `Observation`, `Action`, and `Reward` schemas in `api/schemas.py`. Your `GlobalProcurementEnv.reset()` and `step()` will import and return these Pydantic types — they are the public API contract required by OpenEnv spec.
