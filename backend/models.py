from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    resume_text: str = Field(..., min_length=1)
    jd_text: str = Field(..., min_length=1)


class GapItem(BaseModel):
    skill: str
    importance: Literal["required", "nice_to_have", "covered", "partial"]
    is_must: bool = False
    suggestion_zh: str
    suggestion_en: str


class KeywordItem(BaseModel):
    word: str
    matched: bool


class SkillStatusItem(BaseModel):
    skill: str
    status: Literal["covered", "partial", "missing_required", "missing_optional"]
    is_must: bool = False
    is_preferred: bool = False


class AnalyzeResponse(BaseModel):
    overall_score: int
    skill_score: int
    experience_score: int
    eligibility: dict[str, Any] = Field(default_factory=dict)
    skill_status: list[SkillStatusItem] = Field(default_factory=list)
    gaps: list[GapItem]
    keywords: list[KeywordItem]


class ChangeItem(BaseModel):
    original: str = ""
    updated: str = ""


class GenerateRequest(BaseModel):
    resume_text: str = Field(..., min_length=1)
    jd_text: str = Field(..., min_length=1)
    gaps: list[GapItem] = Field(default_factory=list)
    mode: Literal["smart_fill", "full_rewrite"] = "smart_fill"


class GenerateResponse(BaseModel):
    optimized_resume: str
    changes: list[ChangeItem]
    score_after: dict[str, Any] | None = None