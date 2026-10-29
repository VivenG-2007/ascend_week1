"use client";

import React from "react";
import { SourceCitation } from "@/lib/api";

interface SourceChipsProps {
  sources: SourceCitation[];
}

export const SourceChips: React.FC<SourceChipsProps> = ({ sources }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-800">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
        <svg className="w-3.5 h-3.5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <span>Official Sources Grounding</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {sources.map((src, idx) => (
          <div
            key={idx}
            className={`text-xs px-2.5 py-1.5 rounded-lg border transition-all ${
              src.superseded
                ? "bg-amber-500/10 border-amber-500/30 text-amber-300 line-through"
                : "bg-slate-800/80 hover:bg-slate-700/80 border-slate-700 text-slate-200"
            } flex items-center gap-1.5`}
          >
            <span className="font-medium">{src.title}</span>
            {src.source_date && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900/60 text-slate-400">
                {src.source_date}
              </span>
            )}
            {src.page_number && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-950/70 text-indigo-300 font-mono">
                p.{src.page_number}
              </span>
            )}
            {src.replaces && (
              <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-950/80 text-emerald-300 font-medium">
                (Latest Revised)
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
