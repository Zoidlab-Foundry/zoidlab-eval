"""SQLite persistence for ZoidLab Eval (Foundry Package 09 — AI Evaluation Lab).

Stores evaluation targets, criteria, test sets, runs, and per-case results. Answers and
judge scores come from REAL relay calls — nothing is fabricated. A case with no successful
generation is a failure, not a skipped row. Postgres-portable JSON-as-TEXT. Ownership =
Nyquest user id; seed (owner NULL) is shared.
"""
import os
import json
import uuid
import sqlite3
import datetime

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "eval.db")


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _j(v):
    return json.dumps(v)


def _pj(v, default=None):
    if v is None:
        return default
    try:
        return json.loads(v)
    except Exception:
        return default


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


def init():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT, name TEXT, role TEXT DEFAULT 'user',
                created_at TEXT, updated_at TEXT );
            CREATE TABLE IF NOT EXISTS targets (
                id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT,
                description TEXT, model TEXT, system_prompt TEXT, created_at TEXT, updated_at TEXT );
            CREATE TABLE IF NOT EXISTS criteria (
                id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, description TEXT,
                created_at TEXT );
            CREATE TABLE IF NOT EXISTS testsets (
                id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT,
                description TEXT, cases TEXT, created_at TEXT, updated_at TEXT );
            CREATE TABLE IF NOT EXISTS eval_runs (
                id TEXT PRIMARY KEY, owner_user_id TEXT, target_id TEXT, target_name TEXT, target_model TEXT,
                testset_id TEXT, testset_name TEXT, criteria TEXT, config TEXT, status TEXT DEFAULT 'pending',
                billing_mode TEXT, summary TEXT, error TEXT, created_at TEXT, finished_at TEXT );
            CREATE INDEX IF NOT EXISTS idx_er_owner ON eval_runs(owner_user_id, created_at);
            CREATE TABLE IF NOT EXISTS eval_results (
                id TEXT PRIMARY KEY, run_id TEXT, case_id TEXT, input TEXT, reference TEXT, output TEXT,
                latency_ms INTEGER, total_tokens INTEGER, cost_usd REAL, ok INTEGER, error TEXT,
                scores TEXT, overall REAL, passed INTEGER, created_at TEXT );
            CREATE INDEX IF NOT EXISTS idx_erz_run ON eval_results(run_id);
            """
        )
        # default criteria for first-run convenience (owner NULL = shared)
        n = c.execute("SELECT COUNT(*) n FROM criteria WHERE owner_user_id IS NULL").fetchone()["n"]
        if not n:
            for nm, desc in [
                ("Accuracy", "Is the answer factually correct and free of hallucination?"),
                ("Relevance", "Does it directly address what was asked?"),
                ("Completeness", "Does it cover the important parts of a good answer?"),
                ("Clarity", "Is it clear, well-structured, and easy to follow?"),
                ("Safety", "Is it free of harmful, biased, or policy-violating content?"),
            ]:
                c.execute("INSERT INTO criteria (id,owner_user_id,name,description,created_at) VALUES (?,?,?,?,?)",
                          (new_id("crit"), None, nm, desc, now_iso()))


def _visible(col="owner_user_id"):
    return f"({col} IS NULL OR {col}=?)"


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO users (id,email,name,role,created_at,updated_at) VALUES (?,?,?,'user',?,?)
                     ON CONFLICT(id) DO UPDATE SET email=COALESCE(excluded.email,users.email),
                       name=COALESCE(excluded.name,users.name), updated_at=excluded.updated_at""",
                  (uid, email, name, now, now))


# --- targets -----------------------------------------------------------
def list_targets(viewer=None):
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM targets WHERE {_visible()} ORDER BY updated_at DESC", (viewer,)).fetchall()
    return [dict(r) for r in rows]


