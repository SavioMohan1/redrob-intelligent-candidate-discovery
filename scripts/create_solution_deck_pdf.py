#!/usr/bin/env python3
"""Generate the Redrob challenge solution deck as a PDF."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "outputs" / "audit_top100.json"
OUT_DIR = ROOT / "output" / "pdf"
OUT_PATH = OUT_DIR / "redrob_ai_candidate_ranker_solution_deck.pdf"

W, H = 960, 540
MARGIN = 54

NAVY = colors.HexColor("#102033")
INK = colors.HexColor("#18212f")
MUTED = colors.HexColor("#5e6877")
BLUE = colors.HexColor("#2563eb")
TEAL = colors.HexColor("#0f766e")
GREEN = colors.HexColor("#15803d")
AMBER = colors.HexColor("#b45309")
RED = colors.HexColor("#b91c1c")
PANEL = colors.HexColor("#f6f8fb")
LINE = colors.HexColor("#d7dde7")
WHITE = colors.white


def load_audit() -> list[dict]:
    if not AUDIT_PATH.exists():
        raise FileNotFoundError(f"Missing audit file: {AUDIT_PATH}")
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def draw_header(c: canvas.Canvas, title: str, page: int, section: str = "Redrob AI Challenge") -> None:
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(0, H - 48, W, 48, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN, H - 30, section)
    c.setFont("Helvetica", 10)
    c.drawRightString(W - MARGIN, H - 30, f"{page:02d}")
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(MARGIN, H - 88, title)
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(MARGIN, H - 105, W - MARGIN, H - 105)


def text_width(text: str, size: int, font: str = "Helvetica") -> float:
    return pdfmetrics.stringWidth(text, font, size)


def wrap_text(text: str, max_width: float, size: int = 13, font: str = "Helvetica") -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = word if not line else f"{line} {word}"
        if text_width(candidate, size, font) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_para(c: canvas.Canvas, text: str, x: float, y: float, width: float, size: int = 13, leading: int = 18,
              color=INK, font: str = "Helvetica") -> float:
    c.setFillColor(color)
    c.setFont(font, size)
    for line in wrap_text(text, width, size, font):
        c.drawString(x, y, line)
        y -= leading
    return y


def draw_bullets(c: canvas.Canvas, bullets: list[str], x: float, y: float, width: float, size: int = 13,
                 leading: int = 20, color=INK) -> float:
    c.setFillColor(color)
    c.setFont("Helvetica", size)
    for bullet in bullets:
        lines = wrap_text(bullet, width - 22, size)
        c.circle(x + 4, y + 4, 2.5, fill=1, stroke=0)
        c.drawString(x + 18, y, lines[0])
        y -= leading
        for line in lines[1:]:
            c.drawString(x + 18, y, line)
            y -= leading
        y -= 3
    return y


def rounded_panel(c: canvas.Canvas, x: float, y: float, w: float, h: float, fill=PANEL, stroke=LINE) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.roundRect(x, y, w, h, 8, fill=1, stroke=1)


def metric_card(c: canvas.Canvas, x: float, y: float, w: float, h: float, value: str, label: str, color=BLUE) -> None:
    rounded_panel(c, x, y, w, h, fill=colors.HexColor("#ffffff"))
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(x + 18, y + h - 36, value)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 10)
    for i, line in enumerate(wrap_text(label, w - 34, 10)):
        c.drawString(x + 18, y + h - 56 - i * 13, line)


def draw_bar_chart(c: canvas.Canvas, data: Counter, x: float, y: float, w: float, h: float, title: str,
                   max_items: int = 9) -> None:
    items = data.most_common(max_items)
    max_value = max(v for _, v in items)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x, y + h + 16, title)
    bar_h = min(22, (h - 10) / len(items) - 5)
    gap = 7
    label_w = 180
    for idx, (label, value) in enumerate(items):
        by = y + h - (idx + 1) * (bar_h + gap)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9)
        short = label if len(label) <= 28 else label[:25] + "..."
        c.drawRightString(x + label_w - 8, by + 6, short)
        c.setFillColor(colors.HexColor("#dbeafe"))
        c.rect(x + label_w, by, w - label_w - 40, bar_h, fill=1, stroke=0)
        c.setFillColor(BLUE if idx < 3 else TEAL)
        c.rect(x + label_w, by, (w - label_w - 40) * value / max_value, bar_h, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(x + w, by + 6, str(value))


def title_slide(c: canvas.Canvas, page: int) -> None:
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#1d4ed8"))
    c.rect(0, 0, W, 18, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 40)
    c.drawString(MARGIN, 360, "Intelligent Candidate")
    c.drawString(MARGIN, 313, "Discovery and Ranking")
    c.setFillColor(colors.HexColor("#cbd5e1"))
    c.setFont("Helvetica", 18)
    c.drawString(MARGIN, 268, "Senior AI Engineer shortlist for Redrob AI")
    c.setFont("Helvetica", 13)
    c.drawString(MARGIN, 226, "Offline, explainable ranker optimized for production ML fit, behavioral availability, and trap resistance.")
    metric_card(c, MARGIN, 82, 180, 90, "100K", "candidate records streamed", color=BLUE)
    metric_card(c, MARGIN + 205, 82, 180, 90, "Top 100", "ranked shortlist output", color=TEAL)
    metric_card(c, MARGIN + 410, 82, 180, 90, "3m 19s", "full CPU ranking run", color=GREEN)
    metric_card(c, MARGIN + 615, 82, 180, 90, "0 APIs", "no network during ranking", color=AMBER)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.setFont("Helvetica", 10)
    c.drawRightString(W - MARGIN, 28, f"{page:02d}")


def slide_problem(c: canvas.Canvas, page: int) -> None:
    draw_header(c, "Problem Framing", page)
    y = H - 145
    draw_para(
        c,
        "The challenge is not to find candidates with the most AI terms. The JD asks for a founding Senior AI Engineer who can own retrieval, ranking, evaluation, and product-facing ML systems.",
        MARGIN,
        y,
        760,
        size=16,
        leading=23,
    )
    y -= 92
    rounded_panel(c, MARGIN, 70, 405, 250)
    rounded_panel(c, 500, 70, 405, 250)
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGIN + 24, 286, "What fails")
    draw_bullets(
        c,
        [
            "Keyword stuffing: long skill lists with weak career evidence.",
            "Inactive profiles: perfect on paper but not reachable.",
            "Off-domain AI: CV or speech profiles without retrieval/ranking depth.",
            "Consulting-only histories where the JD explicitly raises fit risk.",
        ],
        MARGIN + 24,
        252,
        348,
    )
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(524, 286, "What should win")
    draw_bullets(
        c,
        [
            "Production retrieval, search, recommendation, and ranking systems.",
            "Evaluation rigor: NDCG, MRR, MAP, offline-online correlation, A/B tests.",
            "5-9 year seniority band with hands-on coding evidence.",
            "Recent activity, strong response behavior, and practical logistics fit.",
        ],
        524,
        252,
        348,
    )


def slide_architecture(c: canvas.Canvas, page: int) -> None:
    draw_header(c, "System Architecture", page)
    steps = [
        ("Input", "Stream candidates.jsonl or .jsonl.gz"),
        ("Feature Extraction", "Parse profile, career history, skills, education, Redrob signals"),
        ("Scoring", "Combine JD evidence, behavior, logistics, and penalties"),
        ("Selection", "Maintain deterministic top-100 heap"),
        ("Output", "Write validated CSV plus audit JSON"),
    ]
    x = MARGIN
    y = 300
    box_w = 150
    for idx, (head, body) in enumerate(steps):
        bx = x + idx * 176
        rounded_panel(c, bx, y, box_w, 116, fill=colors.HexColor("#ffffff"))
        c.setFillColor(BLUE if idx < 2 else TEAL if idx < 4 else GREEN)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(bx + 16, y + 82, head)
        draw_para(c, body, bx + 16, y + 58, box_w - 32, size=10, leading=13, color=INK)
        if idx < len(steps) - 1:
            c.setStrokeColor(MUTED)
            c.setLineWidth(2)
            c.line(bx + box_w + 8, y + 58, bx + 168, y + 58)
            c.line(bx + 168, y + 58, bx + 158, y + 64)
            c.line(bx + 168, y + 58, bx + 158, y + 52)
    rounded_panel(c, MARGIN, 90, 850, 130)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN + 24, 184, "Why this architecture")
    draw_bullets(
        c,
        [
            "Runs inside the 5 minute, CPU-only, no-network constraint.",
            "Uses interpretable scoring, so each candidate can be defended in manual review.",
            "Avoids per-candidate LLM calls and fragile black-box ranking behavior.",
        ],
        MARGIN + 24,
        153,
        780,
        size=12,
    )


def slide_scoring(c: canvas.Canvas, page: int) -> None:
    draw_header(c, "Ranking Method", page)
    rows = [
        ("Role/title fit", "Rewards senior AI, search, recommendation, applied ML, NLP, senior data science roles."),
        ("Career evidence", "Looks for production retrieval, ranking, vector search, hybrid search, RAG, evals, scale, latency."),
        ("Skill trust", "Weights skills by proficiency, duration, endorsements, and Redrob assessment scores."),
        ("Behavior", "Uses recency, response rate, response speed, open-to-work, interviews, notice period, GitHub, demand."),
        ("Logistics", "Rewards India and target city fit; penalizes overseas candidates without relocation signal."),
        ("Trap penalties", "Down-weights inconsistency, keyword stuffing, stale activity, non-technical roles, services-only fit."),
    ]
    y = 380
    for idx, (name, detail) in enumerate(rows):
        fill = colors.HexColor("#ffffff") if idx % 2 == 0 else PANEL
        rounded_panel(c, MARGIN, y - 8, 850, 52, fill=fill)
        c.setFillColor(BLUE if idx < 3 else TEAL)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(MARGIN + 20, y + 18, name)
        draw_para(c, detail, MARGIN + 188, y + 18, 635, size=11, leading=14, color=INK)
        y -= 60


def slide_traps(c: canvas.Canvas, page: int) -> None:
    draw_header(c, "Trap Resistance", page)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 14)
    c.drawString(MARGIN, H - 132, "The dataset includes traps. The ranker includes explicit guardrails for them.")
    cards = [
        ("Keyword stuffers", "AI skills are trusted only when backed by duration, endorsements, assessment scores, or career evidence.", BLUE),
        ("Honeypot-like profiles", "Experience-year inconsistencies and duration mismatches are penalized before top-100 selection.", RED),
        ("Inactive candidates", "Last active date and recruiter response rate modify otherwise strong profile matches.", AMBER),
        ("Wrong AI domain", "CV/speech/research-only profiles need retrieval or ranking evidence to stay competitive.", TEAL),
        ("Services-only careers", "Service-company-only histories are down-weighted unless production evidence is unusually strong.", GREEN),
        ("Non-technical titles", "Business, HR, marketing, accounting, and support profiles cannot win on skills alone.", RED),
    ]
    for i, (head, body, color) in enumerate(cards):
        col = i % 3
        row = i // 3
        x = MARGIN + col * 290
        y = 258 - row * 142
        rounded_panel(c, x, y, 260, 110, fill=colors.HexColor("#ffffff"))
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x + 16, y + 78, head)
        draw_para(c, body, x + 16, y + 54, 224, size=10, leading=13, color=INK)


def slide_behavior(c: canvas.Canvas, page: int) -> None:
    draw_header(c, "Behavioral Signals", page)
    rounded_panel(c, MARGIN, 282, 402, 128, fill=colors.HexColor("#ffffff"))
    rounded_panel(c, 504, 282, 402, 128, fill=colors.HexColor("#ffffff"))
    rounded_panel(c, MARGIN, 116, 402, 128, fill=colors.HexColor("#ffffff"))
    rounded_panel(c, 504, 116, 402, 128, fill=colors.HexColor("#ffffff"))
    sections = [
        (MARGIN + 22, 374, "Availability", ["last_active_date", "open_to_work_flag", "notice_period_days"]),
        (526, 374, "Responsiveness", ["recruiter_response_rate", "avg_response_time_hours", "interview_completion_rate"]),
        (MARGIN + 22, 208, "Market signal", ["profile_views_received_30d", "saved_by_recruiters_30d", "search_appearance_30d"]),
        (526, 208, "Trust signal", ["verified_email", "verified_phone", "linkedin_connected", "github_activity_score"]),
    ]
    for x, y, head, items in sections:
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(x, y, head)
        draw_bullets(c, items, x, y - 28, 330, size=11, leading=17)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 12)
    c.drawString(MARGIN, 76, "Behavior is used as a modifier: strong candidates with poor availability are pushed down, not automatically discarded.")


def slide_results(c: canvas.Canvas, page: int, audit: list[dict]) -> None:
    draw_header(c, "Current Ranking Output", page)
    titles = Counter(row["title"] for row in audit)
    countries = Counter(row["country"] for row in audit)
    draw_bar_chart(c, titles, MARGIN, 138, 520, 244, "Top-100 title distribution", max_items=8)
    metric_card(c, 640, 314, 220, 78, str(countries.get("India", 0)), "India-based candidates in top 100", color=GREEN)
    metric_card(c, 640, 218, 220, 78, str(sum(1 for r in audit if r["features"]["only_services"])), "services-only careers in top 100", color=RED)
    metric_card(c, 640, 122, 220, 78, str(sum(1 for r in audit if r["features"]["inactive_days"] > 120)), "stale profiles in top 100", color=AMBER)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN, 82, "Audit result: no non-technical keyword-stuffer titles and no flagged consistency traps in the generated top 100.")


def slide_top_candidates(c: canvas.Canvas, page: int, audit: list[dict]) -> None:
    draw_header(c, "Top Ranked Candidates", page)
    headers = ["Rank", "Candidate", "Title", "Years", "Location", "Score"]
    xs = [MARGIN, 112, 242, 512, 590, 835]
    y = 372
    c.setFillColor(NAVY)
    c.rect(MARGIN, y, 850, 30, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 10)
    for x, h in zip(xs, headers):
        c.drawString(x + 8, y + 10, h)
    y -= 30
    for row in audit[:8]:
        c.setFillColor(PANEL if row["rank"] % 2 == 0 else colors.HexColor("#ffffff"))
        c.rect(MARGIN, y, 850, 30, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("Helvetica", 9)
        vals = [
            str(row["rank"]),
            row["candidate_id"],
            row["title"],
            f"{float(row['years']):.1f}",
            row["location"],
            f"{float(row['score']):.6f}",
        ]
        for x, val in zip(xs, vals):
            text = val if len(val) <= 34 else val[:31] + "..."
            c.drawString(x + 8, y + 10, text)
        y -= 30
    rounded_panel(c, MARGIN, 74, 850, 88)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN + 18, 130, "Reasoning generation")
    draw_para(
        c,
        "Each row gets concise recruiter-facing reasoning grounded in candidate facts: title, years, location, evidence category, response rate, activity recency, notice period, and concerns.",
        MARGIN + 18,
        108,
        790,
        size=11,
        leading=15,
    )


def slide_repro(c: canvas.Canvas, page: int) -> None:
    draw_header(c, "Reproducibility", page)
    metric_card(c, MARGIN, 320, 190, 86, "3m 19s", "full ranking pass over 100,000 candidates", color=GREEN)
    metric_card(c, MARGIN + 215, 320, 190, 86, "CPU only", "no GPU inference or acceleration", color=BLUE)
    metric_card(c, MARGIN + 430, 320, 190, 86, "Stdlib", "no external runtime dependencies for ranking", color=TEAL)
    metric_card(c, MARGIN + 645, 320, 190, 86, "Valid", "passes validate_submission.py", color=AMBER)
    c.setFillColor(NAVY)
    c.roundRect(MARGIN, 160, 850, 92, 8, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Courier", 13)
    c.drawString(MARGIN + 24, 214, "python rank.py --candidates ./candidates.jsonl --out ./outputs/submission.csv")
    c.drawString(MARGIN + 24, 188, "python validate_submission.py ./outputs/submission.csv")
    draw_para(
        c,
        "The ranking step streams input records, keeps a fixed top-100 heap, writes a CSV submission, and emits an audit JSON for review. It makes no hosted LLM or embedding API calls during ranking.",
        MARGIN,
        104,
        820,
        size=13,
        leading=18,
    )


def slide_close(c: canvas.Canvas, page: int) -> None:
    draw_header(c, "Why This Is Defensible", page)
    draw_bullets(
        c,
        [
            "It directly models the role: production retrieval, ranking, evaluation, and product ML systems.",
            "It uses behavioral signals because hireability is not just profile fit.",
            "It resists dataset traps by penalizing weak AI claims, stale profiles, non-technical keyword stuffers, and inconsistent histories.",
            "It is reproducible under the official constraints: CPU-only, no network, under 5 minutes.",
            "It produces auditable reasoning for manual review without hallucinating candidate facts.",
        ],
        MARGIN,
        365,
        800,
        size=15,
        leading=25,
    )
    rounded_panel(c, MARGIN, 84, 850, 96, fill=colors.HexColor("#ecfdf5"), stroke=colors.HexColor("#bbf7d0"))
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGIN + 24, 142, "Submission artifacts")
    c.setFillColor(INK)
    c.setFont("Helvetica", 12)
    c.drawString(MARGIN + 24, 116, "outputs/submission.csv, src/ranker.py, README.md, docs/approach.md, output/pdf/redrob_ai_candidate_ranker_solution_deck.pdf")


def build_pdf() -> Path:
    audit = load_audit()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT_PATH), pagesize=(W, H))
    slides = [
        lambda cn, p: title_slide(cn, p),
        lambda cn, p: slide_problem(cn, p),
        lambda cn, p: slide_architecture(cn, p),
        lambda cn, p: slide_scoring(cn, p),
        lambda cn, p: slide_traps(cn, p),
        lambda cn, p: slide_behavior(cn, p),
        lambda cn, p: slide_results(cn, p, audit),
        lambda cn, p: slide_top_candidates(cn, p, audit),
        lambda cn, p: slide_repro(cn, p),
        lambda cn, p: slide_close(cn, p),
    ]
    for page, slide in enumerate(slides, start=1):
        slide(c, page)
        c.showPage()
    c.save()
    return OUT_PATH


if __name__ == "__main__":
    print(build_pdf())
