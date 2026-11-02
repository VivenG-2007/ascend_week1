"use client";

import { useEffect, useState } from "react";
import AdminShell, { useAuthGuard } from "@/components/AdminShell";
import { ApiError, getAnalytics, type Analytics } from "@/lib/api";

const Card = ({ label, value }: { label: string; value: string | number }) => (
  <div className="rounded-lg border border-ink/10 bg-white p-4"><p className="text-2xl font-semibold">{value}</p><p className="text-sm text-ink/60">{label}</p></div>
);
function Bars({ title, data }: { title: string; data: [string, number][] }) {
  const max = Math.max(1, ...data.map(([, n]) => n));
  return (
    <section className="rounded-lg border border-ink/10 bg-white p-4"><h2 className="mb-2 font-semibold">{title}</h2>
      {data.length === 0 ? <p className="text-sm text-ink/60">No data yet.</p> : <ul className="space-y-1.5">{data.map(([k, n]) => (
        <li key={k} className="grid grid-cols-[8rem_1fr_2rem] items-center gap-2 text-sm"><span className="truncate">{k}</span><span className="h-3 rounded bg-teal-700/80" style={{ width: `${(n / max) * 100}%` }} /><span className="text-right">{n}</span></li>))}</ul>}
    </section>
  );
}
const ms = (v: number | null | undefined) => (v == null ? "n/a" : `${v} ms`);

function View() {
  const { expired } = useAuthGuard();
  const [a, setA] = useState<Analytics | null>(null); const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    getAnalytics().then(setA).catch((e) => { if (e instanceof ApiError && e.status === 401) expired(); else setError(e instanceof ApiError ? e.message : "Could not load analytics."); });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (error) return <p role="alert" className="text-red-700">{error}</p>;
  if (!a) return <p className="text-ink/60">Loading…</p>;
  const lat = a.latency;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Card label="Questions" value={a.totals.questions} /><Card label="Tickets" value={a.totals.tickets} /><Card label="Documents" value={a.totals.documents} />
        <Card label="Median response" value={ms(lat.total?.median_ms)} /><Card label="Average response" value={ms(lat.total?.average_ms)} /><Card label="Median speech-to-text" value={ms(lat.stt?.median_ms)} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Bars title="Language usage" data={Object.entries(a.language_usage).map(([k, v]) => [k === "te" ? "Telugu" : k === "en" ? "English" : k, v])} />
        <Bars title="Tickets by status" data={Object.entries(a.tickets_by_status)} />
        <Bars title="Tickets by department" data={Object.entries(a.tickets_by_department)} />
        <Bars title="Retrieval confidence (top similarity)" data={a.retrieval_confidence.buckets.map((b) => [b.range, b.count])} />
        <Bars title="Answer decisions" data={Object.entries(a.retrieval_confidence.decisions)} />
        <section className="rounded-lg border border-ink/10 bg-white p-4"><h2 className="mb-2 font-semibold">Latency by stage (median)</h2>
          <ul className="space-y-1 text-sm">{(["total", "stt", "llm", "tts"] as const).map((k) => <li key={k} className="flex justify-between"><span>{k === "total" ? "End to end" : k.toUpperCase()}</span><span>{ms(lat[k]?.median_ms)} <span className="text-ink/50">({lat[k]?.count ?? 0} samples)</span></span></li>)}</ul></section>
      </div>
      <section className="rounded-lg border border-ink/10 bg-white p-4"><h2 className="mb-2 font-semibold">Most frequent questions</h2>
        <ol className="list-decimal space-y-1 pl-5 text-sm">{a.top_questions.map((q) => <li key={q.question}>{q.question} <span className="text-ink/50">× {q.count}</span></li>)}</ol>{a.top_questions.length === 0 && <p className="text-sm text-ink/60">No questions yet.</p>}</section>
      <section className="rounded-lg border border-ink/10 bg-white p-4"><h2 className="mb-2 font-semibold">Unanswered questions (ticketed)</h2>
        <ul className="space-y-1 text-sm">{a.unanswered_questions.map((q) => <li key={q.ticket_id}><span className="font-mono">{q.ticket_id}</span> · {q.department} · {q.status}: {q.question}</li>)}</ul>{a.unanswered_questions.length === 0 && <p className="text-sm text-ink/60">None.</p>}</section>
      <section className="rounded-lg border border-ink/10 bg-white p-4"><h2 className="mb-2 font-semibold">Document processing failures</h2>
        <ul className="space-y-1 text-sm">{a.document_failures.map((d) => <li key={d.id}><strong>{d.title}</strong>: <span className="text-red-700">{d.error ?? "unknown error"}</span></li>)}</ul>{a.document_failures.length === 0 && <p className="text-sm text-ink/60">None.</p>}</section>
    </div>
  );
}
export default function Page() { return <AdminShell><View /></AdminShell>; }
