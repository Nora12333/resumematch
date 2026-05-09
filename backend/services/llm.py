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

try:
    from groq import Groq
except ImportError:
    Groq = None

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

SYSTEM_PROMPT_SMART_FILL = """
You are an expert resume optimizer. Your goal is to improve ATS alignment while keeping the resume truthful, natural, and credible to a human recruiter.

STRATEGY:

1. SUMMARY:
   Write a concise 2-sentence summary after the name/contact section.
   Use the target role and the most relevant JD keywords only when they are clearly supported by the candidate's experience.
   Avoid generic or inflated language.

2. BULLETS:
   Improve bullets using Action + Method/Tool + Result/Purpose.
   Add JD keywords only where they naturally fit the work performed.
   Do not force every bullet to contain keywords.
   Preserve specific metrics, tools, findings, and outcomes from the original resume.

3. SKILLS:
   Reorganize skills into:
   - Programming & Tools
   - Data Skills
   - Languages
   Include only skills that are supported by the resume or clearly implied by the candidate's actual experience.

4. KEYWORD ALIGNMENT:
   Prioritize the most important JD keywords, but avoid keyword stuffing.
   Keywords should improve clarity and relevance, not make the resume sound artificial.

RULES:

1. Never invent facts, metrics, company names, technologies, responsibilities, or achievements.
2. Do not change the nature of the experience.
3. Keep the resume concise and approximately the same length.
4. Mark ALL changes with paired delimiters [NEW] ... [NEW].
5. Output valid JSON only. No markdown code fences before or after the JSON.

Required JSON shape:
{
  "optimized_resume": "full text with [NEW] markers",
  "changes": [
    {"original": "...", "updated": "...", "reason": "brief rationale"}
  ]
}
"""




def _get_api_key() -> str | None:
    _load_env()
    raw = os.environ.get("ANTHROPIC_API_KEY", "")
    key = raw.strip().lstrip("\ufeff").strip('"').strip("'")
    return key or None


def _get_groq_key() -> str | None:
    _load_env()
    return os.environ.get("GROQ_API_KEY", "").strip() or None


def _get_groq_client():
    key = _get_groq_key()
    if not key or Groq is None:
        return None
    return Groq(api_key=key)


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

    anthropic_key = _get_api_key()
    groq_key = _get_groq_key()
    raw_text = ""
    if anthropic_key and anthropic is not None:
        client = anthropic.Anthropic(api_key=anthropic_key)
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
    elif groq_key and Groq is not None:
        gclient = Groq(api_key=groq_key)
        completion = gclient.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=32,
        )
        raw_text = (completion.choices[0].message.content or "").strip()
    else:
        raise RuntimeError("No API key available")

    if not raw_text:
        raise ValueError("Empty response from Claude while scoring experience")

    match = re.search(r"\d+", raw_text)
    if not match:
        raise ValueError(f"Claude did not return a numeric score: {raw_text}")
    score = int(match.group(0))
    return float(max(0, min(100, score)))


