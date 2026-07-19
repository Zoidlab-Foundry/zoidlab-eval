"""Postgres data layer for ZoidLab Eval with per-tenant Row-Level Security (§3.2).

Tenant isolation is enforced by the database, not just the app: targets, criteria,
testsets, and eval_runs carry owner_user_id, have FORCE ROW LEVEL SECURITY, and a policy
exposing only rows whose owner matches `app.current_owner` (set per transaction) or is
NULL (shared seed). `eval_results` has no owner column — it is reached only through an
RLS-protected run — so it stays open. Public API mirrors the former sqlite database.py
exactly.
"""
import os
import json
import uuid
import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# App connections use the RLS-enforced role (app_rls); DDL + cross-tenant admin use the
# superuser (foundry), which bypasses RLS by design.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://app_rls@127.0.0.1:5433/eval")
DATABASE_URL_ADMIN = os.environ.get("DATABASE_URL_ADMIN", "postgresql://foundry@127.0.0.1:5433/eval")
_pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10, open=True, kwargs={"autocommit": False})


def admin_conn():
    return psycopg.connect(DATABASE_URL_ADMIN, row_factory=dict_row)


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


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


class _tx:
    """Transaction scoped to a tenant: sets app.current_owner so RLS applies."""
    def __init__(self, owner):
        self.owner = owner or ""

    def __enter__(self):
        self.conn = _pool.getconn()
        self.cur = self.conn.cursor(row_factory=dict_row)
        self.cur.execute("SELECT set_config('app.current_owner', %s, true)", (self.owner,))
        return self.cur

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            self.cur.close()
            _pool.putconn(self.conn)


_TENANT_TABLES = ["targets", "criteria", "testsets", "eval_runs"]


