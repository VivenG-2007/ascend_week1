"use client";

import React, { useState, useEffect } from "react";
import { fetchHealth, sendChatMessage, ChatResponse, UserProfile } from "@/lib/api";
import { ChatPanel, MessageItem } from "@/components/ChatPanel";
import { AuthModal } from "@/components/AuthModal";
import { MyTicketsModal } from "@/components/MyTicketsModal";

export default function HomePage() {
  const [collegeName, setCollegeName] = useState<string>("Geethanjali College of Engineering and Technology");
  const [healthStatus, setHealthStatus] = useState<"checking" | "connected" | "error">("checking");
  const [selectedLang, setSelectedLang] = useState<"en" | "te">("en");
  const [inputMessage, setInputMessage] = useState<string>("");
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Suggested questions in English and Telugu
  const suggestedQuestions = selectedLang === "te"
    ? [
        "ఫీజు చెల్లించడానికి చివరి తేదీ ఎప్పుడు?",
        "సోమవారం CSE-B మొదటి పీరియడ్ ఏమిటి?",
        "డాక్టర్ K.S. రావు క్యాబిన్ ఎక్కడ ఉంది?",
        "హాస్టల్ మరియు బస్సు నిబంధనలు ఏమిటి?",
      ]
    : [
        "When is the last date to pay semester fees?",
        "What is the first period for CSE-B on Monday?",
        "Where is Dr. K.S. Rao's cabin?",
        "What are the hostel curfew timings?",
      ];

  const [teluguVoice, setTeluguVoice] = useState<string>("te-IN-ShrutiNeural");
  const [cloudInfo, setCloudInfo] = useState<{ dbType?: string; chromaType?: string }>({});

  // Auth & Tickets state
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isTicketsOpen, setIsTicketsOpen] = useState(false);

  // Restore user session from localStorage
  useEffect(() => {
    try {
      const storedToken = localStorage.getItem("cv_token");
      const storedUser = localStorage.getItem("cv_user");
      if (storedToken && storedUser) {
        setAuthToken(storedToken);
        setCurrentUser(JSON.parse(storedUser));
      }
    } catch (e) {
      console.warn("Could not load stored user session:", e);
    }
  }, []);

  const handleLogout = () => {
    setAuthToken(null);
    setCurrentUser(null);
    localStorage.removeItem("cv_token");
    localStorage.removeItem("cv_user");
  };

  // Check health and obtain college name on load
  useEffect(() => {
    async function checkBackendHealth() {
      try {
        const health = await fetchHealth();
        if (health.status === "ok") {
          setHealthStatus("connected");
          if (health.college_name) setCollegeName(health.college_name);
          setCloudInfo({
            dbType: health.database_type,
            chromaType: health.chromadb_type
          });
        } else {
          setHealthStatus("error");
        }
      } catch (err) {
        console.warn("Backend not reachable yet:", err);
        setHealthStatus("error");
      }
    }
    checkBackendHealth();
  }, []);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || isLoading) return;

    setErrorMessage(null);
    setInputMessage("");

    const userMessage: MessageItem = {
      id: `msg-${Date.now()}-user`,
      role: "user",
      text,
      language: selectedLang,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendChatMessage(
        text,
        selectedLang,
        undefined,
        authToken || undefined,
        currentUser || undefined
      );
      const assistantMessage: MessageItem = {
        id: `msg-${Date.now()}-bot`,
        role: "assistant",
        text: response.answer_text,
        language: response.language,
        responseMeta: response,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to get response from server.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-20 px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white font-bold text-xl">
            CV
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-white flex items-center gap-2">
                CampusVoice
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Multilingual Voice AI
                </span>
              </h1>
            </div>
            <p className="text-xs text-slate-400">{collegeName}</p>
          </div>
        </div>

        {/* Right Controls: Health Pill & Language Toggle */}
        <div className="flex items-center gap-3">
          {/* Cloud Status Badges */}
          <div className="hidden sm:flex items-center gap-2">
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                healthStatus === "connected"
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                  : healthStatus === "checking"
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                  : "bg-rose-500/10 border-rose-500/30 text-rose-400"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  healthStatus === "connected"
                    ? "bg-emerald-400 animate-pulse"
                    : healthStatus === "checking"
                    ? "bg-amber-400"
                    : "bg-rose-400"
                }`}
              ></span>
              <span>{cloudInfo.dbType || "DB Connected"}</span>
            </div>

            {cloudInfo.chromaType && (
              <span className="hidden md:inline-block px-2 py-1 rounded-full text-[11px] bg-slate-800/80 border border-slate-700 text-slate-300 font-mono">
                {cloudInfo.chromaType}
              </span>
            )}
          </div>

          {/* Telugu Neural Voice Selector */}
          {selectedLang === "te" && (
            <div className="hidden sm:flex items-center gap-1.5 bg-slate-800/90 px-2.5 py-1 rounded-lg border border-slate-700/70 text-xs">
              <span className="text-slate-400">స్వరం:</span>
              <select
                value={teluguVoice}
                onChange={(e) => setTeluguVoice(e.target.value)}
                className="bg-slate-900 text-indigo-300 text-xs rounded px-2 py-0.5 border border-slate-700 outline-none cursor-pointer hover:border-indigo-500/50"
              >
                <option value="te-IN-ShrutiNeural">Shruti (Female - సహజమైన స్వరం)</option>
                <option value="te-IN-MohanNeural">Mohan (Male - అధికారిక స్వరం)</option>
              </select>
            </div>
          )}

          {/* Language Toggle */}
          <div className="flex bg-slate-800/80 p-0.5 rounded-lg border border-slate-700/60 text-xs">
            <button
              onClick={() => setSelectedLang("en")}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                selectedLang === "en"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              English
            </button>
            <button
              onClick={() => setSelectedLang("te")}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                selectedLang === "te"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              తెలుగు
            </button>
          </div>

          {/* User Auth & Tickets Actions */}
          {currentUser ? (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsTicketsOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/15 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-600/25 text-xs font-medium transition"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
                </svg>
                <span>My Tickets</span>
              </button>

              <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/90 border border-slate-700 text-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span className="text-white font-medium max-w-[110px] truncate">{currentUser.full_name}</span>
                <span className="text-[10px] text-indigo-300 uppercase px-1 rounded bg-slate-900 font-mono">
                  {currentUser.role}
                </span>
              </div>

              <button
                onClick={handleLogout}
                title="Sign out"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          ) : (
            <button
              onClick={() => setIsAuthOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 border border-indigo-500 text-white text-xs font-medium transition shadow-md shadow-indigo-600/20"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span>Login / Sign Up</span>
            </button>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto flex flex-col justify-between overflow-hidden">
        {/* Error notification banner */}
        {errorMessage && (
          <div className="mx-4 mt-3 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-rose-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-slate-400 hover:text-white underline text-xs ml-4"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Chat History Panel */}
        <ChatPanel messages={messages} isLoading={isLoading} />

        {/* Suggested Queries */}
        {messages.length === 0 && (
          <div className="px-4 pb-2">
            <div className="text-xs text-slate-500 font-medium mb-2">Suggested Inquiries:</div>
            <div className="flex flex-wrap gap-2">
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(q)}
                  className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-indigo-500/40 text-slate-300 hover:text-indigo-200 transition-all text-left"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Bar & Large Mic Placeholder */}
        <div className="p-4 sm:p-6 bg-slate-900/40 border-t border-slate-800/80 backdrop-blur-md">
          <div className="flex items-center gap-3">
            {/* Push-to-Talk Mic Button Ready for Phase 2 */}
            <div className="relative group">
              <button
                type="button"
                disabled
                title="Voice Push-To-Talk arrives in Phase 2"
                className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400/60 cursor-not-allowed transition-all"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </button>
              <div className="absolute -top-8 left-0 hidden group-hover:block bg-slate-800 text-[10px] text-indigo-300 py-1 px-2 rounded whitespace-nowrap border border-slate-700 shadow-md">
                Voice push-to-talk in Phase 2
              </div>
            </div>

            {/* Text Input */}
            <div className="flex-1 relative">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  selectedLang === "te"
                    ? "కళాశాల సమాచారం గురించి అడగండి (ఉదా: ఫీజు వివరాలు, తరగతి సమయాలు)..."
                    : "Ask about college fees, timetable, faculty cabins, bus rules..."
                }
                disabled={isLoading}
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none transition-all shadow-inner"
              />
            </div>

            {/* Send Button */}
            <button
              onClick={() => handleSendMessage()}
              disabled={isLoading || !inputMessage.trim()}
              className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm text-white transition-all shadow-md shadow-indigo-600/20 flex items-center gap-2"
            >
              <span>Send</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
          <div className="flex justify-between items-center mt-2 px-1 text-[11px] text-slate-500">
            <span>Powered by official document grounding & structured database</span>
            <span className="font-mono">Phase 1: Connected</span>
          </div>
        </div>
      </main>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onSuccess={(token, user) => {
          setAuthToken(token);
          setCurrentUser(user);
          try {
            localStorage.setItem("cv_token", token);
            localStorage.setItem("cv_user", JSON.stringify(user));
          } catch (e) {
            console.warn("Storage write error", e);
          }
        }}
      />

      {/* User Tickets Modal */}
      <MyTicketsModal
        isOpen={isTicketsOpen}
        onClose={() => setIsTicketsOpen(false)}
        token={authToken}
        userName={currentUser?.full_name || "User"}
      />
    </div>
  );
}
