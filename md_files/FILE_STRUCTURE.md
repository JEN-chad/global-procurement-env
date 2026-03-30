# GlobalProcurementEnv — GitHub Repository File Structure
**Every file, every folder, every `__init__.py`, and exactly who creates what.**

---

## Complete Tree

```
global-procurement-env/                  ← GitHub repo root
│
├── .agents/                             ← Antigravity IDE rules folder
│   └── rules/
│       └── gemini.md                    ← Gemini workspace rules (12000 chars)
│
├── env/                                 ← JENISH owns everything here
│   ├── __init__.py                      ← Empty — makes env/ a Python package
│   ├── global_procurement_env.py        ← Main env class: reset/step/state
│   ├── supply_chain_sim.py              ← SupplyChainState dataclass + apply_action()
│   ├── constraint_engine.py             ← Loads policy JSON, validates actions
│   ├── disruption_engine.py             ← Seeded crisis triggers per step count
│   ├── gym_wrapper.py                   ← Gymnasium wrapper so SB3 can train
│   └── tasks/
│       ├── __init__.py                  ← Empty — makes tasks/ a Python package
│       ├── task1_easy.py                ← India only, 3 suppliers, 20 steps
│       ├── task2_medium.py              ← India + EU, 6 suppliers, 50 steps
│       └── task3_hard.py               ← All 3 countries, 10 suppliers, 100 steps
│
├── graders/                             ← JESWIN owns everything here
│   ├── __init__.py                      ← Empty — makes graders/ a Python package
│   ├── grader1.py                       ← Task 1 grader → returns float 0.0–1.0
│   ├── grader2.py                       ← Task 2 grader → returns float 0.0–1.0
│   └── grader3.py                       ← Task 3 grader → returns float 0.0–1.0
│
├── api/                                 ← JAMAL owns everything here
│   ├── __init__.py                      ← Empty — makes api/ a Python package
│   ├── main.py                          ← FastAPI app: /reset /step /state /health /metrics
│   └── schemas.py                       ← Pydantic models: Observation, Action, Reward + HTTP schemas
│
├── policies/                            ← JESWIN owns everything here
│   ├── india_policy.json                ← GST 18%, duty 18%, local content 30%, max $50k
│   ├── eu_policy.json                   ← Carbon levy $85/ton, max 3 tons/order, EUDR
│   └── usa_policy.json                  ← OFAC sanctions, Buy American 50% above $100k
│
├── data/                                ← JESWIN owns everything here
│   └── suppliers.json                   ← 10 suppliers: 4 India, 3 EU, 3 USA
│
├── disruptions/                         ← JESWIN owns everything here
│   └── scenarios.json                   ← port_strike@8, war_reroute@15, protest_france@22
│
├── models/                              ← JENISH owns everything here
│   ├── .gitkeep                         ← Keeps folder tracked before models are trained
│   ├── task1_ppo.zip                    ← Trained PPO model Task 1 (added Day 3)
│   ├── task2_ppo.zip                    ← Trained PPO model Task 2 (added Day 4)
│   └── task3_ppo.zip                    ← Trained PPO model Task 3 (added Day 4)
│
├── md_files/                            ← Team planning docs (not part of submission)
│   ├── PROJECT_OVERVIEW.md
│   ├── INTEGRATION_GUIDE.md
│   ├── jenish_day1.md
│   ├── jenish_day2.md
│   ├── jenish_day3.md
│   ├── jenish_day4.md
│   ├── jeswin_day1.md
│   ├── jeswin_day2.md
│   ├── jeswin_day3.md
│   ├── jeswin_day4.md
│   ├── jamal_day1.md
│   ├── jamal_day2.md
│   ├── jamal_day3.md
│   └── jamal_day4.md
│
├── baseline.py                          ← JENISH — random agent, no LLM, seeds all runs
├── inference.py                         ← JENISH — ⚠️ LLM agent via OpenAI client (MANDATORY)
├── train.py                             ← JENISH — SB3 PPO training script
├── trained_agent.py                     ← JENISH — loads PPO models, evaluates all 3 tasks
├── README.md                            ← JESWIN — env description, action/obs space, curl examples
├── openenv.yaml                         ← JAMAL — OpenEnv spec file, passes openenv validate
├── Dockerfile                           ← JAMAL — python:3.11-slim, port 7860, workers=1
└── requirements.txt                     ← JAMAL — all packages pinned with ==X.Y.Z
```

---

## Folder-by-Folder Purpose

### `.agents/rules/gemini.md`
The Antigravity IDE reads this file automatically and applies it as a workspace rule for Gemini. It contains the 12,000-character rule set covering the OpenEnv spec, disqualification checklist, approved libraries, banned libraries, and all implementation constraints. **This file must be in `.agents/rules/` exactly — Antigravity will not pick it up from any other path.**

