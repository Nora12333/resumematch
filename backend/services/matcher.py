import os
import re
from dataclasses import dataclass

import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import spacy
except Exception:  # pragma: no cover - optional dependency in early setup
    spacy = None


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

HF_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
HF_API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{HF_MODEL_ID}"


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
        if spacy is not None:
            try:
                self._nlp = spacy.load("en_core_web_sm")
            except Exception:
                self._nlp = None

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

    @staticmethod
    def _experience_score(resume_bullets: list[str], jd_requirements: list[str]) -> float:
        """HF embeddings (MiniLM) first; fallback to TF-IDF if API unavailable."""
        if not resume_bullets or not jd_requirements:
            return 0.0

        resume_clean = [b.strip() for b in resume_bullets if b and b.strip()]
        jd_clean = [r.strip() for r in jd_requirements if r and r.strip()]
        if not resume_clean or not jd_clean:
            return 0.0

        hf_score = ResumeMatcher._experience_score_hf(resume_clean, jd_clean)
        if hf_score is not None:
            return hf_score

        return ResumeMatcher._experience_score_tfidf(resume_clean, jd_clean)

    @staticmethod
    def _experience_score_hf(resume_clean: list[str], jd_clean: list[str]) -> float | None:
        token = os.environ.get("HF_TOKEN", "").strip()
        if not token:
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        all_texts = resume_clean + jd_clean
        embeddings: list[list[float]] = []

        try:
            for text in all_texts:
                response = requests.post(
                    HF_API_URL,
                    headers=headers,
                    json={"inputs": text, "options": {"wait_for_model": True}},
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict) and payload.get("error"):
                    return None
                if not isinstance(payload, list) or not payload:
                    return None

                # API can return token-level vectors; mean-pool if needed.
                if isinstance(payload[0], list):
                    if payload and payload[0] and isinstance(payload[0][0], list):
                        token_vectors = payload
                        dim = len(token_vectors[0][0])
                        pooled = [0.0] * dim
                        count = 0
                        for token_vec in token_vectors:
                            if token_vec and isinstance(token_vec[0], list):
                                vec = token_vec[0]
                                if len(vec) == dim:
                                    pooled = [a + b for a, b in zip(pooled, vec)]
                                    count += 1
                        if count == 0:
                            return None
                        embeddings.append([v / count for v in pooled])
                    else:
                        embeddings.append([float(v) for v in payload[0]])
                else:
                    return None
        except (requests.RequestException, ValueError, TypeError):
            return None

        n_r = len(resume_clean)
        resume_vecs = embeddings[:n_r]
        jd_vecs = embeddings[n_r:]
        if not resume_vecs or not jd_vecs:
            return None

        sim_matrix = cosine_similarity(jd_vecs, resume_vecs)
        top_per_req = sim_matrix.max(axis=1)
        return float(top_per_req.mean() * 100.0)

    @staticmethod
    def _experience_score_tfidf(resume_clean: list[str], jd_clean: list[str]) -> float:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            min_df=1,
            max_df=1.0,
            token_pattern=r"(?u)\b\w+\b",
        )
        corpus = resume_clean + jd_clean
        try:
            tfidf = vectorizer.fit_transform(corpus)
        except ValueError:
            return 0.0

        n_r = len(resume_clean)
        x_resume = tfidf[:n_r]
        x_jd = tfidf[n_r:]
        sim_matrix = cosine_similarity(x_jd, x_resume)
        top_per_req = sim_matrix.max(axis=1)
        return float(top_per_req.mean() * 100.0)

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
