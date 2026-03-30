# Jeswin (P2) — Day 3 Instructions
**Role:** Data & Tasks | **Theme:** Full integration testing, edge case hardening, and README

> ⚠️ **Today's Critical Gate:** All 3 graders must return varying, non-zero scores across at least 10 different episodes when called via the live FastAPI. The README must have working curl examples.

---

## 🔗 Cross-Team Dependency — What You Need Today

**From Jamal (morning):** The locally running Docker container (not just FastAPI, but the actual Docker image). Jamal will have run `docker build` and `docker run -p 7860:7860 gpe` — once that's up, you run all your integration tests against `localhost:7860`. This is your first time testing through the full stack.

**From Jenish (afternoon):** Once Jenish has `baseline.py` working, ask him for the actual grader score structure coming from the live API so you can make sure your README curl examples produce the exact output you document.

---

## Phase 1 — Full Integration Test (All 3 Tasks via FastAPI)

**What you're building:** A test script that calls the real FastAPI endpoints — not just Python imports — and runs 10 full episodes per task, collecting grader scores. This is the closest thing to what the judges will do when evaluating your submission.

```python
# integration_test.py
import requests
import random

BASE_URL = "http://localhost:7860"

def run_episode(task_id: int, seed: int, max_actions: dict = {1: 4, 2: 6, 3: 7}) -> dict:
    """Runs one full episode via the API and returns the state at the end."""
    resp = requests.post(f"{BASE_URL}/reset", json={"task": task_id, "seed": seed})
    resp.raise_for_status()

    done = False
    n_actions = max_actions[task_id]
    steps = 0
    last_result = None

    while not done:
        action = random.randint(0, n_actions - 1)
        step_resp = requests.post(f"{BASE_URL}/step", json={"action": action})
        step_resp.raise_for_status()
        last_result = step_resp.json()
        done = last_result.get("done", False)
        steps += 1

    state = requests.get(f"{BASE_URL}/state").json()
    return {"steps": steps, "state": state, "grader_score": state.get("grader_score", None)}

print("Running 10 episodes per task — looking for score variation...")
for task_id in [1, 2, 3]:
    scores = []
    for seed in range(10):
        result = run_episode(task_id=task_id, seed=seed)
        score = result["grader_score"]
        scores.append(score)
    
    print(f"\nTask {task_id} scores across 10 seeds:")
    for i, s in enumerate(scores):
        print(f"  seed={i}: {s}")
    
    unique = len(set(str(round(s, 3)) for s in scores if s is not None))
    if unique < 3:
        print(f"  ⚠️  WARNING: Only {unique} unique score values — grader may be too constant")
    else:
        print(f"  ✅ {unique} distinct score values — grader is working")
```

### ✅ Pitstop Audit — Phase 1

Run `python integration_test.py`. Pass conditions: no HTTP errors, all 30 calls complete (10 episodes × 3 tasks), and each task shows at least 3 distinct score values across the 10 seeds. If any task shows all identical scores, the grader for that task has a bug — return to Day 2's grader code and trace the logic.

---

## Phase 2 — Edge Case Testing

These are the failure modes that specifically get submissions disqualified. Test each one explicitly:

**Edge Case A — Immediate hard violation at step 1:**
```python
# Reset Task 3, then immediately send an action that will trigger a hard violation.
# The easiest way to force this is to pick a supplier in a sanctioned category.
# If your environment is set up correctly, done=True should come back immediately
# and the grader should return a low (but not None/NaN) score.

resp = requests.post(f"{BASE_URL}/reset", json={"task": 3, "seed": 0})
# Send action 0 repeatedly until done=True in the first few steps
step_resp = requests.post(f"{BASE_URL}/step", json={"action": 0})
result = step_resp.json()
print(f"Reward: {result['reward']}, Done: {result['done']}")
# If done=True on step 1, confirm the state's grader_score is not None
state = requests.get(f"{BASE_URL}/state").json()
print(f"Grader score on immediate fail: {state.get('grader_score')}")
assert state.get("grader_score") is not None, "Grader must not return None on early termination"
assert 0.0 <= state["grader_score"] <= 1.0, "Score must be in [0, 1] even on immediate fail"
```

