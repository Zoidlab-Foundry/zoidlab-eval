"""Eval runner — REAL generation + REAL LLM-judge scoring.

For each test case: (1) generate the target model's answer via the relay, (2) ask a judge
model to score that answer against each criterion on a 1-5 scale, returning JSON. Scores are
a judge model's opinion — labelled as such, never presented as ground truth — but they come
from real calls, not fabricated. A case that fails to generate is a failure, not skipped.
"""
import time
import json
import re
import llm
import pricing
import db_pg as db

JUDGE_MODEL = "anthropic/claude-sonnet-5"  # relay id used for scoring


def _parse_scores(text, criteria):
    """Pull a {criterion: {score, reason}} map from the judge's reply. Tolerant of extra prose."""
    out = {}
    # try to find a JSON object first
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            for c in criteria:
                v = data.get(c["name"]) or data.get(c["name"].lower())
                if isinstance(v, dict):
                    out[c["name"]] = {"score": _clamp(v.get("score")), "reason": str(v.get("reason", ""))[:240]}
                elif isinstance(v, (int, float)):
                    out[c["name"]] = {"score": _clamp(v), "reason": ""}
        except Exception:
            pass
    # fallback: line-based "Criterion: 4 - reason"
    for c in criteria:
        if c["name"] in out:
            continue
        mm = re.search(rf"{re.escape(c['name'])}\s*[:=]\s*(\d(?:\.\d)?)", text or "", re.IGNORECASE)
        out[c["name"]] = {"score": _clamp(mm.group(1)) if mm else None, "reason": ""}
    return out


def _clamp(v):
    try:
        return max(1.0, min(5.0, float(v)))
    except Exception:
        return None


async def _judge(input_text, output_text, reference, criteria):
    rubric = "\n".join(f"- {c['name']}: {c['description']}" for c in criteria)
    ref = f"\n\nREFERENCE (ideal answer, for comparison):\n{reference}" if reference else ""
    sys = ("You are a rigorous evaluation judge. Score the ASSISTANT answer on each criterion "
           "from 1 (very poor) to 5 (excellent). Respond ONLY with a JSON object mapping each "
           'criterion name to {"score": <1-5>, "reason": "<short>"}. No other text.')
    user = f"CRITERIA:\n{rubric}\n\nUSER PROMPT:\n{input_text}{ref}\n\nASSISTANT ANSWER:\n{output_text}"
    text, _ = await llm.chat(JUDGE_MODEL, [{"role": "system", "content": sys}, {"role": "user", "content": user}],
                             temperature=0.0, max_tokens=400)
    return _parse_scores(text, criteria)


async def run(run_id, target, testset, criteria, config, relay_key=None):
    if relay_key:
        llm.set_relay_auth(relay_key)
    if not llm.has_key():
        db.finish_run(run_id, {}, error="No relay key configured — real evaluation requires NYQUEST_API_KEY or a user relay key.")
        return

    threshold = float(config.get("pass_threshold", 3.5))       # per-case overall (1-5)
    ready_pct = float(config.get("readiness_pct", 80))          # % of cases that must pass
    max_tokens = int(config.get("max_tokens", 500))
    model = target.get("model") or "auto"
    system_prompt = target.get("system_prompt") or ""
    cases = testset.get("cases", [])

    passed_n = 0
    crit_sums = {c["name"]: [0.0, 0] for c in criteria}
    total_cost = 0.0

    for cse in cases:
        cid = cse.get("id"); inp = cse.get("input", ""); ref = cse.get("reference", "")
        rec = {"case_id": cid, "input": inp, "reference": ref}
        t0 = time.perf_counter()
        try:
            msgs = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": "user", "content": inp}]
            answer, usage = await llm.chat(model, msgs, temperature=float(config.get("temperature", 0.2)), max_tokens=max_tokens)
            latency = int((time.perf_counter() - t0) * 1000)
            pt = int(usage.get("prompt_tokens", 0) or 0); ct = int(usage.get("completion_tokens", 0) or 0)
            tt = int(usage.get("total_tokens", 0) or (pt + ct))
            gen_cost, _ = pricing.cost_for(model, pt, ct)
            scores = await _judge(inp, answer, ref, criteria)
            vals = [s["score"] for s in scores.values() if s.get("score") is not None]
            overall = round(sum(vals) / len(vals), 2) if vals else None
            passed = overall is not None and overall >= threshold
            rec.update({"output": answer[:4000], "latency_ms": latency, "total_tokens": tt,
                        "cost_usd": gen_cost, "ok": True, "scores": scores, "overall": overall, "passed": passed})
            total_cost += gen_cost
            if passed:
                passed_n += 1
            for c in criteria:
                s = scores.get(c["name"], {}).get("score")
                if s is not None:
                    crit_sums[c["name"]][0] += s; crit_sums[c["name"]][1] += 1
        except Exception as e:
            latency = int((time.perf_counter() - t0) * 1000)
            rec.update({"output": "", "latency_ms": latency, "ok": False, "error": str(e)[:300],
                        "scores": {}, "overall": None, "passed": False, "total_tokens": 0, "cost_usd": 0})
        db.save_result(run_id, rec)

    n = len(cases) or 1
    pass_rate = round(passed_n / n * 100, 1)
    per_criterion = {name: (round(s / c, 2) if c else None) for name, (s, c) in crit_sums.items()}
    summary = {
        "cases": len(cases), "passed": passed_n, "failed": len(cases) - passed_n,
        "pass_rate": pass_rate, "pass_threshold": threshold, "readiness_pct": ready_pct,
        "per_criterion": per_criterion, "total_cost_usd": round(total_cost, 5),
        "production_ready": pass_rate >= ready_pct,
        "verdict": "READY" if pass_rate >= ready_pct else "NOT READY",
    }
    db.finish_run(run_id, summary)
