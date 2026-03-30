# Jamal (P3) — Day 1 Instructions
**Role:** Infra & Deploy | **Theme:** Build the scaffolding that the whole team will build upon

> ⚠️ **Today's Critical Gate:** The GitHub repository must be pushed with all correct folders present, and your Hugging Face Space must be created with Docker SDK (not Gradio). Every teammate must be able to clone the repo and find the correct folder structure.

---

## 🔗 Cross-Team Dependency Note

Today you lay the infrastructure that all three of you depend on. Jenish and Jeswin will start placing their files into the folders you create. If you push the wrong folder names, every import path they write will be wrong. The folder names below are the canonical reference — do not deviate from them.

You also need Jenish's `SupplyChainState` field names by end of day, because your `openenv.yaml` skeleton references observation fields. You'll leave them as placeholders today and fill them in properly on Day 2.

---

## Phase 1 — Create the GitHub Repository with Correct Folder Structure

**What you're building:** The skeleton repository that every file for the next 4 days will live in. Think of this as the building's frame — once it's up and everyone is working inside it, you can't suddenly rename rooms without breaking everything.

Create the repository locally first, then push it to GitHub:

```bash
mkdir global-procurement-env
cd global-procurement-env
git init

# Create all required directories — every folder must exist on Day 1
mkdir -p env/tasks
mkdir -p graders
mkdir -p api
mkdir -p policies
mkdir -p data
mkdir -p disruptions
mkdir -p models

# Git won't track empty directories, so add a .gitkeep placeholder in each
touch env/.gitkeep
touch env/tasks/.gitkeep
touch graders/.gitkeep
touch api/.gitkeep
touch policies/.gitkeep
touch data/.gitkeep
touch disruptions/.gitkeep
touch models/.gitkeep

git add .
git commit -m "Initial repo structure — Day 1"
```

Then create the repository on GitHub (name it `global-procurement-env`) and push:

```bash
git remote add origin https://github.com/YOUR_USERNAME/global-procurement-env.git
git branch -M main
git push -u origin main
```

**Why use `.gitkeep` files?** Git tracks files, not empty folders. Without a file inside, `git add .` won't include the directory, and when Jenish clones the repo, the folders won't exist. A `.gitkeep` is the convention for marking "this folder should exist even when empty."

### ✅ Pitstop Audit — Phase 1

After pushing, clone the repo into a fresh temporary directory and verify all folders are present:

```bash
cd /tmp
git clone https://github.com/YOUR_USERNAME/global-procurement-env.git test_clone
ls test_clone/
# Must see: env  graders  api  policies  data  disruptions  models

ls test_clone/env/
# Must see: tasks  .gitkeep

echo "✅ All folders present in clone"
rm -rf test_clone
```
**All 7 top-level folders and `env/tasks` subfolder exist in the fresh clone → Phase 1 complete.**

---

## Phase 2 — Write the Dockerfile Skeleton

**What you're building:** The recipe that tells Docker how to package your entire application into a self-contained, runnable container. The skeleton today doesn't need to fully work (the Python files it copies don't all exist yet), but writing it now means you won't be under pressure to write it from scratch on Day 3 when you're simultaneously debugging deployment issues.

**File:** `Dockerfile` (root of the repo)

```dockerfile
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first — Docker caches this layer separately.
# If only your code changes (not requirements), Docker reuses the
# cached pip install layer, which saves several minutes per rebuild.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
# This must cover every directory that the Python code imports from
COPY env/ ./env/
COPY graders/ ./graders/
COPY api/ ./api/
COPY policies/ ./policies/
COPY data/ ./data/
COPY disruptions/ ./disruptions/
COPY models/ ./models/

# Expose port 7860 — Hugging Face Spaces expects exactly this port
EXPOSE 7860

# workers=1 is mandatory — see the critical rules section
# Multiple workers each get their own copy of the environment state,
# causing race conditions and corrupted episode data
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
```

**Critical — why `workers=1` is non-negotiable:** When uvicorn spawns multiple workers, each worker process gets its own independent copy of your Python environment in memory. So if Worker A processes `/reset` and Worker B processes the next `/step`, Worker B has no idea what Worker A reset — it starts from its own fresh, empty state. This would make every `/step` call appear to run in a different episode than the `/reset` that preceded it. The only correct design is one worker, one global environment instance, with a threading lock protecting concurrent access.

### ✅ Pitstop Audit — Phase 2

The Dockerfile skeleton doesn't need to build successfully yet (the Python files don't exist). Just validate the syntax is correct:

```bash
# Docker can validate the Dockerfile syntax without building
docker build --check -f Dockerfile . 2>&1 | head -5
# OR just visually confirm: FROM, WORKDIR, COPY, RUN, EXPOSE, CMD are all present
grep -c "^FROM\|^WORKDIR\|^COPY\|^RUN\|^EXPOSE\|^CMD" Dockerfile
# Should output: 8 (or more)
```
**Dockerfile exists with all 6 required instruction types present → Phase 2 complete.**

---

## Phase 3 — Write `requirements.txt`

**What you're building:** The pinned dependency list that ensures everyone — you locally, Docker, and the Hugging Face build server — installs exactly the same versions of every package. Version mismatches are the #1 cause of "it works on my machine but not in Docker."

**File:** `requirements.txt` (root of the repo)

```
openenv-core>=0.2.2
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
openai>=1.0.0
stable-baselines3==2.3.2
gymnasium==0.29.1
torch==2.3.0
numpy==1.26.4
```

