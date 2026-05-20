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
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large (5MB max).")
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
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large (5MB max).")
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

@app.get("/sitemap.xml", response_class=PlainTextResponse)
def sitemap():
    """XML sitemap for search engines."""
    urls = [
        ("/", "weekly", "1.0"),
        ("/ats-scanner", "weekly", "0.9"),
        ("/interview-tips", "weekly", "0.9"),
        ("/youtube-resources", "monthly", "0.8"),
        ("/blogs", "weekly", "0.8"),
        ("/email-generator", "weekly", "0.9"),
        ("/sample-resumes", "monthly", "0.8"),
        ("/career-roadmap", "monthly", "0.8"),
        ("/feedback", "monthly", "0.7"),
    ]

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    for url, changefreq, priority in urls:
        xml += f'  <url>\n'
        xml += f'    <loc>https://getjob4u.com{url}</loc>\n'
        xml += f'    <changefreq>{changefreq}</changefreq>\n'
        xml += f'    <priority>{priority}</priority>\n'
        xml += f'  </url>\n'

    xml += '</urlset>'
    return xml


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    """Robots.txt for search engines."""
    return """User-agent: *
Disallow: /api/
Disallow: /admin/

Sitemap: https://getjob4u.com/sitemap.xml

User-agent: AhrefsBot
Crawl-delay: 10

User-agent: SemrushBot
Crawl-delay: 10
"""
