import json
import os
import re
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None

MODEL_ID = "claude-sonnet-4-20250514"

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _dotenv_candidates() -> list[Path]:
    """Paths where .env may live (cwd varies when running uvicorn)."""
    return [
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env",
        _BACKEND_ROOT / ".env",
        Path.home() / "resumematch" / "backend" / ".env",
    ]


def _load_env() -> None:
    """Load all existing candidate .env files; later files override (so real key in ~/... can win)."""
    seen: set[Path] = set()
    loaded_any = False
    for raw in _dotenv_candidates():
        try:
            path = raw.resolve()
        except OSError:
            continue
        if path in seen:
            continue
        seen.add(path)
        if path.is_file():
            load_dotenv(path, override=True)
            loaded_any = True
    if not loaded_any:
        load_dotenv(override=True)


_load_env()


def _is_anthropic_error(exc: BaseException) -> bool:
    mod = type(exc).__module__ or ""
    return mod.startswith("anthropic")

SYSTEM_PROMPT_SMART_FILL = """You are a professional resume editor. Your job is to improve a resume to better match a job description, based on identified skill gaps.

Rules:
1. Only add content that could plausibly be true given the candidate's existing experience
2. Never invent specific metrics, company names, or technologies not hinted at in the original
3. Mark all new or rewritten content with paired tags: [NEW] at the start and [NEW] at the end of each added or changed span
4. Keep the original structure and format; do not remove or reorder sections unless a tiny fix is needed for consistency
5. Output must be valid JSON only — no markdown fences, no explanations outside JSON
6. Write the optimized_resume in the same language as the input resume

Required JSON keys:
- "optimized_resume": full resume text; use [NEW]... [NEW] around every new or materially updated fragment
- "changes": list of { "original": string, "updated": string }; use "" for original when inserting wholly new lines"""

SYSTEM_PROMPT_SMART_FILL = """You are a professional resume editor. Your job is to improve a resume to better match a job description, based on identified skill gaps.

Rules:
1. Only add content that is directly grounded in the candidate's existing experience — same company, same project, same time period. Never add a new bullet that floats free of any existing context.
2. New content must reference specific details already in the resume: the same dataset, the same tool used in that role, the same business outcome. Generic phrases like "conducted data analysis" or "utilized advanced Excel" with no connection to the existing bullet are forbidden.
3. Never invent specific metrics, company names, or technologies not hinted at in the original.
4. If a skill gap cannot be addressed with specific grounded content, do NOT add a generic sentence. Leave that gap unaddressed rather than padding with vague language.
5. Mark all new or rewritten content with paired tags: [NEW] at the start and [NEW] at the end of each added or changed span.
6. Keep the original structure and format; do not remove or reorder sections.
7. Output must be valid JSON only — no markdown fences, no explanations outside JSON.
8. Write the optimized_resume in the same language as the input resume.

Required JSON keys:
- "optimized_resume": full resume text; use [NEW]... [NEW] around every new or materially updated fragment
- "changes": list of { "original": string, "updated": string }; use "" for original when inserting wholly new lines"""


def _get_api_key() -> str | None:
    _load_env()
    raw = os.environ.get("ANTHROPIC_API_KEY", "")
    key = raw.strip().lstrip("\ufeff").strip('"').strip("'")
    return key or None


