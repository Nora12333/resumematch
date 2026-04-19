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
from fastapi.responses import Response
from models import GenerateRequest
from services.docx_builder import build_resume_docx

@router.post("/generate-docx")
def generate_docx_endpoint(payload: GenerateRequest, pages: int = 2):
    """生成格式化 docx 文件并返回下载"""
    gaps_dicts = [g.model_dump() for g in payload.gaps]
    result = generate_resume(
        resume_text=payload.resume_text,
        jd_text=payload.jd_text,
        gaps=gaps_dicts,
        mode=payload.mode,
    )
    optimized = result["optimized_resume"]
    docx_bytes = build_resume_docx(optimized, pages=pages)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=optimized_resume_{pages}page.docx"}
    )

from fastapi.responses import Response
from io import BytesIO
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _build_docx(optimized_resume: str, pages: int = 2) -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    margin = Inches(0.6) if pages == 1 else Inches(0.75)
    section.top_margin = section.bottom_margin = margin
    section.left_margin = section.right_margin = margin

    body_size = 9 if pages == 1 else 10
    name_size = 14 if pages == 1 else 16
    sec_size  = 10 if pages == 1 else 11
    sp = 1 if pages == 1 else 3

    def parse_segments(text):
        parts = re.split(r'(\[NEW\][\s\S]*?\[NEW\])', text)
        result = []
        for p in parts:
            if re.match(r'^\[NEW\][\s\S]*\[NEW\]$', p):
                result.append((p[5:-5], True))
            elif p:
                result.append((p, False))
        return result

    def add_runs(para, text, bold=False, italic=False, size=10):
        for seg, is_new in parse_segments(text):
            run = para.add_run(seg)
            run.bold = bold
            run.italic = italic
            run.font.size = Pt(size)
            run.font.name = "Arial"
            if is_new:
                rPr = run._r.get_or_add_rPr()
                hl = OxmlElement("w:highlight")
                hl.set(qn("w:val"), "yellow")
                rPr.append(hl)

    def add_hr():
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bot = OxmlElement("w:bottom")
        bot.set(qn("w:val"), "single")
        bot.set(qn("w:sz"), "6")
        bot.set(qn("w:space"), "1")
        bot.set(qn("w:color"), "000000")
        pBdr.append(bot)
        pPr.append(pBdr)

    SECTION_KEYWORDS = {"EDUCATION","EXPERIENCE","PROJECTS","SKILLS","SUMMARY","教育","经历","技能","项目"}

    lines = optimized_resume.split("\n")
    first_nonempty = True

    for raw in lines:
        s = raw.strip()
        if not s:
            continue

        if first_nonempty:
            first_nonempty = False
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            add_runs(p, s, bold=True, size=name_size)
            continue

        if "|" in s or "@" in s:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(sp)
            add_runs(p, s, size=body_size)
            continue

        clean = re.sub(r'\[NEW\]', '', s).strip()
        if clean.upper() in SECTION_KEYWORDS:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.papace_after = Pt(0)
            add_runs(p, s, bold=True, size=sec_size)
            add_hr()
            continue

        if s.startswith("•") or s.startswith("-"):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(sp)
            add_runs(p, re.sub(r'^[•\-]\s*', '', s), size=body_size)
            continue

        if s.startswith("Relevant Coursework"):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(sp)
            if ":" in s:
                label, rest = s.split(":", 1)
                r = p.add_run(label + ":")
                r.italic = True
                r.font.size = Pt(body_size)
                r.font.name = "Arial"
                add_runs(p, rest, size=body_size)
            else:
                add_runs(p, s, italic=True, size=body_size)
            continue

        if ("–" in s or " - " in s) and len(s) < 80:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(s         add_runs(p, s, italic=True, size=body_size)
            continue

        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(sp)
        add_runs(p, s, bold=True, size=body_size)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


@router.post("/generate-docx")
def generate_docx_endpoint(payload: GenerateRequest, pages: int = 2):
    gaps_dicts = [g.model_dump() for g in payload.gaps]
    try:
        result = generate_resume(
            resume_text=payload.resume_text,
            jd_text=payload.jd_text,
            gaps=gaps_dicts,
            mode=payload.mode,
        )
        docx_bytes = _build_docx(result["optimized_resume"], pages=pages)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=optimized_resume_{pages}page.docx"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
