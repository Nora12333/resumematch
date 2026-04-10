import os
from dotenv import load_dotenv
load_dotenv("backend/.env", override=True)
import re


from sklearn.metrics.pairwise import cosine_similarity

from services.llm import analyze_jd, analyze_resume



def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


from huggingface_hub import InferenceClient

def _get_embedding(text: str, token: str) -> list[float] | None:
    try:
        client = InferenceClient(
            model="sentence-transformers/all-MiniLM-L6-v2",
            token=token
        )
        result = client.feature_extraction(text)
        # result 是 numpy array，转成 list
        if hasattr(result, 'tolist'):
            vec = result.tolist()
            # 如果是二维（token-level），mean pool
            if vec and isinstance(vec[0], list):
                dim = len(vec[0])
                pooled = [sum(v[i] for v in vec) / len(vec) for i in range(dim)]
                return pooled
            return vec
        return None
    except Exception as e:
        return None


class ResumeMatcher:
    def analyze(self, resume_text: str, jd_text: str) -> dict:
        # 第一步：结构化解析
        jd_parsed = analyze_jd(jd_text)
        resume_parsed = analyze_resume(resume_text)

        # 第二步：Eligibility Gate
        eligibility = self._check_eligibility(jd_parsed, resume_parsed)

        # 第三步：技能覆盖分析
        skill_results = self._analyze_skills(jd_parsed, resume_parsed, resume_text)

        # 第四步：经历对齐（细粒度矩阵）
        experience_score = self._experience_score_matrix(
            resume_parsed, jd_parsed
        )

        # 第五步：动态权重评分
        overall_score = self._calculate_score(skill_results, experience_score, jd_parsed)

        # 第六步：构建 gaps
        gaps = self._build_gaps(skill_results)

        return {
            "overall_score": max(0, min(100, overall_score)),
            "skill_score": skill_results["skill_score"],
            "experience_score": max(0, min(100, int(round(experience_score)))),
            "eligibility": eligibility,
            "skill_status": skill_results["skill_status"],
            "gaps": gaps,
            "keywords": skill_results["keywords"],
        }

    def _check_eligibility(self, jd_parsed: dict, resume_parsed: dict) -> dict:
        results = {}

        # 工作授权
        if jd_parsed.get("authorization_required"):
            results["authorization"] = "unknown"

        # 地点
        loc = jd_parsed.get("location_requirement", "unknown")
        if loc and loc != "unknown":
            results["location"] = loc

        # 学历（简单判断）
        edu = resume_parsed.get("education", [])
        results["has_education"] = len(edu) > 0

        return results

    def _analyze_skills(
        self, jd_parsed: dict, resume_parsed: dict, resume_text: str
    ) -> dict:
        resume_lower = _normalize_text(resume_text)
        resume_skills = {s.lower() for s in resume_parsed.get("explicit_skills", [])}

        must_have = jd_parsed.get("must_have", [])
        preferred = jd_parsed.get("preferred", [])
        explicit_skills = jd_parsed.get("explicit_skills", [])

        skill_status = []
        matched_count = 0
        total_count = len(explicit_skills)

        for skill in explicit_skills:
            skill_lower = skill.lower()
            in_resume = skill_lower in resume_lower or skill_lower in resume_skills

            # 判断重要性
            is_must = any(skill_lower in r.lower() for r in must_have)
            is_preferred = any(skill_lower in r.lower() for r in preferred)

            if in_resume:
                status = "covered"
                matched_count += 1
            else:
                # 检查语义相近（简单：查 resume_skills 有无相关词）
                partial = any(
                    skill_lower in s or s in skill_lower
                    for s in resume_skills
                )
                if partial:
                    status = "partial"
                    matched_count += 0.5
                else:
                    status = "missing_required" if is_must else "missing_optional"

            skill_status.append({
                "skill": skill,
                "status": status,
                "is_must": is_must,
                "is_preferred": is_preferred,
            })

        skill_score = int((matched_count / total_count * 100)) if total_count > 0 else 0

        keywords = [
            {"word": s["skill"], "matched": s["status"] == "covered"}
            for s in skill_status
        ]

        return {
            "skill_score": skill_score,
            "skill_status": skill_status,
            "keywords": keywords,
        }

    def _experience_score_matrix(
        self, resume_parsed: dict, jd_parsed: dict
    ) -> float:
        # 收集所有简历 bullets
        bullets = []
        for exp in resume_parsed.get("experience", []):
            bullets.extend(exp.get("bullets", []))
        for proj in resume_parsed.get("projects", []):
            desc = proj.get("description", "")
            if desc:
                bullets.append(desc)
        

        requirements = (
            jd_parsed.get("must_have", []) +
            jd_parsed.get("preferred", []) +
            jd_parsed.get("responsibilities", []) +
            jd_parsed.get("explicit_skills", [])
        )
       

        if not bullets or not requirements:
            return 0.0

        hf_token = os.environ.get("HF_TOKEN", "").strip()
        if hf_token:
            score = self._hf_matrix_score(bullets, requirements, hf_token)
            if score is not None:
                return score

        # fallback: TF-IDF
        return self._tfidf_score(bullets, requirements)

    def _hf_matrix_score(
        self, bullets: list[str], requirements: list[str], token: str
    ) -> float | None:
        all_texts = bullets + requirements
        embeddings = []
        for text in all_texts:
            emb = _get_embedding(text, token)
            if emb is None:
                return None
            embeddings.append(emb)

        n_b = len(bullets)
        bullet_vecs = embeddings[:n_b]
        req_vecs = embeddings[n_b:]

        # 每条 requirement 找最强匹配的 bullet
        sim_matrix = cosine_similarity(req_vecs, bullet_vecs)
        top_per_req = sim_matrix.max(axis=1)
        return float(top_per_req.mean() * 100)

    def _tfidf_score(self, bullets: list[str], requirements: list[str]) -> float:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(lowercase=True, min_df=1, token_pattern=r"(?u)\b\w+\b")
        corpus = bullets + requirements
        try:
            tfidf = vectorizer.fit_transform(corpus)
        except ValueError:
            return 0.0
        n_b = len(bullets)
        sim_matrix = cosine_similarity(tfidf[n_b:], tfidf[:n_b])
        return float(sim_matrix.max(axis=1).mean() * 100)

    def _calculate_score(
        self, skill_results: dict, experience_score: float, jd_parsed: dict
    ) -> int:
        # 动态权重：根据 JD 特征调整
        must_have = jd_parsed.get("must_have", [])
        seniority = jd_parsed.get("seniority", "mid")

        # 技能要求越多，技能权重越高
        skill_weight = 0.5 if len(must_have) > 5 else 0.4

        # entry/intern 级别降低经历权重
        if seniority in ["intern", "entry"]:
            skill_weight = 0.5
        
        exp_weight = 1 - skill_weight

        score = skill_weight * skill_results["skill_score"] + exp_weight * experience_score
        return int(round(score))

    def _build_gaps(self, skill_results: dict) -> list[dict]:
        gaps = []
        for item in skill_results["skill_status"]:
            status = item["status"]
            skill = item["skill"]
            is_must = item["is_must"]

            if status == "covered":
                importance = "covered"
            elif status == "partial":
                importance = "partial"
            elif status == "missing_required":
                importance = "required"
            else:
                importance = "nice_to_have"

            gaps.append({
                "skill": skill,
                "importance": importance,
                "is_must": is_must,
                "suggestion_zh": self._suggestion_zh(skill, importance),
                "suggestion_en": self._suggestion_en(skill, importance),
            })
        return gaps

    @staticmethod
    def _suggestion_zh(skill: str, importance: str) -> str:
        if importance == "covered":
            return f"你已体现 {skill}，可补充更具体的场景与量化结果。"
        if importance == "partial":
            return f"你有相关经历，建议在简历中更明确地提及 {skill}。"
        if importance == "required":
            return f"这是岗位必须要求，建议补充 {skill} 的真实项目经验。"
        return f"可在技能或项目部分补充 {skill} 的实践证据作为加分项。"

    @staticmethod
    def _suggestion_en(skill: str, importance: str) -> str:
        if importance == "covered":
            return f"You show {skill}; add concrete outcomes for stronger impact."
        if importance == "partial":
            return f"You have related experience; make {skill} more explicit in your bullets."
        if importance == "required":
            return f"This is a must-have; add truthful examples of {skill} to your resume."
        return f"Consider adding credible evidence of {skill} as a nice-to-have signal."