-- Content-addressed dedup for the embedding cache. Run after 03_rag.sql.
-- Adds a SHA-256 column on candidates so duplicate uploads can copy chunks
-- from an existing candidate instead of re-calling OpenRouter.

ALTER TABLE candidates ADD COLUMN IF NOT EXISTS cv_text_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_candidates_cv_text_hash ON candidates(cv_text_hash);