def score_skills(
    resume_skills: list[str], jd_skills: list[str]
) -> list[dict[str, str]]:
    """
    1) covered: the resume explicitly names this skill OR uses a clear equivalent (e.g. "Tableau dashboards" covers "data visualization", "logistic regression" covers "statistical modeling", "A/B testing" covers "testing methodologies")
    2) partial: resume has related experience but not a direct match
    3) missing: no relevant experience at all
    """
    _load_env()

    clean_resume = [
        s.strip() for s in resume_skills if isinstance(s, str) and s.strip()
    ]
    clean_jd = [s.strip() for s in jd_skills if isinstance(s, str) and s.strip()]
    if not clean_jd:
        return []

    resume_block = "\n".join(f"- {s}" for s in clean_resume) or "(none listed)"
    jd_block = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(clean_jd))
    user_prompt = f"""You compare each JD skill against the resume's explicit skill list only.

Resume skills (explicit list only — this is the only evidence you may use):
{resume_block}

JD skills to evaluate (evaluate EVERY item below, in order; jd_skill must be the exact string from the list):
{jd_block}

Strict rules — apply independently to EACH jd_skill; do not infer from "overall strong candidate":
1) covered: ONLY if the resume skill list explicitly names this tool/skill (or a standard same-thing alias, e.g. "JS" when the JD asks "JavaScript", "K8s" for "Kubernetes"). The name or alias must clearly refer to the same capability. Generic phrases alone are NOT enough.
2) partial: the resume lists something semantically related or in the same family, but it is NOT the same tool/skill as named in the JD. Example: JD asks for "data visualization tools" and the resume lists "Tableau" → partial (related domain, not an exact match to the JD wording). Another example: JD asks "Python" and resume lists "R" → partial if you judge same broad analytics stack but not the requested tool.
3) missing: the resume skill list does not mention this skill and nothing in the list reasonably maps to partial per rule 2.
4) No halo effect: never upgrade a skill because the candidate looks generally senior or the list is long. Judge each jd_skill in isolation. When unsure between covered and partial, choose partial; when unsure between partial and missing, choose missing.

Return ONLY valid JSON, no markdown:
{{
  "matches": [
    {{"jd_skill": "<exact string from JD list>", "status": "covered|partial|missing"}}
  ]
}}

The "matches" array MUST have exactly {len(clean_jd)} objects, same order as the numbered JD list above."""

    anthropic_key = _get_api_key()
    groq_key = _get_groq_key()
    if anthropic_key and anthropic is not None:
        client = anthropic.Anthropic(api_key=anthropic_key)
        try:
            message = client.messages.create(
                model=MODEL_ID,
                max_tokens=4096,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as e:
            if _is_anthropic_error(e):
                raise RuntimeError(f"Claude API error: {e}") from e
            raise
        raw_text = "".join(block.text for block in message.content if block.type == "text")
    elif groq_key and Groq is not None:
        gclient = Groq(api_key=groq_key)
        completion = gclient.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=4096,
        )
        raw_text = completion.choices[0].message.content or ""
    else:
        raise RuntimeError("No API key available")

    if not raw_text.strip():
        raise ValueError("Empty response from Claude while scoring skills")

    data = _parse_llm_json(raw_text)
    matches = data.get("matches")
    if not isinstance(matches, list):
        raise ValueError("Claude skill response missing 'matches' array")

    valid_status = frozenset({"covered", "partial", "missing"})
    lookup: dict[str, str] = {}
    for row in matches:
        if not isinstance(row, dict):
            continue
        key = row.get("jd_skill")
        if not isinstance(key, str) or not key.strip():
            continue
        st = row.get("status", "missing")
        norm = st.strip().lower() if isinstance(st, str) else "missing"
        if norm not in valid_status:
            norm = "missing"
        lookup[key.strip().lower()] = norm

    out: list[dict[str, str]] = []
    for i, jd in enumerate(clean_jd):
        status = "missing"
        if i < len(matches) and isinstance(matches[i], dict):
            row = matches[i]
            row_jd = row.get("jd_skill", "")
            row_jd_norm = row_jd.strip().lower() if isinstance(row_jd, str) else ""
            if row_jd_norm == jd.lower():
                st = row.get("status", "missing")
                if isinstance(st, str) and st.strip().lower() in valid_status:
                    status = st.strip().lower()
        if status == "missing" and jd.lower() in lookup:
            status = lookup[jd.lower()]
        out.append({"skill": jd, "status": status})

    return out


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

    anthropic_key = _get_api_key()
    groq_key = _get_groq_key()
    if anthropic_key and anthropic is not None:
        client = anthropic.Anthropic(api_key=anthropic_key)
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
    elif groq_key and Groq is not None:
        gclient = Groq(api_key=groq_key)
        completion = gclient.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=8192,
        )
        raw_text = completion.choices[0].message.content or ""
    else:
        raise RuntimeError("No API key available")

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

    anthropic_key = _get_api_key()
    groq_key = _get_groq_key()
    if anthropic_key and anthropic is not None:
        client = anthropic.Anthropic(api_key=anthropic_key)
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
    elif groq_key and Groq is not None:
        gclient = Groq(api_key=groq_key)
        completion = gclient.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=1000,
        )
        raw_text = completion.choices[0].message.content or ""
    else:
        raise RuntimeError("No API key available")

    return _parse_llm_json(raw_text)


