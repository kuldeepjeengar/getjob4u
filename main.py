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


def _static_version(rel_path: str) -> str:
    """Return a short cache-busting token for a static asset (mtime as int).

    Used in templates as ?v={{ static_v('css/style.css') }} so browsers fetch
    a fresh copy whenever the file actually changes, but keep caching otherwise.
    """
    try:
        return str(int((BASE_DIR / "static" / rel_path).stat().st_mtime))
    except OSError:
        return "0"


templates.env.globals["static_v"] = _static_version


# ---------------------------------------------------------------- Canonical redirects
# Lower-cased typo path -> canonical path. 301 (permanent) so search engines
# update their index and consolidate link equity onto the real URL.
PATH_REDIRECTS: dict[str, str] = {
    # Robots / sitemap typos
    "/robot.txt": "/robots.txt",
    "/robots": "/robots.txt",
    "/sitemap": "/sitemap.xml",
    "/sitemaps.xml": "/sitemap.xml",
    "/sitemap.html": "/sitemap.xml",
    # Common singular/plural slips
    "/blog": "/blogs",
    "/blogs.html": "/blogs",
    "/python-question": "/python-questions",
    "/python-questions.html": "/python-questions",
    "/interview-tip": "/interview-tips",
    "/interview-tips.html": "/interview-tips",
    "/free-course": "/free-courses",
    "/courses": "/free-courses",
    "/course": "/free-courses",
    "/free-ai-tool": "/free-ai-tools",
    "/ai-tools": "/free-ai-tools",
    "/tools": "/free-ai-tools",
    "/career-roadmaps": "/career-roadmap",
    "/roadmap": "/career-roadmap",
    "/roadmaps": "/career-roadmap",
    "/sample-resume": "/sample-resumes",
    "/resume": "/sample-resumes",
    "/resumes": "/sample-resumes",
    "/feedbacks": "/feedback",
    # ATS / scanner shortcuts
    "/ats": "/ats-scanner",
    "/ats-scan": "/ats-scanner",
    "/atsscanner": "/ats-scanner",
    "/scanner": "/ats-scanner",
    "/resume-scanner": "/ats-scanner",
    "/resume-checker": "/ats-scanner",
    # Email generator shortcuts
    "/email": "/email-generator",
    "/emails": "/email-generator",
    "/cold-email": "/email-generator",
    "/cold-emails": "/email-generator",
    "/email-generators": "/email-generator",
    # YouTube / learning
    "/youtube": "/youtube-resources",
    "/youtube-resource": "/youtube-resources",
    "/learning-resources": "/youtube-resources",
    # Tips shortcuts
    "/tips": "/interview-tips",
    "/interview": "/interview-tips",
    "/interview-prep": "/interview-tips",
    # About / contact / privacy slips
    "/about-us": "/about",
    "/aboutus": "/about",
    "/contact-us": "/contact",
    "/contactus": "/contact",
    "/privacy-policy": "/privacy",
    "/privacy.html": "/privacy",
    # Home variants
    "/home": "/",
    "/index": "/",
    "/index.html": "/",
}


@app.middleware("http")
async def canonical_redirects(request: Request, call_next):
    """Enforce canonical hostname + fix common path typos with 301s.

    - www.getjob4u.com/x  -> https://getjob4u.com/x  (consolidates SEO equity)
    - /robot.txt, /blog, /tools, ... -> their canonical paths
    Local dev (127.0.0.1, localhost) is exempt so reload servers still work.
    """
    host = (request.headers.get("host") or "").lower().split(":")[0]

    # Skip redirect logic for local development hosts.
    is_local = host in {"127.0.0.1", "localhost", "0.0.0.0"} or host.endswith(".local")

    if not is_local and host.startswith("www."):
        target = f"https://{host[4:]}{request.url.path}"
        if request.url.query:
            target += f"?{request.url.query}"
        return RedirectResponse(target, status_code=301)

    # Path-typo fix. Compare case-insensitively, ignore trailing slash.
    raw_path = request.url.path
    normalized = raw_path.lower().rstrip("/") or "/"
    if normalized in PATH_REDIRECTS:
        target = PATH_REDIRECTS[normalized]
        if request.url.query:
            target += f"?{request.url.query}"
        return RedirectResponse(target, status_code=301)

    return await call_next(request)


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
            "page_title": "getjob4u — Free ATS Scanner, Interview Prep & AI/ML/DS Career Toolkit",
            "page_description": "Free career toolkit for AI, ML, and Data Science job seekers. ATS resume scanner, 100 FAANG Python questions, 49+ interview tips, cold email generator, career roadmap, and free certificate courses.",
            "keywords": "free ATS resume scanner, ATS resume checker free, AI resume scanner, ML resume checker, data science resume scanner, machine learning interview questions, data science interview questions, AI engineer interview prep, FAANG Python interview questions, Python coding interview, free AI courses with certificate, free ML courses, free data science courses, cold email generator, LinkedIn referral message, data science career roadmap, ML engineer roadmap, AI job search toolkit, ATS friendly resume, free interview prep, getjob4u",
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
            "keywords": "free ATS resume scanner, ATS resume checker online, AI resume checker, resume ATS score, ATS friendly resume, ATS optimization, beat the ATS, resume keyword scanner, job description matcher, resume optimizer, Workday ATS, Greenhouse ATS, Lever ATS, iCIMS ATS, Taleo ATS, data scientist resume scanner, ML engineer resume scanner, AI engineer resume scanner, no signup ATS scanner, instant ATS score, JD vs resume match, resume keywords for data science, resume keywords for ML engineer",
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
            "keywords": "data science interview questions, machine learning interview questions, AI interview questions, deep learning interview questions, LLM interview questions, generative AI interview questions, RAG interview questions, transformer interview questions, NLP interview questions, statistics interview questions, A/B testing interview questions, SQL interview questions, behavioral interview questions data science, FAANG data science interview, Google data science interview, Meta ML interview, ML engineer interview prep, AI engineer interview prep, MLOps interview questions, data science behavioral questions, STAR method data science",
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
            "keywords": "free YouTube channels machine learning, best YouTube channels for data science, free AI YouTube channels, free ML video courses, StatQuest, 3Blue1Brown, Andrej Karpathy, Andrew Ng courses free, Yannic Kilcher, free deep learning lectures, free ML lectures, free Stanford ML lectures, free MIT AI lectures, free YouTube data analytics, free generative AI tutorials YouTube",
            "og_url": "/youtube-resources",
            "canonical_url": "/youtube-resources",
            "page_category": "youtube_resources",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Learning Resources", "url": "/youtube-resources"},
            ],
        },
    )


