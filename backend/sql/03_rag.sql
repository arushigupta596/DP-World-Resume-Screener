-- Hybrid RAG migration. Run this once in the Supabase SQL editor.
-- Adds pgvector + resume_chunks table + two hybrid-search RPC functions.

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Chunks table — one row per chunk of one CV
CREATE TABLE IF NOT EXISTS resume_chunks (
  id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
  chunk_index  INT NOT NULL,
  chunk_text   TEXT NOT NULL,
  chunk_tsv    TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED,
  embedding    VECTOR(1536),
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_candidate ON resume_chunks(candidate_id);
CREATE INDEX IF NOT EXISTS idx_chunks_fts ON resume_chunks USING GIN (chunk_tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON resume_chunks USING hnsw (embedding vector_cosine_ops);

-- 3. Per-candidate hybrid search (used by RAG scoring).
-- Fuses vector cosine distance + Postgres full-text search via Reciprocal Rank Fusion.
CREATE OR REPLACE FUNCTION hybrid_search_chunks(
  p_candidate_id    uuid,
  p_query_text      text,
  p_query_embedding vector(1536),
  p_k               int DEFAULT 3
) RETURNS TABLE (chunk_id uuid, chunk_text text, rrf_score float)
LANGUAGE sql STABLE AS $$
  WITH v AS (
    SELECT id, chunk_text,
      ROW_NUMBER() OVER (ORDER BY embedding <=> p_query_embedding) AS r
    FROM resume_chunks
    WHERE candidate_id = p_candidate_id AND embedding IS NOT NULL
    LIMIT 20
  ),
  f AS (
    SELECT id, chunk_text,
      ROW_NUMBER() OVER (ORDER BY ts_rank_cd(chunk_tsv, plainto_tsquery('english', p_query_text)) DESC) AS r
    FROM resume_chunks
    WHERE candidate_id = p_candidate_id
      AND chunk_tsv @@ plainto_tsquery('english', p_query_text)
    LIMIT 20
  )
  SELECT
    COALESCE(v.id, f.id),
    COALESCE(v.chunk_text, f.chunk_text),
    (COALESCE(1.0 / (60 + v.r), 0) + COALESCE(1.0 / (60 + f.r), 0))::float AS rrf
  FROM v FULL OUTER JOIN f ON v.id = f.id
  ORDER BY rrf DESC
  LIMIT p_k;
$$;

-- 4. Cross-candidate hybrid search (used by the search bar).
-- For every candidate in a role, picks their best-matching chunk and ranks across the pool.
CREATE OR REPLACE FUNCTION hybrid_search_role(
  p_role_id         uuid,
  p_query_text      text,
  p_query_embedding vector(1536),
  p_limit           int DEFAULT 20
) RETURNS TABLE (candidate_id uuid, best_chunk text, rrf_score float)
LANGUAGE sql STABLE AS $$
  WITH v AS (
    SELECT rc.candidate_id, rc.id AS chunk_id, rc.chunk_text,
      ROW_NUMBER() OVER (ORDER BY rc.embedding <=> p_query_embedding) AS r
    FROM resume_chunks rc
    JOIN candidates c ON c.id = rc.candidate_id
    WHERE c.role_id = p_role_id AND rc.embedding IS NOT NULL
    LIMIT 200
  ),
  f AS (
    SELECT rc.candidate_id, rc.id AS chunk_id, rc.chunk_text,
      ROW_NUMBER() OVER (ORDER BY ts_rank_cd(rc.chunk_tsv, plainto_tsquery('english', p_query_text)) DESC) AS r
    FROM resume_chunks rc
    JOIN candidates c ON c.id = rc.candidate_id
    WHERE c.role_id = p_role_id
      AND rc.chunk_tsv @@ plainto_tsquery('english', p_query_text)
    LIMIT 200
  ),
  unioned AS (
    SELECT
      COALESCE(v.candidate_id, f.candidate_id) AS cand_id,
      COALESCE(v.chunk_text, f.chunk_text) AS chunk_text,
      (COALESCE(1.0 / (60 + v.r), 0) + COALESCE(1.0 / (60 + f.r), 0))::float AS rrf
    FROM v FULL OUTER JOIN f ON v.chunk_id = f.chunk_id
  ),
  best_per_candidate AS (
    SELECT cand_id, chunk_text, rrf,
      ROW_NUMBER() OVER (PARTITION BY cand_id ORDER BY rrf DESC) AS rn
    FROM unioned
  )
  SELECT cand_id, chunk_text, rrf
  FROM best_per_candidate
  WHERE rn = 1
  ORDER BY rrf DESC
  LIMIT p_limit;
$$;