def init():
    with admin_conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT, name TEXT, role TEXT DEFAULT 'user',
            created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS targets (
            id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT,
            description TEXT, model TEXT, system_prompt TEXT, created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS criteria (
            id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, description TEXT,
            created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS testsets (
            id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT,
            description TEXT, cases TEXT, created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS eval_runs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, target_id TEXT, target_name TEXT, target_model TEXT,
            testset_id TEXT, testset_name TEXT, criteria TEXT, config TEXT, status TEXT DEFAULT 'pending',
            billing_mode TEXT, summary TEXT, error TEXT, created_at TEXT, finished_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS eval_results (
            id TEXT PRIMARY KEY, run_id TEXT, case_id TEXT, input TEXT, reference TEXT, output TEXT,
            latency_ms INTEGER, total_tokens INTEGER, cost_usd DOUBLE PRECISION, ok INTEGER, error TEXT,
            scores TEXT, overall DOUBLE PRECISION, passed INTEGER, created_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_er_owner ON eval_runs(owner_user_id, created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_erz_run ON eval_results(run_id)")
        for t in _TENANT_TABLES:
            c.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
            c.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
            c.execute(f"DROP POLICY IF EXISTS {t}_isolation ON {t}")
            c.execute(f"""CREATE POLICY {t}_isolation ON {t}
                USING (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))
                WITH CHECK (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))""")
        c.execute("GRANT USAGE ON SCHEMA public TO app_rls")
        c.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO app_rls")
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
                c.execute("INSERT INTO criteria (id,owner_user_id,name,description,created_at) VALUES (%s,%s,%s,%s,%s)",
                          (new_id("crit"), None, nm, desc, now_iso()))
        c.commit()


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _tx(uid) as cur:
        cur.execute("""INSERT INTO users (id,email,name,role,created_at,updated_at) VALUES (%s,%s,%s,'user',%s,%s)
                       ON CONFLICT (id) DO UPDATE SET email=COALESCE(EXCLUDED.email,users.email),
                         name=COALESCE(EXCLUDED.name,users.name), updated_at=EXCLUDED.updated_at""",
                    (uid, email, name, now, now))


# --- targets -----------------------------------------------------------
def list_targets(viewer=None):
    with _tx(viewer) as cur:
        cur.execute("SELECT * FROM targets ORDER BY updated_at DESC")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_target(tid, viewer=None):
    with _tx(viewer) as cur:
        cur.execute("SELECT * FROM targets WHERE id=%s", (tid,))
        r = cur.fetchone()
    return dict(r) if r else None


def create_target(data, owner):
    tid = new_id("tgt"); now = now_iso()
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO targets (id,owner_user_id,name,slug,description,model,system_prompt,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (tid, owner, data["name"], _slug(data["name"]), data.get("description", ""),
                     data.get("model", "auto"), data.get("system_prompt", ""), now, now))
    return get_target(tid, owner)


def delete_target(tid, owner):
    t = get_target(tid, owner)
    if not t or (t.get("owner_user_id") and t["owner_user_id"] != owner):
        return False
    with _tx(owner) as cur:
        cur.execute("DELETE FROM targets WHERE id=%s", (tid,))
    return True


# --- criteria ----------------------------------------------------------
def list_criteria(viewer=None):
    with _tx(viewer) as cur:
        cur.execute("SELECT * FROM criteria ORDER BY created_at")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def create_criterion(data, owner):
    cid = new_id("crit")
    with _tx(owner) as cur:
        cur.execute("INSERT INTO criteria (id,owner_user_id,name,description,created_at) VALUES (%s,%s,%s,%s,%s)",
                    (cid, owner, data["name"], data.get("description", ""), now_iso()))
    with _tx(owner) as cur:
        cur.execute("SELECT * FROM criteria WHERE id=%s", (cid,))
        r = cur.fetchone()
    return dict(r)


def delete_criterion(cid, owner):
    with _tx(owner) as cur:
        cur.execute("SELECT owner_user_id FROM criteria WHERE id=%s", (cid,))
        r = cur.fetchone()
        if not r or r["owner_user_id"] != owner:  # can't delete shared/seed criteria
            return False
        cur.execute("DELETE FROM criteria WHERE id=%s", (cid,))
    return True


# --- testsets ----------------------------------------------------------
def _ts_out(r):
    if not r:
        return None
    d = dict(r); d["cases"] = _pj(d.get("cases"), []); d["case_count"] = len(d["cases"])
    return d


def list_testsets(viewer=None):
    with _tx(viewer) as cur:
        cur.execute("SELECT * FROM testsets ORDER BY updated_at DESC")
        rows = cur.fetchall()
    return [_ts_out(r) for r in rows]


def get_testset(tsid, viewer=None):
    with _tx(viewer) as cur:
        cur.execute("SELECT * FROM testsets WHERE id=%s", (tsid,))
        r = cur.fetchone()
    return _ts_out(r)


def create_testset(data, owner):
    tsid = new_id("ts"); now = now_iso()
    cases = []
    for i, cse in enumerate(data.get("cases") or []):
        if isinstance(cse, str):
            cse = {"input": cse}
        cases.append({"id": cse.get("id") or f"c{i+1}", "input": cse.get("input", ""),
                      "reference": cse.get("reference", "")})
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO testsets (id,owner_user_id,name,slug,description,cases,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (tsid, owner, data["name"], _slug(data["name"]), data.get("description", ""), _j(cases), now, now))
    return get_testset(tsid, owner)


def delete_testset(tsid, owner):
    t = get_testset(tsid, owner)
    if not t or (t.get("owner_user_id") and t["owner_user_id"] != owner):
        return False
    with _tx(owner) as cur:
        cur.execute("DELETE FROM testsets WHERE id=%s", (tsid,))
    return True


# --- runs --------------------------------------------------------------
def create_run(target, testset, criteria, config, owner, billing_mode):
    rid = new_id("erun")
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO eval_runs (id,owner_user_id,target_id,target_name,target_model,testset_id,
                       testset_name,criteria,config,status,billing_mode,created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'running',%s,%s)""",
                    (rid, owner, target["id"], target["name"], target.get("model"), testset["id"],
                     testset["name"], _j(criteria), _j(config), billing_mode, now_iso()))
    return rid


def save_result(run_id, res):
    with _tx(None) as cur:
        cur.execute("""INSERT INTO eval_results (id,run_id,case_id,input,reference,output,latency_ms,total_tokens,
                       cost_usd,ok,error,scores,overall,passed,created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (new_id("eres"), run_id, res["case_id"], res["input"], res.get("reference", ""),
                     res.get("output", ""), res.get("latency_ms"), res.get("total_tokens", 0),
                     res.get("cost_usd", 0), 1 if res.get("ok") else 0, res.get("error"),
                     _j(res.get("scores", {})), res.get("overall"), 1 if res.get("passed") else 0, now_iso()))


def finish_run(run_id, summary, error=None):
    # owner-agnostic engine write: eval_runs are RLS-guarded, so update via admin
    with admin_conn() as c:
        c.execute("UPDATE eval_runs SET status=%s, summary=%s, error=%s, finished_at=%s WHERE id=%s",
                  ("failed" if error else "complete", _j(summary), error, now_iso(), run_id))
        c.commit()


def _run_out(r):
    if not r:
        return None
    d = dict(r)
    d["criteria"] = _pj(d.get("criteria"), []); d["config"] = _pj(d.get("config"), {})
    d["summary"] = _pj(d.get("summary"), {})
    return d


def list_runs(viewer=None, limit=50):
    with _tx(viewer) as cur:
        cur.execute("SELECT * FROM eval_runs ORDER BY created_at DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
    return [_run_out(r) for r in rows]


def get_run(rid, viewer=None):
    with _tx(viewer) as cur:
        cur.execute("SELECT * FROM eval_runs WHERE id=%s", (rid,))
        r = cur.fetchone()
    return _run_out(r)


def run_results(rid, only_failed=False):
    q = "SELECT * FROM eval_results WHERE run_id=%s"
    if only_failed:
        q += " AND passed=0"
    q += " ORDER BY case_id"
    with _tx(None) as cur:
        cur.execute(q, (rid,))
        rows = cur.fetchall()
    out = []
    for r in rows:
        d = dict(r); d["ok"] = bool(d["ok"]); d["passed"] = bool(d["passed"]); d["scores"] = _pj(d.get("scores"), {}); out.append(d)
    return out


def stats(viewer=None):
    with _tx(viewer) as cur:
        cur.execute("SELECT COUNT(*) n FROM eval_runs")
        runs = int(cur.fetchone()["n"])
        cur.execute("SELECT COUNT(*) n FROM targets")
        tgts = int(cur.fetchone()["n"])
        cur.execute("SELECT COUNT(*) n FROM testsets")
        ts = int(cur.fetchone()["n"])
    return {"runs": runs, "targets": tgts, "testsets": ts}
