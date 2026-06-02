
# ResumeMatch

ResumeMatch is a bilingual resume-job matching analyzer that compares a resume with a job description and generates a match score, keyword overlap, and improvement suggestions.

This project was built to help job seekers understand how well their resume matches different roles and identify areas for improvement before applying.

## Features

* Compare resume content with job descriptions
* Generate resume-job match scores
* Show score improvement after resume optimization
* Support bilingual English and Chinese resume analysis
* Identify important keywords and missing skills
* Provide structured suggestions for resume improvement

## Tech Stack

* Backend: Python
* Frontend: JavaScript, HTML, CSS
* Data Processing: pandas
* Text Analysis: keyword matching and similarity scoring
* Version Control: Git and GitHub

## Project Structure

```text
resumematch/
├── backend/      Backend logic and API-related files
├── frontend/     Frontend interface
├── README.md     Project documentation
└── .gitignore    Files excluded from version control
```

## Sample Output

The system compares a resume against different job descriptions and returns a matching score before and after optimization.

| Candidate            | Job Description           | Before Score | After Score | Improvement |
| -------------------- | ------------------------- | -----------: | ----------: | ----------: |
| sample_candidate_001 | Data Analyst - Healthcare |           74 |          95 |         +21 |
| sample_candidate_001 | Data Scientist - Tech     |           69 |          97 |         +28 |
| sample_candidate_001 | BI Analyst                |           78 |          78 |           0 |

## Why This Project Matters

Many job seekers struggle to understand why their resume may not match a job posting well, especially when applying to roles across data analysis, healthcare analytics, and technical fields. ResumeMatch provides a simple way to compare resume content with job requirements and highlight possible improvements.

## Future Improvements

* Add semantic similarity using text embeddings
* Improve section-level resume feedback
* Add more detailed skill gap analysis
* Build a cleaner user interface
* Deploy a public demo version

