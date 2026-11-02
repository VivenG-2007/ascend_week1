"use client";

import { useEffect, useRef, useState } from "react";

export default function AudioPlayer({ base64, autoPlay, onPlayingChange }: { base64: string; autoPlay?: boolean; onPlayingChange?: (p: boolean) => void }) {
  const ref = useRef<HTMLAudioElement>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [blocked, setBlocked] = useState(false);

  useEffect(() => {
    const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
    const u = URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" }));
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [base64]);

  useEffect(() => {
    if (url && autoPlay) ref.current?.play().catch(() => setBlocked(true)); // browsers may block autoplay
  }, [url, autoPlay]);

  if (!url) return null;
  return (
    <div className="mt-2">
      <audio ref={ref} src={url} controls className="h-9 w-full max-w-xs" aria-label="Spoken answer"
        onPlay={() => { setBlocked(false); onPlayingChange?.(true); }} onPause={() => onPlayingChange?.(false)} onEnded={() => onPlayingChange?.(false)} />
      {blocked && <p className="text-xs text-ink/60">Press play to hear the answer.</p>}
    </div>
  );
}
