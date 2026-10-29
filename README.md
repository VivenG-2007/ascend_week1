# CampusVoice (క్యాంపస్‌వాయిస్)

> **Multilingual Voice AI Helpdesk for College Information**  
> *ASCEND Week-1 | Voice AI & Conversational Agents*

CampusVoice is a production-minded, demo-ready multilingual conversational voice helpdesk for colleges. It empowers students, parents, faculty, and visitors to query official college information in **English** and **Telugu (తెలుగు)** with strict document grounding, citations, and deterministic escalation.

---

## Architecture Overview (Phase 1 Scaffold)

- **Frontend**: Next.js App Router, React 19, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Pydantic, SQLAlchemy
- **Database**: SQLite local fallback / Supabase PostgreSQL compatible ORM models
- **Testing**: PyTest with automated coverage of `/health` and `/api/chat`

---

## Quick Start (Windows PowerShell)

### 1. Prerequisites
- Python 3.11+ (Tested on Python 3.11.7)
- Node.js 18+ (Tested on Node.js v24.12.0)

### 2. Backend Setup & Run
```powershell
# Open terminal in project root
python -m pip install -r backend/requirements.txt

# Run automated tests
python -m pytest

# Start FastAPI backend server
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```
The backend API will be live at `http://localhost:8000`.  
Interactive Swagger documentation: `http://localhost:8000/docs`.

### 3. Frontend Setup & Run
```powershell
# In a second PowerShell terminal
cd frontend
npm run dev
```
The frontend UI will be live at `http://localhost:3000`.

---

## Environment Variables (.env)
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Key variables for Phase 1:
- `COLLEGE_NAME`: Title of the institution (e.g. `"Vignana Institute of Technology & Science"`)
- `DATABASE_URL`: `"sqlite:///./campusvoice.db"`
- `FRONTEND_ORIGIN`: `"http://localhost:3000"`

---

## Phase Status
- [x] **Phase 1 — Scaffold**: Complete (FastAPI, SQLite fallback, ORM models, seed data, /health, /api/chat stub, Next.js UI)
- [ ] **Phase 2 — Voice**: Push-to-talk, Azure AI Speech STT & TTS, audio playback
- [ ] **Phase 3 — Documents, OCR, and RAG**: PDF/Image ingestion, OCR, chunking, multilingual embeddings, ChromaDB
- [ ] **Phase 4 — Agent Tools & Escalation**: Structured DB tools, Telugu LLM grounding, deterministic ticket creation
- [ ] **Phase 5 — Admin**: JWT authentication, document uploads, ticket resolution, analytics
- [ ] **Phase 6 — Hardening & Delivery**: Full test suite, benchmarks, deployment configuration
