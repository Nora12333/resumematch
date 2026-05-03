from dotenv import load_dotenv
load_dotenv("backend/.env", override=True)

from services.llm import analyze_jd, analyze_resume, score_experience, score_skills


class ResumeMatcher:
    def analyze(self, resume_text: str, jd_text: str) -> dict:
        # 第一步：结构化解析
        jd_parsed = analyze_jd(jd_text)
        resume_parsed = analyze_resume(resume_text)

        # 第二步：Eligibility Gate
        eligibility = self._check_eligibility(jd_parsed, resume_parsed)

        # 第三步：技能覆盖分析
        skill_results = self._analyze_skills(jd_parsed, resume_parsed)

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

    def _analyze_skills(self, jd_parsed: dict, resume_parsed: dict) -> dict:
        must_have = jd_parsed.get("must_have", [])
        preferred = jd_parsed.get("preferred", [])
        explicit_skills = jd_parsed.get("explicit_skills", [])

        resume_skill_list = [
            s.strip()
            for s in resume_parsed.get("explicit_skills", [])
            if isinstance(s, str) and s.strip()
        ]
        jd_skill_list = [
            s.strip()
            for s in explicit_skills
            if isinstance(s, str) and s.strip()
        ]

        if not jd_skill_list:
            return {
                "skill_score": 0,
                "skill_status": [],
                "keywords": [],
            }

        llm_matches = score_skills(resume_skill_list, jd_skill_list)

        skill_status = []
        matched_count = 0.0
        total_count = len(jd_skill_list)

        for item in llm_matches:
            skill = item["skill"]
            raw = item.get("status", "missing")
            skill_lower = skill.lower()
            is_must = any(skill_lower in r.lower() for r in must_have)
            is_preferred = any(skill_lower in r.lower() for r in preferred)

            if raw == "covered":
                status = "covered"
                matched_count += 1.0
            elif raw == "partial":
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

        skill_score = int(round(matched_count / total_count * 100)) if total_count > 0 else 0

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
        bullets: list[str] = []
        for exp in resume_parsed.get("experience", []):
            bullets.extend(
                bullet.strip()
                for bullet in exp.get("bullets", [])
                if isinstance(bullet, str) and bullet.strip()
            )
        for proj in resume_parsed.get("projects", []):
            desc = proj.get("description", "")
            if isinstance(desc, str) and desc.strip():
                bullets.append(desc.strip())

        requirements = [
            req.strip()
            for req in (
            jd_parsed.get("must_have", []) +
            jd_parsed.get("preferred", []) +
            jd_parsed.get("responsibilities", []) +
            jd_parsed.get("explicit_skills", [])
            )
            if isinstance(req, str) and req.strip()
        ]

        if not bullets or not requirements:
            return 0.0

        return float(score_experience(bullets, requirements))

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