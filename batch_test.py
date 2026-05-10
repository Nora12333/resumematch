#!/usr/bin/env python3
"""
Batch testing script for ResumeMatch
Tests 25 resume-JD pairs and records before/after scores
"""

import requests
import json
import time
import csv
from datetime import datetime

API_BASE = "https://resumematch-yjva.onrender.com"

# Test pairs (resume_id, jd_id) - 25 selected pairs
TEST_PAIRS = [
    (1, 1),  # Yunmei - Healthcare Data Analyst (high match)
    (1, 2),  # Yunmei - Data Scientist (medium match)
    (1, 7),  # Yunmei - BI Analyst (medium match)
    (1, 8),  # Yunmei - Quantitative Research (high match)
    (1, 3),  # Yunmei - Marketing Analyst (low match)
    (2, 4),  # Alex - Software Engineer (high match)
    (2, 2),  # Alex - Data Scientist (medium match)
    (2, 7),  # Alex - BI Analyst (medium match)
    (2, 6),  # Alex - Product Manager (low match)
    (2, 5),  # Alex - Financial Analyst (low match)
    (3, 3),  # Sarah - Marketing Analyst (high match)
    (3, 6),  # Sarah - Product Manager (medium match)
    (3, 7),  # Sarah - BI Analyst (medium match)
    (3, 1),  # Sarah - Healthcare Analyst (low match)
    (3, 4),  # Sarah - Software Engineer (low match)
    (4, 5),  # James - Financial Analyst (high match)
    (4, 7),  # James - BI Analyst (medium match)
    (4, 2),  # James - Data Scientist (medium match)
    (4, 6),  # James - Product Manager (low match)
    (4, 4),  # James - Software Engineer (low match)
    (5, 6),  # Maria - Product Manager (high match)
    (5, 3),  # Maria - Marketing Analyst (medium match)
    (5, 7),  # Maria - BI Analyst (medium match)
    (5, 2),  # Maria - Data Scientist (low match)
    (5, 5),  # Maria - Financial Analyst (low match)
]

def load_test_data():
    """Load resumes and JDs"""
    exec(open('/home/claude/test_data.py').read(), globals())
    resumes = {r['id']: r for r in test_data['resumes']}
    jds = {j['id']: j for j in test_data['job_descriptions']}
    return resumes, jds

