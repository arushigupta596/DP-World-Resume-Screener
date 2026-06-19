# DP World CV Screener

Full-stack CV scoring and matching demo for DP World's Market Research Analyst role (Dubai).

Recruiters paste/upload a Job Description, bulk-upload up to 100 candidate CVs, and the system scores each CV against 5 weighted criteria using Claude Sonnet 4.5 via OpenRouter. Output: a ranked shortlist with per-criterion evidence, an Excel export, and a printable HR report view.

## Prerequisites

1. **Supabase project** with these tables (run in SQL editor):

```sql
CREATE TABLE roles (
  id                   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title                TEXT NOT NULL,
  company              TEXT,
  location             TEXT,
  reports_to           TEXT,
  min_experience_years INT DEFAULT 0,
  min_qualification    TEXT,
  jd_text              TEXT,
  scoring_criteria     JSONB NOT NULL DEFAULT '[]',
  created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE candidates (
  id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  role_id      UUID REFERENCES roles(id) ON DELETE CASCADE,
  name         TEXT,
  email        TEXT,
  cv_text      TEXT,
  cv_file_path TEXT,
  file_name    TEXT,
  status       TEXT DEFAULT 'pending',
  error_msg    TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE scores (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  candidate_id     UUID REFERENCES candidates(id) ON DELETE CASCADE,
  role_id          UUID REFERENCES roles(id),
  criteria_scores  JSONB NOT NULL DEFAULT '{}',
  total_score      NUMERIC(5,2),
  bonus_tools      JSONB DEFAULT '[]',
  recommendation   TEXT,
  risk_flags       JSONB DEFAULT '[]',
  ai_summary       TEXT,
  scored_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_candidates_role_id ON candidates(role_id);
CREATE INDEX idx_scores_candidate_id ON scores(candidate_id);
CREATE INDEX idx_scores_role_id ON scores(role_id);
```

2. **Storage bucket** named `cvs`:
   - Public: false
   - File size limit: 20MB
   - Allowed MIME types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`

3. **Disable Row Level Security** on `roles`, `candidates`, `scores` for the demo.

4. **OpenRouter account** with API key. Default model: `anthropic/claude-sonnet-4.6` (configurable via `OPENROUTER_MODEL` in `.env`; spec calls for Claude Sonnet 4.6).

## Backend

```
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in credentials
uvicorn main:app --reload --port 8000
```

## Frontend

```
cd frontend
npm install
cp .env.example .env               # fill in credentials
npm run dev                        # http://localhost:5173
```

## Hybrid RAG (vector search)

The screener caches each uploaded CV as embedded chunks in Supabase pgvector and uses **hybrid retrieval** (vector cosine + Postgres full-text search, fused with Reciprocal Rank Fusion) for two things:

1. **RAG-powered scoring** — for each of C1–C5, the top-3 most relevant chunks are retrieved per criterion and passed to the LLM instead of the full CV. Smaller, focused context; better evidence.
2. **Semantic search bar** on the Scoring page — "find candidates with Power BI dashboards" returns ranked matches with snippets.

**Setup (one-time):**

1. **Enable pgvector** in your Supabase project: Dashboard → Database → Extensions → search for "vector" → enable.
2. **Run the migration**: paste `backend/sql/03_rag.sql` into the Supabase SQL editor and run.
3. **Add `OPENAI_API_KEY`** to `backend/.env` (also to Vercel project env vars for production).
4. **Backfill existing candidates** (optional — if you already have uploads in the DB):
   ```
   cd backend && source .venv/bin/activate
   python backfill_embeddings.py
   ```

**Cost:** Embedding ~$0.02 per 1M tokens with `text-embedding-3-small`. A typical CV is ~3K tokens, so ~$0.0001 per CV. Embedding 1000 CVs costs ~$0.10.

**Failure modes (graceful):**
- No `OPENAI_API_KEY` → uploads succeed without chunks, scoring uses full-CV fallback, search bar returns 503 with a clear message.
- `OPENAI_API_KEY` set but quota hit → same fallbacks per-call.
- Candidate has no chunks (legacy or embedding failed) → scoring uses full-CV path automatically.

## Deploy to Vercel (frontend + backend, single project)

The repo is set up as a Vercel monorepo: `vercel.json` builds the Vite frontend and `api/index.py` exposes the FastAPI app as a serverless function.

**One-time prep (locally):**
```
cd backend
source .venv/bin/activate
python seed_role.py
```
This calls the LLM once to extract criteria from `data/JD.docx`, inserts the role into Supabase, and writes `data/role_seed.json`. **Commit the resulting `role_seed.json`** — Vercel cold starts read it so no LLM call is needed on boot. Re-run any time `JD.docx` changes.

**Deploy steps:**
1. Push the repo to GitHub (already done if you cloned).
2. Vercel dashboard → New Project → import the repo.
3. Framework Preset: Other (vercel.json handles everything).
4. Add environment variables in Project Settings:
   - Backend: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`
   - Frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE=` (leave empty for same-origin)
5. Deploy.

**Serverless architecture notes:**
- Scoring is **frontend-driven**: the Scoring page calls `POST /api/candidates/:id/score` once per candidate, with up to 3 in flight at a time. Each request is one LLM call (~6-15s typical) — well within the Hobby tier's 60s function timeout. Closing the browser tab pauses the loop; reopening it resumes from where it left off (only pending/error candidates get re-queued).
- Uploads are **per-file POSTs** to `/api/roles/:id/candidates/single`. The frontend uploads one file at a time and updates progress as each completes.
- The active role is pinned by `backend/data/role_seed.json`. No LLM call on cold start.

## File-type support

- **CV uploads:** `.pdf` (digital only — scanned PDFs are flagged as errors, not OCR'd), `.docx`, `.txt`.
- **JD upload:** `.docx`, `.txt` (no PDF).

## Demo flow

1. `/setup` — paste or upload JD → LLM extracts criteria → review/edit weights → confirm.
2. `/role/:id/upload` — drag-drop up to 100 CVs (per-file streaming progress via SSE).
3. `/role/:id/scoring` — live ranking table, polls scoring status every 3s.
4. `/role/:id/candidate/:cid` — per-candidate detail with evidence.
5. `/role/:id/report` — printable HR report (browser Print-to-PDF for export).
6. Excel export button on the Scoring page.

## Demo constraints

- No authentication. Add Supabase Auth before production use.
- Scanned PDFs are not OCR'd — submit digital CVs only.
- OpenRouter calls are spaced 1s apart in background to avoid 429s.
- Scoring criteria weights default to 25/25/20/15/15 but are editable per role.