def _format_post_date(iso: str) -> str:
    """Render an ISO date like 2026-05-25 → 'May 25, 2026' (cross-platform)."""
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    except (ValueError, TypeError):
        return iso or ""


def _load_blog_posts() -> list[dict]:
    """Load blog_posts.json, decorate each post with display dates + word count,
    and return them sorted newest-first."""
    data = _load_json("blog_posts.json")
    posts = list(data.get("posts", []))
    for p in posts:
        p["published_display"] = _format_post_date(p.get("published", ""))
        p["updated_display"] = _format_post_date(p.get("updated", p.get("published", "")))
        # Cheap word count for Article schema — strip HTML tags, split on whitespace.
        text = " ".join(s.get("body_html", "") for s in p.get("sections", []))
        import re as _re
        words = _re.sub(r"<[^>]+>", " ", text).split()
        p["word_count"] = len(words) + len(p.get("title", "").split()) + len(p.get("summary", "").split())
    posts.sort(key=lambda x: x.get("published", ""), reverse=True)
    return posts


@app.get("/blogs", response_class=HTMLResponse)
def blogs_page(request: Request):
    data = _load_json("blogs.json")
    internal_posts = _load_blog_posts()
    return templates.TemplateResponse(
        request,
        "blogs.html",
        {
            "categories": data["categories"],
            "newsletters": data["newsletters"],
            "internal_posts": internal_posts,
            "page_title": "AI / ML / Data Science Blog - Guides & Curated Reading - getjob4u",
            "page_description": "Original long-form guides on ATS resumes, cold email referrals, and AI/ML career roadmaps, plus a hand-picked list of the best external AI/ML/Data Science blogs to follow.",
            "keywords": "AI blog, ML blog, data science blog, AI ML newsletters, ATS resume tips, cold email referral guide, ML career roadmap guide, best AI blogs to follow 2026, best ML blogs to read, best data science blogs, generative AI blog, LLM blog, MLOps blog, Sebastian Raschka, Lilian Weng, Distill.pub, Towards Data Science, free AI newsletters, AI papers explained, ML paper summaries",
            "og_url": "/blogs",
            "canonical_url": "/blogs",
            "page_category": "blogs",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Blog", "url": "/blogs"},
            ],
        },
    )


