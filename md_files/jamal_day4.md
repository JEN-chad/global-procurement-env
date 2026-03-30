# Jamal (P3) — Day 4 Instructions
**Role:** Infra & Deploy | **Theme:** Harden the API, add metrics, load test, submit

> ⚠️ **Today's Critical Gate:** The HF Space must be running continuously for 30+ minutes without any crash before you submit. Submit only when all three teammates give the green light.

> 🚫 **No new features today.** Harden, verify, and submit only.

---

## 🔗 Cross-Team Dependency — What You Need Today

**From Jenish (morning):** He will push updated model files (`task2_ppo.zip`, `task3_ppo.zip`) to the HF Space. When he does, the Space will rebuild. Watch the build logs — if the rebuild fails (often due to larger model files), investigate and fix immediately.

**From Jeswin (ongoing):** He's running 500 random episodes as a stress test today. Some failures he reports may trace back to your error handling code (e.g. a route returning 500 instead of 400). Be ready to patch routes quickly if he flags anything.

---

## Phase 1 — Error Handling Audit

**What you're building:** A systematic review of every route to ensure no possible input or state condition can cause an HTTP 500 response. The judges' automated system specifically flags 500 responses as evidence of an unstable environment.

Go through every route in `api/main.py` and ask yourself: "What are all the ways this could fail?" Think about it from the outside in — not just happy-path inputs, but edge cases like calling `/step` before calling `/reset` (the environment has no state yet), calling `/step` after `done=True` (the episode is over), or sending an action number that's valid for the schema (0–6) but not valid for the current task (e.g. action 6 in Task 1).

Add specific handling for these in `api/main.py`:

```python
@app.post("/step", response_model=StepResponse)
def step(request: StepRequest):
    try:
        with lock:
            # Guard: /step called before /reset
            if env.state is None:
                raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")

            # Guard: /step called after episode ended
            if env.is_done:
                raise HTTPException(status_code=400, detail="Episode has ended. Call /reset to start a new episode.")

            # Guard: action out of range for current task
            max_action = {1: 3, 2: 5, 3: 6}[env.current_task]
            if request.action > max_action:
                raise HTTPException(
                    status_code=400,
                    detail=f"Action {request.action} is invalid for Task {env.current_task}. Max action is {max_action}."
                )

            result = env.step(action=request.action)
        return result
    except HTTPException:
        raise  # Re-raise our own HTTP exceptions as-is
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Step failed: {str(e)}")
```

### ✅ Pitstop Audit — Phase 1

Test each error case explicitly against the live URL:

```bash
# Test: /step before /reset — should return 400, not 500
curl -s -o /dev/null -w "%{http_code}" -X POST https://REAL_URL/step \
  -H "Content-Type: application/json" -d '{"action": 0}'
# Expected: 400

# Test: action out of range for task
curl -s -X POST https://REAL_URL/reset -H "Content-Type: application/json" -d '{"task":1,"seed":42}'
curl -s -X POST https://REAL_URL/step -H "Content-Type: application/json" -d '{"action": 6}'
# Expected: 400 with descriptive message (not 500)
```
**All error cases return 400 (not 500), with a clear message → Phase 1 complete.**

---

## Phase 2 — Add the `GET /metrics` Route

**What you're building:** An observability endpoint that gives insight into how the environment has been used since the server started. This is not required for submission but is listed as a differentiating feature — environments with richer introspection score higher in judging. It also helps you debug during load testing.

Add this to `api/main.py`:

```python
# Global counters — updated inside the lock to be thread-safe
metrics_data = {
    "episode_count": 0,
    "total_steps": 0,
    "rewards_per_task": {1: [], 2: [], 3: []},
    "total_violations": 0
}

@app.get("/metrics")
def metrics():
    """Returns aggregate statistics since server start."""
    avg_rewards = {}
    for task_id, rewards in metrics_data["rewards_per_task"].items():
        avg_rewards[str(task_id)] = round(sum(rewards) / len(rewards), 4) if rewards else 0.0

    return {
        "episode_count": metrics_data["episode_count"],
        "total_steps": metrics_data["total_steps"],
        "avg_reward_per_task": avg_rewards,
        "total_violations": metrics_data["total_violations"]
    }
```

