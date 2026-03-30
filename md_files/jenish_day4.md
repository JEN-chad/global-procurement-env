# Jenish (P1) — Day 4 Instructions
**Role:** Env Core | **Theme:** Train remaining models, harden, final verification

> ⚠️ **Today's Critical Gates (both must pass):**
> 1. `baseline.py` runs cleanly against the live HF Space URL and prints scores for all 3 tasks
> 2. `inference.py` runs cleanly against the live HF Space URL and prints LLM agent scores for all 3 tasks

> 🚫 **No new features today.** Fix, train, and verify only.

---

## 🔗 Cross-Team Dependency — What You Need Today

**From Jamal (morning):** The live Hugging Face Space URL from Day 3's deployment. Update `baseline.py` and `trained_agent.py` to point at that URL instead of `localhost`. Confirm Jamal's `/metrics` route is live so your episode counts appear there.

**From Jeswin (ongoing):** Jeswin is running 500 random episodes today to stress-test the system. If he finds crashes or unexpected behaviour in the environment, coordinate immediately — some bugs may be in your code.

---

## Phase 1 — Train PPO on Task 2

**What you're building:** The second trained model. Task 2 includes India and EU suppliers (6 total), runs for 50 steps, and includes one disruption at step 8 (port strike India). It requires 100,000 timesteps to learn because it has a larger action space and more complex constraints.

Open `train.py` and add Task 2 training:

```python
if __name__ == "__main__":
    # Day 3 already trained Task 1 — don't re-run that unless needed
    train_task(task_id=2, total_timesteps=100000, save_path="models/task2_ppo")
```

Run this and let it complete. Expect 15–30 minutes on CPU.

### ✅ Pitstop Audit — Phase 1

After training completes, verify the model file exists and is under 150MB:

```bash
ls -lh models/task2_ppo.zip
```

Also do a quick sanity evaluation:
```python
# Quick check — not the full trained_agent.py run
from stable_baselines3 import PPO
model = PPO.load("models/task2_ppo")
print("Model loaded successfully")
print(model.policy)  # Should show MlpPolicy architecture
```
**File exists, loads without error, and is under 150MB → Phase 1 complete.**

---

## Phase 2 — Train PPO on Task 3

**What you're building:** The hardest model. Task 3 includes all 10 suppliers across 3 countries, runs 100 steps, has all 3 disruptions, and the agent has access to all 7 actions including `escalate`. Despite the added complexity, 50,000 timesteps is sufficient because the graders reward meaningful behaviour, not perfect play.

```python
train_task(task_id=3, total_timesteps=50000, save_path="models/task3_ppo")
```

**Important:** Task 3's action space is size 7 (actions 0–6). Double-check that your `ProcurementGymWrapper` initialised with `task=3` uses `spaces.Discrete(7)` — not 4 or 6. A mismatch here will cause SB3 to crash silently during training with a shape error.

### ✅ Pitstop Audit — Phase 2

```bash
ls -lh models/task3_ppo.zip  # exists, < 150MB
```

```python
from stable_baselines3 import PPO
from env.gym_wrapper import ProcurementGymWrapper

model = PPO.load("models/task3_ppo")
env = ProcurementGymWrapper(task=3, seed=42)
obs, _ = env.reset()
action, _ = model.predict(obs, deterministic=True)
print(0 <= int(action) <= 6)  # True — valid action range for Task 3
```
**Model predicts a valid action in [0, 6] → Phase 2 complete.**

---

## Phase 3 — Full Evaluation Against Live URL

**What you're building:** The final proof that everything works end-to-end. Update `trained_agent.py` to point at the live Hugging Face URL and run all 3 tasks. The trained agent must score higher than the random baseline on every task.

Update the URL at the top of both scripts:

```python
# In baseline.py and trained_agent.py
BASE_URL = "https://YOUR_USERNAME-global-procurement-env.hf.space"
```

Then add Tasks 2 and 3 to `trained_agent.py`:

```python
if __name__ == "__main__":
    baseline_scores = {}
    trained_scores = {}

    for task_id in [1, 2, 3]:
        # You can also run baseline here for direct comparison
        trained_avg = evaluate_model(task_id, f"models/task{task_id}_ppo")
        trained_scores[task_id] = trained_avg

    print("\n--- Final Comparison ---")
    for t in [1, 2, 3]:
        print(f"Task {t}: trained={trained_scores[t]:.4f}")
```

