"""Eval assistant manifest — what the in-app assistant knows and may do.

This file is the assistant's security boundary: only the capabilities declared here exist
for it, and they execute through this app's own session-authed API (require_pro + RLS apply).
Delete-class operations are intentionally not declared.
"""
from foundry_common.assistant import cap, page

MANIFEST = {
    "app": "Eval",
    "description": (
        "Eval is a real LLM-judge evaluation lab that answers: is this AI good enough to "
        "ship? A target (a model plus the system prompt under test) is run against a test "
        "set of cases via live relay calls, and a judge model scores every answer 1-5 "
        "against each criterion rubric. Runs produce per-criterion scores, pass rates, and "
        "a READY / NOT READY production-readiness verdict. Nothing is simulated; runs bill "
        "the user's own Nyquest wallet and results export as signed Foundry reports."
    ),
    "base_url": "http://127.0.0.1:8703",
    "pages": [
        page("/", "Dashboard", "Overview: stats, relay status, recent runs and readiness."),
        page("/targets", "Targets", "Create and manage targets — a model + system prompt under test.",
             assists={"new-target": "the New Target button"}),
        page("/criteria", "Criteria", "Judge rubrics scored 1-5 (e.g. accuracy, tone, safety)."),
        page("/testsets", "Test Sets", "Sets of test cases (inputs with optional reference answers)."),
        page("/evaluate", "Evaluate", "Pick a target, test set, and criteria, then launch a live eval run.",
             assists={"run-eval": "the Run evaluation button"}),
        page("/runs", "Runs", "Every eval run with status, scores, and READY/NOT READY verdict."),
    ],
    "capabilities": [
        cap("list_targets", "GET", "/api/targets", risk="read",
            desc="The user's evaluation targets (model + system prompt under test)."),
        cap("list_criteria", "GET", "/api/criteria", risk="read",
            desc="The judge criteria rubrics (each scored 1-5 per answer)."),
        cap("list_testsets", "GET", "/api/testsets", risk="read",
            desc="The user's test sets with case counts."),
        cap("get_testset", "GET", "/api/testsets/{tsid}", risk="read",
            desc="One test set with its cases.", params={"tsid": "test set id"}),
        cap("list_runs", "GET", "/api/runs", risk="read",
            desc="The user's eval runs, newest first, with status and summary verdict."),
        cap("get_run", "GET", "/api/runs/{rid}", risk="read",
            desc="One run: per-case, per-criterion judge scores and the readiness verdict.",
            params={"rid": "run id"}),
        cap("stats", "GET", "/api/stats", risk="read",
            desc="Counts of targets/testsets/criteria/runs, ready targets, relay availability."),
        cap("create_target", "POST", "/api/targets", risk="write",
            desc="Create an evaluation target: the model + system prompt to put under test.",
            params={"name": "target name", "description": "short description",
                    "model": "relay model id (default 'auto')",
                    "system_prompt": "the system prompt under test"}),
        cap("create_testset", "POST", "/api/testsets", risk="write",
            desc="Create a test set. cases is a non-empty list of objects like "
                 "{'input': str, 'reference': str} (reference optional — the ideal answer).",
            params={"name": "test set name", "description": "short description",
                    "cases": "list of case objects"}),
        cap("start_run", "POST", "/api/runs", risk="write",
            desc="Launch a real eval run: every case answered by the target and scored by the "
                 "judge model per criterion, billed to the user's wallet. Confirm target and "
                 "test set with the user first.",
            params={"target_id": "target id", "testset_id": "test set id",
                    "criteria_ids": "list of criterion ids (omit for all)",
                    "pass_threshold": "min avg score 1-5 to pass a criterion (default 3.5)",
                    "readiness_pct": "percent of cases that must pass for READY (default 80)",
                    "max_tokens": "max output tokens per answer (default 500)",
                    "temperature": "sampling temperature (default 0.2)"}),
    ],
}
