export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type Lang = "en" | "te";
export type LangChoice = "auto" | Lang;

export interface SourceRef {
  document_id: string;
  title: string;
  source_date: string | null;
  page_number: number | null;
  department: string | null;
  score: number | null;
  superseded_note: string | null;
}
export interface TicketInfo { id: string; department: string; status: string; summary: string | null }
export interface ChatResponse {
  session_id: string;
  transcript: string;
  language: Lang;
  answer_text: string;
  audio_base64: string | null;
  sources: SourceRef[];
  ticket: TicketInfo | null;
  retrieval: { decision: string | null; top_score: number | null } | null;
  latency_ms: number;
  stt_ms: number | null;
  llm_ms: number | null;
  tts_ms: number | null;
  warnings: string[];
}
export interface Health { status: "ok" | "degraded"; college_name: string; detail: string | null; services: Record<string, string> }

export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); }
}

export const TOKEN_KEY = "cv_admin_token";
const getToken = () => (typeof window === "undefined" ? null : window.sessionStorage.getItem(TOKEN_KEY));

async function request<T>(path: string, init: RequestInit = {}, opts: { timeoutMs?: number; auth?: boolean } = {}): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), opts.timeoutMs ?? 30000);
  const headers = new Headers(init.headers);
  if (opts.auth) { const t = getToken(); if (t) headers.set("Authorization", `Bearer ${t}`); }
  try {
    const res = await fetch(`${API_URL}${path}`, { ...init, headers, signal: ctrl.signal });
    if (!res.ok) {
      let detail = "The server could not process that request.";
      try {
        const body = await res.json();
        if (typeof body.detail === "string") detail = body.detail;
        else if (Array.isArray(body.detail) && body.detail[0]?.msg) detail = String(body.detail[0].msg);
      } catch { /* non-JSON error body */ }
      throw new ApiError(detail, res.status);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") throw new ApiError("The request timed out. Try again.");
    throw new ApiError("Cannot reach the CampusVoice server. Check that the backend is running.");
  } finally {
    clearTimeout(timer);
  }
}

const json = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---------------------------------------------------------------- public
export const getHealth = () => request<Health>("/health", {}, { timeoutMs: 8000 });
export const sendChat = (body: { question: string; session_id?: string; language: LangChoice; speak?: boolean }) =>
  request<ChatResponse>("/api/chat", json(body));
export function sendVoice(wav: Blob, language: LangChoice, sessionId?: string) {
  const f = new FormData();
  f.append("audio", wav, "recording.wav");
  f.append("language", language);
  f.append("speak", "true");
  if (sessionId) f.append("session_id", sessionId);
  return request<ChatResponse>("/api/voice", { method: "POST", body: f }, { timeoutMs: 45000 });
}
export const documentFileUrl = (id: string, page?: number | null) => `${API_URL}/api/documents/${id}/file${page ? `#page=${page}` : ""}`;

// ----------------------------------------------------------------- admin
export interface AdminDocument {
  id: string; title: string; category: string; department: string; source_date: string; language: string | null;
  processing_status: string; extraction_status: string; original_filename: string | null; page_count: number; ocr_pages: number;
  chunk_count: number; warnings: string[]; error_message: string | null; supersedes_id: string | null; superseded_by_id: string | null; created_at: string;
}
export interface UploadReport { document: AdminDocument; pages: number; ocr_pages: number; chunks: number; warnings: string[]; error: string | null; duration_ms: number }
export interface AdminTicket {
  id: string; question: string; summary: string | null; transcript: string | null; language: string; department: string; status: string;
  resolution_note: string | null; created_at: string; updated_at: string; resolved_at: string | null;
}
export interface Analytics {
  totals: { questions: number; tickets: number; documents: number };
  top_questions: { question: string; count: number }[];
  unanswered_questions: { ticket_id: string; question: string; department: string; status: string; created_at: string }[];
  tickets_by_status: Record<string, number>; tickets_by_department: Record<string, number>; language_usage: Record<string, number>;
  latency: Record<string, { count: number; average_ms: number | null; median_ms: number | null }>;
  retrieval_confidence: { buckets: { range: string; count: number }[]; decisions: Record<string, number> };
  document_failures: { id: string; title: string; error: string | null; created_at: string }[];
}
export const DEPARTMENTS = ["Exam Cell", "Accounts", "Hostel", "Transport", "Library", "Admissions", "General"];

export async function adminLogin(username: string, password: string) {
  const r = await request<{ access_token: string }>("/api/admin/login", json({ username, password }));
  window.sessionStorage.setItem(TOKEN_KEY, r.access_token);
}
export const adminLogout = () => window.sessionStorage.removeItem(TOKEN_KEY);
export const hasToken = () => !!getToken();
export const listDocuments = () => request<AdminDocument[]>("/api/admin/documents", {}, { auth: true });
export const uploadDocument = (form: FormData) => request<UploadReport>("/api/admin/documents", { method: "POST", body: form }, { auth: true, timeoutMs: 120000 });
export const listTickets = (department?: string, status?: string) => {
  const q = new URLSearchParams(); if (department) q.set("department", department); if (status) q.set("status", status);
  return request<{ total: number; items: AdminTicket[] }>(`/api/admin/tickets?${q}`, {}, { auth: true });
};
export const patchTicket = (id: string, body: { status?: string; resolution_note?: string }) =>
  request<AdminTicket>(`/api/admin/tickets/${id}`, { ...json(body), method: "PATCH" }, { auth: true });
export const getAnalytics = () => request<Analytics>("/api/admin/analytics", {}, { auth: true });
