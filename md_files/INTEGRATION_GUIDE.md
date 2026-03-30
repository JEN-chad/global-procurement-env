# GlobalProcurementEnv — Integration & Finalisation Guide
**How the three workstreams connect, when they connect, and how to verify the joins**

---

## The Big Picture: What Integration Actually Means Here

Unlike a project where everyone works on separate modules that never touch, GlobalProcurementEnv has deep, daily interdependencies. Think of the three roles as three layers of a sandwich: Jenish builds the filling (the simulation engine), Jeswin provides the ingredients (the data that drives the simulation), and Jamal provides the bread (the API and container that holds everything together and presents it to the world). The sandwich can only be assembled once the filling and ingredients are ready — and assembled in the right order.

There are **four integration points** across the project — one per day — each of which gates the next day's work for at least one person. Understanding these join points is as important as understanding your own tasks.

---

## Integration Point 1 — End of Day 1: The State Contract

**What is being integrated:** Jenish's `SupplyChainState` field names ↔ Jeswin's JSON field names

**Why this matters:** Jenish's `constraint_engine.py` loads Jeswin's policy JSON files and reads specific key names from them. If Jenish's code looks for `policy["carbon_levy_per_ton_usd"]` but Jeswin's JSON has `"carbon_levy"`, Python won't crash — it will return `None`, and all calculations involving the carbon levy will silently produce wrong results. Silent bugs are the hardest kind to diagnose.

**How to execute this integration:**

At the end of Day 1, Jenish posts the complete `SupplyChainState` field list in the team chat — field names, Python types, and default values. Jeswin then goes through each of his JSON files and verifies that every key his files use appears in Jenish's list or matches what Jenish's constraint engine will look for. Any mismatch is fixed by Jeswin on the same day before anyone stops working. Jamal's contribution at this point is to confirm the GitHub repo is pushed with the correct folder structure and that both his teammates can clone and verify it.

**How to verify the join:**

```python
# Jeswin runs this after receiving Jenish's field list
# It confirms that the JSON files use exactly the field names Jenish expects
import json

with open("policies/india_policy.json") as f:
    india = json.load(f)

# These are the keys Jenish's constraint_engine.py will read
expected_keys = [
    "import_duty_rate", "gst_rate", "carbon_levy_per_ton_usd",
    "max_single_source_usd", "mandatory_local_content_pct",
    "sanctioned_categories", "hard_rules", "soft_rules"
]
missing = [k for k in expected_keys if k not in india]
if missing:
    print(f"❌ Missing keys in india_policy.json: {missing}")
else:
    print("✅ India policy keys match constraint engine expectations")
```

Run this for all three policy files before closing out Day 1.

---

## Integration Point 2 — Day 2 Morning: The Env-to-API Bridge

**What is being integrated:** Jenish's `GlobalProcurementEnv` Pydantic return types ↔ Jamal's `api/schemas.py` definitions

**Why this matters:** Jamal defines `Observation`, `Action`, and `Reward` as Pydantic models in `api/schemas.py`. Jenish's `GlobalProcurementEnv` imports these same classes and returns them from `reset()`, `step()`, and `state()`. If Jamal's `Observation` model has a field called `policy_violations_this_episode` but Jenish's code populates a field called `violations`, the serialisation will silently drop the violations count. The field names must match exactly.

Additionally, `step()` returns a **4-tuple** `(Observation, Reward, bool, dict)` per OpenEnv spec. Jamal's `/step` route must unpack this tuple correctly — not treat the return as a dict.

**How to execute this integration:**

The first thing on Day 2 morning is a 15-minute sync between Jenish and Jamal. Jamal opens `api/schemas.py` and walks through each field of `Observation` and `Reward`. Jenish confirms that his `_build_observation()` method populates every field. Any field in the Pydantic model that Jenish doesn't populate will appear as `null` in every API response — silently breaking grader scores.

**Sample handoff message from Jenish to Jamal on Day 2 morning:**