@app.get("/blogs/{slug}", response_class=HTMLResponse)
def blog_post_page(request: Request, slug: str):
    posts = _load_blog_posts()
    post = next((p for p in posts if p.get("slug") == slug), None)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found.")
    other_posts = [p for p in posts if p.get("slug") != slug][:3]
    return templates.TemplateResponse(
        request,
        "blog_post.html",
        {
            "post": post,
            "other_posts": other_posts,
            "page_title": f"{post['title']} - getjob4u",
            "page_description": post["description"],
            "keywords": ", ".join(post.get("tags", [])),
            "og_url": f"/blogs/{slug}",
            "canonical_url": f"/blogs/{slug}",
            "page_category": "blog_post",
            "page_section": post.get("category", ""),
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Blog", "url": "/blogs"},
                {"name": post["title"], "url": f"/blogs/{slug}"},
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
            "keywords": "cold email generator free, LinkedIn message generator, referral request email template, job application email, recruiter outreach email, networking email templates, follow up email after interview, cold email for data science job, cold email for ML engineer job, referral cold email template, free cold email tool, cold DM template LinkedIn, AI cold email generator, cold email examples that work, cold email subject lines",
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
            "keywords": "sample data science resume, sample ML engineer resume, sample AI resume, sample data analyst resume, free resume templates download, ATS friendly resume template, data scientist resume template free, ML resume sample download, resume for data science fresher, AI engineer resume sample, machine learning resume sample, deep learning engineer resume, NLP engineer resume sample, data engineer resume sample, MLOps engineer resume sample, resume PDF download free",
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
            "keywords": "data scientist career roadmap, ML engineer roadmap, AI engineer roadmap, data analyst career roadmap, machine learning learning path, data science learning path 2026, how to become data scientist, how to become ML engineer, AI engineer career path, data science fresher roadmap, ML beginner roadmap, MLOps career path, generative AI engineer roadmap, LLM engineer roadmap, data science skills 2026, AI career path with no experience",
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
            "keywords": "Python coding interview questions, FAANG Python questions, Python LeetCode questions, Blind 75 Python, NeetCode 150 Python, Google Python interview, Amazon Python interview, Meta Python interview, Microsoft Python interview, Netflix Python interview, Apple Python interview, Python algorithm questions, Python data structure interview, two pointer Python, sliding window Python, dynamic programming Python, recursion Python interview, top 100 Python questions, Python interview practice free, Python coding round, Python DSA questions",
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
            "keywords": "getjob4u feedback, AI ML toolkit feedback, ATS scanner feedback, suggest a feature, free career tools feedback, contact getjob4u, report a bug, request a feature",
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
            "keywords": "free AI tools, free AI tools 2026, best free AI tools, free AI video generation, free AI image generation, free AI PDF tools, free AI coding tools, free AI voice generator, free AI chatbot, free ChatGPT alternatives, free AI presentation generator, free AI summarizer, free AI writing tools, free AI design tools, free AI productivity tools, free AI for students, free AI without signup, free AI for resume, free AI logo maker, free AI music generator",
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
            "keywords": "free AI courses with certificate, free machine learning courses with certificate, free data science courses with certificate, free data analytics certificate, free generative AI courses, free Coursera courses, free Udemy courses, free IBM Cognitive Class, free Google AI courses, free Microsoft Learn, free Kaggle courses, free Hugging Face courses, free LangChain course, free LLM courses, free Python certification, free SQL course free certificate, Great Learning Academy free, Simplilearn SkillUp free, freeCodeCamp data science, free MLOps course, free PyTorch course, free TensorFlow course",
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
            "keywords": "about getjob4u, Kuldeep Jeengar, indie founder data science, free AI ML toolkit creator, getjob4u story, who built getjob4u, AI career toolkit by Kuldeep Jeengar, solo founder data scientist",
            "og_url": "/about",
            "canonical_url": "/about",
            "page_category": "about",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "About", "url": "/about"},
            ],
        },
    )


@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    last_updated = datetime.utcfromtimestamp(
        (BASE_DIR / "templates" / "privacy.html").stat().st_mtime
    ).strftime("%B %d, %Y")
    return templates.TemplateResponse(
        request,
        "privacy.html",
        {
            "page_title": "Privacy Policy — getjob4u",
            "page_description": "How getjob4u collects, uses, and protects your data. Covers Google Analytics, Google AdSense, cookies, your rights under GDPR / CCPA / DPDP, and how to request deletion.",
            "keywords": "getjob4u privacy policy, data privacy AI tools, GDPR privacy policy, CCPA privacy policy, DPDP India privacy policy, cookie policy, Google Analytics privacy, Google AdSense privacy, data deletion request",
            "canonical_url": "/privacy",
            "og_url": "/privacy",
            "page_category": "privacy",
            "last_updated": last_updated,
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "Privacy Policy", "url": "/privacy"},
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
            "keywords": "contact getjob4u, getjob4u email, Kuldeep Jeengar LinkedIn, AI ML toolkit contact, getjob4u support, partnership getjob4u, hire Kuldeep Jeengar",
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
            "robots_noindex": True,
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
                "robots_noindex": True,
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
            "robots_noindex": True,
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
        ("/privacy",           "yearly",  "0.30", "privacy.html"),
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

    # Each original blog post is its own indexable URL — uses the post's own
    # 'updated' date for lastmod so Google can prioritize re-crawling edits.
    try:
        for post in _load_blog_posts():
            xml += '  <url>\n'
            xml += f'    <loc>https://getjob4u.com/blogs/{post["slug"]}</loc>\n'
            xml += f'    <lastmod>{post.get("updated") or post.get("published", "")}</lastmod>\n'
            xml += '    <changefreq>monthly</changefreq>\n'
            xml += '    <priority>0.80</priority>\n'
            xml += '  </url>\n'
    except Exception:
        pass

    xml += '</urlset>'
    return Response(content=xml, media_type="application/xml")


@app.get("/blogs-sitemap.xml")
def blogs_sitemap():
    """Dedicated blog sitemap for blog entries and resources.
    
    NOTE: Only includes canonical URLs without query parameters.
    Query params (?category=, ?newsletter=) create alternate page versions
    that confuse Google's indexing. Use URL params in Search Console instead.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
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