---

### `env/` — Jenish's Domain

This is the simulation engine. Every Python file here is owned and maintained by Jenish. No one else edits these files without coordinating first.

**`global_procurement_env.py`** — The top-level environment class. Implements the three OpenEnv-required methods. `reset(task, seed)` returns a Pydantic `Observation`. `step(action)` returns a 4-tuple `(Observation, Reward, bool, dict)`. `state()` returns the current `Observation` without advancing. This file imports from `supply_chain_sim.py`, `constraint_engine.py`, `disruption_engine.py`, and the Pydantic schemas from `api/schemas.py`.

**`supply_chain_sim.py`** — Contains the `SupplyChainState` dataclass (internal state, never returned directly to callers) and the `apply_action()` function which handles all 7 action types. This is the physics engine — it mutates `SupplyChainState` in response to actions.

**`constraint_engine.py`** — Loads the policy JSON files from `policies/` and validates every action against the relevant country's rules. Returns `(is_valid: bool, penalty: float, violation_type: str | None)`. Hard rule violations set `is_valid=False`. Soft rule violations return a negative `penalty` float.

**`disruption_engine.py`** — Tracks the three seeded crisis events. `check(step_count)` returns a list of active disruptions at that step. Uses the same `random.seed(seed)` that `reset()` sets, ensuring identical disruption timing across runs with the same seed.

**`gym_wrapper.py`** — A `gymnasium.Env` subclass that wraps `GlobalProcurementEnv` so that SB3's PPO can train on it. Converts `Observation` objects to flat `numpy` arrays for the neural network. Implements `reset() → (np.ndarray, dict)` and `step(action) → (np.ndarray, float, bool, bool, dict)` per the Gymnasium v0.29 API.

**`tasks/task1_easy.py`, `task2_medium.py`, `task3_hard.py`** — Config modules that define task-specific parameters: `TASK_ID`, `MAX_STEPS`, `VALID_ACTIONS`, `SUPPLIER_COUNTRIES`, `DISRUPTIONS_ENABLED`. These are imported by `global_procurement_env.py` during `reset()` to configure the episode correctly.

---

### `graders/` — Jeswin's Domain

Each grader takes an `episode_log` dict and returns a single `float` in `[0.0, 1.0]`. The grader is called by the API at the end of an episode (when `done=True`). Judges enumerate all three graders and verify scores are non-constant and in range.

**`grader1.py`** — Task 1 scoring. Weights: 50% compliance, 30% delivery, 20% cost. Handles empty episodes by returning `0.0`.

**`grader2.py`** — Task 2 scoring. Adds a carbon component (EU rules apply). Weights: 40% compliance, 25% delivery, 20% cost, 15% carbon.

**`grader3.py`** — Task 3 scoring. Maximises compliance weight because OFAC violations are catastrophic. Weights: 45% compliance, 25% delivery, 15% cost, 15% carbon.

---

### `api/` — Jamal's Domain

**`schemas.py`** — Two categories of Pydantic models. First: OpenEnv interface models (`Observation`, `Action`, `Reward`, `SupplierObservation`) which are imported by `global_procurement_env.py` and returned from the environment's methods. Second: FastAPI HTTP request models (`ResetRequest`, `StepRequest`, `HealthResponse`) which validate incoming JSON from callers. Both live here so there is one single source of truth for all type definitions.

**`main.py`** — The FastAPI application. One global `GlobalProcurementEnv` instance. One `threading.Lock()` wrapping `/reset` and `/step`. Five routes: `GET /health` (no try/except, always 200), `POST /reset`, `POST /step`, `GET /state`, `GET /metrics`. Every route except `/health` wraps its logic in `try/except Exception as e → HTTPException(400)`. The `/step` route unpacks the 4-tuple from `env.step()` and merges it with `model_dump()` before returning JSON.

---

### `policies/` — Jeswin's Domain

Three JSON rulebooks, one per country. Loaded by `constraint_engine.py` at action-validation time.

**`india_policy.json`** — import_duty_rate: 0.18, gst_rate: 0.12, carbon_levy_per_ton_usd: 15.0, max_single_source_usd: 50000, mandatory_local_content_pct: 0.30, sanctioned_categories, hard_rules, soft_rules.

**`eu_policy.json`** — import_duty_rate: 0.05, carbon_levy_per_ton_usd: 85.0, max_carbon_tons_per_order: 3.0, deforestation_act_applies: true, gdpr_data_flag: true, sanctioned_categories, hard_rules, soft_rules.

