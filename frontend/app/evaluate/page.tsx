"use client";
import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

export default function Evaluate() {
  const [targets, setTargets] = useState<any[]>([]);
  const [testsets, setTestsets] = useState<any[]>([]);
  const [criteria, setCriteria] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [tid, setTid] = useState("");
  const [tsid, setTsid] = useState("");
  const [critIds, setCritIds] = useState<string[]>([]);
  const [threshold, setThreshold] = useState("3.5");
  const [readiness, setReadiness] = useState("80");
  const [run, setRun] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const poll = useRef<any>(null);

  useEffect(() => {
    api.targets().then((d) => { setTargets(d); if (d[0]) setTid(d[0].id); }).catch(() => {});
    api.testsets().then((d) => { setTestsets(d); if (d[0]) setTsid(d[0].id); }).catch(() => {});
    api.criteria().then((d) => { setCriteria(d); setCritIds(d.map((c: any) => c.id)); }).catch(() => {});
    api.meta().then(setMeta).catch(() => {});
    return () => poll.current && clearInterval(poll.current);
  }, []);

  const toggle = (id: string) => setCritIds((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);

  async function start() {
    setErr(""); setBusy(true); setRun(null);
    try {
      const r = await api.startRun({ target_id: tid, testset_id: tsid, criteria_ids: critIds,
        pass_threshold: parseFloat(threshold), readiness_pct: parseFloat(readiness) });
      poll.current = setInterval(async () => {
        const full = await api.run(r.run_id);
        setRun(full);
        if (full.status !== "running") { clearInterval(poll.current); setBusy(false); }
      }, 1800);
    } catch (e: any) { setErr(e.message); setBusy(false); }
  }

  const ts = testsets.find((t) => t.id === tsid);
  const sum = run?.summary;

  return (
    <div className="py-8">
      <h1 className="text-[24px] font-semibold">New Evaluation</h1>
      <p className="mt-1 text-[13px] text-dim">Pick a target and test set. Each case is answered by the target and scored by the judge against your criteria.</p>

      {meta && !meta.relay_available && <div className="mt-4 rounded-xl border border-warn/30 bg-warn/5 px-4 py-2.5 text-[12.5px] text-warn">Relay key not configured — real evaluations are unavailable.</div>}

      <div className="mt-5 grid gap-4 lg:grid-cols-[400px_1fr]">
        <div className="rounded-2xl border border-line bg-panel p-5">
          <label className="block text-[12px] text-dim">Target
            <select value={tid} onChange={(e) => setTid(e.target.value)} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink">
              {targets.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
          <label className="mt-3 block text-[12px] text-dim">Test set
            <select value={tsid} onChange={(e) => setTsid(e.target.value)} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink">
              {testsets.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.case_count} cases)</option>)}
            </select>
          </label>
          {ts && <p className="mt-1 text-[11px] text-faint">{ts.description}</p>}

          <div className="mt-4 text-[12px] text-dim">Criteria</div>
          <div className="mt-1.5 space-y-1">
            {criteria.map((c) => (
              <label key={c.id} className="flex items-start gap-2 rounded-lg border border-line bg-panel2 px-3 py-2 text-[12.5px] text-ink hover:border-vi/40">
                <input type="checkbox" checked={critIds.includes(c.id)} onChange={() => toggle(c.id)} className="mt-0.5 accent-vi" />
                <span><span className="font-medium">{c.name}</span><span className="block text-[11px] text-faint">{c.description}</span></span>
              </label>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3">
            <label className="block text-[12px] text-dim">Pass threshold (1–5)<input value={threshold} onChange={(e) => setThreshold(e.target.value)} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink tnum" /></label>
            <label className="block text-[12px] text-dim">Ready if ≥ % pass<input value={readiness} onChange={(e) => setReadiness(e.target.value)} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink tnum" /></label>
          </div>

          <button onClick={start} disabled={busy || !tid || !tsid || !critIds.length || (meta && !meta.relay_available)} className="mt-4 w-full rounded-lg bg-vi px-4 py-2.5 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">
            {busy ? "Evaluating live…" : "Run evaluation"}
          </button>
          {err && <p className="mt-2 text-[12px] text-bad">{err}</p>}
        </div>

        <div className="rounded-2xl border border-line bg-panel p-5">
          {!run && <div className="flex h-full min-h-[300px] items-center justify-center text-center text-[13px] text-faint">The verdict appears here. Each case is a generation + a judge call.</div>}
          {run && (
            <>
              <div className="flex items-center justify-between">
                <h2 className="text-[15px] font-semibold">{run.target_name}</h2>
                {run.status === "complete"
                  ? <span className={`rounded-full px-3 py-1 text-[12px] font-semibold ${sum?.verdict === "READY" ? "bg-ok/15 text-ok" : "bg-bad/15 text-bad"}`}>{sum?.verdict}</span>
                  : <span className={`rounded-full px-2.5 py-0.5 text-[11px] ${run.status === "failed" ? "bg-bad/10 text-bad" : "bg-warn/10 text-warn animate-pulse"}`}>{run.status}</span>}
              </div>
              {run.error && <p className="mt-2 text-[12px] text-bad">{run.error}</p>}
              {run.status === "running" && <p className="mt-2 text-[12px] text-dim">{(run.results || []).length} cases scored…</p>}

              {sum?.cases > 0 && (
                <>
                  <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                    <div className="rounded-xl bg-panel2 p-3"><div className="text-[11px] uppercase tracking-wider text-faint">Pass rate</div><div className="mt-1 text-[22px] font-semibold tnum text-ink">{sum.pass_rate}%</div></div>
                    <div className="rounded-xl bg-panel2 p-3"><div className="text-[11px] uppercase tracking-wider text-faint">Passed</div><div className="mt-1 text-[22px] font-semibold tnum text-ok">{sum.passed}</div></div>
                    <div className="rounded-xl bg-panel2 p-3"><div className="text-[11px] uppercase tracking-wider text-faint">Failed</div><div className="mt-1 text-[22px] font-semibold tnum text-bad">{sum.failed}</div></div>
                  </div>
                  <div className="mt-4 text-[12px] text-dim">Average score by criterion</div>
                  <div className="mt-2 space-y-2">
                    {Object.entries(sum.per_criterion || {}).map(([k, v]: any) => (
                      <div key={k}>
                        <div className="flex justify-between text-[12px]"><span className="text-dim">{k}</span><span className="tnum text-ink">{v != null ? v + "/5" : "—"}</span></div>
                        <div className="mt-1 h-2 rounded bg-white/5"><div className="h-2 rounded bg-vi" style={{ width: `${((v || 0) / 5) * 100}%` }} /></div>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {run.status === "complete" && <Link href={`/runs/${run.id}`} className="mt-4 inline-block text-[12.5px] text-cy hover:underline">See per-case scores, failures & export →</Link>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