def get_target(tid, viewer=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM targets WHERE id=? AND {_visible()}", (tid, viewer)).fetchone()
    return dict(r) if r else None


def create_target(data, owner):
    tid = new_id("tgt"); now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO targets (id,owner_user_id,name,slug,description,model,system_prompt,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (tid, owner, data["name"], _slug(data["name"]), data.get("description", ""),
                   data.get("model", "auto"), data.get("system_prompt", ""), now, now))
    return get_target(tid, owner)


def delete_target(tid, owner):
    t = get_target(tid, owner)
    if not t or (t.get("owner_user_id") and t["owner_user_id"] != owner):
        return False
    with _conn() as c:
        c.execute("DELETE FROM targets WHERE id=?", (tid,))
    return True


# --- criteria ----------------------------------------------------------
def list_criteria(viewer=None):
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM criteria WHERE {_visible()} ORDER BY created_at", (viewer,)).fetchall()
    return [dict(r) for r in rows]


def create_criterion(data, owner):
    cid = new_id("crit")
    with _conn() as c:
        c.execute("INSERT INTO criteria (id,owner_user_id,name,description,created_at) VALUES (?,?,?,?,?)",
                  (cid, owner, data["name"], data.get("description", ""), now_iso()))
    with _conn() as c:
        r = c.execute("SELECT * FROM criteria WHERE id=?", (cid,)).fetchone()
    return dict(r)


def delete_criterion(cid, owner):
    with _conn() as c:
        r = c.execute("SELECT owner_user_id FROM criteria WHERE id=?", (cid,)).fetchone()
        if not r or r["owner_user_id"] != owner:  # can't delete shared/seed criteria
            return False
        c.execute("DELETE FROM criteria WHERE id=?", (cid,))
    return True


# --- testsets ----------------------------------------------------------
def _ts_out(r):
    if not r:
        return None
    d = dict(r); d["cases"] = _pj(d.get("cases"), []); d["case_count"] = len(d["cases"])
    return d


def list_testsets(viewer=None):
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM testsets WHERE {_visible()} ORDER BY updated_at DESC", (viewer,)).fetchall()
    return [_ts_out(r) for r in rows]


def get_testset(tsid, viewer=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM testsets WHERE id=? AND {_visible()}", (tsid, viewer)).fetchone()
    return _ts_out(r)


def create_testset(data, owner):
    tsid = new_id("ts"); now = now_iso()
    cases = []
    for i, cse in enumerate(data.get("cases") or []):
        if isinstance(cse, str):
            cse = {"input": cse}
        cases.append({"id": cse.get("id") or f"c{i+1}", "input": cse.get("input", ""),
                      "reference": cse.get("reference", "")})
    with _conn() as c:
        c.execute("""INSERT INTO testsets (id,owner_user_id,name,slug,description,cases,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (tsid, owner, data["name"], _slug(data["name"]), data.get("description", ""), _j(cases), now, now))
    return get_testset(tsid, owner)


def delete_testset(tsid, owner):
    t = get_testset(tsid, owner)
    if not t or (t.get("owner_user_id") and t["owner_user_id"] != owner):
        return False
    with _conn() as c:
        c.execute("DELETE FROM testsets WHERE id=?", (tsid,))
    return True


# --- runs --------------------------------------------------------------
def create_run(target, testset, criteria, config, owner, billing_mode):
    rid = new_id("erun")
    with _conn() as c:
        c.execute("""INSERT INTO eval_runs (id,owner_user_id,target_id,target_name,target_model,testset_id,
                     testset_name,criteria,config,status,billing_mode,created_at)
                     VALUES (?,?,?,?,?,?,?,?,?,'running',?,?)""",
                  (rid, owner, target["id"], target["name"], target.get("model"), testset["id"],
                   testset["name"], _j(criteria), _j(config), billing_mode, now_iso()))
    return rid


def save_result(run_id, res):
    with _conn() as c:
        c.execute("""INSERT INTO eval_results (id,run_id,case_id,input,reference,output,latency_ms,total_tokens,
                     cost_usd,ok,error,scores,overall,passed,created_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (new_id("eres"), run_id, res["case_id"], res["input"], res.get("reference", ""),
                   res.get("output", ""), res.get("latency_ms"), res.get("total_tokens", 0),
                   res.get("cost_usd", 0), 1 if res.get("ok") else 0, res.get("error"),
                   _j(res.get("scores", {})), res.get("overall"), 1 if res.get("passed") else 0, now_iso()))


def finish_run(run_id, summary, error=None):
    with _conn() as c:
        c.execute("UPDATE eval_runs SET status=?, summary=?, error=?, finished_at=? WHERE id=?",
                  ("failed" if error else "complete", _j(summary), error, now_iso(), run_id))


def _run_out(r):
    if not r:
        return None
    d = dict(r)
    d["criteria"] = _pj(d.get("criteria"), []); d["config"] = _pj(d.get("config"), {})
    d["summary"] = _pj(d.get("summary"), {})
    return d


def list_runs(viewer=None, limit=50):
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM eval_runs WHERE {_visible()} ORDER BY created_at DESC LIMIT ?", (viewer, limit)).fetchall()
    return [_run_out(r) for r in rows]


def get_run(rid, viewer=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM eval_runs WHERE id=? AND {_visible()}", (rid, viewer)).fetchone()
    return _run_out(r)


def run_results(rid, only_failed=False):
    q = "SELECT * FROM eval_results WHERE run_id=?"
    if only_failed:
        q += " AND passed=0"
    q += " ORDER BY case_id"
    with _conn() as c:
        rows = c.execute(q, (rid,)).fetchall()
    out = []
    for r in rows:
        d = dict(r); d["ok"] = bool(d["ok"]); d["passed"] = bool(d["passed"]); d["scores"] = _pj(d.get("scores"), {}); out.append(d)
    return out


def stats(viewer=None):
    with _conn() as c:
        runs = c.execute(f"SELECT COUNT(*) n FROM eval_runs WHERE {_visible()}", (viewer,)).fetchone()["n"]
        tgts = c.execute(f"SELECT COUNT(*) n FROM targets WHERE {_visible()}", (viewer,)).fetchone()["n"]
        ts = c.execute(f"SELECT COUNT(*) n FROM testsets WHERE {_visible()}", (viewer,)).fetchone()["n"]
    return {"runs": runs, "targets": tgts, "testsets": ts}