**`usa_policy.json`** — import_duty_rate: 0.08, buy_american_threshold_usd: 100000, buy_american_domestic_pct: 0.50, ofac_sanctioned_countries: ["Iran","North Korea","Russia"], export_control_applies: true, sanctioned_categories, hard_rules, soft_rules.

---

### `data/` — Jeswin's Domain

**`suppliers.json`** — Array of 10 supplier objects. Each has: `id` (e.g. "IN_01"), `name`, `country` ("India" / "EU" / "USA"), `price_usd`, `lead_days`, `carbon_tons`, `available` (bool), `sanctioned_category` (null or string). Distribution: 4 India, 3 EU, 3 USA.

---

### `disruptions/` — Jeswin's Domain

**`scenarios.json`** — Array of 3 disruption objects. Each has: `name`, `trigger_step`, `min_task` (which task level activates it), `duration_steps`, `affected_suppliers` (list of supplier IDs), `effect` (type of impact), and effect-specific fields (`multiplier` or `days_added`).

---

### `models/` — Jenish's Domain

Stores trained PPO model zip files. All files must be under 150 MB each. Added to the repo during Day 3 (task1) and Day 4 (task2, task3). The `.gitkeep` placeholder ensures the folder exists in the repo before any models are trained so teammates' import paths don't break.

---

### Root-Level Python Files

**`baseline.py`** (Jenish) — Random agent. Calls `/reset` then loops `/step` with `random.randint(0, max_action)` until `done=True`. Prints grader scores for all 3 tasks. Must be deterministic: seeded runs always produce the same scores. This is what judges run first to verify the environment works.

**`inference.py`** (Jenish) — ⚠️ **MANDATORY.** LLM-driven agent. Uses `openai.OpenAI(base_url=os.getenv("API_BASE_URL"), api_key=os.getenv("HF_TOKEN"))`. Reads `MODEL_NAME` from env var. Calls the LLM to choose actions based on the current observation. `MAX_STEPS` ≤ 15 per episode to stay under the 20-minute total runtime limit. Prints LLM agent scores for all 3 tasks.

**`train.py`** (Jenish) — SB3 PPO training. Uses `ProcurementGymWrapper`. Trains Task 1 at 50k steps, Task 2 at 100k steps, Task 3 at 50k steps. Saves to `models/taskN_ppo.zip`.

**`trained_agent.py`** (Jenish) — Loads each saved PPO model and runs 5 evaluation episodes per task. Prints average scores. Used to verify trained > random baseline.

**`README.md`** (Jeswin) — Public documentation. Must include: environment description and motivation, action space table (all 7 actions), observation space table (all fields with types and examples), task descriptions with difficulty levels, setup and usage instructions, curl examples pointing at the live HF Space URL, and the score comparison table (Random Baseline / Trained PPO / LLM Inference).

**`openenv.yaml`** (Jamal) — OpenEnv specification. Must pass `openenv validate openenv.yaml --url LIVE_URL`. Contains: name, version, description, 3 tasks with IDs matching task config files, action_space (Discrete n=7), observation_space (Dict with all fields), reward_range ([-1.0, 1.0]).

**`Dockerfile`** (Jamal) — Uses `FROM python:3.11-slim`. Copies all required directories: `env/`, `graders/`, `api/`, `policies/`, `data/`, `disruptions/`, `models/`. Copies root scripts: `baseline.py`, `inference.py`, `train.py`, `trained_agent.py`. Exposes port 7860. CMD uses `uvicorn api.main:app --host 0.0.0.0 --port 7860 --workers 1`.

**`requirements.txt`** (Jamal) — All dependencies pinned: `openenv-core>=0.2.2`, `fastapi==0.111.0`, `uvicorn[standard]==0.29.0`, `pydantic==2.7.1`, `openai>=1.0.0`, `stable-baselines3==2.3.2`, `gymnasium==0.29.1`, `torch==2.3.0`, `numpy==1.26.4`.

---

## Critical File: `__init__.py` Placement

Every folder that contains Python files that are imported elsewhere **must** have an `__init__.py`. Without it, Python cannot treat the folder as a package, and imports like `from env.global_procurement_env import GlobalProcurementEnv` will fail both locally and inside Docker.

| Folder | Needs `__init__.py`? | Why |
|--------|---------------------|-----|
| `env/` | ✅ Yes | `global_procurement_env.py` is imported by `api/main.py` |
| `env/tasks/` | ✅ Yes | Task configs are imported by `global_procurement_env.py` |
| `graders/` | ✅ Yes | Graders are imported by `api/main.py` or called directly |
| `api/` | ✅ Yes | `schemas.py` is imported by `env/global_procurement_env.py` |
| `policies/` | ❌ No | Only JSON files — no Python imports |
| `data/` | ❌ No | Only JSON files — no Python imports |
| `disruptions/` | ❌ No | Only JSON files — no Python imports |
| `models/` | ❌ No | Only zip files — no Python imports |

