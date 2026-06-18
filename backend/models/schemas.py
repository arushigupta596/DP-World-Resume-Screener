from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CriterionConfig(BaseModel):
    id: str
    label: str
    weight: float


class RoleCreate(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    reports_to: Optional[str] = None
    min_experience_years: Optional[int] = 0
    min_qualification: Optional[str] = None
    jd_text: str
    scoring_criteria: List[CriterionConfig]


class RoleResponse(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    reports_to: Optional[str] = None
    min_experience_years: Optional[int] = 0
    scoring_criteria: List[dict]
    created_at: datetime


class CandidateResponse(BaseModel):
    id: str
    role_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    file_name: Optional[str] = None
    status: str
    created_at: datetime
    score: Optional[dict] = None


class ScoreStatus(BaseModel):
    total: int
    pending: int
    scoring: int
    scored: int
    error: int


class JDExtractRequest(BaseModel):
    jd_text: str
