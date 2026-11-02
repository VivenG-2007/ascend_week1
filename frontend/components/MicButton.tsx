"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { blobToWav16k, micErrorMessage, pickRecorderMime } from "@/lib/audio";

type State = "idle" | "requesting" | "recording" | "processing";

export default function MicButton({ disabled, maxSeconds = 30, onRecorded, onError }: {
  disabled?: boolean; maxSeconds?: number; onRecorded: (wav: Blob) => void; onError: (message: string) => void;
}) {
  const [state, setState] = useState<State>("idle");
  const [seconds, setSeconds] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const cancelled = useRef(false);

  const cleanup = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }, []);
  useEffect(() => cleanup, [cleanup]);

  async function start() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onError("Voice recording is not supported in this browser. You can type your question instead.");
      return;
    }
    setState("requesting");
    cancelled.current = false;
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
      stream.current = s;
      const mime = pickRecorderMime();
      const rec = new MediaRecorder(s, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      rec.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data); };
      rec.onstop = async () => {
        cleanup();
        if (cancelled.current) { setState("idle"); return; }
        setState("processing");
        try {
          const wav = await blobToWav16k(new Blob(chunks.current, { type: rec.mimeType || "audio/webm" }));
          setState("idle");
          onRecorded(wav);
        } catch {
          setState("idle");
          onError("That recording could not be processed. Please try again or type your question.");
        }
      };
      recorder.current = rec;
      rec.start();
      setSeconds(0);
      setState("recording");
      timer.current = setInterval(() => {
        setSeconds((n) => {
          if (n + 1 >= maxSeconds) stop();
          return n + 1;
        });
      }, 1000);
    } catch (e) {
      cleanup();
      setState("idle");
      onError(micErrorMessage(e));
    }
  }

  function stop() { if (recorder.current?.state === "recording") recorder.current.stop(); }
  function cancel() { cancelled.current = true; stop(); }

  const recording = state === "recording";
  return (
    <div className="flex flex-col items-center gap-2">
      <button type="button" onClick={recording ? stop : start} disabled={disabled || state === "requesting" || state === "processing"}
        aria-pressed={recording} aria-label={recording ? "Stop recording and send" : "Start recording your question"}
        className={`flex h-20 w-20 items-center justify-center rounded-full text-white shadow-md transition-colors disabled:opacity-50 ${recording ? "bg-red-600 hover:bg-red-700" : "bg-teal-700 hover:bg-teal-800"}`}>
        {recording ? (
          <svg width="28" height="28" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" /></svg>
        ) : (
          <svg width="30" height="30" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
          </svg>
        )}
      </button>
      <p className="min-h-5 text-sm text-ink/70" role="status">
        {state === "requesting" && "Waiting for microphone permission…"}
        {recording && `Listening… ${seconds}s / ${maxSeconds}s`}
        {state === "processing" && "Preparing audio…"}
        {state === "idle" && "Tap to speak"}
      </p>
      {recording && <button type="button" onClick={cancel} className="text-sm text-ink/70 underline">Cancel</button>}
    </div>
  );
}
