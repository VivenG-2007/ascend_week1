"use client";

import React from "react";
import { ChatResponse } from "@/lib/api";
import { SourceChips } from "./SourceChips";
import { TicketBanner } from "./TicketBanner";

export interface MessageItem {
  id: string;
  role: "user" | "assistant";
  text: string;
  language?: string;
  responseMeta?: ChatResponse;
  timestamp: string;
}

interface ChatPanelProps {
  messages: MessageItem[];
  isLoading: boolean;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ messages, isLoading }) => {
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
      {messages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-center py-12 px-4">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 shadow-inner">
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Welcome to CampusVoice</h3>
          <p className="text-sm text-slate-400 max-w-md">
            Ask any questions regarding fees, faculty cabins, bus routes, examinations, or hostel guidelines in English or తెలుగు.
          </p>
        </div>
      ) : (
        messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            <div className="flex items-center gap-2 mb-1.5 px-1">
              <span className="text-[11px] font-medium text-slate-400">
                {msg.role === "user" ? "You" : "CampusVoice Assistant"}
              </span>
              <span className="text-[10px] text-slate-500">{msg.timestamp}</span>
              {msg.language && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 uppercase font-mono">
                  {msg.language}
                </span>
              )}
            </div>

            <div
              className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed shadow-lg ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-tr-none"
                  : "bg-slate-900 border border-slate-800 text-slate-100 rounded-tl-none"
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.text}</div>

              {/* Citations & Escalations for Assistant answers */}
              {msg.role === "assistant" && msg.responseMeta && (
                <>
                  {msg.responseMeta.sources && msg.responseMeta.sources.length > 0 && (
                    <SourceChips sources={msg.responseMeta.sources} />
                  )}
                  {msg.responseMeta.ticket && (
                    <TicketBanner ticket={msg.responseMeta.ticket} />
                  )}

                  {/* Latency telemetry pill */}
                  <div className="mt-3 pt-2 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/80">
                    <span className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                      Verified Grounded Response
                    </span>
                    <span className="font-mono text-[10px]">
                      LLM: {msg.responseMeta.llm_ms}ms | Total: {msg.responseMeta.latency_ms}ms
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        ))
      )}

      {isLoading && (
        <div className="flex flex-col items-start">
          <div className="flex items-center gap-2 mb-1.5 px-1 text-[11px] text-slate-400">
            <span>CampusVoice Assistant</span>
            <span className="text-indigo-400 animate-pulse">Thinking...</span>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-none p-4 text-sm text-slate-300 flex items-center gap-2">
            <div className="flex gap-1.5">
              <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce"></span>
              <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.2s]"></span>
              <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.4s]"></span>
            </div>
            <span className="text-xs text-slate-400 ml-2">Consulting official college documents...</span>
          </div>
        </div>
      )}
    </div>
  );
};
