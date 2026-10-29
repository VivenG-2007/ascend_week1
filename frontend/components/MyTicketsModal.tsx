"use client";

import React, { useEffect, useState } from "react";
import { fetchMyTickets, UserTicket } from "@/lib/api";

interface MyTicketsModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: string | null;
  userName: string;
}

export function MyTicketsModal({ isOpen, onClose, token, userName }: MyTicketsModalProps) {
  const [tickets, setTickets] = useState<UserTicket[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && token) {
      loadTickets();
    }
  }, [isOpen, token]);

  const loadTickets = async () => {
    if (!token) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await fetchMyTickets(token);
      setTickets(data);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to load tickets.");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
              </svg>
              My Escalation Tickets
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Official tickets submitted for {userName}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-4 space-y-3">
          {isLoading && (
            <div className="text-center py-10 text-xs text-slate-500">
              Loading your tickets...
            </div>
          )}

          {errorMessage && (
            <div className="p-3 rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs">
              {errorMessage}
            </div>
          )}

          {!isLoading && tickets.length === 0 && (
            <div className="text-center py-12">
              <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-3 text-slate-500">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-xs text-slate-400">No tickets raised yet.</p>
              <p className="text-[11px] text-slate-500 mt-1">
                When you ask unanswerable or missing college inquiries, CampusVoice automatically logs a ticket with your identity!
              </p>
            </div>
          )}

          {tickets.map((t) => (
            <div
              key={t.id}
              className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-2 hover:border-slate-600 transition"
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono font-semibold text-indigo-400">{t.id}</span>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-700 text-slate-300">
                    {t.department}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                      t.status === "resolved"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : t.status === "in_progress"
                        ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                        : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                    }`}
                  >
                    {t.status.toUpperCase()}
                  </span>
                </div>
              </div>

              <div className="text-xs text-white font-medium">
                &ldquo;{t.question}&rdquo;
              </div>

              {t.resolution_note && (
                <div className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 font-semibold block mb-0.5">Note:</span>
                  {t.resolution_note}
                </div>
              )}

              <div className="text-[10px] text-slate-500 pt-1">
                Raised: {t.created_at ? new Date(t.created_at).toLocaleString() : "Recently"}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-800 flex justify-between items-center text-xs text-slate-500">
          <span>Total: {tickets.length} ticket(s)</span>
          <button
            onClick={loadTickets}
            className="text-indigo-400 hover:text-indigo-300 underline"
          >
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}