**Why `openenv-core` is non-negotiable:** The judges run `openenv validate openenv.yaml` using this package's CLI. If it's not installed in the container, the validator will not be available and the submission may fail the automated validation phase. `openai` is required for `inference.py` — the mandatory LLM agent script.

**Important:** Run `pip install -r requirements.txt` locally to verify none of the packages conflict with each other or your Python version. If you hit dependency conflicts, try these fallback compatible versions:
- `gymnasium==0.26.3` (older but widely compatible)
- `stable-baselines3==2.1.0`

### ✅ Pitstop Audit — Phase 3

```bash
python -m venv /tmp/test_venv
/tmp/test_venv/bin/pip install -r requirements.txt 2>&1 | tail -5

# Verify all critical packages install successfully
/tmp/test_venv/bin/python -c "
import fastapi, gymnasium, stable_baselines3, openai
import openenv  # from openenv-core
print('✅ All packages install cleanly including openenv-core and openai')
"
```
**All packages install without errors and imports succeed → Phase 3 complete.**

---

## Phase 4 — Write the `openenv.yaml` Skeleton

**What you're building:** The OpenEnv specification file that describes your environment to the hackathon judging system. The YAML must follow the OpenEnv schema exactly — the judges run `openenv validate` against it before they even look at your code. Today you write the skeleton with placeholder values; you'll fill in the real observation field names on Day 2 once you have Jenish's actual API responses.

**File:** `openenv.yaml` (root of the repo)

```yaml
name: global-procurement-env
version: "1.0.0"
description: >
  AI procurement simulation environment. An agent acts as a procurement 
  officer sourcing materials from India, EU, and USA suppliers while 
  following real trade policies and surviving supply chain disruptions.
  Built for the OpenEnv Hackathon.

tasks:
  - id: task_1_easy
    name: "Easy — India Only"
    description: "3 India suppliers, 20 steps, no disruptions"
    max_steps: 20

  - id: task_2_medium
    name: "Medium — India + EU"
    description: "6 suppliers, 50 steps, 1 disruption"
    max_steps: 50

  - id: task_3_hard
    name: "Hard — All 3 Countries"
    description: "10 suppliers, 100 steps, 3 disruptions"
    max_steps: 100

action_space:
  type: Discrete
  n: 7

observation_space:
  type: Dict
  fields:
    - name: step
      type: int
    - name: budget_remaining
      type: float
    - name: inventory
      type: object
    - name: suppliers
      type: array
    - name: active_disruptions
      type: array
    - name: policy_violations_this_episode
      type: int
    - name: current_task
      type: int

reward_range: [-1.0, 1.0]

endpoints:
  reset: POST /reset
  step: POST /step
  state: GET /state
  health: GET /health
```

### ✅ Pitstop Audit — Phase 4

Validate the YAML parses correctly (syntax check only — the validator needs a live URL which you don't have yet):

```python
import yaml

with open("openenv.yaml", "r") as f:
    config = yaml.safe_load(f)

assert config["name"] == "global-procurement-env"
assert len(config["tasks"]) == 3
assert config["action_space"]["n"] == 7
assert config["reward_range"] == [-1.0, 1.0]
print("✅ openenv.yaml parses correctly, all required sections present")
```
**YAML parses without errors and has all required top-level sections → Phase 4 complete.**

---

## Phase 5 — Create the Hugging Face Space (Docker SDK)

**What you're building:** The cloud hosting environment where your application will live. This step is time-sensitive because choosing the wrong SDK type at creation is difficult to undo.

Go to `huggingface.co/new-space` and fill in:
- **Space name:** `global-procurement-env`
- **Space SDK:** Select **Docker** — this is critical. Do NOT select Gradio or Streamlit.
- **Hardware:** CPU Basic (free tier)
- **Visibility:** Public (judges need to access it)

After creation, add the Space as a second git remote:

```bash
# In your local repo
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/global-procurement-env
```

**Do not push anything to the Space remote today.** The Space currently has no application files and would show an error. You will do the first real push on Day 3. Today just sets up the remote so the push command is ready.

### ✅ Pitstop Audit — Phase 5

```bash
git remote -v
# Must show TWO remotes:
# origin  https://github.com/YOUR_USERNAME/global-procurement-env.git (fetch)
# origin  https://github.com/YOUR_USERNAME/global-procurement-env.git (push)
# space   https://huggingface.co/spaces/YOUR_USERNAME/global-procurement-env (fetch)
# space   https://huggingface.co/spaces/YOUR_USERNAME/global-procurement-env (push)
```

Also visit the HF Space URL in your browser — it will show a "Building" or "Error" page since nothing is deployed yet, but it should exist as a Docker Space (you'll see "Docker" in the Space's settings tab).

**Both remotes configured and HF Space exists with Docker SDK → Phase 5 complete.**

---

## 📤 End-of-Day Handoff

Post in the team chat before the sync:

```
JAMAL — DAY 1 HANDOFF

GitHub repo: https://github.com/YOUR_USERNAME/global-procurement-env
HF Space: https://huggingface.co/spaces/YOUR_USERNAME/global-procurement-env (Docker, not yet deployed)

Folders confirmed present: env/, env/tasks/, graders/, api/, policies/, data/, disruptions/, models/
requirements.txt: fastapi, uvicorn, pydantic, stable-baselines3, gymnasium, torch — all pinned

Please clone the repo and confirm you can see all folders.
```
