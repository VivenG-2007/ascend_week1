import { documentFileUrl, type SourceRef } from "@/lib/api";

export default function SourceChips({ sources }: { sources: SourceRef[] }) {
  if (sources.length === 0) return null;
  return (
    <ul className="mt-3 flex flex-wrap gap-2" aria-label="Sources">
      {sources.map((s, i) => {
        const isDoc = s.document_id !== "structured-data";
        const body = (
          <>
            <span className="font-semibold">{s.title}</span>
            {s.source_date && <span>, {s.source_date}</span>}
            {s.page_number != null && <span>, page {s.page_number}</span>}
          </>
        );
        return (
          <li key={`${s.document_id}-${s.page_number ?? 0}-${i}`} className="rounded-md border border-teal-700/30 bg-white px-2.5 py-1 text-xs text-teal-800">
            {isDoc ? (
              <a href={documentFileUrl(s.document_id, s.page_number)} target="_blank" rel="noopener noreferrer" className="underline decoration-dotted underline-offset-2">{body}</a>
            ) : body}
            {s.superseded_note && <span className="mt-0.5 block text-amberink">{s.superseded_note}</span>}
          </li>
        );
      })}
    </ul>
  );
}
