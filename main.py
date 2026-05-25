"""getjob4u — FastAPI app entrypoint.

Run locally:  uv run uvicorn main:app --reload
"""
from __future__ import annotations

import io
import json
import os
import random
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, Depends, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

import ats_scorer
import email_generator
from database import (
    ATSScan,
    AdminUser,
    Feedback,
    GeneratedEmail,
    get_db,
    init_db,
    verify_password,
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

SESSION_COOKIE = "g4u_admin_session"
SESSION_TTL_HOURS = 12
# In-memory session store. For a single-instance free hosting plan this is
# enough; swap for redis/db if you scale horizontally.
_SESSIONS: dict[str, dict] = {}


app = FastAPI(
    title="getjob4u",
    description="Free AI/ML/DS job seeker toolkit - Resume ATS scanner, interview prep, cold email templates, and career roadmap",
    version="1.1.0",
    docs_url=None,
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _load_json(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- Admin session

def _create_session(admin: AdminUser) -> str:
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = {
        "admin_id": admin.id,
        "username": admin.username,
        "expires_at": datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS),
    }
    return token


def _get_session(token: str | None) -> dict | None:
    if not token:
        return None
    sess = _SESSIONS.get(token)
    if not sess:
        return None
    if sess["expires_at"] < datetime.utcnow():
        _SESSIONS.pop(token, None)
        return None
    return sess


def _require_admin(session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    sess = _get_session(session_token)
    if not sess:
        raise HTTPException(status_code=303, detail="Login required", headers={"Location": "/admin/login"})
    return sess


# ---------------------------------------------------------------- Pages

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    tips_data = _load_json("interview_tips.json")
    daily_question = random.choice(tips_data["daily_questions"])
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "daily_question": daily_question,
            "page_title": "getjob4u — Land Your AI/ML/DS Job",
            "page_description": "Free career toolkit for AI, ML, and Data Science job seekers. Score your resume, prep for interviews, and land your dream job.",
            "og_url": "/",
            "canonical_url": "/",
            "page_category": "home",
        },
    )


@app.get("/ats-scanner", response_class=HTMLResponse)
def ats_scanner_page(request: Request):
    return templates.TemplateResponse(
        request,
        "ats_scanner.html",
        {
            "roles": ats_scorer.available_roles(),
            "page_title": "Free ATS Resume Scanner - getjob4u",
            "page_description": "Free AI-powered ATS resume scanner. Check your resume against role keywords or a specific job description. Get an instant ATS score, missing keywords, and concrete fixes.",
            "keywords": "ATS scanner, resume optimizer, resume checker, ATS friendly resume, keywords optimizer, job description matcher",
            "og_url": "/ats-scanner",
            "canonical_url": "/ats-scanner",
            "page_category": "ats_scanner",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "ATS Scanner", "url": "/ats-scanner"},
            ],
        },
    )


@app.get("/interview-tips", response_class=HTMLResponse)
def interview_tips_page(request: Request):
    data = _load_json("interview_tips.json")
    return templates.TemplateResponse(
        request,
        "interview_tips.html",
        {
            "categories": data["categories"],
            "page_title": "AI/ML/DS Interview Tips & Questions - getjob4u",
            "page_description": "Master your AI, ML, and Data Science interviews. Daily questions, behavioral tips, technical prep, and expert guidance for landing your dream role.",
            "keywords": "interview questions, behavioral interview, technical interview, data science interview, ML interview, AI interview",
            "og_url": "/interview-tips",
            "canonical_url": "/interview-tips",
            "page_category": "interview_tips",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Interview Tips", "url": "/interview-tips"},
            ],
        },
    )


