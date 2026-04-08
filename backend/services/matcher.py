import math
import re
from dataclasses import dataclass


try:
    import spacy
except Exception:  # pragma: no cover - optional dependency in early setup
    spacy = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency in early setup
    SentenceTransformer = None


DEFAULT_SKILL_LIST = {
    "python",
    "sql",
    "airflow",
    "spark",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "etl",
    "machine learning",
    "nlp",
    "pytorch",
    "tensorflow",
    "fastapi",
    "react",
    "tableau",
    "power bi",
    "data modeling",
    "statistics",
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _split_lines(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def _split_requirements(jd_text: str) -> list[str]:
    reqs: list[str] = []
    for line in _split_lines(jd_text):
        cleaned = re.sub(r"^[-*•\d\.\)\s]+", "", line).strip()
        if cleaned:
            reqs.append(cleaned)
    if not reqs:
        reqs = [seg.strip() for seg in re.split(r"[.;]\s+", jd_text) if seg.strip()]
    return reqs


def _split_resume_bullets(resume_text: str) -> list[str]:
    bullets: list[str] = []
    for line in _split_lines(resume_text):
        if re.match(r"^[-*•]", line) or re.match(r"^\d+[\.\)]\s+", line):
            bullets.append(re.sub(r"^[-*•\d\.\)\s]+", "", line).strip())
    if not bullets:
        bullets = [seg.strip() for seg in re.split(r"[.;]\s+", resume_text) if seg.strip()]
    return bullets


@dataclass
class KeywordMatch:
    word: str
    matched: bool
    count_in_jd: int
    first_req_index: int


class ResumeMatcher:
    def __init__(self) -> None:
        self._nlp = None
        self._encoder = None
        if spacy is not None:
            try:
                self._nlp = spacy.load("en_core_web_sm")
            except Exception:
                self._nlp = None
        if SentenceTransformer is not None:
            try:
                self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self._encoder = None

    def analyze(self, resume_text: str, jd_text: str) -> dict:
        jd_keywords = self._extract_keywords(jd_text)
        keyword_matches = self._match_keywords(jd_keywords, resume_text, jd_text)
        keyword_score = self._keyword_score(keyword_matches)

        jd_requirements = _split_requirements(jd_text)
        resume_bullets = _split_resume_bullets(resume_text)
        experience_score = self._experience_score(resume_bullets, jd_requirements)

        gaps = self._build_gaps(keyword_matches)
        keywords = [{"word": item.word, "matched": item.matched} for item in keyword_matches]
        overall_score = int(round(0.4 * keyword_score + 0.6 * experience_score))

        return {
            "overall_score": max(0, min(100, overall_score)),
            "skill_score": max(0, min(100, int(round(keyword_score)))),
            "experience_score": max(0, min(100, int(round(experience_score)))),
            "gaps": gaps,
            "keywords": keywords,
        }

    def _extract_keywords(self, jd_text: str) -> list[str]:
        lowered_jd = _normalize_text(jd_text)
        extracted: set[str] = set()

        for skill in DEFAULT_SKILL_LIST:
            if skill in lowered_jd:
                extracted.add(skill)

        if self._nlp is not None:
            doc = self._nlp(jd_text)
            for chunk in doc.noun_chunks:
                candidate = _normalize_text(chunk.text)
                if len(candidate) < 2:
                    continue
                if candidate in DEFAULT_SKILL_LIST or any(s in candidate for s in DEFAULT_SKILL_LIST):
                    extracted.add(candidate)
            for ent in doc.ents:
                candidate = _normalize_text(ent.text)
                if candidate in DEFAULT_SKILL_LIST or any(s in candidate for s in DEFAULT_SKILL_LIST):
                    extracted.add(candidate)
        else:
            tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\+\#\-/\.]{1,}", jd_text.lower())
            for token in tokens:
                if token in DEFAULT_SKILL_LIST:
                    extracted.add(token)

        return sorted(extracted)

    def _match_keywords(self, keywords: list[str], resume_text: str, jd_text: str) -> list[KeywordMatch]:
        resume_lower = _normalize_text(resume_text)
        jd_requirements = _split_requirements(jd_text)
        jd_lower = _normalize_text(jd_text)

        resume_lemmas = set()
        if self._nlp is not None:
            resume_doc = self._nlp(resume_text)
            resume_lemmas = {tok.lemma_.lower() for tok in resume_doc if tok.lemma_}

        results: list[KeywordMatch] = []
        for kw in keywords:
            kw_lower = _normalize_text(kw)
            exact_match = kw_lower in resume_lower

            lemma_match = False
            if self._nlp is not None:
                kw_doc = self._nlp(kw)
                kw_lemmas = {tok.lemma_.lower() for tok in kw_doc if tok.lemma_}
                lemma_match = any(lemma in resume_lemmas for lemma in kw_lemmas)

            jd_occurrences = len(re.findall(rf"\b{re.escape(kw_lower)}\b", jd_lower))
            first_idx = -1
            for idx, req in enumerate(jd_requirements):
                if kw_lower in _normalize_text(req):
                    first_idx = idx
                    break

            results.append(
                KeywordMatch(
                    word=kw,
                    matched=exact_match or lemma_match,
                    count_in_jd=jd_occurrences,
                    first_req_index=first_idx,
                )
            )
        return results

    @staticmethod
    def _keyword_score(keyword_matches: list[KeywordMatch]) -> float:
        if not keyword_matches:
            return 0.0
        matched = sum(1 for item in keyword_matches if item.matched)
        return (matched / len(keyword_matches)) * 100

    def _experience_score(self, resume_bullets: list[str], jd_requirements: list[str]) -> float:
        if not resume_bullets or not jd_requirements:
            return 0.0

        if self._encoder is not None:
            resume_vecs = self._encoder.encode(resume_bullets)
            jd_vecs = self._encoder.encode(jd_requirements)

            top_scores = []
            for jd_vec in jd_vecs:
                sims = [self._cosine(jd_vec, rv) for rv in resume_vecs]
                top_scores.append(max(sims) if sims else 0.0)
            if not top_scores:
                return 0.0
            return float(sum(top_scores) / len(top_scores) * 100)

        # Fallback: lexical Jaccard proxy if transformer model unavailable.
        top_scores = []
        for req in jd_requirements:
            req_tokens = self._token_set(req)
            sims = []
            for bullet in resume_bullets:
                bullet_tokens = self._token_set(bullet)
                union = req_tokens | bullet_tokens
                score = len(req_tokens & bullet_tokens) / len(union) if union else 0.0
                sims.append(score)
            top_scores.append(max(sims) if sims else 0.0)
        return float(sum(top_scores) / len(top_scores) * 100) if top_scores else 0.0

    @staticmethod
    def _token_set(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z]{2,}", text.lower()))

    @staticmethod
    def _cosine(vec_a, vec_b) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _build_gaps(self, keyword_matches: list[KeywordMatch]) -> list[dict]:
        gaps: list[dict] = []
        for item in keyword_matches:
            if item.matched:
                importance = "covered"
            elif item.count_in_jd >= 2 or (item.first_req_index != -1 and item.first_req_index < 3):
                importance = "required"
            else:
                importance = "nice_to_have"

            gaps.append(
                {
                    "skill": item.word,
                    "importance": importance,
                    "suggestion_zh": self._suggestion_zh(item.word, importance),
                    "suggestion_en": self._suggestion_en(item.word, importance),
                }
            )
        return gaps

    @staticmethod
    def _suggestion_zh(skill: str, importance: str) -> str:
        if importance == "covered":
            return f"你已体现 {skill}，可在相关经历中补充更具体的场景与结果。"
        if importance == "required":
            return f"建议优先在经历要点中补充 {skill} 的真实项目应用，突出与你申请岗位的直接关联。"
        return f"可在技能或项目部分补充 {skill} 的实践证据，作为加分项提升匹配度。"

    @staticmethod
    def _suggestion_en(skill: str, importance: str) -> str:
        if importance == "covered":
            return f"You already show {skill}; add concrete context and outcomes for stronger impact."
        if importance == "required":
            return f"Prioritize adding truthful examples of {skill} in your work bullets to match core requirements."
        return f"Consider adding credible evidence of {skill} in skills or projects as a nice-to-have signal."
