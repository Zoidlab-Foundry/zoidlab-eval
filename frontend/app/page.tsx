"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, num } from "../lib/api";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-faint">{label}</div>
      <div className="mt-1.5 text-[24px] font-semibold tnum text-ink">{value}</div>
    </div>
  );
}

function Verdict({ v }: { v?: string }) {
  if (!v) return <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10.5px] text-faint">—</span>;
  return <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${v === "READY" ? "bg-ok/10 text-ok" : "bg-bad/10 text-bad"}`}>{v}</span>;
}

export default function Dashboard() {
  const [s, setS] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);

  useEffect(() => {
    api.stats().then(setS).catch(() => {});
    api.runs().then((r) => setRuns(r.slice(0, 6))).catch(() => {});
    api.meta().then(setMeta).catch(() => {});
  }, []);

  return (
    <div className="py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[24px] font-semibold">Evaluation Lab</h1>
          <p className="mt-1 text-[13px] text-dim">Score your AI's answers against criteria with an LLM judge and get a production-readiness verdict — real relay runs.</p>
        </div>
        <Link href="/evaluate" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90">Run an evaluation →</Link>
      </div>

      {meta && (
        <div className={`mt-4 flex items-center gap-2 rounded-xl border px-4 py-2.5 text-[12.5px] ${meta.relay_available ? "border-ok/30 bg-ok/5 text-ok" : "border-warn/30 bg-warn/5 text-warn"}`}>
          <span className={`h-2 w-2 rounded-full ${meta.relay_available ? "bg-ok" : "bg-warn"}`} />
          {meta.relay_available
            ? <>Live relay connected · answers billed to the <b>{meta.billing_mode}</b> wallet · judge <code className="text-ink">{meta.judge_model}</code>.</>
            : <>Relay key not configured — real evaluations are unavailable until <code className="text-ink">NYQUEST_API_KEY</code> is set.</>}
        </div>
      )}

      <div className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Targets" value={num(s?.targets ?? 0)} />
        <Stat label="Test sets" value={num(s?.testsets ?? 0)} />
        <Stat label="Eval runs" value={num(s?.runs ?? 0)} />
        <Stat label="Ready verdicts" value={num(s?.ready_targets ?? 0)} />
      </div>

      <div className="mt-4 rounded-2xl border border-line bg-panel p-5">
        <div className="flex items-center justify-between"><h2 className="text-[14px] font-semibold">Recent evaluations</h2><Link href="/runs" className="text-[12px] text-cy hover:underline">All →</Link></div>
        <div className="mt-3 space-y-2">
          {runs.map((r) => (
            <Link key={r.id} href={`/runs/${r.id}`} className="flex items-center justify-between rounded-lg border border-line bg-panel2 p-3 hover:border-vi/40">
              <div>
                <div className="text-[13px] font-medium text-ink">{r.target_name}</div>
                <div className="mt-0.5 text-[11px] text-faint">{r.testset_name} · {(r.summary?.cases) ?? 0} cases{r.summary?.pass_rate != null ? ` · ${r.summary.pass_rate}% pass` : ""}</div>
              </div>
              <div className="flex items-center gap-3">
                {r.status !== "complete" && <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${r.status === "failed" ? "bg-bad/10 text-bad" : "bg-warn/10 text-warn"}`}>{r.status}</span>}
                {r.status === "complete" && <Verdict v={r.summary?.verdict} />}
              </div>
            </Link>
          ))}
          {!runs.length && <p className="text-[12px] text-faint">No evaluations yet. <Link href="/evaluate" className="text-cy hover:underline">Run one</Link>.</p>}
        </div>
      </div>
    </div>
  );
}
