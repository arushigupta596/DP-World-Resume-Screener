from __future__ import annotations

import json
import os
import re

import httpx

JD_EXTRACT_PROMPT = """You are an HR analyst configuring a CV scoring system. Read the job description below and return ONLY valid JSON (no markdown, no preamble).

Extract role metadata and design a 5-criterion scoring rubric tailored to the JD. The system always uses exactly 5 criteria labelled C1..C5 with weights summing to 100.

Default weighting suggestion when no strong signal otherwise: 25, 25, 20, 15, 15. Adjust if the JD weights some skills heavier than others.

For a DP World Market Research Analyst role (offshore / marine logistics), the canonical criteria are:
  C1: Offshore / Maritime sector fit
  C2: Market analysis & forecasting experience
  C3: Microsoft Office + BI tooling proficiency (Excel, PowerPoint, Power BI)
  C4: Commercial / revenue impact from analytical work
  C5: Stakeholder reporting & influence on strategic decisions

If the JD is for a different role, design 5 criteria appropriate to that role instead.

Return exactly this JSON shape:
{{
  "title": "Role title from the JD",
  "company": "Company name if mentioned, else null",
  "location": "Location if mentioned, else null",
  "reports_to": "Reporting line if mentioned, else null",
  "min_experience_years": 0,
  "min_qualification": "Minimum qualification text or null",
  "jd_text": "The full JD text passed back as-is",
  "scoring_criteria": [
    {{"id": "C1", "label": "...", "weight": 25}},
    {{"id": "C2", "label": "...", "weight": 25}},
    {{"id": "C3", "label": "...", "weight": 20}},
    {{"id": "C4", "label": "...", "weight": 15}},
    {{"id": "C5", "label": "...", "weight": 15}}
  ]
}}

Weights must be integers and sum to exactly 100.

JOB DESCRIPTION:
{jd_text}
"""


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict:
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


async def extract_jd(jd_text: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    prompt = JD_EXTRACT_PROMPT.format(jd_text=jd_text)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    parsed = _extract_json(content)

    parsed["jd_text"] = jd_text
    criteria = parsed.get("scoring_criteria") or []
    total = sum(int(c.get("weight", 0)) for c in criteria)
    if total != 100 and criteria:
        scale = 100.0 / total if total else 0
        for c in criteria:
            c["weight"] = round(int(c.get("weight", 0)) * scale)
        diff = 100 - sum(int(c["weight"]) for c in criteria)
        if criteria:
            criteria[0]["weight"] = int(criteria[0]["weight"]) + diff

    return parsed
