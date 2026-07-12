"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "../../../lib/api";

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<any>(null);
  const [failedOnly, setFailedOnly] = useState(false);

  useEffect(() => { if (id) api.run(id).then(setRun).catch(() => {}); }, [id]);
  if (!run) return <div className="py-20 text-center text-[13px] text-faint">Loading…</div>;

  const sum = run.summary || {};
  const crit = (run.criteria || []).map((c: any) => c.name);
  const results = (run.results || []).filter((r: any) => !failedOnly || !r.passed);

  return (
    <div className="py-8">
      <Link href="/runs" className="text-[12px] text-cy hover:underline">← Runs</Link>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">{run.target_name}</h1>
          <p className="mt-1 text-[12.5px] text-dim">{run.testset_name} · {run.target_model} · pass ≥ {run.config?.pass_threshold}/5 · ready ≥ {run.config?.readiness_pct}% · billed {run.billing_mode} · {(run.created_at || "").slice(0, 16).replace("T", " ")}</p>
        </div>
        <div className="flex items-center gap-2">
          {run.status === "complete" && <span className={`rounded-full px-3 py-1 text-[12px] font-semibold ${sum.verdict === "READY" ? "bg-ok/15 text-ok" : "bg-bad/15 text-bad"}`}>{sum.verdict}</span>}
          <a href={api.exportJsonUrl(run.id)} target="_blank" rel="noopener" className="rounded-lg bg-vi px-3.5 py-2 text-[12.5px] font-semibold text-white hover:opacity-90">Export JSON</a>
          <a href={api.exportYamlUrl(run.id)} target="_blank" rel="noopener" className="rounded-lg border border-line px-3.5 py-2 text-[12.5px] text-ink hover:bg-white/5">YAML</a>
        </div>
      </div>
      {run.error && <p className="mt-3 text-[12.5px] text-bad">{run.error}</p>}

      {sum.cases > 0 && (
        <div className="mt-5 grid gap-4 lg:grid-cols-[320px_1fr]">
          <div className="rounded-2xl border border-line bg-panel p-5">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-xl bg-panel2 p-3"><div className="text-[10.5px] uppercase tracking-wider text-faint">Pass rate</div><div className="mt-1 text-[20px] font-semibold tnum text-ink">{sum.pass_rate}%</div></div>
              <div className="rounded-xl bg-panel2 p-3"><div className="text-[10.5px] uppercase tracking-wider text-faint">Passed</div><div className="mt-1 text-[20px] font-semibold tnum text-ok">{sum.passed}</div></div>
              <div className="rounded-xl bg-panel2 p-3"><div className="text-[10.5px] uppercase tracking-wider text-faint">Failed</div><div className="mt-1 text-[20px] font-semibold tnum text-bad">{sum.failed}</div></div>
            </div>
            <div className="mt-4 text-[12px] text-dim">Average by criterion</div>
            <div className="mt-2 space-y-2">
              {Object.entries(sum.per_criterion || {}).map(([k, v]: any) => (
                <div key={k}>
                  <div className="flex justify-between text-[12px]"><span className="text-dim">{k}</span><span className="tnum text-ink">{v != null ? v + "/5" : "—"}</span></div>
                  <div className="mt-1 h-2 rounded bg-white/5"><div className="h-2 rounded bg-vi" style={{ width: `${((v || 0) / 5) * 100}%` }} /></div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <h2 className="text-[15px] font-semibold">Cases</h2>
              <label className="flex items-center gap-1.5 text-[12px] text-dim"><input type="checkbox" checked={failedOnly} onChange={(e) => setFailedOnly(e.target.checked)} className="accent-vi" /> failures only</label>
            </div>
            <div className="mt-3 space-y-2">
              {results.map((r: any) => (
                <div key={r.id} className={`rounded-xl border p-3.5 ${r.passed ? "border-line bg-panel" : "border-bad/30 bg-bad/5"}`}>
                  <div className="flex items-center justify-between gap-2 text-[11.5px]">
                    <div className="flex items-center gap-2"><span className="rounded bg-white/5 px-1.5 text-faint">{r.case_id}</span>{!r.ok && <span className="rounded bg-bad/10 px-1.5 text-bad">gen failed</span>}</div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${r.passed ? "bg-ok/10 text-ok" : "bg-bad/10 text-bad"}`}>{r.passed ? "PASS" : "FAIL"}</span>
                      {r.overall != null && <span className="tnum text-dim">{r.overall}/5</span>}
                    </div>
                  </div>
                  <div className="mt-2 text-[12px] text-dim">{r.input}</div>
                  {r.ok ? <pre className="mt-2 max-h-[200px] overflow-auto whitespace-pre-wrap rounded-lg border border-line bg-panel2 p-2.5 text-[12px] text-ink">{r.output}</pre>
                        : <div className="mt-2 rounded-lg border border-bad/30 bg-bad/5 p-2.5 text-[12px] text-bad">{r.error}</div>}
                  {Object.keys(r.scores || {}).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {crit.map((name: string) => {
                        const sc = r.scores[name];
                        return <span key={name} className="rounded-full border border-line px-2 py-0.5 text-[11px] text-dim" title={sc?.reason || ""}>{name}: <span className="tnum text-ink">{sc?.score != null ? sc.score : "—"}</span></span>;
                      })}
                    </div>
                  )}
                </div>
              ))}
              {!results.length && <p className="text-[12px] text-faint">{failedOnly ? "No failures 🎉" : "No cases."}</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