def analyze_resume(resume_text: str) -> dict[str, Any]:
    """
    用 Claude 解析简历，返回结构化 JSON。
    """
    _load_env()

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

    anthropic_key = _get_api_key()
    groq_key = _get_groq_key()
    if anthropic_key and anthropic is not None:
        client = anthropic.Anthropic(api_key=anthropic_key)
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
    elif groq_key and Groq is not None:
        gclient = Groq(api_key=groq_key)
        completion = gclient.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=2000,
        )
        raw_text = completion.choices[0].message.content or ""
    else:
        raise RuntimeError("No API key available")

    return _parse_llm_json(raw_text)
def generate_resume_structured(
    resume_text: str,
    jd_text: str,
    gaps: list[dict[str, Any]],
    mode: Literal["smart_fill", "full_rewrite"],
) -> dict[str, Any]:
    _load_env()

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

    anthropic_key = _get_api_key()
    groq_key = _get_groq_key()
    if anthropic_key and anthropic is not None:
        client = anthropic.Anthropic(api_key=anthropic_key)
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=8192,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = "".join(block.text for block in message.content if block.type == "text")
    elif groq_key and Groq is not None:
        gclient = Groq(api_key=groq_key)
        completion = gclient.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=8192,
        )
        raw_text = completion.choices[0].message.content or ""
    else:
        raise RuntimeError("No API key available")

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

def generate_gap_suggestions(gaps: list[dict], jd_text: str, resume_text: str) -> list[dict]:
    """Generate intelligent gap recommendations based on JD context."""
    _load_env()
    anthropic_key = _get_api_key()
    groq_key = _get_groq_key()
    if not ((anthropic_key and anthropic is not None) or (groq_key and Groq is not None)):
        return gaps
    
    gaps_block = "\n".join(f"- {g['skill']} ({g['importance']})" for g in gaps if g.get('importance') != 'covered')
    
    user_prompt = f"""You are a resume advisor. For each skill gap below, write a SHORT, specific recommendation (1 sentence max) explaining:
1. WHY it's a gap (what the JD expects vs what the resume shows)
2. WHAT to do about it (only if the candidate actually has the experience)

Be honest and specific. Don't recommend adding skills the candidate clearly doesn't have.

Job Description:
{jd_text[:1500]}

Resume (summary):
{resume_text[:1500]}

Skill gaps to analyze:
{gaps_block}

Return ONLY valid JSON, no markdown:
{{
  "recommendations": [
    {{"skill": "skill name", "recommendation": "specific 1-sentence recommendation"}}
  ]
}}"""

    try:
        if anthropic_key and anthropic is not None:
            client = anthropic.Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model=MODEL_ID,
                max_tokens=1000,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = "".join(b.text for b in message.content if b.type == "text")
        elif groq_key and Groq is not None:
            gclient = Groq(api_key=groq_key)
            completion = gclient.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=1000,
            )
            raw = completion.choices[0].message.content or ""
        else:
            return gaps
        data = _parse_llm_json(raw)
        recs = {r["skill"].lower(): r["recommendation"] for r in data.get("recommendations", [])}
        
        for gap in gaps:
            skill_lower = gap.get("skill", "").lower()
            if skill_lower in recs:
                gap["suggestion_en"] = recs[skill_lower]
        return gaps
    except Exception as e:
        return gaps