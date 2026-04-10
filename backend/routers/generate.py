import json
import logging

from fastapi import APIRouter, HTTPException

from models import GenerateRequest, GenerateResponse
from services.llm import generate_resume
from services.matcher import ResumeMatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate", response_model=GenerateResponse)
def generate_resume_endpoint(payload: GenerateRequest) -> GenerateResponse:
    gaps_dicts = [g.model_dump() for g in payload.gaps]
    try:
        result = generate_resume(
            resume_text=payload.resume_text,
            jd_text=payload.jd_text,
            gaps=gaps_dicts,
            mode=payload.mode,
        )

        # 生成后自动对改写简历重新打分
        try:
            matcher = ResumeMatcher()
            score_after = matcher.analyze(
                resume_text=result["optimized_resume"],
                jd_text=payload.jd_text,
            )
            result["score_after"] = score_after
        except Exception as e:
            logger.warning(f"Re-scoring failed: {e}")
            result["score_after"] = None

        return GenerateResponse(**result)

    except RuntimeError as e:
        msg = str(e)
        if "ANTHROPIC_API_KEY" in msg or "not installed" in msg:
            raise HTTPException(status_code=503, detail=msg) from e
        if msg.startswith("Claude API error:"):
            raise HTTPException(status_code=502, detail=msg) from e
        raise HTTPException(status_code=500, detail=msg) from e
    except (json.JSONDecodeError, ValueError) as e:
        logger.exception("LLM returned invalid JSON or schema")
        raise HTTPException(
            status_code=502,
            detail=f"Invalid response from language model: {e}",
        ) from e
    except Exception as e:
        logger.exception("Claude API call failed")
        raise HTTPException(status_code=502, detail=str(e)) from e
