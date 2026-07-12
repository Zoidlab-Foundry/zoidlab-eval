"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

export default function Testsets() {
  const [testsets, setTestsets] = useState<any[]>([]);
  const [view, setView] = useState<any>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [f, setF] = useState({ name: "", description: "", cases: "" });

  const load = () => api.testsets().then(setTestsets).catch(() => {});
  useEffect(() => { load(); }, []);

  async function create() {
    setBusy(true); setErr("");
    try {
      const cases = f.cases.split("\n").map((l) => l.trim()).filter(Boolean).map((input, i) => ({ id: `c${i + 1}`, input }));
      if (!cases.length) throw new Error("Add at least one case (one prompt per line).");
      await api.createTestset({ name: f.name, description: f.description, cases });
      setOpen(false); setF({ name: "", description: "", cases: "" }); load();
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  async function remove(id: string) { await api.deleteTestset(id); load(); }

  return (
    <div className="py-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[24px] font-semibold">Test Sets</h1>
          <p className="mt-1 text-[13px] text-dim">Collections of prompts (with optional reference answers) you evaluate a target against.</p>
        </div>
        <button onClick={() => setOpen(true)} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90">+ New test set</button>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {testsets.map((t) => (
          <div key={t.id} className="rounded-2xl border border-line bg-panel p-4">
            <div className="flex items-start justify-between">
              <div><div className="text-[14px] font-semibold text-ink">{t.name}</div><div className="mt-0.5 text-[11px] text-faint">{t.case_count} cases</div></div>
              {t.owner_user_id && <button onClick={() => remove(t.id)} className="text-[11px] text-faint hover:text-bad">Delete</button>}
            </div>
            <p className="mt-2 line-clamp-2 text-[12px] text-dim">{t.description}</p>
            <div className="mt-3 flex gap-2">
              <button onClick={() => setView(t)} className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim hover:text-ink">View cases</button>
              <Link href="/evaluate" className="rounded-lg border border-vi/40 px-3 py-1.5 text-[12px] text-vi hover:bg-vi/10">Evaluate →</Link>
            </div>
          </div>
        ))}
        {!testsets.length && <div className="col-span-3 rounded-2xl border border-dashed border-line py-14 text-center text-[13px] text-faint">No test sets yet.</div>}
      </div>

      {view && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-black/60 p-4" onClick={() => setView(null)}>
          <div className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-line bg-panel p-5" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-[16px] font-semibold">{view.name}</h2>
            <div className="mt-3 space-y-2">
              {view.cases.map((c: any) => (
                <div key={c.id} className="rounded-lg border border-line bg-panel2 p-2.5">
                  <div className="text-[10.5px] text-faint">{c.id}</div>
                  <div className="mt-0.5 text-[12.5px] text-ink">{c.input}</div>
                  {c.reference && <div className="mt-1 text-[11px] text-dim">ref: {c.reference}</div>}
                </div>
              ))}
            </div>
            <button onClick={() => setView(null)} className="mt-4 rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Close</button>
          </div>
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-black/60 p-4" onClick={() => setOpen(false)}>
          <div className="w-full max-w-lg rounded-2xl border border-line bg-panel p-5" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-[16px] font-semibold">New test set</h2>
            <div className="mt-4 space-y-3">
              <label className="block text-[12px] text-dim">Name<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink" /></label>
              <label className="block text-[12px] text-dim">Description<input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink" /></label>
              <label className="block text-[12px] text-dim">Cases (one prompt per line)<textarea value={f.cases} onChange={(e) => setF({ ...f, cases: e.target.value })} rows={7} className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink" placeholder={"How do I cancel my subscription?\nWhat languages do you support?"} /></label>
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
