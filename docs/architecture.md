# Architecture

```
Browser (Next.js)                         FastAPI backend                                   Services
 ├ text  ── POST /api/chat ─────────────► chat router ─┐
 └ voice ── POST /api/voice (WAV) ──────► voice router ┤  validate audio ─► Azure STT (REST)
                                                       ▼
                                              chat_service.handle_turn ──► AgentService
                                                       │                    ├ guards (injection / personal data)  [Python]
                                                       │                    ├ scope: college | off-topic | unknown [Python]
                                                       │                    ├ tool loop (Azure AI Foundry) OR rule-based planner
                                                       │                    │    search_documents ─► RetrievalService ─► ChromaDB (vectors)
                                                       │                    │                         └► chunks/documents (Supabase PG)
                                                       │                    │    get_timetable / get_exam_schedule / find_faculty / get_events ─► Supabase PG
                                                       │                    ├ evidence gate (similarity ≥ threshold, or structured "found") [Python]
                                                       │                    └ escalation: ticket + department routing + dedupe [Python]
                                                       ├► Azure TTS (REST, voice by language)
                                                       └► messages table (text, sources, metrics, stt/llm/tts/total ms)
Admin UI ── JWT ─► /api/admin/*  documents (upload→ingest), tickets, analytics
Ingestion: validate (MIME + signature + size) → store original (Supabase Storage / local) → PDF text or OCR (Tesseract)
           → clean → chunk (~500 tokens, overlap, page-aware) → embed (multilingual-e5) → Postgres (pages, chunks) + Chroma (vectors)
           → `processed` only if every step succeeded
```

## Responsibilities
| Store | Holds | Why |
|---|---|---|
| Supabase/Postgres | documents, pages, **canonical chunk text**, faculty, timetable, exams, events, tickets, messages | source of truth; auditable |
| ChromaDB | vectors + chunk text + metadata (`document_id`, page, title, department, source_date) | semantic search only; rebuildable from Postgres (`python -m app.scripts.reindex`, or automatically at startup) |
| Supabase Storage | original PDFs/images | sources a user can open from a citation chip |

## Key decisions
- **The backend enforces the rules, not the prompt.** Guards, scope, the evidence gate, ticket creation, department routing, dedupe and the list of cited sources are all Python. When evidence is insufficient the reply is a fixed template, so model text can never become an "official fact". Tool arguments from the model are validated; a model-requested ticket is rejected if evidence exists.
- **Similarity semantics verified:** Chroma collections use cosine space; `distance = 1 − cosine similarity` (checked in code and in a test). Scores reported to users/analytics are similarities (higher is better). The default threshold 0.55 is a starting point and must be tuned on the real embedding model.
- **Supersession:** `documents.supersedes_id`. Retrieval drops hits from a document that has a newer processed replacement, pulls the replacement's chunks, and attaches a "replaces …" note that is shown to the user.
- **Voice format:** the browser records with MediaRecorder, then converts to 16 kHz mono WAV client-side (Web Audio), so the server needs no ffmpeg for the normal path. Other formats are converted with ffmpeg only if it is installed.
- **STT language:** the REST short-audio API recognises one locale per request; for `auto` the audio is sent for en-IN and te-IN in parallel and the more confident result wins.
- **Reliability:** text chat never depends on speech; TTS failure still returns the written answer; LLM failure falls back to the rule-based planner with a visible warning.
- **Sync endpoints** (`def`) run in FastAPI's threadpool: right for blocking SQLAlchemy/OCR/embedding work without stalling the event loop. Heavy services load once at startup.
- **No Redis:** short conversation memory is the last 6 messages of the session from the `messages` table. The abuse limiter is in-process.
