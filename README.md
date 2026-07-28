# ZoidLab Eval — Foundry Package 09

**AI Evaluation Lab.** Answers *"is this AI good enough to ship?"* by generating a target's
answers on the **live Nyquest relay** and scoring them with an LLM judge against your criteria,
producing a production-readiness verdict.

Part of the [ZoidLab Foundry](https://foundry.zoidlab.ai). Requires **Nyquest Pro** (enforced
on both the frontend gate and every backend data endpoint, fail-closed).

## What it does

- **Targets** — what's under evaluation: a model + system prompt.
- **Criteria** — the rubric (Accuracy, Relevance, Completeness, Clarity, Safety by default; add
  your own). The judge scores each 1–5.
- **Test sets** — prompts (+ optional reference answers).
- **Real eval runs** — each case is (1) answered by the target model via the relay, then (2)
  scored by a judge model per criterion. Per-case pass/fail against a threshold, aggregated to a
  pass rate and a **READY / NOT READY** production-readiness verdict.
- **Failures view** — filter to the cases that failed, with the judge's per-criterion scores and
  reasons.
- **Reports & export** — portable **Nyquest Eval Report** (JSON/YAML).

## Honesty

- Answers and scores come from **real relay calls** — nothing is fabricated; no results exist
  until you run an evaluation (which spends real relay credits).
- Judge scores are **one judge model's opinion** (1–5), clearly labelled — not ground truth. The
  readiness verdict is a transparent threshold over those scores.
- A case that fails to generate is recorded as a **failure**, never silently skipped.
- If no relay key is configured, the run endpoint returns `503 relay_unavailable`.

## Stack

- **Backend**: FastAPI + **Postgres with per-tenant FORCE row-level security** (every query runs
  as the non-superuser `app_rls` role keyed on `app.current_owner`, so tenant isolation is
  enforced by the database, not by application code). `eval_engine.py` (real generate + judge,
  measured), `llm.py` (relay client), `pricing.py` (cost from tokens). Runs execute in a
  background task, polled.
- **Frontend**: Next.js 15 + React 19 + Tailwind. Shared `zb_session` SSO + reusable Pro gate.
- **Deploy** (zoidberg): `eval-api` (:8703) + `eval-web` (:3703) behind the Cloudflare tunnel at
  `eval.zoidlab.ai`.

## Dev

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
NYQUEST_API_KEY=... .venv/bin/uvicorn main:app --port 8703
cd ../frontend && npm install && npm run dev   # proxies /api → 127.0.0.1:8703
```
