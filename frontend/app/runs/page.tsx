"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

export default function Runs() {
  const [runs, setRuns] = useState<any[]>([]);
  useEffect(() => { api.runs().then(setRuns).catch(() => {}); }, []);
  return (
    <div className="py-8">
      <h1 className="text-[24px] font-semibold">Evaluation Runs</h1>
      <p className="mt-1 text-[13px] text-dim">Every evaluation you've run, with its production-readiness verdict.</p>
      <div className="mt-5 space-y-2">
        {runs.map((r) => (
          <Link key={r.id} href={`/runs/${r.id}`} className="block rounded-xl border border-line bg-panel p-4 hover:border-vi/40">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[14px] font-medium text-ink">{r.target_name}</div>
                <div className="mt-0.5 text-[11.5px] text-faint">{r.testset_name} · {(r.created_at || "").slice(0, 16).replace("T", " ")} · {(r.summary?.cases) ?? 0} cases{r.summary?.pass_rate != null ? ` · ${r.summary.pass_rate}% pass` : ""}</div>
              </div>
              {r.status === "complete"
                ? <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${r.summary?.verdict === "READY" ? "bg-ok/10 text-ok" : "bg-bad/10 text-bad"}`}>{r.summary?.verdict}</span>
                : <span className={`rounded-full px-2.5 py-0.5 text-[11px] ${r.status === "failed" ? "bg-bad/10 text-bad" : "bg-warn/10 text-warn"}`}>{r.status}</span>}
            </div>
          </Link>
        ))}
        {!runs.length && <div className="rounded-2xl border border-dashed border-line py-14 text-center text-[13px] text-faint">No runs yet. <Link href="/evaluate" className="text-cy hover:underline">Run an evaluation</Link>.</div>}
      </div>
    </div>
  );
}
