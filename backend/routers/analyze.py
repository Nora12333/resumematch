from fastapi import APIRouter

from models import AnalyzeRequest, AnalyzeResponse
from services.matcher import ResumeMatcher


router = APIRouter(prefix="/api", tags=["analysis"])
matcher = ResumeMatcher()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    result = matcher.analyze(payload.resume_text, payload.jd_text)
    return AnalyzeResponse(**result)