---

## GitHub Setup Commands

```bash
# Clone and set up from scratch
git clone https://github.com/YOUR_USERNAME/global-procurement-env
cd global-procurement-env

# Create all directories with gitkeep placeholders
mkdir -p .agents/rules
mkdir -p env/tasks
mkdir -p graders api policies data disruptions models

touch env/__init__.py env/tasks/__init__.py
touch graders/__init__.py api/__init__.py
touch models/.gitkeep

# Add the HF Space as a second remote
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/global-procurement-env

# Verify both remotes exist
git remote -v
# origin  https://github.com/YOUR_USERNAME/global-procurement-env.git
# space   https://huggingface.co/spaces/YOUR_USERNAME/global-procurement-env
```

---

## Day-by-Day File Creation Schedule

| File | Created on | By |
|------|-----------|-----|
| `.agents/rules/gemini.md` | Day 1 | Jamal |
| `env/__init__.py`, `env/tasks/__init__.py` | Day 1 | Jamal (repo setup) |
| `graders/__init__.py`, `api/__init__.py` | Day 1 | Jamal (repo setup) |
| `models/.gitkeep` | Day 1 | Jamal (repo setup) |
| `env/supply_chain_sim.py` | Day 1 | Jenish |
| `env/constraint_engine.py` | Day 1 | Jenish |
| `policies/india_policy.json` | Day 1 | Jeswin |
| `policies/eu_policy.json` | Day 1 | Jeswin |
| `policies/usa_policy.json` | Day 1 | Jeswin |
| `data/suppliers.json` | Day 1 | Jeswin |
| `disruptions/scenarios.json` | Day 1 | Jeswin |
| `Dockerfile` (skeleton) | Day 1 | Jamal |
| `requirements.txt` | Day 1 | Jamal |
| `openenv.yaml` (skeleton) | Day 1 | Jamal |
| `env/global_procurement_env.py` | Day 2 | Jenish |
| `env/disruption_engine.py` | Day 2 | Jenish |
| `env/tasks/task1_easy.py` | Day 2 | Jeswin |
| `env/tasks/task2_medium.py` | Day 2 | Jeswin |
| `env/tasks/task3_hard.py` | Day 2 | Jeswin |
| `graders/grader1.py` | Day 2 | Jeswin |
| `graders/grader2.py` | Day 2 | Jeswin |
| `graders/grader3.py` | Day 2 | Jeswin |
| `api/schemas.py` | Day 2 | Jamal |
| `api/main.py` | Day 2 | Jamal |
| `openenv.yaml` (finalised) | Day 2 | Jamal |
| `baseline.py` | Day 3 | Jenish |
| `inference.py` | Day 3 | Jenish |
| `env/gym_wrapper.py` | Day 3 | Jenish |
| `train.py` | Day 3 | Jenish |
| `trained_agent.py` | Day 3 | Jenish |
| `models/task1_ppo.zip` | Day 3 | Jenish |
| `README.md` | Day 3 | Jeswin |
| `Dockerfile` (finalised) | Day 3 | Jamal |
| `models/task2_ppo.zip` | Day 4 | Jenish |
| `models/task3_ppo.zip` | Day 4 | Jenish |

---

## `.gitignore` Recommended Contents

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.env
venv/
.venv/

# Training artifacts (only keep final zips)
*.zip.bak
replay_buffer_*.pkl

# Local test files
test_day*.py
load_test.py
stress_test.py
integration_test.py

# OS
.DS_Store
Thumbs.db
```

---

## Submission Checklist — What GitHub Must Have

Before pushing to the HF Space and submitting, confirm these files exist at exactly these paths:

```
✅ inference.py              (root — disqualification if missing)
✅ baseline.py               (root)
✅ openenv.yaml              (root)
✅ Dockerfile                (root)
✅ requirements.txt          (root)
✅ README.md                 (root)
✅ env/__init__.py           (prevents import errors)
✅ graders/__init__.py       (prevents import errors)
✅ api/__init__.py           (prevents import errors)
✅ env/tasks/__init__.py     (prevents import errors)
✅ models/task1_ppo.zip      (under 150 MB)
✅ models/task2_ppo.zip      (under 150 MB)
✅ models/task3_ppo.zip      (under 150 MB)
✅ .agents/rules/gemini.md   (Antigravity workspace rules)
```
