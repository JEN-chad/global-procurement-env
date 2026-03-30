# Jamal (P3) — Day 3 Instructions
**Role:** Infra & Deploy | **Theme:** Docker, first live deployment, watch it go green

> ⚠️ **Today's Critical Gate:** The live Hugging Face Space URL must respond to `/health` with `{"status": "ok"}` before the end of day. First-time deployments always have issues — this is why you deploy today, not tomorrow.

---

## 🔗 Cross-Team Dependency — What You Need Today

**From Jenish (morning):** Confirmation that `baseline.py` can successfully call the local FastAPI server and receive scores. This tells you the full Python stack is wired up correctly before you containerise it. If `baseline.py` fails against your local server, fix that before starting the Docker build.

**From Jeswin (afternoon):** Confirmation that the integration test (10 episodes per task via FastAPI) ran cleanly. This gives you confidence that the environment and graders work end-to-end, so any Docker deployment failures you see are almost certainly packaging or configuration issues — not code bugs.

---

## Phase 1 — Finalize the Dockerfile

**What you're building:** The complete, production-ready Dockerfile. The Day 1 skeleton had the right structure but some details need finalising now that all the application files exist. The most critical addition is making sure every directory is copied — missing a single `COPY` line means the container will build successfully but crash at runtime when Python tries to import from a directory that doesn't exist inside the container.

**File:** `Dockerfile` (root of the repo)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install requirements first — Docker caches this layer.
# Changing application code won't invalidate this cache layer,
# so rebuilds after code changes only take ~10 seconds instead of ~3 minutes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application directories.
# If any directory is missing here, imports will fail at runtime.
# A successful docker build does NOT mean runtime imports work.
COPY env/ ./env/
COPY graders/ ./graders/
COPY api/ ./api/
COPY policies/ ./policies/
COPY data/ ./data/
COPY disruptions/ ./disruptions/
COPY models/ ./models/

# Copy root-level Python scripts
COPY baseline.py .
COPY inference.py .
COPY train.py .
COPY trained_agent.py .

# Hugging Face Spaces requires port 7860 specifically
EXPOSE 7860

# workers=1 is mandatory — see Day 2 notes on race conditions
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
```

**A subtle trap to watch out for:** `COPY . .` (copy everything) is tempting and seems simpler, but it copies files you don't want — `.git/`, `__pycache__/`, local virtual environments, and model files that might be too large. Explicit per-directory COPY lines give you precise control.

### ✅ Pitstop Audit — Phase 1

Run the build locally:

```bash
docker build -t gpe .
```

The build passes if it exits with `Successfully built <hash>`. If you see `error: could not find requirements.txt` or similar, a COPY source path is wrong. If you see pip dependency conflicts, your `requirements.txt` has an incompatibility — resolve it on your local machine first. **A failing docker build must be fixed before moving to Phase 2.**

---

## Phase 2 — Local Docker Run and Container Testing

**What you're building:** Proof that the Docker container actually serves the API correctly, tested from outside the container exactly the way the judges will test it.

```bash
# Start the container, exposing port 7860
docker run -p 7860:7860 gpe
```

Leave this running and open a second terminal. Run the same curl tests you ran in Day 2's audit:

```bash
# Every one of these must work against the CONTAINER (port 7860)
curl -s http://localhost:7860/health
curl -s -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": 1, "seed": 42}'
curl -s -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action": 0}'
curl -s http://localhost:7860/state
```

**Common Docker runtime failures and how to diagnose them:**

If `/health` returns 502 or connection refused, the uvicorn server isn't starting. Check `docker logs <container_id>` — you'll likely see a Python ImportError telling you exactly which module can't be found.

If `/health` works but `/reset` returns 500, the environment class is failing to initialise. The error message in the 500 response body should tell you why.

If the build succeeded but `/reset` gives a `ModuleNotFoundError: No module named 'env'`, it means Python can't find the `env/` directory inside the container. This usually means your `COPY env/ ./env/` line in the Dockerfile copied the contents but not the directory itself, or the WORKDIR is wrong.

### ✅ Pitstop Audit — Phase 2

```bash
# Health check returns exactly this:
curl -s http://localhost:7860/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok', d; print('✅ /health OK')"

# Reset returns a valid observation (has budget_remaining key)
curl -s -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{"task":1,"seed":42}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'budget_remaining' in d, d; print('✅ /reset OK')"

# Step returns reward and done keys
curl -s -X POST http://localhost:7860/step -H "Content-Type: application/json" -d '{"action":0}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'reward' in d and 'done' in d, d; print('✅ /step OK')"
```
**All 3 assertions pass against the running container → Phase 2 complete.**

---

## Phase 3 — Push to GitHub and Deploy to HF Space

**What you're building:** The first real deployment. You push the repo to HF Space, which triggers an automatic Docker build on Hugging Face's infrastructure. This build may take 5–15 minutes.

```bash
# Push to GitHub first (keeps main branch in sync)
git add .
git commit -m "Day 3 — finalize Dockerfile and requirements"
git push origin main

# Push to HF Space — this triggers the build
git push space main
```

After pushing, go to your HF Space page on huggingface.co. Click the "Build" tab. Watch the log stream in real time. You will see the same `pip install` and `docker build` steps run on HF's servers.

**Most common first-deployment failures:**

If you see `ERROR: Could not find a version that satisfies the requirement torch==2.3.0`, the HF build server can't find that exact wheel. Try removing the minor version (`torch==2.3` instead of `torch==2.3.0`), or use `torch>=2.2.0,<2.4.0`.

If you see `[Errno 28] No space left on device`, your total image size (packages + model files) exceeds the HF Space limit. Check your model file sizes with `ls -lh models/*.zip` and ask Jenish if any exceed 150MB.

If the build goes green but `/health` still returns nothing, the container started but crashed immediately. Check "Runtime" logs (different from Build logs) on the HF Space page.

### ✅ Pitstop Audit — Phase 3 (Day 3 Critical Gate)

```bash
# Health check returns exactly this:
curl -s https://YOUR_USERNAME-global-procurement-env.hf.space/health
# Must return: {"status":"ok"}

# Run openenv validate against the live URL
pip install openenv-core  # if not already installed locally
openenv validate openenv.yaml --url https://YOUR_USERNAME-global-procurement-env.hf.space
# Must print: "✅ Validation passed" (or equivalent success message)
```

**Live HF URL returns `{"status":"ok"}` AND `openenv validate` passes → Day 3 critical gate cleared.** Share the URL with Jenish and Jeswin so they can test `/reset` and `/step` against it immediately.
