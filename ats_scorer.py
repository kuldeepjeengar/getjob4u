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
    "software_engineer": [
        "java", "python", "c++", "javascript", "typescript", "data structures",
        "algorithms", "system design", "oop", "design patterns", "rest api",
        "microservices", "git", "linux", "ci/cd", "unit testing", "agile",
        "docker", "kubernetes", "aws", "sql", "nosql", "spring", "react",
        "node.js", "multithreading", "debugging",
    ],
    "powerbi_developer": [
        "power bi", "dax", "power query", "m language", "sql", "excel",
        "data modeling", "etl", "ssas", "ssis", "ssrs", "tabular model",
        "azure data factory", "synapse", "row-level security", "dashboards",
        "kpi", "reporting", "data warehouse", "star schema", "data visualization",
        "python", "r",
    ],
    "frontend_developer": [
        "javascript", "typescript", "react", "vue", "angular", "next.js",
        "html", "css", "sass", "tailwind", "redux", "webpack", "vite",
        "rest api", "graphql", "responsive design", "accessibility",
        "jest", "cypress", "git", "figma", "ui/ux",
    ],
    "backend_developer": [
        "python", "java", "node.js", "go", "c#", "spring boot", "django",
        "fastapi", "flask", "express", "rest api", "graphql", "microservices",
        "sql", "postgresql", "mysql", "mongodb", "redis", "kafka",
        "docker", "kubernetes", "aws", "ci/cd", "git", "system design",
    ],
    "fullstack_developer": [
        "javascript", "typescript", "react", "node.js", "next.js", "python",
        "django", "fastapi", "express", "rest api", "graphql", "html", "css",
        "tailwind", "postgresql", "mongodb", "redis", "docker", "aws",
        "git", "ci/cd", "system design", "agile",
    ],
    "devops_engineer": [
        "linux", "bash", "python", "docker", "kubernetes", "terraform",
        "ansible", "jenkins", "github actions", "gitlab ci", "aws", "gcp",
        "azure", "ci/cd", "prometheus", "grafana", "elk", "helm",
        "monitoring", "infrastructure as code", "networking", "security",
    ],
    "cloud_engineer": [
        "aws", "gcp", "azure", "terraform", "cloudformation", "ec2", "s3",
        "lambda", "rds", "iam", "vpc", "kubernetes", "docker", "linux",
        "python", "bash", "ci/cd", "networking", "security", "monitoring",
        "cost optimization", "serverless",
    ],
    "qa_engineer": [
        "selenium", "cypress", "playwright", "junit", "testng", "pytest",
        "manual testing", "automation testing", "test cases", "regression testing",
        "performance testing", "jmeter", "api testing", "postman", "rest assured",
        "sql", "ci/cd", "jira", "agile", "git", "bug tracking",
    ],
    "android_developer": [
        "kotlin", "java", "android studio", "jetpack compose", "mvvm", "mvp",
        "retrofit", "room", "coroutines", "firebase", "rest api", "git",
        "material design", "play store", "gradle", "rxjava", "dagger", "hilt",
    ],
    "ios_developer": [
        "swift", "objective-c", "swiftui", "uikit", "xcode", "core data",
        "combine", "mvvm", "rest api", "git", "app store", "cocoapods",
        "swift package manager", "tdd", "auto layout",
    ],
    "product_manager": [
        "product strategy", "roadmap", "user research", "agile", "scrum",
        "stakeholder management", "kpi", "metrics", "a/b testing", "wireframes",
        "jira", "confluence", "sql", "data analysis", "go-to-market",
        "user stories", "prd", "discovery", "prioritization",
    ],
    "business_analyst": [
        "sql", "excel", "tableau", "power bi", "requirements gathering",
        "stakeholder management", "process mapping", "uml", "agile", "scrum",
        "jira", "confluence", "data analysis", "kpi", "reporting",
        "business process", "user stories", "gap analysis",
    ],
    "cybersecurity_analyst": [
        "siem", "splunk", "wireshark", "nmap", "burp suite", "metasploit",
        "incident response", "threat hunting", "vulnerability assessment",
        "penetration testing", "owasp", "iso 27001", "nist", "soc",
        "firewall", "ids", "ips", "linux", "python", "powershell", "encryption",
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
        {"value": "software_engineer", "label": "Software Engineer (SDE)"},
        {"value": "powerbi_developer", "label": "Power BI Developer"},
        {"value": "frontend_developer", "label": "Frontend Developer"},
        {"value": "backend_developer", "label": "Backend Developer"},
        {"value": "fullstack_developer", "label": "Full Stack Developer"},
        {"value": "devops_engineer", "label": "DevOps Engineer"},
        {"value": "cloud_engineer", "label": "Cloud Engineer"},
        {"value": "qa_engineer", "label": "QA / Test Engineer"},
        {"value": "android_developer", "label": "Android Developer"},
        {"value": "ios_developer", "label": "iOS Developer"},
        {"value": "product_manager", "label": "Product Manager"},
        {"value": "business_analyst", "label": "Business Analyst"},
        {"value": "cybersecurity_analyst", "label": "Cybersecurity Analyst"},
    ]


