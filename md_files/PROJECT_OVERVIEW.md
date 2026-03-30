# GlobalProcurementEnv — Full Project Overview
**OpenEnv Hackathon · 3-Person Team · Hugging Face Docker Deployment**

---

## 👥 Team

| Role | Person | Responsibility |
|------|--------|----------------|
| **P1 — Env Core** | **Jenish** | All environment Python files, training scripts, and RL models |
| **P2 — Data & Tasks** | **Jeswin** | All JSON data files, graders, task configs, and README |
| **P3 — Infra & Deploy** | **Jamal** | FastAPI app, Dockerfile, Hugging Face Space deployment |

---

## 🏗 What We Are Building

GlobalProcurementEnv is an AI simulation environment. An AI agent acts as a **procurement officer** — it buys materials from suppliers in India, the EU, and the USA while following real government trade rules and surviving unexpected crises. The environment runs inside a Docker container hosted on Hugging Face Spaces, exposed via a FastAPI REST API that the hackathon judges call automatically.

---

## 📁 Repository Structure

```
global-procurement-env/
│
├── env/
│   ├── global_procurement_env.py     ← Jenish (P1)
│   ├── supply_chain_sim.py           ← Jenish (P1)
│   ├── constraint_engine.py          ← Jenish (P1)
│   ├── disruption_engine.py          ← Jenish (P1)
│   ├── gym_wrapper.py                ← Jenish (P1)
│   └── tasks/
│       ├── task1_easy.py             ← Jenish (P1)
│       ├── task2_medium.py           ← Jenish (P1)
│       └── task3_hard.py             ← Jenish (P1)
│
├── graders/
│   ├── grader1.py                    ← Jeswin (P2)
│   ├── grader2.py                    ← Jeswin (P2)
│   └── grader3.py                    ← Jeswin (P2)
│
├── api/
│   ├── main.py                       ← Jamal (P3)
│   └── schemas.py                    ← Jamal (P3)
│
├── policies/
│   ├── india_policy.json             ← Jeswin (P2)
│   ├── eu_policy.json                ← Jeswin (P2)
│   └── usa_policy.json               ← Jeswin (P2)
│
├── data/
│   └── suppliers.json                ← Jeswin (P2)
│
├── disruptions/
│   └── scenarios.json                ← Jeswin (P2)
│
├── models/
│   ├── task1_ppo.zip                 ← Jenish (P1)
│   ├── task2_ppo.zip                 ← Jenish (P1)
│   └── task3_ppo.zip                 ← Jenish (P1)
│
├── baseline.py                       ← Jenish (P1) — random agent, no LLM
├── inference.py                      ← Jenish (P1) — ⚠️ LLM agent (MANDATORY)
├── train.py                          ← Jenish (P1)
├── trained_agent.py                  ← Jenish (P1)
├── README.md                         ← Jeswin (P2)
├── openenv.yaml                      ← Jamal (P3)
├── Dockerfile                        ← Jamal (P3)
└── requirements.txt                  ← Jamal (P3)
```

---

## 🗓 4-Day Master Task Table

### DAY 1 — Build the Foundation (Work Independently)
> **Critical Gate:** Each person tests their own piece in a plain Python terminal. No Docker. No API.

| Jenish (P1) | Jeswin (P2) | Jamal (P3) |
|-------------|-------------|------------|
| Write `SupplyChainState` dataclass | Write `policies/india_policy.json` | Create GitHub repo with correct folder structure |
| Write `supply_chain_sim.py` (all 7 actions) | Write `policies/eu_policy.json` | Write Dockerfile skeleton |
| Write `constraint_engine.py` | Write `policies/usa_policy.json` | Write `requirements.txt` |
| Test both files in terminal | Write `data/suppliers.json` (10 suppliers) | Write `openenv.yaml` skeleton |
| Share `SupplyChainState` field names with team | Write `disruptions/scenarios.json` | Create Hugging Face Space (Docker SDK) |
| | Verify JSON fields match Jenish's state | Push repo to GitHub |

**End-of-Day Sync:** Jenish shares field names → Jeswin confirms match → Jamal confirms GitHub is live → Everyone pulls from main.

---

### DAY 2 — Assemble + First Full Run
> **Critical Gate:** `env.reset()` + 100 random steps must complete without crashing.

| Jenish (P1) | Jeswin (P2) | Jamal (P3) |
|-------------|-------------|------------|
| Write `global_procurement_env.py` (reset/step/state) | Write `env/tasks/task1_easy.py` | Write `api/schemas.py` (Pydantic models) |
| `reset()` must create fresh state every call | Write `env/tasks/task2_medium.py` | Write `api/main.py` (all routes + lock) |
| Implement full `step()` flow | Write `env/tasks/task3_hard.py` | Add try/except to every route (400, never 500) |
| Implement reward formula (4-part weighted) | Write `graders/grader1.py` | Test all routes with curl on localhost:8000 |
| Seed random events with `random.seed(seed)` | Write `grader2.py` and `grader3.py` | Update `openenv.yaml` with real definitions |
| Run 100 random episodes — must not crash | Test all 3 graders with completed episode dict | |

