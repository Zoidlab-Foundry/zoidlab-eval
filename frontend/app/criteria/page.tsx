"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function Criteria() {
  const [criteria, setCriteria] = useState<any[]>([]);
  const [f, setF] = useState({ name: "", description: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = () => api.criteria().then(setCriteria).catch(() => {});
  useEffect(() => { load(); }, []);

  async function create() {
    setBusy(true); setErr("");
    try { await api.createCriterion(f); setF({ name: "", description: "" }); load(); }
    catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  async function remove(id: string) { try { await api.deleteCriterion(id); load(); } catch {} }

  return (
    <div className="py-8 max-w-[840px]">
      <h1 className="text-[24px] font-semibold">Criteria</h1>
      <p className="mt-1 text-[13px] text-dim">The rubric the judge scores each answer against (1–5). Shared defaults plus any you add.</p>

      <div className="mt-5 rounded-2xl border border-line bg-panel p-4">
        <div className="grid gap-2 sm:grid-cols-[1fr_2fr_auto] sm:items-end">
          <label className="block text-[12px] text-dim">Name<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink" placeholder="Tone" /></label>
          <label className="block text-[12px] text-dim">Description<input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink" placeholder="Is the tone appropriate for the audience?" /></label>
          <button onClick={create} disabled={busy || !f.name} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">Add</button>
        </div>
        {err && <p className="mt-2 text-[12px] text-bad">{err}</p>}
      </div>

      <div className="mt-4 space-y-2">
        {criteria.map((c) => (
          <div key={c.id} className="flex items-start justify-between gap-3 rounded-xl border border-line bg-panel p-3.5">
            <div>
              <div className="text-[13.5px] font-medium text-ink">{c.name}{!c.owner_user_id && <span className="ml-2 rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-faint">default</span>}</div>
              <div className="mt-0.5 text-[12px] text-dim">{c.description}</div>
            </div>
            {c.owner_user_id && <button onClick={() => remove(c.id)} className="shrink-0 text-[11px] text-faint hover:text-bad">Delete</button>}
          </div>
        ))}
      </div>
    </div>
  );
}
