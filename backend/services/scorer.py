from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx

from db.supabase import get_client

logger = logging.getLogger("cv-screener.scorer")

SCORING_PROMPT_TEMPLATE = """You are an expert HR analyst. Score the following CV for the role of {role_title} at {company}.
Return ONLY valid JSON. No markdown, no explanation, no preamble.

SCORING SCALE (apply to every criterion):
9-10  Direct, substantial, explicitly stated experience
7-8   Adjacent or clearly transferable experience
5-6   Indirect or implied with some evidence
3-4   Minimal or unclear relevance
0-2   No evidence found

CRITERIA AND RUBRIC ANCHORS:

C1 — {c1_label} (weight: {c1_weight}%)
  9-10: Named offshore marine, OSV, subsea, or offshore oil & gas role
  7-8:  Ports, shipping, energy, or offshore renewables sector
  5-6:  Adjacent logistics or transportation industry
  <5:   No maritime or energy background

C2 — {c2_label} (weight: {c2_weight}%)
  9-10: Published market reports, forecasting models, or competitor intelligence work named
  7-8:  Regular market analysis as part of role, trend reporting explicitly mentioned
  5-6:  Some analytical work described; data-driven insights referenced
  <5:   No clear market analysis experience

C3 — {c3_label} (weight: {c3_weight}%)
  9-10: Advanced Excel (modelling, VBA, pivot tables), Power BI dashboards built, strong PPT evidence
  7-8:  Proficient Excel and PowerPoint explicitly stated; some BI tool usage
  5-6:  Basic Office suite mentioned
  <5:   No Microsoft tools mentioned

C4 — {c4_label} (weight: {c4_weight}%)
  9-10: Explicit examples of analysis leading to commercial wins, revenue growth, or new business
  7-8:  Connected analytical output to business development or commercial strategy
  5-6:  Some commercial awareness evident; link to revenue unclear
  <5:   No evidence of commercial or revenue linkage

C5 — {c5_label} (weight: {c5_weight}%)
  9-10: Named senior stakeholders; research directly cited in strategic decisions
  7-8:  Regular reporting to VP/C-level; insights demonstrably influenced strategy
  5-6:  Analysis shared with teams; impact on decisions unclear
  <5:   No evidence of supporting commercial decisions

BONUS SIGNALS (do not score, just detect presence):
Flag any of: Clarkson Research, IHS Markit, S&P Global, Rystad Energy, BIMCO, Platts

RISK FLAGS — add a flag for any of these:
- No offshore or maritime experience
- Tools listed without demonstrated usage (e.g. "proficient in Excel" only)
- Tenure under 12 months in any analytical role
- Purely academic background, no commercial exposure
- CV appears to be for a different functional area entirely

OUTPUT FORMAT — return exactly this JSON structure:
{{
  "candidate_name": "Full name from CV header",
  "criteria_scores": {{
    "C1": {{"score": 0, "evidence": "direct quote or paraphrase from CV supporting score", "confidence": "high"}},
    "C2": {{"score": 0, "evidence": "...", "confidence": "medium"}},
    "C3": {{"score": 0, "evidence": "...", "confidence": "high"}},
    "C4": {{"score": 0, "evidence": "...", "confidence": "low"}},
    "C5": {{"score": 0, "evidence": "...", "confidence": "medium"}}
  }},
  "bonus_tools": [],
  "risk_flags": [],
  "ai_summary": "2-3 sentence plain English summary suitable for an HR manager. Lead with the strongest qualification, note the biggest gap."
}}

confidence must be exactly one of: high | medium | low
evidence must be a specific phrase or paraphrase from the CV, not a generic statement.
If no evidence exists for a criterion, set score to 0 and evidence to "Not mentioned".

CV TO SCORE:
{cv_text}
"""


_score_lock = asyncio.Lock()
_last_call_ts = 0.0
RATE_LIMIT_SECONDS = 1.0
SCORE_CONCURRENCY = int(os.getenv("SCORE_CONCURRENCY", "3"))

_concurrency_sem: asyncio.Semaphore | None = None


def _get_sem() -> asyncio.Semaphore:
    global _concurrency_sem
    if _concurrency_sem is None:
        _concurrency_sem = asyncio.Semaphore(SCORE_CONCURRENCY)
    return _concurrency_sem


async def _rate_limit_gate():
    """Space OpenRouter call starts at least RATE_LIMIT_SECONDS apart globally."""
    global _last_call_ts
    async with _score_lock:
        now = asyncio.get_event_loop().time()
        wait = RATE_LIMIT_SECONDS - (now - _last_call_ts)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call_ts = asyncio.get_event_loop().time()


# Per-criterion retrieval queries used for RAG. The criterion's label is
# concatenated with a "strongest signal" hint so the embedded query matches
# CV chunks describing the exact qualifications the rubric rewards.
RAG_CRITERION_HINTS = {
    "C1": "offshore marine OSV subsea offshore oil gas ports shipping energy renewables maritime",
    "C2": "market analysis forecasting models competitor intelligence market reports trend analysis",
    "C3": "advanced Excel modelling VBA pivot tables Power BI dashboards PowerPoint Office tools",
    "C4": "commercial wins revenue growth new business business development commercial strategy impact",
    "C5": "senior stakeholders VP C-level executive reporting strategic decisions board presentations",
}


