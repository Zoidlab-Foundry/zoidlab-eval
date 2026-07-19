"use client";
import { useEffect, useState } from "react";

/* In-app guide: what Eval is and how to run your first evaluation.
   Auto-opens once per browser (localStorage) and lives behind the Guide nav button. */

const STORAGE_KEY = "ev_guide_v1";

const STEPS: { title: string; body: string }[] = [
  {
    title: "Register a target",
    body: "A target is what you're evaluating — a model plus the system prompt that defines its behavior. On Targets, click New Target, pick a relay model, and paste the system prompt your assistant runs with.",
  },
  {
    title: "Pick your criteria",
    body: "Criteria are the rubric the judge scores each answer against, 1–5. Start with the shared defaults or add your own — a name like \"Tone\" and one sentence describing what a good answer looks like.",
  },
  {
    title: "Build a test set",
    body: "A test set is the suite of prompts your target must handle. On Test Sets, paste real user questions one per line — add reference answers if you want the judge to score against ground truth.",
  },
  {
    title: "Run the evaluation",
    body: "On New Eval, pick a target and test set, tick criteria, and set your pass threshold (1–5) and readiness bar (% of cases that must pass). Every case is a real generation plus a real LLM-judge call over the Nyquest relay — nothing is simulated.",
  },
  {
    title: "Drill into failures",
    body: "The run ends in a READY or NOT READY verdict. Open the run to see every case with per-criterion scores and the judge's reasons — flip on \"failures only\" to see exactly where your target falls short.",
  },
  {
    title: "Export the evidence",
    body: "Any completed run exports as JSON or YAML — the full verdict, per-case scores, and config. Drop it in a ticket, a release checklist, or your CI gate.",
  },
];

export default function HelpGuide() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) setOpen(true);
    } catch {}
  }, []);

  const dismiss = () => {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") dismiss(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim transition hover:text-ink hover:bg-white/5"
        aria-label="Open the Eval guide"
      >
        Guide
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={dismiss} role="dialog" aria-modal="true" aria-label="Eval guide">
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-line bg-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-1 flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-md bg-vi/15 text-[13px] text-vi">✓</span>
              <h2 className="text-[16px] font-semibold">How Eval works</h2>
            </div>
            <p className="mb-5 text-[13px] text-dim">
              Score your AI's answers against your own rubric with a real LLM judge and get a production-readiness verdict. Six steps from zero to READY:
            </p>
            <ol className="space-y-4">
              {STEPS.map((s, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-vi/15 text-[12px] font-semibold text-vi">{i + 1}</span>
                  <div>
                    <div className="text-[13.5px] font-medium">{s.title}</div>
                    <div className="text-[12.5px] leading-relaxed text-dim">{s.body}</div>
                  </div>
                </li>
              ))}
            </ol>
            <div className="mt-6 flex items-center justify-between border-t border-line pt-4">
              <a href="https://foundry.zoidlab.ai" className="text-[12px] text-dim hover:text-ink">◈ All Foundry apps</a>
              <button onClick={dismiss} className="rounded-lg bg-vi px-4 py-1.5 text-[12.5px] font-semibold text-white hover:opacity-90">
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