Update the `/reset` and `/step` routes to increment these counters inside the lock. In `/reset`, increment `episode_count`. In `/step`, increment `total_steps`, and if `result["done"]` is True, append the final reward to `rewards_per_task[current_task]`.

### ✅ Pitstop Audit — Phase 2

```bash
# Run a quick episode first
curl -s -X POST https://REAL_URL/reset -H "Content-Type: application/json" -d '{"task":1,"seed":0}'
for i in {1..5}; do
  curl -s -X POST https://REAL_URL/step -H "Content-Type: application/json" -d '{"action":0}' > /dev/null
done

# Now check metrics — counts should be non-zero
curl -s https://REAL_URL/metrics
# Expected: episode_count >= 1, total_steps >= 5
```
**Metrics route returns non-zero counts → Phase 2 complete.**

---

## Phase 3 — Load Test (20 Concurrent Requests)

**What you're building:** Proof that the threading lock works correctly and the server doesn't crash under concurrency. The `threading.Lock()` you added ensures only one request touches the environment at a time — the load test verifies this guarantee holds in practice.

```python
# load_test.py
import threading
import requests

BASE_URL = "https://YOUR_USERNAME-global-procurement-env.hf.space"
errors = []

def send_step():
    try:
        resp = requests.post(f"{BASE_URL}/step",
                             json={"action": 0},
                             timeout=10)
        if resp.status_code == 500:
            errors.append(f"HTTP 500: {resp.text[:100]}")
    except Exception as e:
        errors.append(str(e))

# First reset to establish state
requests.post(f"{BASE_URL}/reset", json={"task": 1, "seed": 42})

# Fire 20 concurrent /step requests
threads = [threading.Thread(target=send_step) for _ in range(20)]
for t in threads:
    t.start()
for t in threads:
    t.join()

if errors:
    print(f"❌ Load test failed with {len(errors)} errors:")
    for e in errors:
        print(f"  {e}")
else:
    print("✅ Load test passed — 20 concurrent requests, 0 errors")
```

**What you're looking for:** Zero HTTP 500 responses. Some requests may return 400 (e.g. "action invalid for current task" because the episode may have ended mid-test) — that is acceptable. A 400 means your error handling worked. A 500 means something crashed.

### ✅ Pitstop Audit — Phase 3

Run `python load_test.py`. The test passes if it prints "Load test passed — 20 concurrent requests, 0 errors." If you see any 500s, check the server logs on the HF Space "Runtime" tab — the stack trace will point to the specific crash location.

---

## Phase 4 — Final Deploy, 30-Minute Stability Check, and Submission

**What you're building:** The final proof of stability. A server that worked for 5 minutes might still have a slow memory leak or delayed crash. Watching it run for 30 minutes gives confidence it won't crash during judging.

```bash
# Final push — includes Jenish's model files and any last fixes
git add .
git commit -m "Day 4 — error hardening, metrics route, final deploy"
git push space main
```

Watch the build go green on the HF Space page. Then note the time and do nothing for 30 minutes except occasionally ping `/health`:

```bash
# Run this every 5 minutes for 30 minutes
watch -n 300 'curl -s https://YOUR_USERNAME-global-procurement-env.hf.space/health'
```

While waiting, coordinate with Jenish (run `baseline.py` one final time) and Jeswin (confirm all README curl examples work).

### ✅ Final Submission Checklist for Jamal

Before you submit the URL to the hackathon portal, confirm all of these yourself:

- [ ] `docker build -t gpe .` completes cleanly locally
- [ ] HF Space build logs show green
- [ ] `/health` returns `{"status":"ok"}` from the live URL
- [ ] `/reset`, `/step`, `/state`, `/metrics` all return valid JSON
- [ ] No HTTP 500 responses in load test (20 concurrent requests)
- [ ] Space has been running for 30+ continuous minutes without crashing
- [ ] Jenish confirms `baseline.py` runs cleanly against the live URL
- [ ] Jenish confirms `inference.py` runs cleanly (LLM agent, prints 3 scores)
- [ ] Jeswin confirms all README curl examples work against the live URL
- [ ] `openenv validate openenv.yaml --url LIVE_URL` passes (run this yourself)

**All boxes checked → submit the HF Space URL to the hackathon portal.**
