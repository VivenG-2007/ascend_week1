"use client";

import { useState } from "react";
import { ApiError, DEPARTMENTS, uploadDocument, type AdminDocument, type UploadReport } from "@/lib/api";

const field = "w-full rounded-md border border-ink/25 bg-white px-3 py-2";

export default function DocumentUpload({ documents, onDone, onAuthError }: { documents: AdminDocument[]; onDone: () => void; onAuthError: () => void }) {
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<UploadReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true); setError(null); setReport(null);
    try {
      const r = await uploadDocument(new FormData(form));
      setReport(r); onDone();
      if (r.document.processing_status === "processed") form.reset();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return onAuthError();
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally { setBusy(false); }
  }

  return (
    <section aria-labelledby="up" className="rounded-lg border border-ink/10 bg-white p-4">
      <h2 id="up" className="mb-3 text-lg font-semibold">Upload an official document</h2>
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <label className="sm:col-span-2">File (PDF, JPG or PNG)<input name="file" type="file" required accept="application/pdf,image/png,image/jpeg" className={field} /></label>
        <label className="sm:col-span-2">Title<input name="title" required maxLength={300} className={field} placeholder="Revised Fee Payment Circular" /></label>
        <label>Category<input name="category" required defaultValue="Circular" maxLength={100} className={field} /></label>
        <label>Department<select name="department" required defaultValue="General" className={field}>{DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}</select></label>
        <label>Source date<input name="source_date" type="date" required className={field} /></label>
        <label>Replaces (optional)<select name="supersedes_id" defaultValue="" className={field}><option value="">Nothing</option>{documents.filter((d) => d.processing_status === "processed").map((d) => <option key={d.id} value={d.id}>{d.title} ({d.source_date})</option>)}</select></label>
        <div className="sm:col-span-2 flex items-center gap-3">
          <button disabled={busy} className="rounded-md bg-teal-700 px-5 py-2 font-semibold text-white hover:bg-teal-800 disabled:opacity-50">{busy ? "Processing…" : "Upload and index"}</button>
          {busy && <span role="status" className="text-sm text-ink/60">Extracting text, running OCR if needed, and indexing. This can take up to a minute.</span>}
        </div>
      </form>
      {error && <p role="alert" className="mt-3 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {report && (
        <div role="status" className={`mt-3 rounded-md border px-3 py-2 text-sm ${report.document.processing_status === "processed" ? "border-teal-700/40 bg-teal-50" : "border-red-300 bg-red-50 text-red-800"}`}>
          <p className="font-semibold">{report.document.processing_status === "processed" ? "Indexed and searchable" : "Processing failed"}: {report.document.title}</p>
          <p>{report.pages} page(s), {report.ocr_pages} read with OCR, {report.chunks} chunk(s), {report.duration_ms} ms. Extraction: {report.document.extraction_status}.</p>
          {report.error && <p>Reason: {report.error}</p>}
          {report.warnings.length > 0 && <ul className="mt-1 list-disc pl-5">{report.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
        </div>
      )}
    </section>
  );
}
