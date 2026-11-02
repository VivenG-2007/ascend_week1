# Test report

Date: 2026-11-01. Environment: Linux sandbox, Python 3.12.3, Node 22, Tesseract 5 with `eng` and `tel`, ChromaDB 1.5, no internet access to Azure or Hugging Face.

## Automated results (real, from this build)
| Check | Result |
|---|---|
| `python -m pytest -q` (backend) | **189 passed, 0 failed** (~20 s) |
| `npm run typecheck` | passed |
| `npm run build` (Next.js production build) | passed, 6 routes |
| `alembic upgrade head` / `downgrade base` on SQLite | passed |
| `python -m app.scripts.run_scenarios` against a live uvicorn (SQLite, real ChromaDB, **real Tesseract**, offline agent) | **14 passed, 0 failed, 2 not run**; see `docs/TEST_SCENARIOS.md` |

The first scenario run found a real defect (the offline answer picked the wrong sentences from a freshly uploaded circular); it was fixed and the run repeated. 

### What the 189 tests cover
health; chunking and page metadata; text cleaning; PDF/scanned-PDF/image ingestion (fake OCR plus one real-Tesseract test); unreadable, blank, corrupt, duplicate and oversized files; indexing-failure rollback; unsafe filenames; ChromaDB indexing/retrieval, score semantics, department filter, dedupe, revised-circular precedence; reindex from Postgres rows; structured tools (timetable/exams/faculty/events); local and Supabase storage (mocked HTTP); agent: grounded answers with citations, escalation gate, off-topic refusal without tickets, ticket routing and de-duplication, ambiguity handling, injection and personal-data refusal, LLM tool loop with a **mocked** LLM, model hallucination discarded, model-requested tickets rejected when evidence exists, document-borne injection fenced; Azure STT/TTS clients against mocked HTTP; audio validation; voice endpoint (happy path, Telugu, silence, STT/TTS failures, bad audio, unconfigured speech); admin auth (401 on every route, expired/forged/`alg:none` tokens, 403 role check, login rate limit); admin upload/patch/tickets/analytics; settings validation; rate limiting; CORS; error bodies.

## NOT verified (be honest about these in the demo)
1. **Azure AI Foundry LLM**: the client uses the `openai` SDK's Azure client and standard tool-calling; never called for real. Deployment availability, API version and tool-calling support must be checked on your resource.
2. **Azure Speech STT/TTS**: implemented against the documented REST endpoints and checked with mocked HTTP only. **Telugu and Telugu-English code-mixed accuracy has not been measured**; please record real clips on day one.
3. **Real embeddings (`multilingual-e5-small`)**: could not be downloaded here. All retrieval tests use the deterministic `hash` embedder, which has **no cross-language ability**. English-question-against-Telugu-document and vice versa are therefore untested, and `SIMILARITY_THRESHOLD=0.55` is an untuned starting point. A labelled set is in `data/validation_questions.json` and `python -m app.scripts.tune_threshold` measures it. With the hash embedder the tuner reports overlapping score ranges, as expected.
4. **Browser voice path** (MediaRecorder, microphone permission, client-side WAV conversion, autoplay, mobile layouts): compiled and type-checked only; no browser was available. Scenarios 10 and 14 are NOT RUN.
5. **Supabase** (Postgres, Storage), **Docker build**, **Render/Vercel deployment**: not run. The migration was tested on SQLite only; run `alembic upgrade head` against Supabase early.
6. **Latency**: the 20-query median measured here (~10 ms) is offline mode with no network calls and says nothing about the 6-second target with Azure.
7. **Telugu OCR on real photographed notices**: only synthetic rendered text was OCR'd (English). Telugu PDFs with a text layer work; Telugu OCR quality is untested.
8. **Accessibility** beyond labels/roles/focus styles was not audited with a screen reader.

## Known limitations
- A similarity score only measures topical closeness: a question that merely shares words with a circular (e.g. "late fee waiver for X") can be answered from it. The citation is always shown so users can judge; tune the threshold and add more specific documents to reduce this.
- Offline answers are extractive (best-matching sentences), not generated prose.
- Rate limiting is per process; admin is a single configured account.
- Structured data answers cite "Timetable CSE-B" etc. without a date because those tables carry none.
