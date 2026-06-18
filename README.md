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