def _format_gaps_for_prompt(gaps: list[dict[str, Any]]) -> str:
    lines = []
    for g in gaps:
        skill = g.get("skill", "")
        imp = g.get("importance", "")
        zh = g.get("suggestion_zh", "")
        en = g.get("suggestion_en", "")
        lines.append(f"- {skill} ({imp}): {zh} | {en}")
    return "\n".join(lines) if lines else "(none)"


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_llm_json(raw: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start == -1:
            raise
        try:
            data, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if not match:
                raise
            data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object")
    return data


def score_experience(resume_bullets: list[str], jd_requirements: list[str]) -> float:
    """
    Ask Claude to score resume experience match against JD requirements.
    Returns a numeric score in [0, 100].
    """
    _load_env()
    if anthropic is None:
        raise RuntimeError("anthropic package is not installed")
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    clean_bullets = [b.strip() for b in resume_bullets if isinstance(b, str) and b.strip()]
    clean_requirements = [r.strip() for r in jd_requirements if isinstance(r, str) and r.strip()]
    if not clean_bullets or not clean_requirements:
        return 0.0

    bullets_block = "\n".join(f"- {b}" for b in clean_bullets)
    reqs_block = "\n".join(f"- {r}" for r in clean_requirements)
    user_prompt = f"""You are scoring resume-to-JD experience alignment.

Evaluate how well the candidate's experience bullets match the job requirements.
Return ONLY one integer from 0 to 100 (no JSON, no explanation).

Resume bullets:
{bullets_block}

Job requirements:
{reqs_block}
"""

    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=32,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        if _is_anthropic_error(e):
            raise RuntimeError(f"Claude API error: {e}") from e
        raise

    raw_text = "".join(block.text for block in message.content if block.type == "text").strip()
    if not raw_text:
        raise ValueError("Empty response from Claude while scoring experience")

    match = re.search(r"\d+", raw_text)
    if not match:
        raise ValueError(f"Claude did not return a numeric score: {raw_text}")
    score = int(match.group(0))
    return float(max(0, min(100, score)))


def generate_resume(
    resume_text: str,
    jd_text: str,
    gaps: list[dict[str, Any]],
    mode: Literal["smart_fill", "full_rewrite"],
) -> dict[str, Any]:
    """
    Call Claude (claude-sonnet-4-20250514) and return
    {"optimized_resume": str, "changes": list[{"original", "updated"}]}.

    - smart_fill: keep structure; only add/adjust for gaps; mark additions with [NEW]...[NEW].
    - full_rewrite: rewrite for maximum JD alignment while truthful; mark changes with [NEW]...[NEW].

    Raises RuntimeError if API key missing, package missing, or Claude API fails.
    """
    _load_env()
    if anthropic is None:
        raise RuntimeError("anthropic package is not installed")

    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    system = SYSTEM_PROMPT_SMART_FILL if mode == "smart_fill" else SYSTEM_PROMPT_FULL_REWRITE
    gaps_block = _format_gaps_for_prompt(gaps)

    if mode == "smart_fill":
        mode_instruction = """Mode: smart_fill
- Preserve all original resume text that does not need changing.
- Only add or lightly adjust content to address the listed gaps; keep section order and headings.
- Wrap every new sentence, bullet, or edited phrase in paired markers: [NEW] ... [NEW] (opening [NEW] immediately before new/changed text, closing [NEW] immediately after)."""
    else:
        mode_instruction = """Mode: full_rewrite
- Rewrite the full resume to maximize relevance to the job description (keywords, priorities, tone), without inventing facts.
- You may reorder sections, merge bullets, and rewrite for impact; ground every claim in the original resume.
- Wrap every new or materially rewritten span in paired [NEW] ... [NEW] markers."""

    user_prompt = f"""Resume:
{resume_text}

Job Description:
{jd_text}

Skill gaps to address:
{gaps_block}
Before writing any new content, for each gap:
1. Find the most relevant existing bullet in the resume that relates to this gap
2. Only if a relevant bullet exists, extend or supplement it with specific details
3. If no relevant bullet exists, only add the skill to the Skills section, do not create a new experience bullet
{mode_instruction}

Return exactly one JSON object (UTF-8) with:
- "optimized_resume": string — full resume text; all new or changed spans must use paired [NEW] delimiters as described.
- "changes": array of objects {{ "original": string, "updated": string }} — concise pairs for each meaningful edit (use "" for "original" when inserting new lines).

No markdown code fences. No text before or after the JSON object."""

    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        if _is_anthropic_error(e):
            raise RuntimeError(f"Claude API error: {e}") from e
        raise

    raw_text = ""
    for block in message.content:
        if block.type == "text":
            raw_text += block.text

    if not raw_text.strip():
        raise ValueError("Empty response from Claude")

    data = _parse_llm_json(raw_text)
    optimized = data.get("optimized_resume", "")
    changes = data.get("changes", [])
    if not isinstance(optimized, str):
        raise ValueError("optimized_resume must be a string")
    if not isinstance(changes, list):
        changes = []

    normalized_changes: list[dict[str, str]] = []
    for item in changes:
        if isinstance(item, dict):
            original = item.get("original", "")
            updated = item.get("updated", "")
            if isinstance(original, str) and isinstance(updated, str):
                normalized_changes.append({"original": original, "updated": updated})

    return {
        "optimized_resume": optimized,
        "changes": normalized_changes,
    }
def analyze_jd(jd_text: str) -> dict[str, Any]:
    """
    用 Claude 解析 JD，返回结构化 JSON。
    """
    _load_env()
    if anthropic is None:
        raise RuntimeError("anthropic package is not installed")
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    user_prompt = f"""You are a structured job description parser.

Analyze the job description below. Extract ONLY what is explicitly written.

STRICT RULES:
- must_have: Only truly non-negotiable requirements. "familiarity with" and "experience with" are usually preferred, not must-have. "should have", "we expect", "need" can be must-have if they are core to the role.
- preferred: Requirements with "preferred", "plus", "nice to have", "bonus", "familiarity with", "experience with"
- responsibilities: job duties listed in the JD, do not infer capabilities
- explicit_skills: tool/skill names that literally appear in the text
- inferred_capabilities: skills implied but not explicitly stated, mark as low confidence
- domain: one of [Data Analytics, Data Engineering, Software Engineering, Product, Marketing, Finance, Other]
- seniority: one of [intern, entry, mid, senior, lead, unknown]
- location_requirement: exact location text or "remote" or "unknown"
- authorization_required: true only if JD explicitly mentions work authorization requirement

Return ONLY a valid JSON object, no markdown, no explanation:

{{
  "must_have": [],
  "preferred": [],
  "responsibilities": [],
  "explicit_skills": [],
  "inferred_capabilities": [],
  "domain": "",
  "seniority": "",
  "location_requirement": "",
  "authorization_required": false
}}

Job Description:
{jd_text}"""

    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=1000,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        if _is_anthropic_error(e):
            raise RuntimeError(f"Claude API error: {e}") from e
        raise

    raw_text = ""
    for block in message.content:
        if block.type == "text":
            raw_text += block.text

    return _parse_llm_json(raw_text)


def analyze_resume(resume_text: str) -> dict[str, Any]:
    """
    用 Claude 解析简历，返回结构化 JSON。
    """
    _load_env()
    if anthropic is None:
        raise RuntimeError("anthropic package is not installed")
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    user_prompt = f"""You are a structured resume parser.

Parse the resume below into structured data.

STRICT RULES:
- Extract only what is explicitly written
- bullets: extract each bullet point as a separate string
- quantified_outcomes: only bullets that contain numbers or percentages
- seniority_signals: action verbs that signal level (led, managed, designed, built, assisted, etc.)

Return ONLY a valid JSON object, no markdown, no explanation:

{{
  "education": [
    {{"school": "", "degree": "", "major": "", "year": ""}}
  ],
  "experience": [
    {{
      "company": "",
      "title": "",
      "duration": "",
      "bullets": []
    }}
  ],
  "projects": [
    {{
      "name": "",
      "description": "",
      "tools": []
    }}
  ],
  "explicit_skills": [],
  "quantified_outcomes": [],
  "domains": [],
  "seniority_signals": []
}}

Resume:
{resume_text}"""

    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=2000,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        if _is_anthropic_error(e):
            raise RuntimeError(f"Claude API error: {e}") from e
        raise

    raw_text = ""
    for block in message.content:
        if block.type == "text":
            raw_text += block.text

    return _parse_llm_json(raw_text)
def generate_resume_structured(
    resume_text: str,
    jd_text: str,
    gaps: list[dict[str, Any]],
    mode: Literal["smart_fill", "full_rewrite"],
) -> dict[str, Any]:
    _load_env()
    if anthropic is None:
        raise RuntimeError("anthropic package is not installed")
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    gaps_block = _format_gaps_for_prompt(gaps)

    user_prompt = f"""You are a professional resume editor. Improve the resume below to better match the job description.

RULES:
1. Only add content grounded in the candidate's existing experience.
2. Never invent metrics, company names, or technologies not in the original.
3. Mark ALL new or changed text with [NEW] before and [NEW] after.
4. Return ONLY valid JSON, no markdown fences.

Resume:
{resume_text}

Job Description:
{jd_text}

Skill gaps to address:
{gaps_block}

Return this exact JSON structure:
{{
  "name": "candidate full name",
  "contact": "contact line e.g. City | email | phone",
  "education": [
    {{
      "school": "",
      "degree": "",
      "date": "",
      "coursework": ""
    }}
  ],
  "experience": [
    {{
      "company": "",
      "location": "",
      "title": "",
      "date": "",
      "bullets": ["bullet text, use [NEW]...[NEW] for new/changed parts"]
    }}
  ],
  "projects": [
    {{
      "name": "",
      "bullets": ["bullet text"]
    }}
  ],
  "skills": [
    {{
      "label": "Programming & Tools",
      "content": "skill list, use [NEW]...[NEW] for new parts"
    }}
  ],
  "changes": [
    {{"original": "", "updated": ""}}
  ]
}}"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL_ID,
        max_tokens=8192,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = "".join(block.text for block in message.content if block.type == "text")
    if not raw_text.strip():
        raise ValueError("Empty response from Claude")

    data = _parse_llm_json(raw_text)
    return data
def _build_docx_structured(data: dict, pages: int = 2) -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    margin = Inches(0.6) if pages == 1 else Inches(0.75)
    section.top_margin = section.bottom_margin = margin
    section.left_margin = section.right_margin = margin

    body_size = 9 if pages == 1 else 10
    name_size = 14 if pages == 1 else 16
    sec_size = 10 if pages == 1 else 11
    sp = 1 if pages == 1 else 3

    # Name
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    _add_runs(p, data.get("name", ""), bold=True, size=name_size)

    # Contact
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(sp)
    _add_runs(p, data.get("contact", ""), size=body_size)

    # Education
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(0)
    _add_runs(p, "EDUCATION", bold=True, size=sec_size)
    _add_hr(doc)

    for edu in data.get("education", []):
        # School name (bold, left) + date (right)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        pPr = p._p.get_or_add_pPr()
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right")
        tab.set(qn("w:pos"), "9360")
        tabs.append(tab)
        pPr.append(tabs)
        run = p.add_run(edu.get("school", ""))
        run.bold = True
        run.font.size = Pt(body_size)
        run.font.name = "Arial"

        # Degree (italic) + date
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        pPr = p._p.get_or_add_pPr()
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right")
        tab.set(qn("w:pos"), "9360")
        tabs.append(tab)
        pPr.append(tabs)
        run = p.add_run(edu.get("degree", ""))
        run.italic = True
        run.font.size = Pt(body_size)
        run.font.name = "Arial"
        run2 = p.add_run("\t" + edu.get("date", ""))
        run2.italic = True
        run2.font.size = Pt(body_size)
        run2.font.name = "Arial"

        if edu.get("coursework"):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(sp)
            r = p.add_run("Relevant Coursework: ")
            r.italic = True
            r.font.size = Pt(body_size)
            r.font.name = "Arial"
            _add_runs(p, edu["coursework"], size=body_size)

    # Experience
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(0)
    _add_runs(p, "EXPERIENCE", bold=True, size=sec_size)
    _add_hr(doc)

    for exp in data.get("experience", []):
        # Company + location
        org = exp.get("company", "")
        if exp.get("location"):
            org += f", {exp['location']}"
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        _add_runs(p, org, bold=True, size=body_size)

        # Title + date
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(sp)
        pPr = p._p.get_or_add_pPr()
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right")
        tab.set(qn("w:pos"), "9360")
        tabs.append(tab)
        pPr.append(tabs)
        run = p.add_run(exp.get("title", ""))
        run.italic = True
        run.font.size = Pt(body_size)
        run.font.name = "Arial"
        run2 = p.add_run("\t" + exp.get("date", ""))
        run2.italic = True
        run2.font.size = Pt(body_size)
        run2.font.name = "Arial"

        for bullet in exp.get("bullets", []):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(sp)
            p.paragraph_format.left_indent = Inches(0.15)
            run = p.add_run("• ")
            run.font.size = Pt(body_size)
            run.font.name = "Arial"
            _add_runs(p, bullet, size=body_size)

    # Projects
    if data.get("projects"):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(0)
        _add_runs(p, "PROJECTS", bold=True, size=sec_size)
        _add_hr(doc)

        for proj in data.get("projects", []):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(sp)
            _add_runs(p, proj.get("name", ""), bold=True, size=body_size)
            for bullet in proj.get("bullets", []):
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(sp)
                p.paragraph_format.left_indent = Inches(0.15)
                run = p.add_run("• ")
                run.font.size = Pt(body_size)
                run.font.name = "Arial"
                _add_runs(p, bullet, size=body_size)

    # Skills
    if data.get("skills"):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(0)
        _add_runs(p, "SKILLS", bold=True, size=sec_size)
        _add_hr(doc)

        for skill in data.get("skills", []):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(sp)
            p.paragraph_format.left_indent = Inches(0.15)
            run = p.add_run("• ")
            run.font.size = Pt(body_size)
            run.font.name = "Arial"
            r = p.add_run(skill.get("label", "") + ": ")
            r.bold = True
            r.font.size = Pt(body_size)
            r.font.name = "Arial"
            _add_runs(p, skill.get("content", ""), size=body_size)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()