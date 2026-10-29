"use client";

import React from "react";
import { TicketInfo } from "@/lib/api";

interface TicketBannerProps {
  ticket: TicketInfo;
}

export const TicketBanner: React.FC<TicketBannerProps> = ({ ticket }) => {
  return (
    <div className="mt-3 p-3.5 bg-gradient-to-r from-amber-500/15 to-orange-500/15 border border-amber-500/30 rounded-xl text-xs text-amber-200">
      <div className="flex items-center justify-between mb-1.5 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
          <span className="font-semibold text-amber-300 uppercase tracking-wide">
            Official Escalation Ticket Created
          </span>
        </div>
        <span className="px-2 py-0.5 rounded bg-amber-500/20 font-mono text-amber-300 font-bold">
          #{ticket.id}
        </span>
      </div>

      <p className="text-slate-300 mb-2">
        Sufficient verified evidence was unavailable in official documents. Your inquiry has been forwarded to the{" "}
        <strong className="text-white font-medium">{ticket.department}</strong> department for administrative resolution.
      </p>

      {/* User details badge */}
      {ticket.user_name && (
        <div className="mt-2 pt-2 border-t border-amber-500/20 flex items-center justify-between text-[11px] text-amber-300/90">
          <span>
            Raised for: <strong className="text-white">{ticket.user_name}</strong>
            {ticket.user_email && <span className="text-slate-400 ml-1">({ticket.user_email})</span>}
          </span>
          <span className="text-slate-400">Track under &lsquo;My Tickets&rsquo;</span>
        </div>
      )}
    </div>
  );
};
