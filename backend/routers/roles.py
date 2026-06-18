from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, Form
from typing import Optional

from db.supabase import get_client
from models.schemas import RoleCreate
from services.cv_parser import parse_jd
from services.jd_extractor import extract_jd

router = APIRouter(tags=["roles"])


@router.get("/active-role")
async def get_active_role(request: Request):
    role_id = getattr(request.app.state, "active_role_id", None)
    if not role_id:
        raise HTTPException(503, "Active role not yet bootstrapped")
    sb = get_client()
    resp = sb.table("roles").select("*").eq("id", role_id).single().execute()
    if not resp.data:
        raise HTTPException(500, f"Active role {role_id} missing from DB")
    return resp.data


@router.post("/roles")
async def create_role(payload: RoleCreate):
    sb = get_client()
    data = payload.model_dump()
    data["scoring_criteria"] = [c if isinstance(c, dict) else c.model_dump() for c in data["scoring_criteria"]]
    resp = sb.table("roles").insert(data).execute()
    if not resp.data:
        raise HTTPException(500, "Failed to create role")
    return resp.data[0]


@router.get("/roles/{role_id}")
async def get_role(role_id: str):
    sb = get_client()
    resp = sb.table("roles").select("*").eq("id", role_id).single().execute()
    if not resp.data:
        raise HTTPException(404, "Role not found")
    return resp.data


@router.post("/extract-jd")
async def extract_jd_endpoint(
    jd_text: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
):
    text = jd_text or ""
    if file is not None:
        contents = await file.read()
        try:
            text = parse_jd(contents, file.filename or "")
        except ValueError as e:
            raise HTTPException(400, str(e))
    text = (text or "").strip()
    if not text:
        raise HTTPException(400, "JD text or file is required")
    try:
        parsed = await extract_jd(text)
    except Exception as e:
        raise HTTPException(502, f"JD extraction failed: {e}")
    return parsed