# ---------------------------------------------------------------- JD scoring

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "for", "with", "to", "of", "in", "on",
    "at", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "should", "could",
    "may", "might", "must", "can", "this", "that", "these", "those", "it", "its",
    "we", "you", "your", "our", "their", "they", "them", "he", "she", "his", "her",
    "i", "me", "my", "us", "if", "then", "else", "than", "such", "so", "not", "no",
    "yes", "all", "any", "some", "more", "most", "other", "such", "only", "own",
    "same", "than", "too", "very", "s", "t", "just", "don", "now", "also", "etc",
    "across", "into", "out", "over", "under", "about", "above", "below", "between",
    "through", "during", "before", "after", "while", "where", "when", "what",
    "which", "who", "whom", "how", "why", "experience", "work", "working",
    "ability", "able", "team", "teams", "role", "roles", "skill", "skills",
    "candidate", "candidates", "year", "years", "responsibilities", "requirements",
    "preferred", "required", "looking", "join", "company", "job", "jobs",
    "position", "positions", "knowledge", "understanding", "good", "great", "strong",
    "excellent", "include", "including", "etc", "using", "use", "used", "uses",
    "across", "within", "based", "ensure", "ensuring", "deliver", "delivering",
    "develop", "developing", "build", "building", "ship", "shipping", "drive",
    "driving", "support", "supporting", "help", "helping", "make", "making",
    "etc.", "e.g.", "i.e.",
}

_JD_PHRASE_HINTS = [
    "machine learning", "deep learning", "data science", "data analysis",
    "data visualization", "data modeling", "data engineering", "data pipeline",
    "data warehouse", "data lake", "feature engineering", "feature store",
    "computer vision", "natural language processing", "natural language",
    "large language model", "large language models", "prompt engineering",
    "vector database", "rest api", "rest apis", "graphql", "system design",
    "object oriented", "object-oriented", "test driven", "test-driven",
    "ci/cd", "version control", "cloud computing", "agile", "scrum",
    "power bi", "power query", "row level security", "row-level security",
    "model deployment", "model monitoring", "a/b testing", "hypothesis testing",
    "time series", "recommender system", "fine tuning", "fine-tuning",
    "prompt engineering", "ab testing", "etl pipeline", "etl pipelines",
    "spring boot", "node.js", "scikit-learn", "stakeholder management",
]


def _extract_jd_keywords(jd_text: str, max_keywords: int = 40) -> list[str]:
    """Pull skill-like terms out of a job description.

    Combines (a) known multi-word phrases that often appear in JDs and
    (b) frequent single tokens with stopwords removed.
    """
    if not jd_text:
        return []
    lower = jd_text.lower()
    phrase_hits: list[str] = []
    for phrase in _JD_PHRASE_HINTS:
        if phrase in lower and phrase not in phrase_hits:
            phrase_hits.append(phrase)

    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#/-]*", lower)
    freq: dict[str, int] = {}
    for tok in tokens:
        tok = tok.strip(".-/").lower()
        if not tok or tok in _STOPWORDS or len(tok) <= 2:
            continue
        if tok.isdigit():
            continue
        freq[tok] = freq.get(tok, 0) + 1

    # words that are already inside a multi-word phrase shouldn't count again
    words_in_phrases: set[str] = set()
    for p in phrase_hits:
        for part in re.split(r"[\s/-]+", p):
            if part:
                words_in_phrases.add(part)

    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    singles = [w for w, _ in ranked if w not in words_in_phrases]

    combined: list[str] = []
    for p in phrase_hits:
        combined.append(p)
    for s in singles:
        if s in combined:
            continue
        combined.append(s)
        if len(combined) >= max_keywords:
            break
    return combined[:max_keywords]


def _score_jd_keywords(text_lower: str, jd_keywords: list[str]) -> tuple[float, list[str], list[str]]:
    if not jd_keywords:
        return 0.0, [], []
    matched = [k for k in jd_keywords if k in text_lower]
    missing = [k for k in jd_keywords if k not in text_lower]
    ratio = len(matched) / len(jd_keywords)
    return min(100, ratio * 110), matched, missing


def score_resume_against_jd(filename: str, file_bytes: bytes, jd_text: str) -> ATSResult:
    text = extract_text(filename, file_bytes)
    if not text.strip():
        raise ValueError("Could not extract text. Resume may be image-based — export as text PDF.")
    if not jd_text or len(jd_text.strip()) < 30:
        raise ValueError("Paste at least a couple of sentences of the job description (30+ chars).")

    text_lower = text.lower()
    word_count = len(re.findall(r"\b\w+\b", text))

    jd_keywords = _extract_jd_keywords(jd_text)
    kw_score, matched, missing = _score_jd_keywords(text_lower, jd_keywords)
    sec_score, sec_details = _score_sections(text_lower)
    contact_score, contact_details = _score_contact_info(text)
    verb_score, verb_count = _score_action_verbs(text_lower)
    quant_score, quant_count = _score_quantification(text)
    len_score, len_label = _score_length(word_count)

    breakdown = {
        "keywords": {
            "score": round(kw_score, 1),
            "weight": SCORE_WEIGHTS["keywords"],
            "label": f"{len(matched)}/{len(jd_keywords)} JD keywords matched",
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
    if missing:
        suggestions.insert(0, f"JD asks for: {', '.join(missing[:8])} — call these out if you have them.")

    return ATSResult(
        overall_score=overall,
        grade=_grade(overall),
        breakdown=breakdown,
        matched_keywords=matched,
        missing_keywords=missing[:20],
        suggestions=suggestions,
        word_count=word_count,
        target_role="custom_jd",
    )
