"use client";

import { useCallback, useEffect, useState } from "react";
import AdminShell, { useAuthGuard } from "@/components/AdminShell";
import DocumentUpload from "@/components/DocumentUpload";
import { ApiError, listDocuments, type AdminDocument } from "@/lib/api";

const badge = (s: string) => ({ processed: "bg-teal-100 text-teal-900", failed: "bg-red-100 text-red-800", processing: "bg-amber-100 text-amber-900", pending: "bg-slate-100 text-slate-700" }[s] ?? "bg-slate-100");

function Documents() {
  const { expired } = useAuthGuard();
  const [docs, setDocs] = useState<AdminDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    try { setDocs(await listDocuments()); setError(null); }
    catch (e) { if (e instanceof ApiError && e.status === 401) expired(); else setError(e instanceof ApiError ? e.message : "Could not load documents."); }
  }, [expired]);
  useEffect(() => { void refresh(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6">
      <DocumentUpload documents={docs} onDone={() => void refresh()} onAuthError={expired} />
      <section aria-labelledby="dl">
        <h2 id="dl" className="mb-2 text-lg font-semibold">Documents ({docs.length})</h2>
        {error && <p role="alert" className="text-red-700">{error}</p>}
        <div className="overflow-x-auto rounded-lg border border-ink/10 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-mist text-xs uppercase text-ink/70"><tr>{["Title", "Department", "Source date", "Status", "Pages / OCR", "Chunks", "Notes"].map((h) => <th key={h} scope="col" className="px-3 py-2">{h}</th>)}</tr></thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-t border-ink/10 align-top">
                  <td className="px-3 py-2 font-medium">{d.title}<div className="text-xs font-normal text-ink/50">{d.original_filename}</div></td>
                  <td className="px-3 py-2">{d.department}</td><td className="px-3 py-2">{d.source_date}</td>
                  <td className="px-3 py-2"><span className={`rounded px-2 py-0.5 text-xs ${badge(d.processing_status)}`}>{d.processing_status}</span><div className="text-xs text-ink/60">extraction: {d.extraction_status}</div></td>
                  <td className="px-3 py-2">{d.page_count} / {d.ocr_pages}</td><td className="px-3 py-2">{d.chunk_count}</td>
                  <td className="max-w-xs px-3 py-2 text-xs">
                    {d.error_message && <p className="text-red-700">{d.error_message}</p>}
                    {d.warnings.map((w, i) => <p key={i} className="text-amberink">{w}</p>)}
                    {d.superseded_by_id && <p className="text-ink/60">Superseded by a newer document</p>}
                    {d.supersedes_id && <p className="text-ink/60">Replaces an older document</p>}
                  </td>
                </tr>
              ))}
              {docs.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-center text-ink/60">No documents yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
export default function Page() { return <AdminShell><Documents /></AdminShell>; }