@app.get("/youtube-resources", response_class=HTMLResponse)
def youtube_page(request: Request):
    data = _load_json("youtube_channels.json")
    return templates.TemplateResponse(
        request,
        "youtube_resources.html",
        {
            "categories": data["categories"],
            "courses": data["free_courses"],
            "page_title": "Free AI/ML/DS Learning Resources - YouTube & Courses",
            "page_description": "Curated free YouTube channels and courses for AI, ML, and Data Science learning. Top creators and structured learning paths.",
            "keywords": "free courses, YouTube channels, machine learning courses, data science courses, AI learning",
            "og_url": "/youtube-resources",
            "canonical_url": "/youtube-resources",
            "page_category": "youtube_resources",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Learning Resources", "url": "/youtube-resources"},
            ],
        },
    )


@app.get("/blogs", response_class=HTMLResponse)
def blogs_page(request: Request):
    data = _load_json("blogs.json")
    return templates.TemplateResponse(
        request,
        "blogs.html",
        {
            "categories": data["categories"],
            "newsletters": data["newsletters"],
            "page_title": "Best AI / ML / Data Science Blogs - getjob4u",
            "page_description": "Hand-picked AI, ML, and Data Science blogs from Medium, Distill, Hugging Face, Netflix, Uber, and more. Read what practitioners actually read.",
            "keywords": "AI blogs, ML blogs, data science blogs, Medium AI, Towards Data Science, deep learning blogs, MLOps blogs",
            "og_url": "/blogs",
            "canonical_url": "/blogs",
            "page_category": "blogs",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Blogs", "url": "/blogs"},
            ],
        },
    )


@app.get("/email-generator", response_class=HTMLResponse)
def email_generator_page(request: Request):
    return templates.TemplateResponse(
        request,
        "email_generator.html",
        {
            "templates": email_generator.available_templates(),
            "page_title": "Cold Email & LinkedIn Message Generator - getjob4u",
            "page_description": "Generate personalized cold emails and LinkedIn DMs for job seekers. Templates for referrals, applications, follow-ups, and networking.",
            "keywords": "cold email templates, LinkedIn templates, networking messages, job search templates",
            "og_url": "/email-generator",
            "canonical_url": "/email-generator",
            "page_category": "email_generator",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Cold Email Generator", "url": "/email-generator"},
            ],
        },
    )


@app.get("/sample-resumes", response_class=HTMLResponse)
def sample_resumes_page(request: Request):
    data = _load_json("sample_resumes.json")
    return templates.TemplateResponse(
        request,
        "sample_resumes.html",
        {
            "resumes": data["resumes"],
            "tips": data["general_tips"],
            "page_title": "Sample AI/ML/DS Resumes - Free Resume Templates",
            "page_description": "Download free sample resumes for Data Scientists, ML Engineers, and AI specialists. ATS-optimized templates and best practices.",
            "keywords": "resume templates, sample resumes, data science resume, ML engineer resume",
            "og_url": "/sample-resumes",
            "canonical_url": "/sample-resumes",
            "page_category": "sample_resumes",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Sample Resumes", "url": "/sample-resumes"},
            ],
        },
    )


@app.get("/career-roadmap", response_class=HTMLResponse)
def roadmap_page(request: Request):
    data = _load_json("career_roadmap.json")
    return templates.TemplateResponse(
        request,
        "career_roadmap.html",
        {
            "roadmaps": data["roadmaps"],
            "page_title": "AI/ML/DS Career Roadmap - Learning Paths & Milestones",
            "page_description": "Step-by-step career roadmaps for Data Scientists and ML Engineers. Learn skills, milestones, and resources for each level.",
            "keywords": "career roadmap, learning path, data science skills, machine learning career",
            "og_url": "/career-roadmap",
            "canonical_url": "/career-roadmap",
            "page_category": "career_roadmap",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Career Roadmap", "url": "/career-roadmap"},
            ],
        },
    )


