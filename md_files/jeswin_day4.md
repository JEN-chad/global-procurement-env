# Jeswin (P2) — Day 4 Instructions
**Role:** Data & Tasks | **Theme:** Stress test, harden graders, finalize README, submit

> ⚠️ **Today's Critical Gate:** Every curl example in the README must return valid JSON against the live URL. All graders must survive 500 random episodes without returning NaN/None/constant values.

> 🚫 **No new features today.** Fix, verify, and submit only.

---

## 🔗 Cross-Team Dependency — What You Need Today

**From Jenish (morning):** The actual trained PPO scores from `trained_agent.py`. These go into your README score table. Ask Jenish for the numbers as soon as his Day 4 training runs complete.

**From Jamal (ongoing):** If Jamal finds any HTTP 500 errors from your grader-related endpoints during his load test (20 concurrent POST /step), he will notify you. Some 500s may originate from your grader code throwing an exception. Be ready to debug.

---

## Phase 1 — Run 500 Random Episodes (Stress Test)

**What you're building:** A stress test that hammers the system 500 times with random actions across all 3 tasks and confirms the graders never raise an exception or return out-of-range values. This is exactly what the judges' automated system will do.

```python
# stress_test.py
import requests
import random

BASE_URL = "https://YOUR_USERNAME-global-procurement-env.hf.space"

def run_stress_test(n_episodes_per_task=167):
    failures = []
    
    for episode_num in range(n_episodes_per_task * 3):
        task_id = (episode_num % 3) + 1
        seed = random.randint(0, 9999)
        max_action = {1: 4, 2: 6, 3: 7}[task_id]

        try:
            requests.post(f"{BASE_URL}/reset", json={"task": task_id, "seed": seed}).raise_for_status()
            done = False
            while not done:
                action = random.randint(0, max_action - 1)
                result = requests.post(f"{BASE_URL}/step", json={"action": action}).json()
                done = result.get("done", True)

            score = requests.get(f"{BASE_URL}/state").json().get("grader_score")

            if score is None:
                failures.append(f"Episode {episode_num}: grader returned None (task={task_id}, seed={seed})")
            elif not isinstance(score, (int, float)):
                failures.append(f"Episode {episode_num}: grader returned non-numeric: {score}")
            elif not (0.0 <= score <= 1.0):
                failures.append(f"Episode {episode_num}: score out of range: {score}")

        except Exception as e:
            failures.append(f"Episode {episode_num}: exception — {e}")

        if (episode_num + 1) % 50 == 0:
            print(f"Progress: {episode_num + 1}/500 — failures so far: {len(failures)}")

    print(f"\n✅ Stress test complete — {len(failures)} failures out of 500 episodes")
    for f in failures:
        print(f"  ❌ {f}")

    return len(failures) == 0

if __name__ == "__main__":
    success = run_stress_test()
    if not success:
        print("\n⚠️  FIX FAILURES BEFORE SUBMITTING")
```

### ✅ Pitstop Audit — Phase 1

Run `python stress_test.py`. The target is **0 failures**. If there are failures, triage by type:

Failures mentioning `None` mean the grader hit a code path that returns `None` — trace back through the grader logic and add defensive `return 0.0` guards. Failures mentioning "out of range" mean the grader formula is producing values outside `[0, 1]` — check your normalisation divisors (if `total_lead_days` can exceed your assumed max, your rate will go negative). Failures mentioning "exception" usually point to an API or environment bug — bring in Jamal or Jenish depending on whether the error is in the API or simulation layer.

**Zero failures across 500 episodes → Phase 1 complete.**

---

## Phase 2 — Verify Grader Boundary Behaviour

**What you're building:** Three targeted tests that specifically probe the conditions the judges look for as disqualification triggers.