```
Jenish → Jamal Day 2 handoff:

env.reset(task: int, seed: int) → Observation
env.step(action: int) → tuple[Observation, Reward, bool, dict]
  The 4-tuple: (observation, reward, done, info)
env.state() → Observation
env.is_done: bool  (property)
env.current_task: int  (property)

Observation fields I will populate:
  step, budget_remaining, inventory, suppliers (as SupplierObservation list),
  active_disruptions, policy_violations_this_episode, current_task, grader_score

Reward fields I will populate:
  value, compliance, cost_efficiency, delivery_speed, carbon_score
```

**How to verify the join:**

```bash
# Start the FastAPI server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Confirm reset() returns correct Observation shape
curl -s -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task": 1, "seed": 42}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
required = ['step','budget_remaining','inventory','suppliers',
            'active_disruptions','policy_violations_this_episode','current_task']
missing = [f for f in required if f not in d]
if missing: print('❌ Missing fields:', missing)
else: print('✅ All Observation fields present')
"

# Confirm step() returns reward, done, and reward_breakdown
curl -s -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": 0}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'reward' in d and 'done' in d and 'reward_breakdown' in d
assert isinstance(d['done'], bool)
print('✅ step() 4-tuple correctly unpacked and serialised')
"
```

If these pass, Jenish runs `baseline.py` against the local server to confirm the full integration works.

---

## Integration Point 3 — Day 2 Afternoon: The Grader-to-Episode Bridge

**What is being integrated:** Jeswin's grader functions ↔ the episode log structure that the environment actually produces

**Why this matters:** Jeswin's graders expect an `episode_log` dict with specific keys (`steps`, `total_violations`, `final_budget`, etc.). The environment needs to produce a log that matches this structure. If the environment calls the violations counter `"violations"` but the grader looks for `"total_violations"`, the grader will receive `None` and produce wrong scores.

**How to execute this integration:**

After Jamal's server is running and Jenish's environment is wired to it, Jeswin runs a real episode via curl, captures the final state response, and checks that it contains all the keys his graders expect. If the keys don't match, Jeswin and Jenish align on the names — typically by Jeswin adjusting his grader to use whatever field names the environment actually produces (since the environment is already built and tested).

**How to verify the join:**

```bash
# Run a complete episode via curl
curl -s -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d '{"task":1,"seed":42}'
for i in {1..20}; do
  curl -s -X POST http://localhost:8000/step -H "Content-Type: application/json" -d '{"action":0}' > /dev/null
done
curl -s http://localhost:8000/state
```

The final `/state` response is the "episode log" structure. Jeswin manually checks that every key his graders read (`total_violations`, `final_budget`, `total_lead_days`, `total_carbon`) is present in this response. Then he runs:

```python
# Jeswin feeds the real API response into grader1 and confirms a non-None, in-range float
import requests

requests.post("http://localhost:8000/reset", json={"task": 1, "seed": 42})
done = False
while not done:
    r = requests.post("http://localhost:8000/step", json={"action": 0})
    done = r.json().get("done", False)

state = requests.get("http://localhost:8000/state").json()

from graders.grader1 import grade
score = grade(state)
assert isinstance(score, float) and 0.0 <= score <= 1.0, f"Grader failed: {score}"
print(f"✅ Integration Point 3 verified — grader1 score: {score:.4f}")
```

---

## Integration Point 4 — Day 3: The Live Deployment Integration

**What is being integrated:** The entire codebase ↔ the Hugging Face Space Docker container

**Why this matters:** A Python application that runs perfectly on your local machine can still fail in Docker because the container has a slightly different environment — different Python path, missing system libraries, or a missing directory that wasn't included in a `COPY` command. This integration point is about closing the gap between "works locally" and "works in production."

**How to execute this integration:**

Jamal leads this integration. The sequence is: build locally with Docker → test all endpoints against the container → push to HF Space → watch build logs → test all endpoints against the live URL → share the URL with the team. Once the URL is live, Jenish points `baseline.py` at it and Jeswin runs the integration test against it. Any failures at this stage are almost always packaging issues (missing files in the Dockerfile), not code bugs — since the code was already tested locally.

**How to verify the join:**

This is the most comprehensive integration check of the whole project. All three of you participate:

```bash
# Jamal verifies infrastructure
curl https://REAL_URL/health  # → {"status":"ok"}

# Jenish verifies the simulation runs end-to-end
python baseline.py  # (pointing at live URL) → prints scores for all 3 tasks

# Jeswin verifies the graders work against live API
python integration_test.py  # → 10 episodes per task, scores vary across seeds
```

