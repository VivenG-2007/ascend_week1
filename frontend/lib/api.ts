export interface SourceCitation {
  title: string;
  department?: string;
  source_date?: string;
  page_number?: number;
  document_id?: string;
  replaces?: string;
  superseded?: boolean;
}

export interface TicketInfo {
  id: string;
  question: string;
  department: string;
  status: string;
  summary?: string;
  created_at?: string;
  user_name?: string;
  user_email?: string;
  user_phone?: string;
}

export interface ChatResponse {
  transcript: string;
  language: string;
  answer_text: string;
  audio_base64?: string | null;
  audio_url?: string | null;
  sources: SourceCitation[];
  ticket?: TicketInfo | null;
  confidence?: number;
  latency_ms: number;
  stt_ms?: number;
  llm_ms: number;
  tts_ms?: number;
}

export interface HealthResponse {
  status: string;
  app: string;
  college_name: string;
  database: string;
  database_type?: string;
  supabase_storage?: string;
  chromadb_type?: string;
  chromadb_status?: string;
  timestamp: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string; // student, faculty, parent, visitor, admin
  department?: string;
  phone?: string;
  student_id?: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface UserTicket {
  id: string;
  question: string;
  department: string;
  status: string;
  resolution_note?: string;
  created_at?: string;
  resolved_at?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Health check failed with status: ${res.status}`);
  }
  return res.json();
}

export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  return res.json();
}

export async function registerUser(payload: {
  username: string;
  email: string;
  password: string;
  full_name: string;
  role?: string;
  department?: string;
  phone?: string;
  student_id?: string;
}): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Registration failed");
  }
  return res.json();
}

export async function fetchMyTickets(token: string): Promise<UserTicket[]> {
  const res = await fetch(`${API_BASE}/api/auth/my-tickets`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch user tickets");
  }
  return res.json();
}

export async function sendChatMessage(
  message: string,
  language: string = "en",
  sessionId?: string,
  token?: string,
  userInfo?: Partial<UserProfile>
): Promise<ChatResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      message,
      language,
      session_id: sessionId,
      user_id: userInfo?.id,
      user_name: userInfo?.full_name,
      user_email: userInfo?.email,
      user_phone: userInfo?.phone,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Chat request failed: ${res.status}`);
  }

  return res.json();
}