```python
from graders.grader1 import grade as grade1
from graders.grader2 import grade as grade2
from graders.grader3 import grade as grade3

import math

print("=== Boundary Condition Tests ===")

# Test: done=True at step 1 must not crash and must return float in [0, 1]
immediate_fail = {
    "steps": [{"step": 1, "action": 0, "reward": -1.0, "done": True}],
    "total_violations": 1, "final_budget": 200000.0,
    "total_lead_days": 0, "total_carbon": 0.0
}

for i, grader in enumerate([grade1, grade2, grade3], 1):
    score = grader(immediate_fail)
    assert score is not None, f"grader{i} returned None on immediate fail"
    assert not math.isnan(score), f"grader{i} returned NaN on immediate fail"
    assert 0.0 <= score <= 1.0, f"grader{i} score {score} out of [0,1]"
    print(f"  ✓ grader{i}: immediate fail score = {score:.4f}")

# Test: completely empty episode dict must return 0.0
for i, grader in enumerate([grade1, grade2, grade3], 1):
    score = grader({"steps": []})
    assert score == 0.0, f"grader{i} returned {score} for empty episode, expected 0.0"
    print(f"  ✓ grader{i}: empty episode = 0.0")

# Test: graders return different values for clearly different episodes
perfect_ep = {
    "steps": [{"step": i, "done": i==20} for i in range(1, 21)],
    "total_violations": 0, "final_budget": 180000.0,
    "total_lead_days": 20, "total_carbon": 5.0
}
terrible_ep = {
    "steps": [{"step": i, "done": i==5} for i in range(1, 6)],
    "total_violations": 5, "final_budget": 0.0,
    "total_lead_days": 150, "total_carbon": 48.0
}
for i, grader in enumerate([grade1, grade2, grade3], 1):
    s1 = grader(perfect_ep)
    s2 = grader(terrible_ep)
    assert s1 != s2, f"grader{i} returns same score for perfect and terrible episodes!"
    print(f"  ✓ grader{i}: perfect={s1:.4f}, terrible={s2:.4f} (different ✓)")

print("\n✅ All boundary tests passed")
```

### ✅ Pitstop Audit — Phase 2

All three graders must pass every assertion above. Any assertion failure is a disqualification risk — fix it before moving on. **Phase 2 complete when the script prints "✅ All boundary tests passed" with no assertion errors.**

---

## Phase 3 — Final README Update

Update the README with the real numbers from Jenish's trained agent run. Replace all "TBD" values in the score table:

```markdown
## Model Performance

| Task | Random Baseline | Trained PPO | Improvement |
|------|----------------|-------------|-------------|
| Task 1 (Easy — India only) | 0.XX | 0.XX | +XX% |
| Task 2 (Medium — India + EU) | 0.XX | 0.XX | +XX% |
| Task 3 (Hard — All 3 Countries) | 0.XX | 0.XX | +XX% |
```

Also replace all `YOUR_USERNAME` placeholders in the curl examples with the actual Hugging Face username. Then run every single curl command yourself, in a fresh terminal, against the live URL, and confirm each one returns valid JSON. Do not publish a README with curl examples you haven't personally tested.

### ✅ Pitstop Audit — Phase 3

Run each of these curl commands in your terminal (substituting the real URL):

```bash
curl https://REAL_URL/health                              # → {"status":"ok"}
curl -X POST https://REAL_URL/reset -H "Content-Type: application/json" -d '{"task":1,"seed":42}'    # → JSON obs
curl -X POST https://REAL_URL/step -H "Content-Type: application/json" -d '{"action":0}'             # → JSON step result
curl https://REAL_URL/state                               # → JSON state with grader_score
curl https://REAL_URL/metrics                             # → JSON metrics
```

Every command returns a 200 status with valid JSON → Phase 3 complete.

---

## Phase 4 — Final `openenv.yaml` Check

This is your last chance to catch YAML validation failures before submission. Go through the file field by field:

The `name` field should be `global-procurement-env` matching the repo and HF Space name exactly. The `tasks` list should have exactly 3 entries with IDs matching `TASK_ID` from your task config files. The `action_space` section should show `type: Discrete` with `n: 7` (the maximum, from Task 3). The `observation_space` section should list every key returned in the `/state` response — if `/state` returns `"grader_score"` but the YAML doesn't list it, the validator will flag it. The `reward_range` should be `[-1.0, 1.0]` matching Jenish's clamped reward formula.

```bash
# Run validation if the CLI is available
openenv validate openenv.yaml --url https://REAL_URL
```

### ✅ Final Submission Checklist for Jeswin

Before telling the team "ready to submit," confirm all of these yourself:

- [ ] 500-episode stress test completed with 0 failures
- [ ] Boundary condition tests all pass (no NaN, no None, no constant graders)
- [ ] README score table has real numbers from Jenish (both random baseline AND trained PPO AND LLM inference scores)
- [ ] Every curl example in README tested live and returns valid JSON
- [ ] `openenv.yaml` task IDs, action space, and observation fields all verified
- [ ] No `YOUR_USERNAME` placeholder remains anywhere in any file
- [ ] Confirmed with Jenish that `inference.py` exists and runs cleanly

When all boxes are checked, tell Jamal he can submit the HF Space URL.
