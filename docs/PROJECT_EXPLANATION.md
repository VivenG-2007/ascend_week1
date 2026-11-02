# CampusVoice: Complete Technical & Architectural Deep Dive

CampusVoice is an enterprise-grade, bilingual (**English** and **Telugu**) conversational AI helpdesk built specifically for educational institutions. It solves a primary failure mode of generic LLMs in enterprise settings: **hallucination**. It enforces **strict, evidence-bounded retrieval**, meaning the system never answers from parametric memory for campus facts; every answer is backed by verifiable, uploaded circulars or structured relational records.

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Layer (Next.js 15)"]
        BrowserUI["Web Client / Chat Interface"]
        MicCapture["16kHz PCM WAV Audio Stream"]
    end

    subgraph API ["Gateway & Orchestration (FastAPI)"]
        Guard["Security & Prompt Injection Filters"]
        LangDetect["Language Resolver (EN / TE)"]
        Agent["Tool-Calling Agent Orchestrator"]
        OfflinePlan["Deterministic Fallback Planner"]
    end

    subgraph AI_Cloud ["Cognitive & Vector Services"]
        STT["Azure Speech STT (en-IN, te-IN)"]
        TTS["Azure Neural TTS (Neerja / Shruti)"]
        DocAI["Azure Document Intelligence (prebuilt-read)"]
        Embed["Azure Embeddings (text-embedding-3-small)"]
        LLM["Azure AI Foundry (GPT-4.1-mini / GPT-4o)"]
        Chroma["ChromaDB Cloud (Vector Store)"]
    end

    subgraph Storage_Layer ["Data Persistence"]
        DB[(Relational DB: SQLite / Supabase PostgreSQL)]
        SupaStorage["Supabase Storage (PDFs & Images)"]
    end

    MicCapture -->|Audio Payload| STT
    STT -->|Transcribed Text| Guard
    BrowserUI -->|Text Query| Guard
    Guard --> LangDetect
    LangDetect --> Agent

    Agent -->|Evaluate Question| LLM
    LLM -->|Tool Call: search_documents| Embed
    Embed --> Chroma
    LLM -->|Tool Call: timetable/faculty/exams| DB

    Agent -->|Threshold Checked (< 0.30)| DB
    Agent -->|Synthesize Speech| TTS
    TTS --> BrowserUI
    Agent -->|Answer + Citations| BrowserUI
```

---

## 2. Core Operational Pipelines

### A. Document Ingestion Pipeline (`app/services/ingestion.py`)
When an administrator uploads a circular, timetable, or notice via `/admin`:
1. **Tri-Validation Security Check**: Inspects declared MIME type, verifies physical magic bytes (`%PDF-`, `\xFF\xD8\xFF`, `\x89PNG`), and enforces file size limits.
2. **Object Storage**: The raw binary is uploaded to `Supabase Storage` under `documents/{doc_id}/{clean_name}`.
3. **Extraction & Adaptive Compression**:
   - For native PDFs: PyMuPDF extracts text directly. If a page has fewer than 25 characters, it is classified as a scanned raster.
   - For scanned PDFs & Images: Processed through `Azure Document Intelligence` (`prebuilt-read`).
   - If image size exceeds Azure's 4MB limit, an optimization hook automatically compresses it to JPEG while maintaining full character readability.
4. **Recursive Chunking**: Chunks pages with token overlap (`app/services/chunking.py`).
5. **Azure Vector Embedding & Indexing**:
   - Vectors are created via `text-embedding-3-small` (1536 dimensions).
   - Stored in `ChromaDB Cloud` alongside metadata (Document ID, Category, Department, Source Date, Page Number).

### B. Two-Tier Conversational Agent (`app/services/llm_agent.py`)
1. **Guard Evaluation**: Checks for malicious jailbreaks, system prompt extractions, and student private data requests (e.g., individual grades or phone numbers) before calling the LLM.
2. **Dynamic Tool Calling**: Powered by Azure OpenAI (`GPT-4.1-mini`), which selects between:
   - `search_documents`: Semantic search in ChromaDB.
   - `get_timetable`: Section-specific weekly class schedules.
   - `get_exam_schedule`: Department exam schedules.
   - `find_faculty`: Cabin numbers, office hours, and departments.
   - `get_events`: Campus seminars and workshops.
3. **Grounding & Threshold Verification**:
   - Vectors retrieved must exceed `SIMILARITY_THRESHOLD=0.30`.
   - If evidence is below threshold or absent, the model does not guess—it automatically generates an institutional support ticket (`CV-XXXXXXXX`) routed to the relevant department (Exam Cell, Accounts, Transport, Hostel, or General).

### C. Voice Pipeline (`app/services/stt.py` & `tts.py`)
- **Speech-to-Text (STT)**: Accepts 16kHz mono PCM WAV. For automatic language detection, runs parallel recognition across `en-IN` and `te-IN`, selecting the hypothesis with the highest acoustic confidence.
- **Text-to-Speech (TTS)**: Translates responses into neural speech using `en-IN-NeerjaNeural` (English) or `te-IN-ShrutiNeural` (Telugu).

---

## 3. Technology Stack & Component Mapping

| Layer | Technology | Primary Function |
| :--- | :--- | :--- |
| **Frontend** | Next.js 15 (App Router), React 19, Tailwind CSS | Voice push-to-talk UI, chat history, citation chips, admin document console |
| **Backend Framework** | FastAPI 0.115+, Uvicorn, Pydantic Settings | Async endpoints, typed configuration, token-bucket rate limiting |
| **Relational Database** | SQLAlchemy 2.0, Alembic, SQLite (Dev) / Supabase PG (Prod) | Documents metadata, chunks, tickets, chat logs, timetable, faculty records |
| **Object Storage** | Supabase Storage (S3 API) | Original uploaded PDFs and JPEG/PNG circular images |
| **Vector Database** | ChromaDB Cloud (`api.trychroma.com`) | Cosine similarity HNSW index for document chunk vectors |
| **LLM & Reasoning** | Azure AI Foundry (`gpt-4.1-mini` / `gpt-4o`) | Tool selection, answer phrasing, bilingual text generation |
| **Embeddings** | Azure OpenAI (`text-embedding-3-small`) | 1536-dimensional multilingual semantic vectors |
| **Speech Processing** | Azure AI Speech Service | Dual-dialect short-audio STT and neural SSML TTS |
| **OCR Engine** | Azure AI Document Intelligence | Document layout and optical text recognition on scanned circulars |

---

## 4. Key Engineering Controls

1. **Superseding Logic**: When an updated circular is uploaded, marking it with `supersedes_id` automatically de-weights and flags prior notices so students never receive outdated exam dates or fee deadlines.
2. **Strict Citation Transparency**: Chat responses embed clickable source citations with document titles, source dates, and exact page numbers.
3. **No-PII Privacy Enforcement**: Deterministic regex blocking prevents student mark disclosures, parent phone leaks, or sensitive credential displays.
4. **Fail-Safe Offline Mode**: If Azure credentials or internet connection are unavailable, the backend seamlessly falls back to lexical hashing (`HashEmbedder`) and a rule-based deterministic planner (`OfflinePlanner`).

