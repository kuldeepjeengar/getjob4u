"""getjob4u — FastAPI app entrypoint.

Run locally:  uv run uvicorn main:app --reload
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import ats_scorer
import email_generator
from database import (
    ATSScan,
    Feedback,
    GeneratedEmail,
    get_db,
    init_db,
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

app = FastAPI(title="getjob4u", description="AI/ML/DS career toolkit")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _load_json(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- Pages

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    tips_data = _load_json("interview_tips.json")
    daily_question = random.choice(tips_data["daily_questions"])
    return templates.TemplateResponse(
        request, "index.html", {"daily_question": daily_question}
    )


@app.get("/ats-scanner", response_class=HTMLResponse)
def ats_scanner_page(request: Request):
    return templates.TemplateResponse(
        request, "ats_scanner.html", {"roles": ats_scorer.available_roles()}
    )


@app.get("/interview-tips", response_class=HTMLResponse)
def interview_tips_page(request: Request):
    data = _load_json("interview_tips.json")
    return templates.TemplateResponse(
        request, "interview_tips.html", {"categories": data["categories"]}
    )


@app.get("/youtube-resources", response_class=HTMLResponse)
def youtube_page(request: Request):
    data = _load_json("youtube_channels.json")
    return templates.TemplateResponse(
        request,
        "youtube_resources.html",
        {"categories": data["categories"], "courses": data["free_courses"]},
    )


@app.get("/email-generator", response_class=HTMLResponse)
def email_generator_page(request: Request):
    return templates.TemplateResponse(
        request,
        "email_generator.html",
        {"templates": email_generator.available_templates()},
    )


@app.get("/sample-resumes", response_class=HTMLResponse)
def sample_resumes_page(request: Request):
    data = _load_json("sample_resumes.json")
    return templates.TemplateResponse(
        request,
        "sample_resumes.html",
        {"resumes": data["resumes"], "tips": data["general_tips"]},
    )


@app.get("/career-roadmap", response_class=HTMLResponse)
def roadmap_page(request: Request):
    data = _load_json("career_roadmap.json")
    return templates.TemplateResponse(
        request, "career_roadmap.html", {"roadmaps": data["roadmaps"]}
    )


@app.get("/feedback", response_class=HTMLResponse)
def feedback_page(request: Request):
    return templates.TemplateResponse(request, "feedback.html", {})


# ---------------------------------------------------------------- API

@app.post("/api/ats/scan")
async def api_ats_scan(
    file: UploadFile = File(...),
    target_role: str = Form("data_scientist"),
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
    db.add(ATSScan(filename=file.filename, target_role=target_role, score=result.overall_score))
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
