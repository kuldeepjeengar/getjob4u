"""Rule-based ATS resume scorer for AI / ML / Data Science roles.

Zero API cost. Parses PDF/DOCX, scores against 6 dimensions, returns a
detailed breakdown + actionable suggestions.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Iterable

import PyPDF2
from docx import Document


ROLE_KEYWORDS: dict[str, list[str]] = {
    "data_scientist": [
        "python", "r", "sql", "pandas", "numpy", "scikit-learn", "tensorflow",
        "pytorch", "machine learning", "deep learning", "statistics",
        "data visualization", "matplotlib", "seaborn", "tableau", "power bi",
        "a/b testing", "hypothesis testing", "regression", "classification",
        "clustering", "feature engineering", "etl", "spark", "hadoop",
        "jupyter", "git", "aws", "gcp", "azure", "docker", "mlflow",
    ],
    "ml_engineer": [
        "python", "tensorflow", "pytorch", "keras", "scikit-learn",
        "machine learning", "deep learning", "mlops", "kubernetes", "docker",
        "aws sagemaker", "vertex ai", "mlflow", "airflow", "kubeflow",
        "model deployment", "model monitoring", "feature store", "ci/cd",
        "rest api", "fastapi", "flask", "spark", "kafka", "redis",
        "git", "linux", "bash", "cuda", "gpu",
    ],
    "ai_engineer": [
        "python", "langchain", "llama-index", "openai", "anthropic",
        "transformers", "huggingface", "rag", "vector database", "pinecone",
        "chroma", "weaviate", "embeddings", "prompt engineering", "fine-tuning",
        "llm", "agents", "fastapi", "pytorch", "tensorflow", "docker",
        "aws bedrock", "azure openai", "gradio", "streamlit",
    ],
    "data_analyst": [
        "sql", "excel", "tableau", "power bi", "python", "pandas",
        "data visualization", "etl", "dashboards", "reporting", "kpi",
        "a/b testing", "statistics", "google analytics", "looker",
        "data cleaning", "data modeling", "business intelligence",
    ],
    "data_engineer": [
        "python", "sql", "spark", "hadoop", "kafka", "airflow", "dbt",
        "snowflake", "redshift", "bigquery", "etl", "elt", "data pipeline",
        "data warehouse", "data lake", "aws", "gcp", "azure", "docker",
        "kubernetes", "scala", "java", "nosql", "mongodb", "postgresql",
    ],
}

ACTION_VERBS = {
    "achieved", "improved", "developed", "designed", "built", "led",
    "managed", "implemented", "deployed", "optimized", "reduced", "increased",
    "automated", "analyzed", "created", "delivered", "launched", "scaled",
    "trained", "engineered", "researched", "published", "presented",
    "collaborated", "mentored", "architected", "migrated", "integrated",
}

SECTION_HEADERS = {
    "experience": ["experience", "work experience", "professional experience", "employment"],
    "education": ["education", "academic background", "qualifications"],
    "skills": ["skills", "technical skills", "core competencies", "expertise"],
    "projects": ["projects", "personal projects", "key projects"],
    "summary": ["summary", "objective", "profile", "about"],
    "certifications": ["certifications", "certificates", "courses"],
    "contact": ["email", "phone", "linkedin", "github"],
}


@dataclass
class ATSResult:
    overall_score: float
    grade: str
    breakdown: dict[str, dict] = field(default_factory=dict)
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    word_count: int = 0
    target_role: str = ""

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "grade": self.grade,
            "breakdown": self.breakdown,
            "matched_keywords": self.matched_keywords,
            "missing_keywords": self.missing_keywords,
            "suggestions": self.suggestions,
            "word_count": self.word_count,
            "target_role": self.target_role,
        }


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(filename: str, file_bytes: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if name.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    if name.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")
    raise ValueError("Unsupported file type. Upload PDF, DOCX, or TXT.")


def _score_keywords(text_lower: str, role: str) -> tuple[float, list[str], list[str]]:
    keywords = ROLE_KEYWORDS.get(role, ROLE_KEYWORDS["data_scientist"])
    matched = [k for k in keywords if k in text_lower]
    missing = [k for k in keywords if k not in text_lower]
    ratio = len(matched) / len(keywords) if keywords else 0
    return min(100, ratio * 100 * 1.4), matched, missing


def _score_sections(text_lower: str) -> tuple[float, dict]:
    found = {}
    for section, variants in SECTION_HEADERS.items():
        found[section] = any(re.search(rf"\b{re.escape(v)}\b", text_lower) for v in variants)
    score = (sum(found.values()) / len(found)) * 100
    return score, found


def _score_contact_info(text: str) -> tuple[float, dict]:
    checks = {
        "email": bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)),
        "phone": bool(re.search(r"(\+?\d[\d\s\-().]{7,}\d)", text)),
        "linkedin": "linkedin.com" in text.lower(),
        "github": "github.com" in text.lower(),
    }
    score = (sum(checks.values()) / len(checks)) * 100
    return score, checks


def _score_action_verbs(text_lower: str) -> tuple[float, int]:
    words = set(re.findall(r"\b[a-z]+\b", text_lower))
    used = words & ACTION_VERBS
    score = min(100, (len(used) / 12) * 100)
    return score, len(used)


def _score_quantification(text: str) -> tuple[float, int]:
    metrics = re.findall(r"\b\d+(?:\.\d+)?\s*(?:%|percent|x|k|m|million|billion|years?|months?)\b", text.lower())
    bare_numbers = re.findall(r"\$\d+|\b\d{2,}\b", text)
    total = len(metrics) + len(bare_numbers)
    score = min(100, (total / 10) * 100)
    return score, total


def _score_length(word_count: int) -> tuple[float, str]:
    if 400 <= word_count <= 800:
        return 100.0, "ideal"
    if 300 <= word_count < 400 or 800 < word_count <= 1000:
        return 80.0, "acceptable"
    if 200 <= word_count < 300 or 1000 < word_count <= 1200:
        return 60.0, "borderline"
    return 35.0, "too short" if word_count < 200 else "too long"


def _grade(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Fair"
    if score >= 40:
        return "Needs work"
    return "Poor"


def _build_suggestions(
    breakdown: dict,
    missing_keywords: list[str],
    word_count: int,
) -> list[str]:
    out: list[str] = []
    if breakdown["keywords"]["score"] < 70 and missing_keywords:
        top = ", ".join(missing_keywords[:6])
        out.append(f"Add these high-value keywords if you have the experience: {top}.")
    if breakdown["sections"]["score"] < 100:
        missing_sections = [k for k, v in breakdown["sections"]["details"].items() if not v]
        if missing_sections:
            out.append(f"Add missing sections: {', '.join(missing_sections)}.")
    if breakdown["contact"]["score"] < 75:
        details = breakdown["contact"]["details"]
        if not details.get("linkedin"):
            out.append("Add your LinkedIn URL — recruiters check it 90% of the time.")
        if not details.get("github"):
            out.append("Add a GitHub profile — essential for AI/ML/DS roles.")
        if not details.get("phone"):
            out.append("Add a phone number to your contact section.")
    if breakdown["action_verbs"]["score"] < 70:
        out.append("Start bullet points with strong action verbs (built, deployed, optimized, led, scaled).")
    if breakdown["quantification"]["score"] < 60:
        out.append("Quantify achievements with numbers: '%' improvement, model accuracy, dataset size, users impacted.")
    if breakdown["length"]["score"] < 80:
        if word_count < 300:
            out.append("Resume is too short. Expand with project details, impact metrics, and tech stack.")
        elif word_count > 1000:
            out.append("Resume is too long. Trim to 1 page for <5 yrs experience, 2 pages max.")
    if not out:
        out.append("Strong resume! Tailor keywords to each job description for best ATS match.")
    return out


SCORE_WEIGHTS = {
    "keywords": 0.30,
    "sections": 0.15,
    "contact": 0.10,
    "action_verbs": 0.15,
    "quantification": 0.20,
    "length": 0.10,
}


def score_resume(filename: str, file_bytes: bytes, target_role: str = "data_scientist") -> ATSResult:
    text = extract_text(filename, file_bytes)
    if not text.strip():
        raise ValueError("Could not extract text. Resume may be image-based — export as text PDF.")

    text_lower = text.lower()
    word_count = len(re.findall(r"\b\w+\b", text))

    kw_score, matched, missing = _score_keywords(text_lower, target_role)
    sec_score, sec_details = _score_sections(text_lower)
    contact_score, contact_details = _score_contact_info(text)
    verb_score, verb_count = _score_action_verbs(text_lower)
    quant_score, quant_count = _score_quantification(text)
    len_score, len_label = _score_length(word_count)

    breakdown = {
        "keywords": {
            "score": round(kw_score, 1),
            "weight": SCORE_WEIGHTS["keywords"],
            "label": f"{len(matched)}/{len(matched) + len(missing)} role keywords matched",
        },
        "sections": {
            "score": round(sec_score, 1),
            "weight": SCORE_WEIGHTS["sections"],
            "label": "Standard resume sections detected",
            "details": sec_details,
        },
        "contact": {
            "score": round(contact_score, 1),
            "weight": SCORE_WEIGHTS["contact"],
            "label": "Contact info completeness",
            "details": contact_details,
        },
        "action_verbs": {
            "score": round(verb_score, 1),
            "weight": SCORE_WEIGHTS["action_verbs"],
            "label": f"{verb_count} unique action verbs used",
        },
        "quantification": {
            "score": round(quant_score, 1),
            "weight": SCORE_WEIGHTS["quantification"],
            "label": f"{quant_count} quantified metrics found",
        },
        "length": {
            "score": round(len_score, 1),
            "weight": SCORE_WEIGHTS["length"],
            "label": f"{word_count} words ({len_label})",
        },
    }

    overall = sum(breakdown[k]["score"] * SCORE_WEIGHTS[k] for k in SCORE_WEIGHTS)
    suggestions = _build_suggestions(breakdown, missing, word_count)

    return ATSResult(
        overall_score=overall,
        grade=_grade(overall),
        breakdown=breakdown,
        matched_keywords=matched,
        missing_keywords=missing[:15],
        suggestions=suggestions,
        word_count=word_count,
        target_role=target_role,
    )


def available_roles() -> list[dict]:
    return [
        {"value": "data_scientist", "label": "Data Scientist"},
        {"value": "ml_engineer", "label": "Machine Learning Engineer"},
        {"value": "ai_engineer", "label": "AI Engineer (LLM/GenAI)"},
        {"value": "data_analyst", "label": "Data Analyst"},
        {"value": "data_engineer", "label": "Data Engineer"},
    ]
