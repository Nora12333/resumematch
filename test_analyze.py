import json
import os
import sys


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(CURRENT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from services.matcher import ResumeMatcher


def main() -> None:
    resume_text = """
John Doe
Data Engineer

Experience
- Built Python ETL pipelines for analytics workloads and data quality checks.
- Designed SQL data models and improved reporting latency by optimizing queries.
- Deployed Dockerized services and collaborated with ML team on model serving.

Skills
Python, SQL, Docker, FastAPI, NLP
"""

    jd_text = """
We are hiring a Data Engineer.
Requirements:
1. Strong Python and SQL skills for building robust data pipelines.
2. Hands-on experience with Airflow orchestration and cloud platforms (AWS or GCP).
3. Familiarity with Spark and ETL best practices.
4. Good communication and cross-functional collaboration.
"""

    matcher = ResumeMatcher()
    result = matcher.analyze(resume_text=resume_text, jd_text=jd_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
