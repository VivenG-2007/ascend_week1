# Deployment guide (NOT yet performed, see "What was verified" in docs/TEST_REPORT.md)

Targets: **Vercel** (frontend), **Render or Azure** (backend), **Supabase** (Postgres + Storage), **Azure** (AI Foundry + Speech).

## 1. Supabase
1. Create a project. Copy a Postgres connection string (Project Settings → Database). Free-tier direct connections can be IPv6-only; if Render cannot connect, use the **session pooler** string. Prefix must be `postgresql://`.
2. Storage → create a **private** bucket `campusvoice-documents`. Copy the project URL and the **service_role** key (backend only).
3. From your laptop: set `DATABASE_URL` and run `cd backend && alembic upgrade head && python -m app.db.seed`. Confirm the tables exist in the Table Editor.

## 2. Azure
1. AI Foundry: deploy a chat model that supports tool calling (the plan is to evaluate GPT-4.1 against a smaller sibling such as GPT-4.1 mini if they are available in your region/subscription). Set `AZURE_AI_FOUNDRY_ENDPOINT`, `_API_KEY`, `_DEPLOYMENT` (the *deployment name*), and check `_API_VERSION` against your resource.
2. Speech: create a Speech resource in a region that offers Telugu STT and neural TTS; set `AZURE_SPEECH_KEY/REGION`. Test `te-IN-ShrutiNeural` vs `te-IN-MohanNeural` and pick one.

## 3. Backend (Docker image in `backend/Dockerfile`)
- **Render:** New Web Service → Docker → root directory `backend`. Add every secret from `.env.example` in the dashboard (never in git). Set `APP_ENV=production`, `FRONTEND_ORIGIN=https://<your-vercel-domain>`, `DATABASE_URL`, `JWT_SECRET`, `ADMIN_PASSWORD_HASH`, Supabase and Azure variables, `EMBEDDING_PROVIDER=e5`.
- **Chroma persistence:** the container disk is ephemeral unless you attach a persistent disk (paid on Render, Azure Files on Azure; check your plan). If you cannot, leave `AUTO_REINDEX=true`: on every start the backend rebuilds missing vectors from the chunks stored in Postgres (it re-embeds, so allow extra startup time). Originals persist in Supabase Storage either way.
- Memory: PyTorch + the e5 model need roughly 1 GB RAM; very small free instances may not fit. `EMBEDDING_MODEL` can be changed, but then run `python -m app.scripts.reindex --full`.
- Health check path: `/health` (503 until the DB and schema are ready).
- Seed sample circulars (optional): `python -m app.scripts.seed_documents` (uses the samples in `data/sample_circulars`).

## 4. Frontend (Vercel)
Root directory `frontend`, framework Next.js, env `NEXT_PUBLIC_API_URL=https://<backend-host>`. Microphone access requires **HTTPS** (Vercel provides it).

## 5. Pre-demo checklist
- [ ] `GET <backend>/health` → `status: ok`, services show `azure` and `configured`.
- [ ] Admin login works; a PDF and a phone photo of a notice upload, show OCR warnings if any, and become searchable.
- [ ] Restart the backend; a previously uploaded document is still answerable (checks Chroma/auto-reindex).
- [ ] Text question, English voice question, Telugu voice question on the **deployed** site, including on a phone.
- [ ] Browser DevTools → Network/Sources: no keys in any response or bundle (`NEXT_PUBLIC_*` must only hold the API URL).
- [ ] Run `python -m app.scripts.run_scenarios --base <backend> ...` and keep the generated `docs/TEST_SCENARIOS.md`.
- [ ] Tune the threshold: `python -m app.scripts.tune_threshold` against the real model, then set `SIMILARITY_THRESHOLD`.

## 6. Backup demo path
1. **Text-only:** works with no Azure at all (rule-based agent). Set `AGENT_MODE=offline`, leave Speech empty; the UI hides the mic automatically and says voice is not set up.
2. **Local laptop:** follow README "Run locally" with `EMBEDDING_PROVIDER=hash` (no model download, works offline; lexical matching only, no cross-language search, so prepare English/Telugu demo questions that share words with the documents).
3. Keep a short screen recording of a successful voice run in case venue Wi-Fi blocks Azure.
