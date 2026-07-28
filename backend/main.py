"""ZoidLab Eval API — Foundry Package 09, AI Evaluation Lab.

Evaluates a target (a model + system prompt) against a test set, using REAL relay calls to
generate answers and a judge model to score them per criterion. Produces a production-readiness
verdict. Every data endpoint requires Nyquest Pro (backend fail-closed). Runs execute in a
background task and are polled.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List

import db_pg as db
import pricing
import llm
import eval_engine
import exporter
import envelope
import seed_eval
from auth import session, require_pro, relay_key, entitlement


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    n = seed_eval.run()
    if n:
        print(f"[eval] seeded {n} demo target/testset(s)")
    yield


app = FastAPI(title="ZoidLab Eval API", lifespan=lifespan)

from foundry_common import assistant
from assistant_manifest import MANIFEST
app.include_router(assistant.make_router(MANIFEST))


def require_owner(request: Request):
    o = require_pro(request)
    s = session(request)
    db.upsert_user(o, s.get("email") if s else None, s.get("name") if s else None)
    return o


# ---- auth / meta --------------------------------------------------------
@app.get("/api/health")
def health():
    return {"ok": True, "service": "eval"}


@app.get("/api/auth/me")
def auth_me(request: Request):
    s = session(request)
    if not s:
        return {"authenticated": False}
    return {"authenticated": True, "user_id": s.get("sub"), "email": s.get("email"),
            "name": s.get("name"), "tier": s.get("tier")}


@app.get("/api/auth/entitlements")
def auth_entitlements(request: Request):
    return entitlement(request)


@app.get("/api/meta")
async def meta():
    try:
        models = await llm.featured_models()
    except Exception:
        models = ["auto"]
    return {"relay_available": llm.available(), "billing_mode": llm.billing_mode(),
            "featured_models": models, "judge_model": eval_engine.JUDGE_MODEL}


@app.get("/api/stats")
def stats(request: Request, owner: str = Depends(require_owner)):
    s = db.stats(owner)
    runs = db.list_runs(owner)
    ready = sum(1 for r in runs if (r.get("summary") or {}).get("production_ready"))
    s["relay_available"] = llm.available()
    s["ready_targets"] = ready
    return s


# ---- targets ------------------------------------------------------------
class TargetBody(BaseModel):
    name: str
    description: Optional[str] = ""
    model: Optional[str] = "auto"
    system_prompt: Optional[str] = ""


@app.get("/api/targets")
def targets(request: Request, owner: str = Depends(require_owner)):
    return {"targets": db.list_targets(owner)}


@app.post("/api/targets")
def create_target(body: TargetBody, owner: str = Depends(require_owner)):
    return {"ok": True, "target": db.create_target(body.model_dump(), owner)}


@app.delete("/api/targets/{tid}")
def delete_target(tid: str, owner: str = Depends(require_owner)):
    if not db.delete_target(tid, owner):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# ---- criteria -----------------------------------------------------------
class CriterionBody(BaseModel):
    name: str
    description: Optional[str] = ""


@app.get("/api/criteria")
def criteria(request: Request, owner: str = Depends(require_owner)):
    return {"criteria": db.list_criteria(owner)}


@app.post("/api/criteria")
def create_criterion(body: CriterionBody, owner: str = Depends(require_owner)):
    return {"ok": True, "criterion": db.create_criterion(body.model_dump(), owner)}


@app.delete("/api/criteria/{cid}")
def delete_criterion(cid: str, owner: str = Depends(require_owner)):
    if not db.delete_criterion(cid, owner):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# ---- testsets -----------------------------------------------------------
class TestsetBody(BaseModel):
    name: str
    description: Optional[str] = ""
    cases: List[dict] = []


@app.get("/api/testsets")
def testsets(request: Request, owner: str = Depends(require_owner)):
    return {"testsets": db.list_testsets(owner)}


@app.get("/api/testsets/{tsid}")
def get_testset(tsid: str, request: Request, owner: str = Depends(require_owner)):
    t = db.get_testset(tsid, owner)
    if not t:
        raise HTTPException(404, "not_found")
    return t


@app.post("/api/testsets")
def create_testset(body: TestsetBody, owner: str = Depends(require_owner)):
    if not body.cases:
        raise HTTPException(400, "at least one case required")
    return {"ok": True, "testset": db.create_testset(body.model_dump(), owner)}


@app.delete("/api/testsets/{tsid}")
def delete_testset(tsid: str, owner: str = Depends(require_owner)):
    if not db.delete_testset(tsid, owner):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# ---- eval runs ----------------------------------------------------------
class RunBody(BaseModel):
    target_id: str
    testset_id: str
    criteria_ids: Optional[List[str]] = None    # None = all visible criteria
    pass_threshold: Optional[float] = 3.5
    readiness_pct: Optional[float] = 80
    max_tokens: Optional[int] = 500
    temperature: Optional[float] = 0.2


async def _execute(run_id, target, testset, criteria, config, rkey):
    try:
        await eval_engine.run(run_id, target, testset, criteria, config, relay_key=rkey)
    except Exception as e:
        db.finish_run(run_id, {}, error=str(e)[:300])


@app.post("/api/runs")
async def start_run(body: RunBody, request: Request, bg: BackgroundTasks, owner: str = Depends(require_owner)):
    target = db.get_target(body.target_id, owner)
    testset = db.get_testset(body.testset_id, owner)
    if not target:
        raise HTTPException(404, "target_not_found")
    if not testset:
        raise HTTPException(404, "testset_not_found")
    if not llm.available():
        raise HTTPException(503, "relay_unavailable: real evaluation needs a relay key (NYQUEST_API_KEY)")
    all_crit = db.list_criteria(owner)
    criteria = [c for c in all_crit if (body.criteria_ids is None or c["id"] in body.criteria_ids)]
    if not criteria:
        raise HTTPException(400, "select at least one criterion")
    config = {"pass_threshold": body.pass_threshold, "readiness_pct": body.readiness_pct,
              "max_tokens": body.max_tokens, "temperature": body.temperature}
    rid = db.create_run(target, testset, criteria, config, owner, llm.billing_mode())
    bg.add_task(_execute, rid, target, testset, criteria, config, relay_key(request))
    return {"ok": True, "run_id": rid, "status": "running",
            "note": f"Evaluating {target['name']} on {testset['case_count']} case(s) × {len(criteria)} criteria via live relay. Poll /api/runs/{rid}."}


@app.get("/api/runs")
def runs(request: Request, owner: str = Depends(require_owner)):
    return {"runs": db.list_runs(owner)}


@app.get("/api/runs/{rid}")
def get_run(rid: str, request: Request, only_failed: bool = False, owner: str = Depends(require_owner)):
    r = db.get_run(rid, owner)
    if not r:
        raise HTTPException(404, "not_found")
    r["results"] = db.run_results(rid, only_failed=only_failed)
    return r


# ---- export -------------------------------------------------------------
def _wrapped(r, owner):
    payload = exporter.to_package(r, db.run_results(r["id"]))
    return envelope.wrap("eval", "eval_report", r["id"], "1.0.0", payload, nyquest_user_id=owner)


@app.get("/api/runs/{rid}/export/json")
def export_json(rid: str, request: Request, owner: str = Depends(require_owner)):
    r = db.get_run(rid, owner)
    if not r:
        raise HTTPException(404, "not_found")
    return _wrapped(r, owner)


@app.get("/api/runs/{rid}/export/yaml")
def export_yaml(rid: str, request: Request, owner: str = Depends(require_owner)):
    r = db.get_run(rid, owner)
    if not r:
        raise HTTPException(404, "not_found")
    return PlainTextResponse(exporter.to_yaml(_wrapped(r, owner)))