**End-of-Day Sync:** Jamal starts FastAPI → Jenish calls `/reset` and `/step` via curl → Jeswin extracts a grader score (must be float 0.0–1.0).

---

### DAY 3 — Baseline + Docker + First HF Space Deploy
> **Critical Gate:** Live HF Space URL must respond to `/health` by end of day.

| Jenish (P1) | Jeswin (P2) | Jamal (P3) |
|-------------|-------------|------------|
| Write `baseline.py` (random agent, all 3 tasks) | Run full integration test (all 3 tasks via FastAPI) | Finalize Dockerfile (all directories in COPY) |
| Write `inference.py` (LLM agent via OpenAI client) | Test edge cases (budget=0, all suppliers disrupted) | |
| Write `env/gym_wrapper.py` (Gymnasium wrapper) | Test edge cases (budget=0, all suppliers disrupted) | `docker build -t gpe .` — must build cleanly |
| Write `train.py` (PPO, 50k steps, save model) | Fix any grader returning NaN/None/constant | `docker run -p 7860:7860 gpe` — test from outside container |
| Run Task 1 training — verify trained > random | Write `README.md` (full with curl examples) | `git push space main` → watch HF build logs |
| Write `trained_agent.py` (load models, run 5 episodes each) | Proofread `openenv.yaml` | Fix any import errors, rebuild until green |
| Confirm models under 100MB | Add curl examples pointing at live HF URL | Share live URL with team |

**End-of-Day Sync:** Jamal shares live HF URL → Jenish runs `baseline.py` against it → Jeswin reads grader scores from response.

---

### DAY 4 — Train Models + Harden + Submit
> **Critical Gate:** `baseline.py` must run cleanly against the live URL before submitting.

| Jenish (P1) | Jeswin (P2) | Jamal (P3) |
|-------------|-------------|------------|
| Train PPO on Task 2 (100k steps) → save `task2_ppo.zip` | Run 500 random episodes across all 3 tasks | Error handling audit — every route returns 400, never 500 |
| Train PPO on Task 3 (50k steps) → save `task3_ppo.zip` | Verify graders never return NaN/None/out-of-range | Add `GET /metrics` route |
| Run `trained_agent.py` — trained must beat random on all 3 | Test `done=True` at step 1 doesn't crash grader | Load test: 20 concurrent POST /step — must not crash |
| Verify `inference.py` runs cleanly against live URL | Final README check — run every curl example live | Final git push + HF Space deploy |
| Add model score table to README | Double-check `openenv.yaml` all fields | Confirm HF Space running 30+ min without crashing |
| Run `baseline.py` final time against live URL | Run `openenv validate` against live Space URL | **Submit HF Space URL to hackathon portal** |

**Final Submission Check:** All 3 tasks print scores → All curl examples work → Live URL responds → SUBMIT.

---

## 🔩 Core Technical Specs

**7 Discrete Actions:** `approve_cheapest (0)`, `approve_fastest (1)`, `approve_greenest (2)`, `reject_all (3)`, `negotiate_price (4)`, `split_order (5)`, `escalate (6)`

**Reward Formula:** `0.35 × compliance + 0.25 × cost_efficiency + 0.25 × delivery_speed + 0.15 × carbon_score`

**3 Disruptions (seeded):** Port strike India @ step 8 · War reroute EU @ step 15 · Protest France @ step 22

**OpenEnv Interface Contract (Pydantic typed):**
- `reset() → Observation` — returns a Pydantic `Observation` model
- `step(action: Action) → tuple[Observation, Reward, bool, dict]` — returns a 4-tuple, NOT a dict
- `state() → Observation` — returns current state without advancing

---

## ⚠️ Two Required Root Scripts — Don't Confuse Them

| File | Agent Type | LLM? | Owner | Notes |
|------|-----------|------|-------|-------|
| `baseline.py` | Random (no LLM) | No | Jenish | Judges run this to verify env works |
| `inference.py` | LLM-driven | **Yes — OpenAI client** | Jenish | **Disqualification if missing** |

`inference.py` must use `openai.OpenAI(base_url=os.getenv("API_BASE_URL"), api_key=os.getenv("HF_TOKEN"))` and read `MODEL_NAME` from env vars. Runtime must be under 20 minutes on 2 vCPU / 8 GB RAM.

---

## ✅ Mandatory Submission Requirements

| Requirement | Owner | Notes |
|-------------|-------|-------|
| OpenEnv typed `step()` / `reset()` / `state()` API | Jenish | Returns must be Pydantic models |
| 3 tasks with graders returning 0.0–1.0 | Jeswin | Graders must vary — constant = disqualified |
| `openenv.yaml` spec + `openenv validate` passes | Jamal | Uses `openenv-core` CLI |
| Dockerfile builds and runs | Jamal | Port 7860, workers=1 |
| HF Space deploys and `/health` responds 200 | Jamal | Judges ping this first |
| `baseline.py` reproduces scores | Jenish | Random agent, seeded, deterministic |
| `inference.py` with OpenAI client | Jenish | **Mandatory — disqualification if absent** |
| README with env description + curl examples | Jeswin | Must have action/obs space tables |
