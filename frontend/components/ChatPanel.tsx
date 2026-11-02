"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ApiError, getHealth, sendChat, sendVoice, type ChatResponse, type LangChoice } from "@/lib/api";
import AudioPlayer from "./AudioPlayer";
import MicButton from "./MicButton";
import SourceChips from "./SourceChips";
import TicketBanner from "./TicketBanner";

type Turn = { role: "user"; text: string; lang?: string } | { role: "assistant"; data: ChatResponse; fresh: boolean };
type Status = "idle" | "thinking" | "speaking";

const SUGGESTIONS = [
  "When is the last date to pay semester fees?",
  "What is the first period for CSE-B on Monday?",
  "హాస్టల్ నియమాలు ఏమిటి?",
  "What events are happening this week?",
  "Where is Dr. Rohan Keshav's cabin?",
];
const LANGS: { value: LangChoice; label: string }[] = [{ value: "auto", label: "Auto" }, { value: "en", label: "English" }, { value: "te", label: "తెలుగు" }];
const WARNINGS: Record<string, string> = {
  tts_failed: "Audio could not be generated. The written answer is shown below.",
  tts_unavailable: "Spoken answers are not set up on this server.",
  llm_unavailable: "The AI model was unavailable, so a simpler answer is shown.",
};

export default function ChatPanel() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [lang, setLang] = useState<LangChoice>("auto");
  const [speakText, setSpeakText] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState<(() => void) | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [college, setCollege] = useState<string | null>(null);
  const [backendNote, setBackendNote] = useState<string | null>(null);
  const [voiceReady, setVoiceReady] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);
  const busy = status !== "idle";

  useEffect(() => {
    getHealth()
      .then((h) => { setCollege(h.college_name); setVoiceReady(!h.services?.speech?.startsWith("not configured")); if (h.status !== "ok") setBackendNote(h.detail); })
      .catch((e: ApiError) => setBackendNote(e.message));
  }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns, status]);

  function accept(data: ChatResponse, replaceLastUser: boolean) {
    setSessionId(data.session_id);
    setTurns((t) => {
      const base = replaceLastUser ? [...t.slice(0, -1), { role: "user" as const, text: data.transcript, lang: data.language }] : t;
      return [...base.map((x) => (x.role === "assistant" ? { ...x, fresh: false } : x)), { role: "assistant" as const, data, fresh: true }];
    });
    setStatus(data.audio_base64 ? "speaking" : "idle");
  }

  async function ask(question: string, addUser = true) {
    const q = question.trim();
    if (!q || busy) return;
    setError(null); setRetry(null); setStatus("thinking"); setInput("");
    if (addUser) setTurns((t) => [...t, { role: "user", text: q }]);
    try { accept(await sendChat({ question: q, session_id: sessionId, language: lang, speak: speakText }), false); }
    catch (e) { setStatus("idle"); setError(e instanceof ApiError ? e.message : "Something went wrong. Try again."); setRetry(() => () => void ask(q, false)); }
  }

  async function askVoice(wav: Blob) {
    setError(null); setRetry(null); setStatus("thinking");
    setTurns((t) => [...t, { role: "user", text: "🎤 …" }]);
    try { accept(await sendVoice(wav, lang, sessionId), true); }
    catch (e) {
      setTurns((t) => t.slice(0, -1)); setStatus("idle");
      setError((e instanceof ApiError ? e.message : "Something went wrong.") + " You can also type your question below.");
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 pb-6 pt-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">CampusVoice</h1>
          <p className="mt-1 text-sm text-ink/70">{college ?? "Official college information"}, in English and తెలుగు</p>
        </div>
        <div role="group" aria-label="Language" className="flex overflow-hidden rounded-md border border-ink/20 bg-white text-sm">
          {LANGS.map((l) => (
            <button key={l.value} type="button" onClick={() => setLang(l.value)} aria-pressed={lang === l.value} className={`px-3 py-1.5 ${lang === l.value ? "bg-ink text-white" : "hover:bg-mist"}`}>{l.label}</button>
          ))}
        </div>
      </header>

      {backendNote && <p role="alert" className="mb-4 rounded-md border border-amber-400 bg-amberwash px-3 py-2 text-sm text-amberink">{backendNote}</p>}

      <section aria-live="polite" aria-label="Conversation" className="flex-1 space-y-4">
        {turns.length === 0 && (
          <div>
            <p className="mb-3 text-ink/80">Ask about fees, timetables, faculty, rules, or events. Type below{voiceReady ? ", or tap the microphone" : ""}.</p>
            <ul className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <li key={s}><button type="button" onClick={() => void ask(s)} className="rounded-full border border-ink/20 bg-white px-3 py-1.5 text-left text-sm hover:border-teal-700">{s}</button></li>
              ))}
            </ul>
          </div>
        )}
        {turns.map((t, i) =>
          t.role === "user" ? (
            <div key={i} className="flex justify-end"><p className="max-w-[85%] rounded-lg bg-ink px-4 py-2.5 text-white" lang={t.lang}>{t.text}</p></div>
          ) : (
            <article key={i} className="max-w-[92%] rounded-lg border border-ink/10 bg-white px-4 py-3 shadow-sm" lang={t.data.language}>
              <p className="leading-relaxed">{t.data.answer_text}</p>
              <SourceChips sources={t.data.sources} />
              {t.data.ticket && <TicketBanner ticket={t.data.ticket} />}
              {t.data.warnings.filter((w) => WARNINGS[w]).map((w) => <p key={w} className="mt-2 text-xs text-amberink">{WARNINGS[w]}</p>)}
              {t.data.audio_base64 && <AudioPlayer base64={t.data.audio_base64} autoPlay={t.fresh} onPlayingChange={(p) => t.fresh && setStatus(p ? "speaking" : "idle")} />}
              <p className="mt-2 text-xs text-ink/50">
                {t.data.latency_ms} ms total
                {t.data.stt_ms != null && ` · speech-to-text ${t.data.stt_ms} ms`}{t.data.llm_ms != null && ` · agent ${t.data.llm_ms} ms`}{t.data.tts_ms != null && ` · text-to-speech ${t.data.tts_ms} ms`}
              </p>
            </article>
          ),
        )}
        {status === "thinking" && <p className="text-sm text-ink/60" role="status">Thinking…</p>}
        {error && (
          <div role="alert" className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error} {retry && <button type="button" className="font-semibold underline" onClick={retry}>Try again</button>}
          </div>
        )}
        <div ref={endRef} />
      </section>

      <div className="sticky bottom-0 mt-6 space-y-3 bg-mist pt-3">
        {voiceReady && <MicButton disabled={busy} onRecorded={(w) => void askVoice(w)} onError={setError} />}
        <p className="text-center text-xs font-medium text-ink/60" aria-live="polite">{status === "speaking" ? "Speaking…" : ""}</p>
        <form onSubmit={(e) => { e.preventDefault(); void ask(input); }} className="flex gap-2">
          <label htmlFor="q" className="sr-only">Your question</label>
          <input id="q" value={input} onChange={(e) => setInput(e.target.value)} maxLength={1000} autoComplete="off" placeholder="Type your question in English or తెలుగు" className="min-w-0 flex-1 rounded-md border border-ink/25 bg-white px-3 py-2.5" />
          <button type="submit" disabled={busy || !input.trim()} className="rounded-md bg-teal-700 px-5 py-2.5 font-semibold text-white hover:bg-teal-800 disabled:opacity-50">Ask</button>
        </form>
        <div className="flex items-center justify-between text-xs text-ink/60">
          {voiceReady ? <label className="flex items-center gap-1.5"><input type="checkbox" checked={speakText} onChange={(e) => setSpeakText(e.target.checked)} /> Read typed answers aloud</label> : <span>Voice is not set up on this server. Text chat works.</span>}
          <Link href="/admin" className="underline">Staff login</Link>
        </div>
      </div>
    </div>
  );
}
