from fastapi import APIRouter

from models import AnalyzeRequest, AnalyzeResponse
from services.matcher import ResumeMatcher


router = APIRouter(prefix="/api", tags=["analysis"])
matcher = ResumeMatcher()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    result = matcher.analyze(payload.resume_text, payload.jd_text)
    return AnalyzeResponse(**result)

import pdfplumber
import io
from fastapi import UploadFile, File

@router.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return {"text": text.strip()}
    except Exception as e:
        return {"error": str(e), "text": ""}