@app.get("/python-questions", response_class=HTMLResponse)
def python_questions_page(request: Request):
    data = _load_json("python_questions.json")
    return templates.TemplateResponse(
        request,
        "python_questions.html",
        {
            "questions": data["questions"],
            "categories": data["categories"],
            "page_title": "100 Most Asked Python Coding Interview Questions (FAANG) - getjob4u",
            "page_description": "Top 100 Python coding interview questions asked at FAANG companies — Google, Amazon, Meta, Apple, Microsoft, Netflix. Each with a worked Python solution you can reveal, copy, and study. Free, no signup.",
            "keywords": "Python coding interview questions, FAANG Python questions, Python LeetCode, Blind 75 Python, NeetCode 150 Python, Google Python interview, Amazon Python interview, Meta Python interview",
            "og_url": "/python-questions",
            "canonical_url": "/python-questions",
            "page_category": "python_questions",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Python Coding Questions", "url": "/python-questions"},
            ],
        },
    )


@app.get("/feedback", response_class=HTMLResponse)
def feedback_page(request: Request):
    return templates.TemplateResponse(
        request,
        "feedback.html",
        {
            "page_title": "Share Feedback - getjob4u",
            "page_description": "Help us improve getjob4u. Share your feedback, suggestions, and feature requests.",
            "og_url": "/feedback",
            "canonical_url": "/feedback",
            "page_category": "feedback",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Feedback", "url": "/feedback"},
            ],
        },
    )


@app.get("/free-ai-tools", response_class=HTMLResponse)
def free_ai_tools_page(request: Request):
    data = _load_json("free_ai_tools.json")
    return templates.TemplateResponse(
        request,
        "free_ai_tools.html",
        {
            "categories": data["categories"],
            "intro": data.get("intro", ""),
            "page_title": "50+ Free AI Tools (Video, PDF, Image, Code, Voice) - getjob4u",
            "page_description": "Hand-picked free AI tools across video generation, PDF tools, image gen, voice, code, presentations and more. All links verified, every tool has a real free tier.",
            "keywords": "free AI tools, free video generation AI, free PDF AI tools, free image generation, free AI coding tools, free AI voice generator, free chatbot",
            "og_url": "/free-ai-tools",
            "canonical_url": "/free-ai-tools",
            "page_category": "free_ai_tools",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Free AI Tools", "url": "/free-ai-tools"},
            ],
        },
    )


@app.get("/free-courses", response_class=HTMLResponse)
def free_courses_page(request: Request):
    data = _load_json("free_courses.json")
    return templates.TemplateResponse(
        request,
        "free_courses.html",
        {
            "platforms": data["platforms"],
            "intro": data.get("intro", ""),
            "page_title": "Free AI/ML/Data Science Courses with Certificates - getjob4u",
            "page_description": "Free online courses with certificates in AI, ML, Data Science, Data Analytics, and Generative AI from IBM, Google, Microsoft, Coursera, Udemy, freeCodeCamp, Kaggle, Hugging Face and more.",
            "keywords": "free AI courses with certificate, free ML courses, free data science certificate, free Udemy courses, free Coursera, IBM Cognitive Class, Great Learning Academy, Simplilearn SkillUp",
            "og_url": "/free-courses",
            "canonical_url": "/free-courses",
            "page_category": "free_courses",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Free Courses", "url": "/free-courses"},
            ],
        },
    )


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse(
        request,
        "about.html",
        {
            "page_title": "About getjob4u - Built solo by Kuldeep Jeengar",
            "page_description": "About getjob4u - a free career toolkit for AI, ML and Data Science job seekers. Built solo by Kuldeep Jeengar to make the AI/ML job hunt fair for everyone.",
            "og_url": "/about",
            "canonical_url": "/about",
            "page_category": "about",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "About", "url": "/about"},
            ],
        },
    )


@app.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request):
    return templates.TemplateResponse(
        request,
        "contact.html",
        {
            "page_title": "Contact getjob4u",
            "page_description": "Get in touch with getjob4u. Email getjob4u@gmail.com (launching soon), reach out to founder Kuldeep Jeengar on LinkedIn, or use our feedback form.",
            "og_url": "/contact",
            "canonical_url": "/contact",
            "page_category": "contact",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Contact", "url": "/contact"},
            ],
        },
    )


