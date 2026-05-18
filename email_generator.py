"""Template-based cold email + LinkedIn DM generator.

Rule-based (no API cost). Pulls from curated templates and fills slots.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


COLD_EMAIL_TEMPLATES = {
    "referral_request": [
        {
            "subject": "Quick question about {company} — {role} role",
            "body": (
                "Hi {recipient_name},\n\n"
                "I came across your profile while researching {company}'s {team} team — your work on "
                "{their_work} stood out to me. I'm a {your_role} with experience in {your_skills}, "
                "and I'm really excited about the {role} role you have open.\n\n"
                "Would you be open to a 15-minute chat about your experience at {company}? "
                "If it feels like a fit, I'd be grateful for a referral — but I'd love the conversation regardless.\n\n"
                "I've attached my resume for context. Thanks so much for your time.\n\n"
                "Best,\n{your_name}"
            ),
        },
        {
            "subject": "Aspiring {your_role} — would love your advice on {company}",
            "body": (
                "Hi {recipient_name},\n\n"
                "I hope this finds you well. I'm {your_name}, a {your_role} working with {your_skills}. "
                "I've been following {company}'s work, especially {their_work}, and I noticed an opening "
                "for {role}.\n\n"
                "Rather than dropping into the pile, I wanted to reach out directly. Could I ask you 2-3 "
                "questions about what the team values in candidates? If a referral makes sense after that, "
                "it would mean a lot.\n\n"
                "Either way, I appreciate you reading this.\n\n"
                "Thanks,\n{your_name}"
            ),
        },
    ],
    "cold_application": [
        {
            "subject": "{your_role} interested in the {role} position",
            "body": (
                "Dear {recipient_name},\n\n"
                "I'm writing to express my interest in the {role} position at {company}. "
                "With my background in {your_skills}, I believe I can contribute to {their_work}.\n\n"
                "A few highlights from my work:\n"
                "- Built and deployed ML models in production\n"
                "- Strong foundation in {your_skills}\n"
                "- {achievement}\n\n"
                "I've attached my resume and would welcome the chance to discuss how I can add value to your team.\n\n"
                "Thank you for your consideration.\n\n"
                "Best regards,\n{your_name}"
            ),
        },
    ],
    "informational_interview": [
        {
            "subject": "{your_role} interested in {company} — 15 min chat?",
            "body": (
                "Hi {recipient_name},\n\n"
                "I'm {your_name}, currently working as a {your_role} with focus on {your_skills}. "
                "I've been admiring {company}'s approach to {their_work} and would love to learn more "
                "about how your team operates.\n\n"
                "Would you have 15 minutes for a quick virtual coffee in the next two weeks? "
                "I'm not asking about openings — just genuinely curious about your career path and "
                "what's exciting at {company} right now.\n\n"
                "Happy to work around your schedule.\n\n"
                "Thanks,\n{your_name}"
            ),
        },
    ],
    "follow_up": [
        {
            "subject": "Re: {role} application — following up",
            "body": (
                "Hi {recipient_name},\n\n"
                "I wanted to follow up on my application for the {role} role at {company} submitted on "
                "{date}. I remain very excited about the opportunity and the chance to contribute to "
                "{their_work}.\n\n"
                "If there's any additional information I can provide — projects, references, or work "
                "samples — please let me know. Happy to make a 15-minute call work at your convenience.\n\n"
                "Thanks for your time and consideration.\n\n"
                "Best,\n{your_name}"
            ),
        },
    ],
    "thank_you_post_interview": [
        {
            "subject": "Thank you — {role} interview",
            "body": (
                "Hi {recipient_name},\n\n"
                "Thank you for taking the time to speak with me today about the {role} role. I really "
                "enjoyed our conversation, especially the part about {their_work} — it confirmed that "
                "{company} is a place I'd be excited to contribute.\n\n"
                "If any follow-up questions come up on your side, I'm happy to expand on anything we "
                "discussed. Looking forward to next steps.\n\n"
                "Best,\n{your_name}"
            ),
        },
    ],
}

LINKEDIN_DM_TEMPLATES = {
    "connect_request": [
        (
            "Hi {recipient_name}, I came across your profile while exploring {company} and was impressed by "
            "your work in {their_work}. I'm a {your_role} also working with {your_skills} — would love to "
            "connect and follow your journey."
        ),
        (
            "Hello {recipient_name}, fellow {your_role} here. Your background at {company} is exactly the "
            "kind of trajectory I'm aiming for. Hoping to connect and learn from your posts."
        ),
    ],
    "post_connect_intro": [
        (
            "Hi {recipient_name}, thanks for connecting! Quick context: I'm a {your_role} skilled in "
            "{your_skills}, currently exploring {role} roles. {company} has been on my radar for a while — "
            "particularly your team's work on {their_work}.\n\n"
            "If you're open to it, I'd value 10 minutes of your time to hear what the team looks for in "
            "candidates. No pressure if your week is busy — even a written tip or two would help.\n\n"
            "Thanks either way!"
        ),
    ],
    "referral_ask": [
        (
            "Hi {recipient_name}, hope you're doing well. I applied to the {role} role at {company} last "
            "week. Given your experience there with {their_work}, would you be open to a quick chat? "
            "And if it feels like a fit, a referral would mean a lot. Resume ready to share."
        ),
    ],
    "alumni_outreach": [
        (
            "Hi {recipient_name}, fellow {alma_mater} alum here! I'm a {your_role} exploring {role} roles "
            "and noticed you're at {company}. Would love to hear about your transition and what you've "
            "learned along the way. Open to a quick chat?"
        ),
    ],
    "recruiter_response": [
        (
            "Hi {recipient_name}, thanks for reaching out — the {role} role at {company} sounds "
            "interesting. I'd be happy to learn more. My current focus is {your_skills}, and I'm "
            "actively considering new opportunities. Could we set up a 20-minute intro call? "
            "I'm available {availability}."
        ),
    ],
}


@dataclass
class GenerationRequest:
    template_key: str  # e.g., "referral_request"
    medium: str  # "email" or "linkedin"
    your_name: str = "Your Name"
    your_role: str = "Data Scientist"
    your_skills: str = "Python, ML, SQL"
    recipient_name: str = "Hiring Manager"
    company: str = "the company"
    role: str = "Data Scientist"
    team: str = "Data Science"
    their_work: str = "your recent projects"
    achievement: str = "Shipped a model that improved KPI by 20%"
    date: str = "this week"
    alma_mater: str = "your alma mater"
    availability: str = "Tue/Thu afternoons"

    def as_slots(self) -> dict[str, str]:
        return {
            "your_name": self.your_name,
            "your_role": self.your_role,
            "your_skills": self.your_skills,
            "recipient_name": self.recipient_name,
            "company": self.company,
            "role": self.role,
            "team": self.team,
            "their_work": self.their_work,
            "achievement": self.achievement,
            "date": self.date,
            "alma_mater": self.alma_mater,
            "availability": self.availability,
        }


def generate_email(req: GenerationRequest) -> dict:
    pool = COLD_EMAIL_TEMPLATES.get(req.template_key)
    if not pool:
        raise ValueError(f"Unknown email template: {req.template_key}")
    template = random.choice(pool)
    slots = req.as_slots()
    return {
        "subject": template["subject"].format(**slots),
        "body": template["body"].format(**slots),
        "medium": "email",
    }


def generate_linkedin_dm(req: GenerationRequest) -> dict:
    pool = LINKEDIN_DM_TEMPLATES.get(req.template_key)
    if not pool:
        raise ValueError(f"Unknown LinkedIn template: {req.template_key}")
    template = random.choice(pool)
    return {
        "message": template.format(**req.as_slots()),
        "medium": "linkedin",
    }


def generate(req: GenerationRequest) -> dict:
    if req.medium == "linkedin":
        return generate_linkedin_dm(req)
    return generate_email(req)


def available_templates() -> dict:
    return {
        "email": [
            {"value": "referral_request", "label": "Referral request"},
            {"value": "cold_application", "label": "Cold application"},
            {"value": "informational_interview", "label": "Informational interview"},
            {"value": "follow_up", "label": "Application follow-up"},
            {"value": "thank_you_post_interview", "label": "Thank-you after interview"},
        ],
        "linkedin": [
            {"value": "connect_request", "label": "Connection request (300 char)"},
            {"value": "post_connect_intro", "label": "After they accept"},
            {"value": "referral_ask", "label": "Ask for a referral"},
            {"value": "alumni_outreach", "label": "Alumni outreach"},
            {"value": "recruiter_response", "label": "Reply to recruiter"},
        ],
    }
