"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

export default function Targets() {
  const [targets, setTargets] = useState<any[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [f, setF] = useState({ name: "", description: "", model: "auto", system_prompt: "" });

  const load = () => api.targets().then(setTargets).catch(() => {});
  useEffect(() => { load(); api.meta().then((m) => setModels(m.featured_models || [])).catch(() => {}); }, []);

  async function create() {
    setBusy(true); setErr("");
    try { await api.createTarget(f); setOpen(false); setF({ name: "", description: "", model: "auto", system_prompt: "" }); load(); }
    catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  async function remove(id: string) { await api.deleteTarget(id); load(); }

  return (
    <div className="py-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[24px] font-semibold">Targets</h1>
          <p className="mt-1 text-[13px] text-dim">What you're evaluating — a model plus the system prompt that defines its behavior.</p>
        </div>
        <button data-assist="new-target" onClick={() => setOpen(true)} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90">+ New target</button>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {targets.map((t) => (
          <div key={t.id} className="rounded-2xl border border-line bg-panel p-4">
            <div className="flex items-start justify-between">
              <div><div className="text-[14px] font-semibold text-ink">{t.name}</div><div className="mt-0.5 text-[11px] text-faint">{t.model}</div></div>
              {t.owner_user_id && <button onClick={() => remove(t.id)} className="text-[11px] text-faint hover:text-bad">Delete</button>}
            </div>
            {t.description && <p className="mt-2 line-clamp-2 text-[12px] text-dim">{t.description}</p>}
            {t.system_prompt && <pre className="mt-2 max-h-[80px] overflow-hidden whitespace-pre-wrap rounded-lg border border-line bg-panel2 p-2 text-[11px] text-faint">{t.system_prompt}</pre>}
            <Link href="/evaluate" className="mt-3 inline-block text-[12px] text-cy hover:underline">Evaluate →</Link>
          </div>
        ))}
        {!targets.length && <div className="col-span-3 rounded-2xl border border-dashed border-line py-14 text-center text-[13px] text-faint">No targets yet.</div>}
      </div>

      {open && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-black/60 p-4" onClick={() => setOpen(false)}>
          <div className="w-full max-w-lg rounded-2xl border border-line bg-panel p-5" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-[16px] font-semibold">New target</h2>
            <div className="mt-4 space-y-3">
              <label className="block text-[12px] text-dim">Name<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink" placeholder="Support Assistant v2" /></label>
              <label className="block text-[12px] text-dim">Model
                <select value={f.model} onChange={(e) => setF({ ...f, model: e.target.value })} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink">
                  {models.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </label>
              <label className="block text-[12px] text-dim">Description<input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink" /></label>
              <label className="block text-[12px] text-dim">System prompt<textarea value={f.system_prompt} onChange={(e) => setF({ ...f, system_prompt: e.target.value })} rows={4} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink" placeholder="You are a concise, friendly support assistant…" /></label>
            </div>
            {err && <p className="mt-2 text-[12px] text-bad">{err}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setOpen(false)} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Cancel</button>
              <button onClick={create} disabled={busy || !f.name} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Creating…" : "Create"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