**Edge Case B — Budget exhaustion mid-episode:**
```python
# Keep approving the most expensive suppliers until budget hits 0
# The environment should handle this gracefully (not crash, just end the episode or reject)
# Your grader should still return a valid float.
```

**Edge Case C — All suppliers disrupted:**
This tests what happens in Task 3 when both `port_strike_india` and `war_reroute_eu` are active simultaneously (they overlap between steps 15–17). After step 15, Indian suppliers IN_02 and IN_03 are already unavailable from the strike (started step 8), and now all EU suppliers have doubled lead times. The agent may have very few good options. The environment should not crash — it should either allow a `reject_all` action or handle the empty supplier list gracefully.

### ✅ Pitstop Audit — Phase 2

All three edge cases complete without raising Python exceptions on the server side (no HTTP 500 responses) and all grader scores remain in `[0.0, 1.0]`. Check Jamal's server logs during this test — any 500 responses need to be investigated with Jamal immediately.

---

## Phase 3 — Write the README

**What you're building:** The public-facing documentation that judges read to understand your environment. A good README increases your score because judges directly evaluate documentation quality. It must include working curl examples that someone can paste into a terminal and get real results.

**File:** `README.md`

Structure your README with these sections in order:

**Section 1 — Overview:** Describe what GlobalProcurementEnv is in 3–4 sentences. An AI procurement agent, 3 countries, real policy rules, 3 difficulty levels.

**Section 2 — Action Space:** A table of all 7 actions (id, name, description, which tasks it's available in).

**Section 3 — Observation Space:** A table of all observation fields returned by `/state` and each `/step` response. Include the type and an example value for each field.

**Section 4 — Tasks:** A table showing Task 1/2/3, their supplier count, step count, and disruptions.

**Section 5 — Setup and Running Locally:**
```bash
git clone https://github.com/YOUR_TEAM/global-procurement-env
cd global-procurement-env
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 7860
```

**Section 6 — API Curl Examples** (these must work against the live URL — fill in the real URL once Jamal deploys):
```bash
# Health check
curl https://YOUR_USERNAME-global-procurement-env.hf.space/health

# Reset Task 1
curl -X POST https://YOUR_USERNAME-global-procurement-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task": 1, "seed": 42}'

# Take action: approve cheapest supplier
curl -X POST https://YOUR_USERNAME-global-procurement-env.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"action": 0}'

# Get current state
curl https://YOUR_USERNAME-global-procurement-env.hf.space/state
```

**Section 7 — Score Table** (Jenish fills in the actual numbers on Day 4 after `inference.py` and trained agent runs are both complete):

| Task | Random Baseline | Trained PPO | LLM Agent (`inference.py`) |
|------|----------------|-------------|---------------------------|
| Task 1 (Easy) | TBD | TBD | TBD |
| Task 2 (Medium) | TBD | TBD | TBD |
| Task 3 (Hard) | TBD | TBD | TBD |

### ✅ Pitstop Audit — Phase 3

Once Jamal shares the live HF URL, replace all `YOUR_USERNAME` placeholders and run every curl command in the README yourself. Every command must return a valid JSON response. If any curl returns HTML (an error page) or a 4xx/5xx status, the README has a broken example — fix it before committing.

---

## Phase 4 — Proofread `openenv.yaml`

You don't own this file (Jamal does), but you're the person most familiar with the task IDs, action counts, and observation fields. Do a careful review:

Check that the 3 task IDs in the YAML exactly match the `TASK_ID` values in your task config files (`task1_easy.py`, `task2_medium.py`, `task3_hard.py`). Check that the action space size is `7` (discrete) since Task 3 uses all 7 actions. Check that every key in the observation space section of the YAML matches the actual keys returned by your graders and the environment's `/state` endpoint. If you spot any mismatch, tell Jamal immediately.

### ✅ Pitstop Audit — Phase 4

```bash
# If the openenv CLI tool is available
openenv validate openenv.yaml
```
If the CLI isn't available, do a manual field-by-field comparison of `openenv.yaml` against the observation fields in your README. Any field listed in the YAML that doesn't exist in the actual API response is a judging failure point.

**All curl examples work, graders vary across episodes, and YAML fields match actual output → Day 3 complete.**