All three checks passing simultaneously means the full system is integrated.

---

## Final Submission Sequence (Day 4)

The submission itself is a coordinated three-person act. Here is the exact order:

**Step 1 — Jenish trains and pushes final models.** He runs training for Tasks 2 and 3, verifies trained agents beat baseline on all 3 tasks, and pushes the model zip files to the HF Space. When the Space rebuilds after his push, Jamal watches the build logs to confirm it goes green.

**Step 2 — Jenish verifies `inference.py` against the live URL.** This is a mandatory separate check. Run:
```bash
ENV_URL=https://YOUR_USERNAME-global-procurement-env.hf.space \
API_BASE_URL=https://router.huggingface.co/v1 \
MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3 \
HF_TOKEN=your_token \
python inference.py
```
It must print 3 LLM agent scores and exit cleanly in under 20 minutes. If it times out or crashes, it's a disqualification risk — fix it before submitting.

**Step 3 — Jeswin runs the 500-episode stress test and final README verification.** He runs `stress_test.py` against the live URL and confirms 0 failures. He gets the real model scores from Jenish (random baseline, trained PPO, and LLM inference scores) and fills them into the README score table. He manually runs every curl example in the README against the live URL. He runs `openenv validate openenv.yaml --url LIVE_URL`.

**Step 4 — Jamal runs load test and 30-minute stability watch.** He fires 20 concurrent requests and confirms no 500 errors. He monitors the live Space for 30 continuous minutes.

**Step 5 — All three give green light.** Jenish says "`baseline.py` passes AND `inference.py` prints 3 scores." Jeswin says "README curl examples all work, graders verified, `openenv validate` passes." Jamal says "Space running 30+ min, no crashes, load test passed." Only when all three have given their green light does Jamal submit the HF Space URL to the hackathon portal.

**One rule above all others: Never submit a broken URL.** A live URL that fails during judging is worse than submitting late with a working URL.

---

## Common Integration Failure Patterns and Fixes

**Field name mismatch (silent bug):** Symptom is grader scores that are unexpectedly low or constant. Fix: add print statements in the grader to confirm the `episode_log` dict keys that are actually arriving, then align with the environment's actual output field names.

**`step()` returns dict instead of 4-tuple:** Symptom is `TypeError: cannot unpack non-sequence dict` in `api/main.py` when it tries `observation, reward, done, info = env.step(action)`. Fix: ensure `GlobalProcurementEnv.step()` returns exactly `(Observation, Reward, bool, dict)` — a 4-element tuple.

**Import paths break in Docker:** Symptom is 500 responses from any route after the container starts, with `ModuleNotFoundError` in the Docker logs. Fix: check that the failing module's directory is explicitly listed in a `COPY` command in the Dockerfile. Also check that there are `__init__.py` files in all package directories (`env/`, `graders/`, `api/`).

**`inference.py` crashes or times out:** Symptom is the script hanging or raising an exception against the live URL. Most common causes: wrong `API_BASE_URL` env var format (must include `/v1`), `HF_TOKEN` not set, or `MAX_STEPS` set too high causing runtime to exceed 20 minutes. Fix: test locally with `MAX_STEPS=5` first, then increase carefully.

**`openenv validate` fails:** Symptom is the CLI reporting field mismatches or missing sections. Check that every key in `openenv.yaml`'s `observation_space.fields` exists in the actual JSON returned by `/state`. Check that task IDs in the YAML exactly match the `TASK_ID` constants in your task config Python files.

**`reset()` called before `step()`:** Symptom is a crash in `/step` with a `NoneType` attribute error. Fix: add the guard in `api/main.py` that checks `if env.state is None` before calling `env.step()`.

**Grader returns constant value:** Symptom is all episodes scoring the same float. Root cause is usually that the grader is reading a key that doesn't exist in the episode log (getting `None` each time, then defaulting to a constant value). Fix: print the full episode log dict and verify every key the grader reads is actually present.

**HF Space times out during build:** Symptom is the build log stopping and showing "Build timed out." Usually caused by large model files or long pip install times. Fix: ensure all model zip files are under 150MB, and consider adding `--timeout 60` to the pip install command in the Dockerfile.