def _build_prompt(role: dict, cv_text: str) -> str:
    criteria = role.get("scoring_criteria") or []
    by_id = {c["id"]: c for c in criteria}

    def label(cid: str) -> str:
        return by_id.get(cid, {}).get("label", cid)

    def weight(cid: str) -> float:
        return by_id.get(cid, {}).get("weight", 20)

    return SCORING_PROMPT_TEMPLATE.format(
        role_title=role.get("title", ""),
        company=role.get("company") or "the company",
        c1_label=label("C1"),
        c1_weight=weight("C1"),
        c2_label=label("C2"),
        c2_weight=weight("C2"),
        c3_label=label("C3"),
        c3_weight=weight("C3"),
        c4_label=label("C4"),
        c4_weight=weight("C4"),
        c5_label=label("C5"),
        c5_weight=weight("C5"),
        cv_text=cv_text,
    )


def _build_rag_prompt(role: dict, retrieved_by_criterion: dict[str, list[dict]]) -> str:
    """Variant of _build_prompt that swaps the full CV for per-criterion
    retrieved excerpts. Excerpts are de-duplicated but tagged with the
    criterion that retrieved them so the LLM knows what evidence supports
    what score."""
    sections = []
    seen: set[str] = set()
    for cid in ("C1", "C2", "C3", "C4", "C5"):
        chunks = retrieved_by_criterion.get(cid) or []
        if not chunks:
            sections.append(f"{cid}: (no relevant excerpts retrieved)")
            continue
        texts = []
        for c in chunks:
            t = (c.get("chunk_text") or "").strip()
            if t and t not in seen:
                texts.append(t)
                seen.add(t)
        if not texts:
            sections.append(f"{cid}: (only duplicates of earlier excerpts)")
        else:
            sections.append(f"{cid}:\n" + "\n---\n".join(texts))

    block = "RETRIEVED CV EXCERPTS (top-K per criterion via hybrid pgvector + FTS):\n\n" + "\n\n".join(sections)
    return _build_prompt(role, block)


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Parse JSON from an LLM response, tolerating stray text or fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(text)
        if not match:
            raise
        return json.loads(match.group(0))


async def _call_openrouter(prompt: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return _extract_json(content)


def _calculate_total(criteria_scores: dict, role_criteria: list) -> float:
    total = 0.0
    for c in role_criteria:
        cid = c["id"]
        weight = float(c.get("weight", 0))
        entry = criteria_scores.get(cid) or {}
        score = float(entry.get("score", 0))
        total += score * (weight / 10.0)
    return round(total, 2)


def _recommendation(total: float) -> str:
    if total >= 70:
        return "Shortlist"
    if total >= 50:
        return "Review"
    return "Reject"


async def _build_scoring_prompt(role: dict, candidate: dict) -> str:
    """RAG-only scoring prompt. No fallback (demo policy).

    Embeddings MUST exist for the candidate before scoring runs. Per-
    criterion retrieval errors propagate so the recruiter sees an honest
    failure instead of silent degradation to a different code path.
    """
    candidate_id = candidate["id"]
    criteria = role.get("scoring_criteria") or []
    by_id = {c["id"]: c for c in criteria}

    from services.retriever import retrieve_chunks_for_candidate

    retrieved: dict[str, list[dict]] = {}
    for cid in ("C1", "C2", "C3", "C4", "C5"):
        label = by_id.get(cid, {}).get("label", cid)
        hint = RAG_CRITERION_HINTS.get(cid, "")
        query = f"{label}. {hint}".strip()
        retrieved[cid] = retrieve_chunks_for_candidate(candidate_id, query, k=3)

    total_chunks = sum(len(v) for v in retrieved.values())
    if total_chunks == 0:
        raise RuntimeError(
            f"No RAG context for candidate {candidate_id}. "
            "Run backfill_embeddings.py or re-upload the CV."
        )
    logger.info("RAG context for %s: %d chunks across C1-C5", candidate_id, total_chunks)
    return _build_rag_prompt(role, retrieved)


async def score_candidate(candidate_id: str, role: dict) -> None:
    """Background task: score one candidate against the role's criteria."""
    sb = get_client()
    try:
        cand_resp = sb.table("candidates").select("*").eq("id", candidate_id).single().execute()
        candidate = cand_resp.data
        if not candidate:
            return

        if not candidate.get("cv_text"):
            sb.table("candidates").update(
                {"status": "error", "error_msg": "No CV text available to score"}
            ).eq("id", candidate_id).execute()
            return

        prompt = await _build_scoring_prompt(role, candidate)

        async with _get_sem():
            sb.table("candidates").update({"status": "scoring"}).eq("id", candidate_id).execute()
            await _rate_limit_gate()
            try:
                parsed = await _call_openrouter(prompt)
            except (json.JSONDecodeError, KeyError):
                await _rate_limit_gate()
                parsed = await _call_openrouter(prompt)

        criteria_scores = parsed.get("criteria_scores", {})
        total = _calculate_total(criteria_scores, role.get("scoring_criteria") or [])
        recommendation = _recommendation(total)

        sb.table("scores").insert(
            {
                "candidate_id": candidate_id,
                "role_id": role["id"],
                "criteria_scores": criteria_scores,
                "total_score": total,
                "bonus_tools": parsed.get("bonus_tools", []),
                "recommendation": recommendation,
                "risk_flags": parsed.get("risk_flags", []),
                "ai_summary": parsed.get("ai_summary", ""),
            }
        ).execute()

        update: dict[str, Any] = {"status": "scored", "error_msg": None}
        ai_name = parsed.get("candidate_name")
        if ai_name and not candidate.get("name"):
            update["name"] = ai_name
        sb.table("candidates").update(update).eq("id", candidate_id).execute()

    except Exception as e:
        sb.table("candidates").update(
            {"status": "error", "error_msg": str(e)[:500]}
        ).eq("id", candidate_id).execute()
