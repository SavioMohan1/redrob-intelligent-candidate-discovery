#!/usr/bin/env python3
"""Fast, offline candidate ranking for the Redrob AI challenge.

The ranker is intentionally transparent: it converts the JD into interpretable
signals, scores each candidate in one streaming pass, then writes the required
top-100 CSV. It uses only the Python standard library so the ranking step is
easy to reproduce inside the CPU/no-network constraint.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import heapq
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


TODAY = dt.date(2026, 6, 12)

PROFICIENCY_WEIGHT = {
    "beginner": 0.35,
    "intermediate": 0.65,
    "advanced": 0.9,
    "expert": 1.0,
}

EDU_TIER_WEIGHT = {
    "tier_1": 1.0,
    "tier_2": 0.65,
    "tier_3": 0.25,
    "tier_4": 0.0,
    "unknown": 0.1,
}

SERVICE_COMPANIES = {
    "accenture",
    "capgemini",
    "cognizant",
    "hcl",
    "hcltech",
    "ibm",
    "infosys",
    "lti",
    "ltimindtree",
    "mindtree",
    "tata consultancy services",
    "tcs",
    "tech mahindra",
    "wipro",
}

PRODUCT_INDUSTRIES = {
    "adtech",
    "ai services",
    "ai/ml",
    "conversational ai",
    "e-commerce",
    "edtech",
    "fintech",
    "food delivery",
    "gaming",
    "healthtech ai",
    "insurance tech",
    "internet",
    "media",
    "saas",
    "software",
    "transportation",
    "voice ai",
}

TARGET_CITY_WEIGHTS = {
    "pune": 1.0,
    "noida": 1.0,
    "delhi": 0.88,
    "gurgaon": 0.85,
    "gurugram": 0.85,
    "mumbai": 0.8,
    "hyderabad": 0.78,
    "bangalore": 0.72,
    "bengaluru": 0.72,
    "chennai": 0.45,
}

STRONG_TITLES = {
    "senior ai engineer",
    "lead ai engineer",
    "staff machine learning engineer",
    "senior machine learning engineer",
    "senior nlp engineer",
    "senior applied scientist",
    "recommendation systems engineer",
    "search engineer",
}

GOOD_TITLES = {
    "ai engineer",
    "applied ml engineer",
    "machine learning engineer",
    "nlp engineer",
    "senior data scientist",
    "senior software engineer (ml)",
}

MODERATE_TITLES = {
    "ai research engineer",
    "ai specialist",
    "data scientist",
    "junior ml engineer",
    "ml engineer",
}

ADJACENT_TITLES = {
    "analytics engineer",
    "backend engineer",
    "cloud engineer",
    "data analyst",
    "data engineer",
    "devops engineer",
    "senior data engineer",
    "senior software engineer",
    "software engineer",
}

NON_TECH_TITLES = {
    "accountant",
    "business analyst",
    "civil engineer",
    "content writer",
    "customer support",
    "graphic designer",
    "hr manager",
    "marketing manager",
    "mechanical engineer",
    "operations manager",
    "project manager",
    "sales executive",
}

TEXT_PATTERNS = {
    "retrieval": [
        (r"\bhybrid retrieval\b", 3.0),
        (r"\bembedding[- ]based retrieval\b", 2.8),
        (r"\bsemantic search\b", 2.7),
        (r"\bvector search\b", 2.6),
        (r"\brag\b", 2.3),
        (r"\bretrieval\b", 2.0),
        (r"\bsearch\b", 1.4),
        (r"\bembeddings?\b", 1.35),
        (r"\bvector\b", 1.0),
        (r"\bfaiss\b|\bmilvus\b|\bqdrant\b|\bpinecone\b|\bweaviate\b", 1.8),
        (r"\bopensearch\b|\belasticsearch\b|\bbm25\b", 1.55),
    ],
    "ranking": [
        (r"\blearning[- ]to[- ]rank\b", 3.0),
        (r"\branking\b|\branker\b", 2.3),
        (r"\brecommendation system\b|\brecommender\b", 2.2),
        (r"\bcandidate[- ]jd matching\b", 2.6),
        (r"\bmatching pipeline\b", 1.8),
        (r"\bdiscovery feed\b", 1.5),
    ],
    "evaluation": [
        (r"\bndcg\b|\bmrr\b|\bmap\b|\brecall\b", 2.3),
        (r"\boffline[-/ ]online\b", 2.0),
        (r"\bevaluation harness\b|\beval framework\b", 2.4),
        (r"\ba/b\b|\bab test\b|\bexperimentation\b", 1.6),
        (r"\brelevance\b|\bfeedback loop\b", 1.2),
    ],
    "production": [
        (r"\bproduction\b|\bdeployed\b|\blaunched\b|\bshipped\b", 1.8),
        (r"\breal users\b|\bserving\b|\bserved\b", 1.6),
        (r"\bqps\b|\bp95\b|\blatency\b|\bmillisecond\b", 1.45),
        (r"\bdrift\b|\bmonitoring\b|\bindex refresh\b|\bretraining\b", 1.35),
        (r"\bscale\b|\bscaled\b|\bcorpus\b|\bqueries per month\b", 1.2),
        (r"\bon-call\b|\bdata quality\b", 0.8),
    ],
    "shipper": [
        (r"\bship\b|\bshipping\b|\bscrappy\b|\bproduct\b", 1.2),
        (r"\bv1\b|\bprototype to production\b|\bworking v1\b", 1.2),
    ],
    "research_only": [
        (r"\bacademic lab\b|\bresearch-only\b|\bpapers?\b|\bpublication\b", 1.0),
    ],
    "cv_speech_robotics": [
        (r"\bcomputer vision\b|\bimage classification\b|\bobject detection\b", 1.0),
        (r"\bspeech recognition\b|\btts\b|\bvoice\b", 0.9),
        (r"\brobotics\b|\bgan\b", 0.8),
    ],
}

COMPILED_TEXT_PATTERNS = {
    group: [(re.compile(pattern, flags=re.IGNORECASE), weight) for pattern, weight in patterns]
    for group, patterns in TEXT_PATTERNS.items()
}

YEARS_RE = re.compile(r"\b(\d{1,2}(?:\.\d)?)\+?\s+years?\b", flags=re.IGNORECASE)

SKILL_GROUPS = {
    "core": {
        "python",
        "machine learning",
        "ml",
        "nlp",
        "llms",
        "llm",
        "rag",
        "embeddings",
        "vector search",
        "semantic search",
        "recommendation systems",
        "ranking",
        "learning to rank",
        "search relevance",
        "fine-tuning llms",
        "lora",
        "qlora",
        "peft",
        "transformers",
        "xgboost",
        "statistical modeling",
        "feature engineering",
    },
    "vector": {
        "faiss",
        "milvus",
        "qdrant",
        "pinecone",
        "weaviate",
        "opensearch",
        "elasticsearch",
    },
    "infra": {
        "airflow",
        "apache beam",
        "aws",
        "bigquery",
        "ci/cd",
        "databricks",
        "dbt",
        "docker",
        "etl",
        "gcp",
        "kafka",
        "kubernetes",
        "rest apis",
        "snowflake",
        "spark",
        "terraform",
    },
    "off_domain": {
        "computer vision",
        "image classification",
        "speech recognition",
        "tts",
        "gans",
        "robotics",
    },
}


@dataclass(slots=True)
class ScoredCandidate:
    score: float
    candidate_id: str
    rank_sort: tuple[float, str] = field(init=False, repr=False)
    record: dict[str, Any] = field(compare=False, repr=False)
    features: dict[str, Any] = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        self.rank_sort = (-self.score, self.candidate_id)

    def heap_key(self) -> tuple[float, str]:
        return (self.score, _reverse_id_for_heap(self.candidate_id))


def _reverse_id_for_heap(candidate_id: str) -> str:
    # For equal scores, candidate_id ascending should win. The heap stores the
    # weakest retained candidate, so invert the id lexicographically.
    return "".join(chr(255 - ord(ch)) for ch in candidate_id)


def open_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def norm(text: str | None) -> str:
    return (text or "").strip().lower()


def tokenize_text(candidate: dict[str, Any]) -> str:
    profile = candidate["profile"]
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_industry", ""),
        profile.get("current_company", ""),
    ]
    for job in candidate.get("career_history", []):
        parts.extend(
            [
                job.get("title", ""),
                job.get("industry", ""),
                job.get("company", ""),
                job.get("description", ""),
            ]
        )
    for skill in candidate.get("skills", []):
        parts.append(skill.get("name", ""))
    for cert in candidate.get("certifications", []):
        parts.append(cert.get("name", ""))
    return "\n".join(parts).lower()


def pattern_score(text: str, group: str) -> tuple[float, list[str]]:
    total = 0.0
    hits: list[str] = []
    for pattern, weight in COMPILED_TEXT_PATTERNS[group]:
        count = 0
        for _ in pattern.finditer(text):
            count += 1
            if count == 5:
                break
        if count:
            total += min(count, 5) * weight
            hits.append(pattern.pattern)
    return total, hits


def title_score(title: str) -> float:
    title_l = norm(title)
    if title_l in STRONG_TITLES:
        return 1.0
    if title_l in GOOD_TITLES:
        return 0.84
    if title_l in MODERATE_TITLES:
        return 0.58
    if title_l in ADJACENT_TITLES:
        return 0.32
    if title_l in NON_TECH_TITLES:
        return -0.85
    return 0.0


def experience_score(years: float) -> float:
    if 5.0 <= years <= 9.0:
        return 1.0
    if 4.0 <= years < 5.0:
        return 0.72
    if 9.0 < years <= 10.5:
        return 0.68
    if 3.0 <= years < 4.0:
        return 0.35
    if 10.5 < years <= 12.0:
        return 0.25
    return -0.35


def skill_scores(candidate: dict[str, Any]) -> dict[str, Any]:
    total = 0.0
    core = 0.0
    vector = 0.0
    infra = 0.0
    off_domain = 0.0
    trusted_core_count = 0
    weak_ai_claims = 0
    top_skills: list[str] = []

    assessments = {
        norm(k): float(v)
        for k, v in candidate["redrob_signals"].get("skill_assessment_scores", {}).items()
    }

    for skill in candidate.get("skills", []):
        name = norm(skill.get("name"))
        if not name:
            continue
        prof = PROFICIENCY_WEIGHT.get(skill.get("proficiency"), 0.5)
        duration = float(skill.get("duration_months") or 0)
        endorsements = float(skill.get("endorsements") or 0)
        trust = 0.55 + 0.25 * min(duration / 36.0, 1.0) + 0.20 * min(math.log1p(endorsements) / math.log(51), 1.0)
        if name in assessments:
            trust *= 0.75 + 0.5 * min(assessments[name] / 100.0, 1.0)
        value = prof * trust

        is_core = name in SKILL_GROUPS["core"]
        is_vector = name in SKILL_GROUPS["vector"]
        is_infra = name in SKILL_GROUPS["infra"]
        is_off_domain = name in SKILL_GROUPS["off_domain"]

        if is_core:
            core += value
            if duration >= 12 and endorsements >= 3:
                trusted_core_count += 1
            if len(top_skills) < 7:
                top_skills.append(skill.get("name", ""))
        if is_vector:
            vector += value
            if duration >= 12 and endorsements >= 3:
                trusted_core_count += 1
            if len(top_skills) < 7:
                top_skills.append(skill.get("name", ""))
        if is_infra:
            infra += value
        if is_off_domain:
            off_domain += value
        if (is_core or is_vector or is_off_domain) and prof >= 0.9 and (duration <= 2 or endorsements == 0):
            weak_ai_claims += 1

    total = 1.65 * min(core / 5.0, 1.0) + 1.2 * min(vector / 2.0, 1.0) + 0.55 * min(infra / 5.0, 1.0)
    return {
        "skill_score": total,
        "core_skill_strength": core,
        "vector_skill_strength": vector,
        "infra_skill_strength": infra,
        "off_domain_strength": off_domain,
        "trusted_core_count": trusted_core_count,
        "weak_ai_claims": weak_ai_claims,
        "top_relevant_skills": top_skills,
    }


def behavior_score(signals: dict[str, Any], location: str, country: str) -> tuple[float, dict[str, Any]]:
    last_active = parse_date(signals.get("last_active_date"))
    inactive_days = 999
    if last_active:
        inactive_days = max((TODAY - last_active).days, 0)

    if inactive_days <= 21:
        recency = 1.0
    elif inactive_days <= 45:
        recency = 0.82
    elif inactive_days <= 90:
        recency = 0.58
    elif inactive_days <= 180:
        recency = 0.28
    else:
        recency = 0.05

    response = float(signals.get("recruiter_response_rate") or 0)
    avg_hours = float(signals.get("avg_response_time_hours") or 999)
    response_speed = max(0.0, min(1.0, 1.0 - (avg_hours / 168.0)))
    open_to_work = 1.0 if signals.get("open_to_work_flag") else 0.0
    interview = float(signals.get("interview_completion_rate") or 0)
    offer = float(signals.get("offer_acceptance_rate") or -1)
    offer_component = 0.45 if offer < 0 else offer
    notice = float(signals.get("notice_period_days") or 0)
    notice_component = 1.0 if notice <= 30 else 0.72 if notice <= 60 else 0.35 if notice <= 90 else 0.08
    github = float(signals.get("github_activity_score") or -1)
    github_component = 0.45 if github < 0 else min(github / 75.0, 1.0)
    verified = (
        int(bool(signals.get("verified_email")))
        + int(bool(signals.get("verified_phone")))
        + int(bool(signals.get("linkedin_connected")))
    ) / 3.0

    demand = (
        0.35 * min(math.log1p(float(signals.get("saved_by_recruiters_30d") or 0)) / math.log(40), 1.0)
        + 0.25 * min(math.log1p(float(signals.get("profile_views_received_30d") or 0)) / math.log(160), 1.0)
        + 0.15 * min(math.log1p(float(signals.get("search_appearance_30d") or 0)) / math.log(900), 1.0)
        + 0.25 * min(math.log1p(float(signals.get("endorsements_received") or 0)) / math.log(160), 1.0)
    )

    city = location.lower()
    city_score = 0.0
    for key, weight in TARGET_CITY_WEIGHTS.items():
        if key in city:
            city_score = max(city_score, weight)
    if norm(country) == "india":
        geo = max(0.45, city_score)
    else:
        geo = 0.18
    if signals.get("willing_to_relocate"):
        geo = max(geo, 0.78)
    mode = norm(signals.get("preferred_work_mode"))
    work_mode = 1.0 if mode in {"hybrid", "flexible"} else 0.74 if mode == "onsite" else 0.5

    score = (
        0.24 * recency
        + 0.20 * response
        + 0.08 * response_speed
        + 0.10 * open_to_work
        + 0.08 * interview
        + 0.06 * offer_component
        + 0.07 * notice_component
        + 0.06 * github_component
        + 0.05 * demand
        + 0.04 * verified
        + 0.02 * work_mode
    )

    details = {
        "inactive_days": inactive_days,
        "recency": recency,
        "response": response,
        "notice_component": notice_component,
        "geo": geo,
        "city_score": city_score,
        "github_component": github_component,
        "demand": demand,
    }
    return score + 0.18 * geo, details


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def product_company_score(candidate: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    jobs = candidate.get("career_history", [])
    product_jobs = 0
    service_jobs = 0
    current_product = norm(candidate["profile"].get("current_industry")) in PRODUCT_INDUSTRIES

    for job in jobs:
        industry = norm(job.get("industry"))
        company = norm(job.get("company"))
        if industry in PRODUCT_INDUSTRIES:
            product_jobs += 1
        if industry == "it services" or company in SERVICE_COMPANIES:
            service_jobs += 1

    if product_jobs:
        score = min(product_jobs / max(len(jobs), 1), 1.0)
        score += 0.25 if current_product else 0.0
        score = min(score, 1.0)
    else:
        score = -0.4 if service_jobs == len(jobs) and jobs else -0.1

    return score, {
        "product_jobs": product_jobs,
        "service_jobs": service_jobs,
        "current_product": current_product,
        "only_services": bool(jobs and service_jobs == len(jobs)),
    }


def consistency_penalty(candidate: dict[str, Any], text: str, skill_info: dict[str, Any]) -> tuple[float, list[str]]:
    penalties = 0.0
    flags: list[str] = []
    profile = candidate["profile"]
    years = float(profile.get("years_of_experience") or 0)
    title = norm(profile.get("current_title"))

    years_mentions = []
    for match in YEARS_RE.finditer(text):
        value = float(match.group(1))
        if 0.5 <= value <= 25:
            years_mentions.append(value)
    if years_mentions:
        nearest_diff = min(abs(years - y) for y in years_mentions)
        if nearest_diff > 4.0:
            penalties += 2.1 if years > 12.0 or years < 3.5 else 0.85
            flags.append("experience_years_mismatch")
        elif nearest_diff > 2.5:
            penalties += 0.22
            flags.append("minor_experience_years_mismatch")

    if skill_info["weak_ai_claims"] >= 5:
        penalties += 0.5
        flags.append("weak_ai_skill_claims")
    elif skill_info["weak_ai_claims"] >= 3:
        penalties += 0.25
        flags.append("some_weak_ai_skill_claims")

    duration_mismatches = 0
    for job in candidate.get("career_history", []):
        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date")) or TODAY
        if not start or not end:
            continue
        actual_months = max(0, (end.year - start.year) * 12 + (end.month - start.month))
        stated = int(job.get("duration_months") or 0)
        if abs(actual_months - stated) > max(9, 0.35 * max(actual_months, 1)):
            duration_mismatches += 1
    if duration_mismatches:
        penalties += min(0.18 * duration_mismatches, 0.55)
        flags.append("career_duration_mismatch")

    if "senior" in title and years < 4.0:
        penalties += 0.35
        flags.append("senior_title_low_experience")

    return penalties, flags


def score_candidate(candidate: dict[str, Any]) -> ScoredCandidate:
    profile = candidate["profile"]
    text = tokenize_text(candidate)

    retrieval, _ = pattern_score(text, "retrieval")
    ranking, _ = pattern_score(text, "ranking")
    evaluation, _ = pattern_score(text, "evaluation")
    production, _ = pattern_score(text, "production")
    shipper, _ = pattern_score(text, "shipper")
    research_only, _ = pattern_score(text, "research_only")
    cv_speech_robotics, _ = pattern_score(text, "cv_speech_robotics")

    skill_info = skill_scores(candidate)
    behavior, behavior_info = behavior_score(
        candidate["redrob_signals"],
        profile.get("location", ""),
        profile.get("country", ""),
    )
    product, product_info = product_company_score(candidate)
    consistency, flags = consistency_penalty(candidate, text, skill_info)

    title = norm(profile.get("current_title"))
    years = float(profile.get("years_of_experience") or 0)

    title_component = title_score(title)
    exp_component = experience_score(years)
    retrieval_component = min((retrieval + 0.85 * ranking) / 18.0, 1.0)
    evaluation_component = min(evaluation / 7.0, 1.0)
    production_component = min(production / 12.0, 1.0)
    shipper_component = min(shipper / 5.0, 1.0)
    product_component = product

    off_domain_penalty = 0.0
    if cv_speech_robotics > 3.0 and retrieval + ranking < 4.0:
        off_domain_penalty += 0.25
    if title == "ai research engineer" and production < 3.5:
        off_domain_penalty += 0.28
    if research_only > 2.0 and production < 4.0:
        off_domain_penalty += 0.35

    nontech_penalty = 0.0
    if title in NON_TECH_TITLES:
        nontech_penalty += 1.25
        if retrieval + ranking < 6.0:
            nontech_penalty += 0.6

    services_penalty = 0.0
    if product_info["only_services"]:
        services_penalty += 0.32
        if production + retrieval + ranking < 9:
            services_penalty += 0.25

    logistics_penalty = 0.0
    if norm(profile.get("country")) != "india":
        logistics_penalty += 0.65
        if candidate["redrob_signals"].get("willing_to_relocate"):
            logistics_penalty -= 0.42

    engagement_gate = 0.75 + 0.35 * behavior
    if behavior_info["inactive_days"] > 180:
        engagement_gate -= 0.18
    if behavior_info["response"] < 0.12:
        engagement_gate -= 0.16

    raw = (
        1.85 * title_component
        + 1.25 * exp_component
        + 2.35 * retrieval_component
        + 1.55 * evaluation_component
        + 1.65 * production_component
        + 1.10 * skill_info["skill_score"]
        + 0.85 * product_component
        + 0.65 * behavior
        + 0.35 * behavior_info["geo"]
        + 0.25 * shipper_component
    )

    penalty = consistency + off_domain_penalty + nontech_penalty + services_penalty + logistics_penalty
    adjusted = raw * engagement_gate - penalty

    # Keep scores in a validator-friendly 0-1 range while preserving order.
    score = 1.0 / (1.0 + math.exp(-0.72 * (adjusted - 4.7)))

    features = {
        "title_component": title_component,
        "experience_component": exp_component,
        "retrieval_component": retrieval_component,
        "evaluation_component": evaluation_component,
        "production_component": production_component,
        "product_component": product_component,
        "behavior": behavior,
        "raw": raw,
        "adjusted": adjusted,
        "penalty": penalty,
        "retrieval_terms_score": retrieval,
        "ranking_terms_score": ranking,
        "evaluation_terms_score": evaluation,
        "production_terms_score": production,
        "shipper_terms_score": shipper,
        "research_only_score": research_only,
        "cv_speech_robotics_score": cv_speech_robotics,
        "flags": flags,
        **skill_info,
        **behavior_info,
        **product_info,
    }

    return ScoredCandidate(score=score, candidate_id=candidate["candidate_id"], record=candidate, features=features)


def build_reasoning(scored: ScoredCandidate) -> str:
    candidate = scored.record
    profile = candidate["profile"]
    features = scored.features
    signals = candidate["redrob_signals"]
    title = profile.get("current_title", "Candidate")
    years = float(profile.get("years_of_experience") or 0)
    location = profile.get("location", "")

    strengths: list[str] = []
    if features["retrieval_component"] >= 0.6:
        strengths.append("clear retrieval/search/ranking production evidence")
    elif features["retrieval_component"] >= 0.35:
        strengths.append("some retrieval or recommendation-system evidence")
    if features["evaluation_component"] >= 0.45:
        strengths.append("ranking/evaluation signal")
    if features["production_component"] >= 0.55:
        strengths.append("production ML systems experience")
    if features["top_relevant_skills"]:
        skills = ", ".join(features["top_relevant_skills"][:3])
        strengths.append(f"relevant skills including {skills}")
    if features["product_jobs"] > 0:
        strengths.append("product-company background")

    if not strengths:
        strengths.append("adjacent ML/data background")

    availability = (
        f"last active {features['inactive_days']}d ago"
        if features["inactive_days"] < 999
        else "activity date unavailable"
    )
    response = float(signals.get("recruiter_response_rate") or 0)

    concerns: list[str] = []
    notice = int(signals.get("notice_period_days") or 0)
    if notice > 60:
        concerns.append(f"{notice}d notice")
    if norm(profile.get("country")) != "india" and not signals.get("willing_to_relocate"):
        concerns.append("outside India without relocation signal")
    if features["only_services"]:
        concerns.append("services-heavy career")
    if features["flags"]:
        concerns.append("minor consistency concerns")
    if response < 0.18:
        concerns.append(f"low recruiter response rate {response:.2f}")
    if features["inactive_days"] > 120:
        concerns.append("stale platform activity")

    first = (
        f"{title} with {years:.1f} yrs in {location}; "
        f"{'; '.join(strengths[:3])}."
    )
    second = f"Behavioral fit: response rate {response:.2f}, {availability}"
    if concerns:
        second += f"; concern: {', '.join(concerns[:2])}."
    else:
        second += "."
    return f"{first} {second}"


def rank_candidates(candidates_path: Path, limit: int = 100) -> list[ScoredCandidate]:
    heap: list[tuple[tuple[float, str], ScoredCandidate]] = []
    for candidate in open_jsonl(candidates_path):
        scored = score_candidate(candidate)
        item = (scored.heap_key(), scored)
        if len(heap) < limit:
            heapq.heappush(heap, item)
        elif item[0] > heap[0][0]:
            heapq.heapreplace(heap, item)
    ranked = [item[1] for item in heap]
    ranked.sort(key=lambda x: (-x.score, x.candidate_id))
    return ranked


def write_submission(ranked: list[ScoredCandidate], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, scored in enumerate(ranked, start=1):
            writer.writerow(
                [
                    scored.candidate_id,
                    rank,
                    f"{scored.score:.6f}",
                    build_reasoning(scored),
                ]
            )


def write_audit(ranked: list[ScoredCandidate], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for rank, scored in enumerate(ranked, start=1):
        profile = scored.record["profile"]
        row = {
            "rank": rank,
            "candidate_id": scored.candidate_id,
            "score": round(scored.score, 6),
            "title": profile.get("current_title"),
            "years": profile.get("years_of_experience"),
            "location": profile.get("location"),
            "country": profile.get("country"),
            "industry": profile.get("current_industry"),
            "reasoning": build_reasoning(scored),
            "features": scored.features,
        }
        rows.append(row)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Rank Redrob candidates for the Senior AI Engineer JD.")
    parser.add_argument("--candidates", default="candidates.jsonl", type=Path, help="Path to candidates.jsonl or .jsonl.gz")
    parser.add_argument("--out", default="outputs/submission.csv", type=Path, help="Output CSV path")
    parser.add_argument("--audit", default="outputs/audit_top100.json", type=Path, help="Optional JSON audit path")
    parser.add_argument("--limit", default=100, type=int, help="Number of ranked candidates to emit")
    args = parser.parse_args(argv)

    ranked = rank_candidates(args.candidates, args.limit)
    write_submission(ranked, args.out)
    if args.audit:
        write_audit(ranked, args.audit)
    print(f"Wrote {len(ranked)} ranked candidates to {args.out}")


if __name__ == "__main__":
    main()
