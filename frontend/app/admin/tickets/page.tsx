"use client";

import { useCallback, useEffect, useState } from "react";
import AdminShell, { useAuthGuard } from "@/components/AdminShell";
import { ApiError, DEPARTMENTS, listTickets, patchTicket, type AdminTicket } from "@/lib/api";

const STATUSES = ["open", "in_progress", "resolved"];

function Ticket({ t, onSaved, onAuth }: { t: AdminTicket; onSaved: () => void; onAuth: () => void }) {
  const [status, setStatus] = useState(t.status);
  const [note, setNote] = useState(t.resolution_note ?? "");
  const [msg, setMsg] = useState<string | null>(null);
  async function save() {
    try { await patchTicket(t.id, { status, resolution_note: note }); setMsg("Saved"); onSaved(); }
    catch (e) { if (e instanceof ApiError && e.status === 401) onAuth(); else setMsg(e instanceof ApiError ? e.message : "Could not save."); }
  }
  return (
    <li className="rounded-lg border border-ink/10 bg-white p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-mono text-sm font-semibold">{t.id}</p>
        <p className="text-xs text-ink/60">{t.department} · {t.language.toUpperCase()} · created {new Date(t.created_at).toLocaleString()}{t.resolved_at && ` · resolved ${new Date(t.resolved_at).toLocaleString()}`}</p>
      </div>
      <p className="mt-2" lang={t.language}>{t.question}</p>
      {t.transcript && t.transcript !== t.question && <p className="mt-1 text-sm text-ink/70">Transcript: {t.transcript}</p>}
      <div className="mt-3 grid gap-2 sm:grid-cols-[10rem_1fr_auto]">
        <select aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-md border border-ink/25 px-2 py-1.5">{STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
        <input aria-label="Resolution note" value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} placeholder="Resolution note" className="rounded-md border border-ink/25 px-2 py-1.5" />
        <button onClick={() => void save()} className="rounded-md bg-ink px-4 py-1.5 text-white">Save</button>
      </div>
      {msg && <p role="status" className="mt-1 text-xs text-ink/60">{msg}</p>}
    </li>
  );
}

function Tickets() {
  const { expired } = useAuthGuard();
  const [dept, setDept] = useState(""); const [status, setStatus] = useState("");
  const [items, setItems] = useState<AdminTicket[]>([]); const [total, setTotal] = useState(0); const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try { const r = await listTickets(dept || undefined, status || undefined); setItems(r.items); setTotal(r.total); setError(null); }
    catch (e) { if (e instanceof ApiError && e.status === 401) expired(); else setError(e instanceof ApiError ? e.message : "Could not load tickets."); }
  }, [dept, status, expired]);
  useEffect(() => { void load(); }, [load]);
  const sel = "rounded-md border border-ink/25 bg-white px-2 py-1.5";
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">Tickets ({total})</h1>
        <select aria-label="Filter by department" value={dept} onChange={(e) => setDept(e.target.value)} className={sel}><option value="">All departments</option>{DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}</select>
        <select aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)} className={sel}><option value="">All statuses</option>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
      </div>
      {error && <p role="alert" className="text-red-700">{error}</p>}
      <ul className="space-y-3">{items.map((t) => <Ticket key={`${t.id}-${t.updated_at}`} t={t} onSaved={() => void load()} onAuth={expired} />)}</ul>
      {items.length === 0 && !error && <p className="text-ink/60">No tickets match.</p>}
    </div>
  );
}
export default function Page() { return <AdminShell><Tickets /></AdminShell>; }