def analyze_resume(resume_text, jd_text):
    """Call analyze API"""
    try:
        resp = requests.post(
            f"{API_BASE}/api/analyze",
            json={"resume_text": resume_text, "jd_text": jd_text},
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  Analyze error: {e}")
    return None

def generate_resume(resume_text, jd_text, gaps):
    """Call generate API"""
    try:
        resp = requests.post(
            f"{API_BASE}/api/generate",
            json={
                "resume_text": resume_text,
                "jd_text": jd_text,
                "gaps": gaps,
                "mode": "smart_fill"
            },
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  Generate error: {e}")
    return None

def run_batch_test():
    """Run all test pairs and record results"""
    print("Loading test data...")
    
    # Load data inline
    resumes = {
        1: {"name": "Yunmei Zhou (Data/Biostatistics)", "text": """Yunmei Zhou
New York, USA | yunmeizhou2@gmail.com

EDUCATION
New York University - Master of Science in Biostatistics Jun 2026 (Expected)
Harbin Normal University - Bachelor of Science in Applied Statistics Jun 2024

EXPERIENCE
Quality Improvement Analyst Intern, New Alternatives for Children, May 2025 – Dec 2025
• Analyzed 10 years of multi-program service data using SQL, R, and Python to identify key drivers of case outcomes.
• Built logistic regression models showing 1.5× higher odds of successful closure.
• Developed Tableau KPI dashboards for QI leadership review.

Data Analyst Intern, Harbin Guoyun Data Technology, Mar 2022 – Dec 2023
• Processed 10M+ raw ride-hailing records in Python, created 100K+ stratified sample.
• Identified demand concentration with top corridors accounting for 40% of trip volume.
• Designed pricing strategies using A/B testing, driving 10% improvement in GMV.

SKILLS: R, Python, SQL, Stata, SAS, Tableau, MS Office"""},
        2: {"name": "Alex Chen (Software Engineer)", "text": """Alex Chen
San Francisco, CA | alexchen@email.com

EDUCATION
UC Berkeley - Bachelor of Science in Computer Science May 2023

EXPERIENCE
Software Engineer, Stripe, Jun 2023 – Present
• Built RESTful APIs serving 50M+ daily transactions using Python and FastAPI.
• Optimized PostgreSQL queries reducing response time by 40%.
• Developed microservices using Docker and Kubernetes, achieving 99.9% reliability.

Software Engineering Intern, Meta, May 2022 – Aug 2022
• Built React frontend components improving engagement by 15%.
• Wrote unit and integration tests achieving 95% code coverage.
• Improved CI/CD pipeline reducing deployment time by 30%.

SKILLS: Python, JavaScript, Go, Java, SQL, React, FastAPI, Docker, Kubernetes, AWS, PostgreSQL"""},
        3: {"name": "Sarah Kim (Marketing Analytics)", "text": """Sarah Kim
New York, NY | sarahkim@email.com

EDUCATION
NYU Stern - Bachelor of Science in Marketing Analytics May 2024

EXPERIENCE
Marketing Analyst, L'Oreal, Jun 2024 – Present
• Analyzed campaign performance using Google Analytics for $5M+ marketing budget.
• Built competitive analysis reports identifying market trends across demographic segments.
• Created Tableau dashboards presenting monthly insights to senior leadership.

Marketing Research Intern, Nielsen, Jun 2023 – Aug 2023
• Conducted survey-based consumer research with 10,000+ respondents.
• Applied segmentation analysis identifying 5 distinct consumer groups.
• Presented findings to cross-functional teams for product positioning.

SKILLS: Google Analytics, Tableau, Excel, SPSS, Salesforce, HubSpot, A/B testing, segmentation"""},
        4: {"name": "James Liu (Finance)", "text": """James Liu
New York, NY | jamesliu@email.com

EDUCATION
Columbia University - Master of Science in Financial Engineering Dec 2023

EXPERIENCE
Financial Analyst, Goldman Sachs, Jan 2024 – Present
• Built financial models in Excel and Python to value M&A targets, supporting $2B+ in transactions.
• Conducted scenario analysis and sensitivity modeling to assess market risk.
• Prepared investor presentations and data-driven reports for senior management.

Investment Banking Intern, JPMorgan Chase, Jun 2023 – Aug 2023
• Performed DCF and comparable company analysis for 5 deals.
• Built automated reporting tools in Python reducing manual work by 60%.
• Analyzed financial statements to identify investment opportunities.

SKILLS: Excel, Python, Bloomberg, FactSet, SQL, Tableau, DCF, financial modeling"""},
        5: {"name": "Maria Rodriguez (Product Manager)", "text": """Maria Rodriguez
Seattle, WA | mariarodriguez@email.com

EDUCATION
University of Washington - Bachelor of Science in Information Systems Jun 2022

EXPERIENCE
Associate Product Manager, Amazon, Jul 2022 – Present
• Led cross-functional teams of 15+ to ship 3 major features used by 10M+ customers.
• Defined product roadmap and KPIs based on user research and A/B testing.
• Analyzed user behavior using SQL and Tableau, reducing customer churn by 12%.

Product Management Intern, Microsoft, May 2021 – Aug 2021
• Conducted competitive analysis and user interviews for Teams features.
• Created product specs shipped to 50M+ users.
• Analyzed usage metrics to prioritize backlog.

SKILLS: JIRA, Figma, SQL, Tableau, Google Analytics, Excel, A/B testing, user research"""}
    }
    
    jds = {
        1: {"title": "Data Analyst - Healthcare", "text": "Analyze clinical data to support quality improvement. SQL, Python or R required. Tableau or Power BI for dashboards. Statistical modeling and regression analysis preferred. Communicate findings to clinical leadership."},
        2: {"title": "Data Scientist - Tech", "text": "Build ML models at scale. Python with scikit-learn required. SQL and big data tools. Hypothesis testing and A/B experimentation. Feature engineering and model evaluation."},
        3: {"title": "Marketing Data Analyst", "text": "Measure campaign performance. Google Analytics required. Excel and SQL. A/B testing experience. Demographic and behavioral data analysis. Tableau or Power BI preferred."},
        4: {"title": "Software Engineer - Backend", "text": "Build scalable backend systems. Python, Go, or Java. RESTful APIs. SQL and NoSQL databases. Docker, Kubernetes, AWS. CI/CD pipelines and testing."},
        5: {"title": "Financial Analyst", "text": "Support investment decisions. Financial modeling in Excel and Python. DCF and comparable company analysis. Bloomberg or FactSet. Scenario modeling and sensitivity analysis."},
        6: {"title": "Product Manager", "text": "Lead consumer product initiatives. SQL and data analysis. A/B testing and user research. Cross-functional collaboration. KPI definition and product metrics."},
        7: {"title": "Business Intelligence Analyst", "text": "Build data infrastructure and dashboards. Strong SQL skills. Tableau, Looker, or Power BI. Python or R. Data warehousing concepts."},
        8: {"title": "Quantitative Research Analyst", "text": "Conduct quantitative analysis. R, Python, or MATLAB. Regression analysis, time series, causal inference. Survey methodology. Propensity score matching preferred."}
    }

    results = []
    
    print(f"\nStarting batch test of {len(TEST_PAIRS)} pairs...")
    print("=" * 60)
    
    for idx, (resume_id, jd_id) in enumerate(TEST_PAIRS):
        resume = resumes[resume_id]
        jd = jds[jd_id]
        
        print(f"\n[{idx+1}/{len(TEST_PAIRS)}] {resume['name']} → {jd['title']}")
        
        # Step 1: Analyze before
        print("  Analyzing before...")
        before_result = analyze_resume(resume['text'], jd['text'])
        if not before_result:
            print("  FAILED - skipping")
            continue
        
        before_score = before_result.get('overall_score', 0)
        print(f"  Before score: {before_score}%")
        
        # Step 2: Generate optimized resume
        print("  Generating optimized resume...")
        gaps = before_result.get('gaps', [])
        gen_result = generate_resume(resume['text'], jd['text'], gaps)
        if not gen_result:
            print("  Generation FAILED - recording before score only")
            results.append({
                'resume': resume['name'],
                'jd': jd['title'],
                'before_score': before_score,
                'after_score': 'N/A',
                'improvement': 'N/A',
                'skill_score_before': before_result.get('skill_score', 0),
                'exp_score_before': before_result.get('experience_score', 0),
            })
            time.sleep(2)
            continue
        
        # Step 3: Analyze after
        print("  Analyzing after...")
        optimized_text = gen_result.get('optimized_resume', '').replace('[NEW]', '')
        after_result = analyze_resume(optimized_text, jd['text'])
        
        after_score = after_result.get('overall_score', 0) if after_result else 0
        improvement = after_score - before_score
        
        print(f"  After score: {after_score}%")
        print(f"  Improvement: {'+' if improvement >= 0 else ''}{improvement}%")
        
        results.append({
            'resume': resume['name'],
            'jd': jd['title'],
            'before_score': before_score,
            'after_score': after_score,
            'improvement': improvement,
            'skill_score_before': before_result.get('skill_score', 0),
            'exp_score_before': before_result.get('experience_score', 0),
            'skill_score_after': after_result.get('skill_score', 0) if after_result else 0,
            'exp_score_after': after_result.get('experience_score', 0) if after_result else 0,
        })
        
        # Rate limiting
        time.sleep(3)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'/home/claude/batch_results_{timestamp}.csv'
    
    with open(output_file, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    # Print summary
    print("\n" + "=" * 60)
    print("BATCH TEST COMPLETE")
    print("=" * 60)
    
    valid = [r for r in results if r['improvement'] != 'N/A']
    if valid:
        avg_before = sum(r['before_score'] for r in valid) / len(valid)
        avg_after = sum(r['after_score'] for r in valid) / len(valid)
        avg_improvement = sum(r['improvement'] for r in valid) / len(valid)
        
        print(f"Total pairs tested: {len(results)}")
        print(f"Average before score: {avg_before:.1f}%")
        print(f"Average after score: {avg_after:.1f}%")
        print(f"Average improvement: +{avg_improvement:.1f}%")
        print(f"\nResults saved to: {output_file}")
    
    return results

if __name__ == "__main__":
    run_batch_test()