# ---------------------------------------------------------------- Admin

@app.get("/admin", response_class=HTMLResponse)
def admin_root(session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    if _get_session(session_token):
        return RedirectResponse("/admin/dashboard", status_code=303)
    return RedirectResponse("/admin/login", status_code=303)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request, session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    if _get_session(session_token):
        return RedirectResponse("/admin/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin_login.html",
        {
            "page_title": "Admin Login — getjob4u",
            "page_description": "Sign in to the getjob4u admin dashboard.",
            "canonical_url": "/admin/login",
            "og_url": "/admin/login",
            "page_category": "admin_login",
            "error": None,
        },
    )


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(AdminUser).filter(AdminUser.username == username, AdminUser.is_active == True).first()  # noqa: E712
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "admin_login.html",
            {
                "page_title": "Admin Login — getjob4u",
                "canonical_url": "/admin/login",
                "og_url": "/admin/login",
                "page_category": "admin_login",
                "error": "Invalid name or password.",
            },
            status_code=401,
        )
    user.last_login = datetime.utcnow()
    db.commit()
    token = _create_session(user)
    resp = RedirectResponse("/admin/dashboard", status_code=303)
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_HOURS * 3600,
        secure=False,
    )
    return resp


@app.post("/admin/logout")
def admin_logout(session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    if session_token:
        _SESSIONS.pop(session_token, None)
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
):
    sess = _get_session(session_token)
    if not sess:
        return RedirectResponse("/admin/login", status_code=303)

    scans = db.query(ATSScan).order_by(desc(ATSScan.created_at)).limit(100).all()
    feedback = db.query(Feedback).order_by(desc(Feedback.created_at)).limit(100).all()

    total_scans = db.query(func.count(ATSScan.id)).scalar() or 0
    jd_scans = db.query(func.count(ATSScan.id)).filter(ATSScan.scan_type == "jd").scalar() or 0
    avg_score = db.query(func.avg(ATSScan.score)).scalar() or 0
    total_feedback = db.query(func.count(Feedback.id)).scalar() or 0
    avg_rating = db.query(func.avg(Feedback.rating)).scalar() or 0
    total_emails = db.query(func.count(GeneratedEmail.id)).scalar() or 0

    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "page_title": "Admin Dashboard — getjob4u",
            "page_description": "Internal admin dashboard.",
            "canonical_url": "/admin/dashboard",
            "og_url": "/admin/dashboard",
            "page_category": "admin_dashboard",
            "admin_name": sess["username"],
            "scans": scans,
            "feedback": feedback,
            "stats": {
                "total_scans": total_scans,
                "jd_scans": jd_scans,
                "avg_score": round(float(avg_score), 1),
                "total_feedback": total_feedback,
                "avg_rating": round(float(avg_rating), 2),
                "total_emails": total_emails,
            },
        },
    )


