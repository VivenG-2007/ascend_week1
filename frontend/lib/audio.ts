/** Browser-side audio helpers. MediaRecorder produces WebM/Opus (or MP4 on Safari); the speech service needs
 *  16 kHz mono PCM WAV, so we decode and re-encode in the browser. No server-side ffmpeg is required. */

export function pickRecorderMime(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"].find((m) => MediaRecorder.isTypeSupported(m));
}

export async function blobToWav16k(blob: Blob): Promise<Blob> {
  const AC: typeof AudioContext = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AC();
  try {
    const decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
    const rate = 16000;
    const offline = new OfflineAudioContext(1, Math.max(1, Math.ceil(decoded.duration * rate)), rate);
    const src = offline.createBufferSource();
    src.buffer = decoded;
    src.connect(offline.destination);
    src.start();
    const rendered = await offline.startRendering();
    return encodeWav(rendered.getChannelData(0), rate);
  } finally {
    void ctx.close();
  }
}

function encodeWav(samples: Float32Array, rate: number): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const w = (o: number, s: string) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  w(36, "data"); v.setUint32(40, samples.length * 2, true);
  samples.forEach((s, i) => { const c = Math.max(-1, Math.min(1, s)); v.setInt16(44 + i * 2, c < 0 ? c * 0x8000 : c * 0x7fff, true); });
  return new Blob([buf], { type: "audio/wav" });
}

export function micErrorMessage(err: unknown): string {
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") return "Microphone access was blocked. Allow the microphone in your browser, or type your question instead.";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "No microphone was found. You can type your question instead.";
  if (name === "NotReadableError") return "Your microphone is being used by another app. Close it, or type your question.";
  return "Could not start recording. You can type your question instead.";
}