### ✅ Pitstop Audit — Phase 3

Expected output (your numbers will differ, but the pattern should hold):
```
Task 1: avg_reward over 5 episodes = 0.6123
Task 2: avg_reward over 5 episodes = 0.4871
Task 3: avg_reward over 5 episodes = 0.3509

--- Final Comparison ---
Task 1: trained=0.6123
Task 2: trained=0.4871
Task 3: trained=0.3509
```

Task 3 scoring lower than Task 1 is completely expected — it's a harder problem. What matters is that each trained score is higher than the random baseline from Day 3. **If any trained score equals or is lower than random → re-train that task with 2× timesteps.**

---

## Phase 4 — Verify `inference.py` Against Live URL

**What you're doing:** Running the mandatory LLM agent script against the live HF Space and confirming it completes within the 20-minute budget. This is a separate submission requirement from `baseline.py` — judges check both files. `inference.py` missing or crashing = disqualification.

Update the `ENV_URL` in `inference.py` to point at the live HF Space:

```python
ENV_URL = os.getenv("ENV_URL", "https://YOUR_USERNAME-global-procurement-env.hf.space")
```

Then run it with real credentials:

```bash
ENV_URL=https://YOUR_USERNAME-global-procurement-env.hf.space \
API_BASE_URL=https://router.huggingface.co/v1 \
MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3 \
HF_TOKEN=your_hf_token \
python inference.py
```

**Expected output:**
```
=== GlobalProcurementEnv — LLM Inference ===
Model: mistralai/Mistral-7B-Instruct-v0.3
Environment: https://YOUR_USERNAME-global-procurement-env.hf.space

Task 1: LLM agent score = 0.XXXX
Task 2: LLM agent score = 0.XXXX
Task 3: LLM agent score = 0.XXXX
```

**If the LLM calls time out:** Reduce `MAX_STEPS` to 10 — it's better to get a lower score than to timeout. The 20-minute limit is hard.

**If you get HTTP 401 from the LLM API:** The `HF_TOKEN` is wrong or not set. Double-check the token has inference access on Hugging Face.

### ✅ Pitstop Audit — Phase 4

```bash
# Time the full run to verify <20 min
time python inference.py
# Must print 3 lines of scores AND exit in under 20 minutes
```

Pass conditions: 3 score lines printed, no Python exceptions, no HTTP 500s from the environment API, total runtime under 20 minutes. **Both `baseline.py` and `inference.py` must pass before Day 4 is done.**

---

## Phase 5 — Add Model Scores to README & Push Everything

Tell Jeswin the three score columns to put in the README — he owns that file:

```markdown
## Model Performance

| Task | Random Baseline | Trained PPO | LLM Agent (inference.py) |
|------|----------------|-------------|--------------------------|
| Task 1 (Easy)   | 0.XX | 0.XX | 0.XX |
| Task 2 (Medium) | 0.XX | 0.XX | 0.XX |
| Task 3 (Hard)   | 0.XX | 0.XX | 0.XX |
```

Then push all model files and `inference.py` to the HF Space:

```bash
git add models/task1_ppo.zip models/task2_ppo.zip models/task3_ppo.zip inference.py
git commit -m "Day 4 — trained models all 3 tasks + verified inference.py"
git push origin main
git push space main
```

Watch the HF Space build logs. Confirm it goes green after the push.

### ✅ Pitstop Audit — Phase 5 (Day 4 Final Gate)

```bash
# 1. Space still responds after rebuild
curl -s https://YOUR_USERNAME-global-procurement-env.hf.space/health
# → {"status":"ok"}

# 2. Random baseline agent — reproducible scores
python baseline.py
# → Task 1: 0.XXXX, Task 2: 0.XXXX, Task 3: 0.XXXX (no errors)

# 3. LLM inference agent — under 20 minutes
time python inference.py
# → Task 1: 0.XXXX, Task 2: 0.XXXX, Task 3: 0.XXXX (no errors, <20 min)
```

**All three commands succeed → both Day 4 critical gates cleared. Tell Jeswin and Jamal you're ready to submit.**