@app.get("/admin/resumes/{scan_id}/download")
def admin_download_resume(
    scan_id: int,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
):
    if not _get_session(session_token):
        return RedirectResponse("/admin/login", status_code=303)
    scan = db.query(ATSScan).filter(ATSScan.id == scan_id).first()
    if not scan or not scan.file_content:
        raise HTTPException(404, "Resume not found.")
    filename = scan.filename or f"resume_{scan_id}"
    lower = filename.lower()
    if lower.endswith(".pdf"):
        media_type = "application/pdf"
    elif lower.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"
    return Response(
        content=scan.file_content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------- API

@app.post("/api/ats/scan")
async def api_ats_scan(
    file: UploadFile = File(...),
    target_role: str = Form("data_scientist"),
    uploader_name: str = Form(""),
    uploader_email: str = Form(""),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "No file provided.")
    contents = await file.read()
    if len(contents) > int(2.5 * 1024 * 1024):
        raise HTTPException(400, "File too large (2.5MB max).")
    try:
        result = ats_scorer.score_resume(file.filename, contents, target_role)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.add(ATSScan(
        filename=file.filename,
        target_role=target_role,
        score=result.overall_score,
        grade=result.grade,
        word_count=result.word_count,
        scan_type="role",
        file_size=len(contents),
        file_content=contents,
        uploader_name=(uploader_name or None),
        uploader_email=(uploader_email or None),
    ))
    db.commit()
    return JSONResponse(result.to_dict())


@app.post("/api/ats/scan-jd")
async def api_ats_scan_jd(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    uploader_name: str = Form(""),
    uploader_email: str = Form(""),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "No file provided.")
    contents = await file.read()
    if len(contents) > int(2.5 * 1024 * 1024):
        raise HTTPException(400, "File too large (2.5MB max).")
    if len(jd_text) > 20000:
        raise HTTPException(400, "Job description too long (20k chars max).")
    try:
        result = ats_scorer.score_resume_against_jd(file.filename, contents, jd_text)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.add(ATSScan(
        filename=file.filename,
        target_role="custom_jd",
        score=result.overall_score,
        grade=result.grade,
        word_count=result.word_count,
        scan_type="jd",
        jd_text=jd_text[:10000],
        file_size=len(contents),
        file_content=contents,
        uploader_name=(uploader_name or None),
        uploader_email=(uploader_email or None),
    ))
    db.commit()
    return JSONResponse(result.to_dict())


@app.post("/api/email/generate")
async def api_email_generate(payload: dict, db: Session = Depends(get_db)):
    try:
        req = email_generator.GenerationRequest(
            template_key=payload.get("template_key", "referral_request"),
            medium=payload.get("medium", "email"),
            your_name=payload.get("your_name", "Your Name"),
            your_role=payload.get("your_role", "Data Scientist"),
            your_skills=payload.get("your_skills", "Python, ML, SQL"),
            recipient_name=payload.get("recipient_name", "Hiring Manager"),
            company=payload.get("company", "the company"),
            role=payload.get("role", "Data Scientist"),
            team=payload.get("team", "Data Science"),
            their_work=payload.get("their_work", "your recent projects"),
            achievement=payload.get("achievement", "Shipped a model that improved KPI by 20%"),
            date=payload.get("date", "this week"),
            alma_mater=payload.get("alma_mater", "your alma mater"),
            availability=payload.get("availability", "Tue/Thu afternoons"),
        )
        result = email_generator.generate(req)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.add(GeneratedEmail(email_type=req.template_key, recipient_role=req.role))
    db.commit()
    return JSONResponse(result)


@app.post("/api/feedback/submit")
async def api_feedback_submit(payload: dict, db: Session = Depends(get_db)):
    required = ["name", "email", "rating", "category", "message"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise HTTPException(400, f"Missing fields: {', '.join(missing)}")
    try:
        rating = int(payload["rating"])
    except (TypeError, ValueError):
        raise HTTPException(400, "Rating must be 1-5.")
    if not 1 <= rating <= 5:
        raise HTTPException(400, "Rating must be between 1 and 5.")
    fb = Feedback(
        name=payload["name"][:100],
        email=payload["email"][:120],
        rating=rating,
        category=payload["category"][:50],
        message=payload["message"][:2000],
    )
    db.add(fb)
    db.commit()
    return {"ok": True, "id": fb.id, "message": "Thanks for your feedback!"}


@app.get("/api/daily-question")
def api_daily_question():
    data = _load_json("interview_tips.json")
    return {"question": random.choice(data["daily_questions"])}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------- SEO

@app.get("/sitemap.xml")
def sitemap():
    """XML sitemap for search engines.

    lastmod is taken from each template's filesystem mtime — a real signal
    Google can use to recrawl just changed pages, instead of the previous
    "everything was modified today" lie which Google has learned to ignore.
    """
    template_dir = BASE_DIR / "templates"

    def lastmod_for(template: str) -> str:
        path = template_dir / template
        try:
            return datetime.utcfromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        except OSError:
            return datetime.utcnow().strftime("%Y-%m-%d")

    # (path, changefreq, priority, template_file)
    urls = [
        ("/",                  "weekly",  "1.00", "index.html"),
        ("/ats-scanner",       "weekly",  "0.95", "ats_scanner.html"),
        ("/python-questions",  "weekly",  "0.95", "python_questions.html"),
        ("/career-roadmap",    "monthly", "0.90", "career_roadmap.html"),
        ("/free-ai-tools",     "weekly",  "0.95", "free_ai_tools.html"),
        ("/free-courses",      "weekly",  "0.95", "free_courses.html"),
        ("/interview-tips",    "weekly",  "0.90", "interview_tips.html"),
        ("/email-generator",   "weekly",  "0.90", "email_generator.html"),
        ("/blogs",             "weekly",  "0.85", "blogs.html"),
        ("/youtube-resources", "monthly", "0.80", "youtube_resources.html"),
        ("/sample-resumes",    "monthly", "0.80", "sample_resumes.html"),
        ("/about",             "monthly", "0.70", "about.html"),
        ("/contact",           "monthly", "0.65", "contact.html"),
        ("/feedback",          "monthly", "0.60", "feedback.html"),
    ]

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url, changefreq, priority, tpl in urls:
        xml += '  <url>\n'
        xml += f'    <loc>https://getjob4u.com{url}</loc>\n'
        xml += f'    <lastmod>{lastmod_for(tpl)}</lastmod>\n'
        xml += f'    <changefreq>{changefreq}</changefreq>\n'
        xml += f'    <priority>{priority}</priority>\n'
        xml += '  </url>\n'
    xml += '</urlset>'
    return Response(content=xml, media_type="application/xml")


@app.get("/blogs-sitemap.xml")
def blogs_sitemap():
    """Dedicated blog sitemap for blog entries and resources."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    try:
        blogs_data = _load_json("blogs.json")
        blog_urls = []
        
        # Add main blogs page
        blog_urls.append(("/blogs", "weekly", "0.90"))
        
        # Add individual blog sources/categories if they exist
        if "categories" in blogs_data:
            for category in blogs_data.get("categories", []):
                if "name" in category:
                    slug = category["name"].lower().replace(" ", "-")
                    blog_urls.append((f"/blogs?category={slug}", "weekly", "0.80"))
        
        # Add newsletter entries if they exist
        if "newsletters" in blogs_data:
            for newsletter in blogs_data.get("newsletters", []):
                if "name" in newsletter:
                    slug = newsletter["name"].lower().replace(" ", "-")
                    blog_urls.append((f"/blogs?newsletter={slug}", "weekly", "0.75"))
        
    except Exception:
        blog_urls = [("/blogs", "weekly", "0.90")]
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for url, changefreq, priority in blog_urls:
        xml += '  <url>\n'
        xml += f'    <loc>https://getjob4u.com{url}</loc>\n'
        xml += f'    <lastmod>{today}</lastmod>\n'
        xml += f'    <changefreq>{changefreq}</changefreq>\n'
        xml += f'    <priority>{priority}</priority>\n'
        xml += '  </url>\n'
    
    xml += '</urlset>'
    return Response(content=xml, media_type="application/xml")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    """Robots.txt for search engines."""
    return """User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/

# AI / answer-engine crawlers — allow indexing for AEO reach.
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Applebot-Extended
Allow: /

# Rate limiting for aggressive crawlers
User-agent: AhrefsBot
Crawl-delay: 10

User-agent: SemrushBot
Crawl-delay: 10

Sitemap: https://getjob4u.com/sitemap.xml
Sitemap: https://getjob4u.com/blogs-sitemap.xml
"""
