# getjob4u

Free career toolkit for **AI / ML / Data Science** job seekers.

A complete FastAPI + SQLite web app with 6 tools — built to run cheaply, deploy easily, and grow over time.

## What's inside

| Feature | Route | Description |
|---|---|---|
| ATS Resume Scanner | `/ats-scanner` | Upload PDF / DOCX / TXT, get a 0-100 ATS score with role-specific keyword analysis, breakdown across 6 dimensions, and actionable fixes. Rule-based — no API costs. |
| Interview Tips | `/interview-tips` | 35+ curated tips across General Strategy, ML Fundamentals, Deep Learning, LLMs/GenAI, Statistics, SQL/Coding, and Behavioral. |
| Cold Email & LinkedIn DM Generator | `/email-generator` | 10 templates (5 email + 5 LinkedIn). Fill the slots, copy the message. Referrals, recruiter replies, alumni outreach, follow-ups. |
| YouTube + Free Courses | `/youtube-resources` | 30+ hand-picked YouTube channels organized by topic + 7 free courses worth your time. |
| Sample Resumes | `/sample-resumes` | 3 ATS-friendly templates: Fresher Data Scientist, Mid-level ML Engineer, AI/LLM Engineer. Copy-to-clipboard. |
| Career Roadmap | `/career-roadmap` | Month-by-month plans for Data Scientist (9-12 mo), ML Engineer (12-15 mo), AI Engineer (6-9 mo). |
| Feedback Form | `/feedback` | Star rating + categorized feedback. Stored in SQLite. |
| Question of the Day | `/api/daily-question` | Random interview question, refreshable on the home page. |

## Tech stack

- **Backend:** FastAPI (Python 3.10+)
- **Templates:** Jinja2
- **DB:** SQLite (via SQLAlchemy)
- **Package manager:** `uv`
- **Frontend:** Vanilla HTML / CSS / JS (no framework, no build step)
- **Resume parsing:** PyPDF2, python-docx
- **AI features:** Rule-based — **zero API costs**

## Running locally

```bash
# 1. Clone / cd into the project
cd first_project

# 2. Install dependencies (uv reads pyproject.toml)
uv sync

# 3. Run the dev server
uv run uvicorn main:app --reload --port 8000
```

Open <http://127.0.0.1:8000>.

### API docs

FastAPI auto-generates Swagger UI at <http://127.0.0.1:8000/docs>.

## Project structure

```
first_project/
├── main.py                  # FastAPI app + routes
├── database.py              # SQLAlchemy models (Feedback, ATSScan, GeneratedEmail)
├── ats_scorer.py            # Rule-based ATS scoring engine
├── email_generator.py       # Cold email + LinkedIn DM templates
├── pyproject.toml           # uv-managed dependencies
├── uv.lock                  # Lockfile
├── data/                    # JSON data (interview tips, YouTube, resumes, roadmaps)
│   ├── interview_tips.json
│   ├── youtube_channels.json
│   ├── sample_resumes.json
│   └── career_roadmap.json
├── templates/               # Jinja2 HTML (base + 8 pages)
├── static/
│   ├── css/style.css        # Design system + all page styles
│   └── js/                  # Vanilla JS modules (ATS, email, feedback, tabs, copy)
├── uploads/                 # (unused — resumes never persisted)
└── getjob4u.db              # SQLite database (created on first run)
```

## Adding new content

Most content is JSON-driven — no code changes needed.

| To add… | Edit | Then… |
|---|---|---|
| New interview tip | `data/interview_tips.json` → category → `tips` | Refresh `/interview-tips` |
| New YouTube channel | `data/youtube_channels.json` → category → `channels` | Refresh `/youtube-resources` |
| New sample resume | `data/sample_resumes.json` → `resumes` | Refresh `/sample-resumes` |
| New ATS role + keywords | `ats_scorer.py` → `ROLE_KEYWORDS` + `available_roles()` | Restart server |
| New cold-email template | `email_generator.py` → `COLD_EMAIL_TEMPLATES` or `LINKEDIN_DM_TEMPLATES` + `available_templates()` | Restart server |

## ATS scoring methodology

The score is weighted across 6 dimensions:

| Dimension | Weight | What it measures |
|---|---|---|
| Keywords | 30% | Role-specific keyword match |
| Quantified impact | 20% | Numbers, percentages, metrics |
| Sections | 15% | Standard resume sections present (Experience, Education, Skills, Projects, Summary, Certifications, Contact) |
| Action verbs | 15% | Strong verbs (built, deployed, optimized, led, scaled, etc.) |
| Contact info | 10% | Email, phone, LinkedIn, GitHub |
| Length | 10% | 400-800 words considered ideal |

All scoring is **deterministic and rule-based** — no LLM calls, no API costs.

## Deployment to AWS

See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for a full step-by-step guide covering:

1. **AWS Elastic Beanstalk** (recommended — free tier eligible)
2. **AWS EC2 + nginx + systemd** (more control, free tier eligible)
3. **AWS App Runner** (zero-ops, pay-per-use)
4. **Cost-saving tips**: Free tier limits, SQLite → RDS migration path, S3 for uploads.

## Roadmap (future features)

These are intentionally not built yet — easy to add as v2:

- **Skill Gap Analyzer** — given a target role + your resume, recommend the top 5 skills to learn.
- **Job Application Tracker** — log applications, track status, follow-up reminders.
- **Mock Interview Q&A bank** — categorized question bank with sample answers.
- **Resume PDF download** — generate PDF from sample resume templates.
- **Salary Insights** — static data table per role + experience.
- **Email templates for Twitter/X DM** — same generator, new medium.
- **GitHub OAuth login** — optional, lets users save their ATS scan history.
- **Admin dashboard** — view feedback submissions, ATS scan stats.

## License

MIT (or your choice — add a LICENSE file if you publish).
