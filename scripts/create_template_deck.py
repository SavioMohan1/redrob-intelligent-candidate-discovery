#!/usr/bin/env python3
"""Fill the Redrob idea-submission PPTX template and emit a matching PDF.

This script preserves the original PPTX package, slide backgrounds, layouts, and
media assets. It replaces the template prompt text with the actual solution
content and creates a PDF using the same template backgrounds.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "Idea Submission Template _ Redrob.pptx"
AUDIT = ROOT / "outputs" / "audit_top100.json"
OUT_PPTX = ROOT / "output" / "pptx" / "redrob_intelligent_candidate_discovery_template_filled.pptx"
OUT_PDF = ROOT / "output" / "pdf" / "redrob_intelligent_candidate_discovery_template_filled.pdf"
MEDIA_DIR = ROOT / "templates" / "extracted_media"

SLIDE_W_EMU = 12192000
SLIDE_H_EMU = 6858000
PDF_W = 960
PDF_H = 540

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

NS = {"p": P_NS, "a": A_NS, "r": R_NS}
ET.register_namespace("p", P_NS)
ET.register_namespace("a", A_NS)
ET.register_namespace("r", R_NS)

TITLE_COLOR = "FFFFFF"
BODY_COLOR = "111827"
ACCENT = colors.HexColor("#0f2edc")


def qn(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def audit_stats() -> dict:
    rows = json.loads(AUDIT.read_text(encoding="utf-8"))
    return {
        "rows": rows,
        "title_counts": Counter(row["title"] for row in rows),
        "india_count": sum(1 for row in rows if row["country"] == "India"),
        "stale_count": sum(1 for row in rows if row["features"]["inactive_days"] > 120),
        "services_only": sum(1 for row in rows if row["features"]["only_services"]),
        "low_response": sum(1 for row in rows if row["features"]["response"] < 0.2),
    }


def slide_content() -> dict[int, dict[str, object]]:
    stats = audit_stats()
    rows = stats["rows"]
    top_titles = ", ".join(f"{k} ({v})" for k, v in stats["title_counts"].most_common(4))
    top3 = "\n".join(
        f"- #{r['rank']} {r['candidate_id']}: {r['title']}, {float(r['years']):.1f} yrs, {r['location']}, score {float(r['score']):.4f}"
        for r in rows[:3]
    )
    return {
        1: {
            "cover": [
                "Team Name : SavioMohan1",
                "Problem Statement : Intelligent Candidate Discovery and Ranking",
                "Team Leader Name : Savio Mohan",
            ]
        },
        2: {
            "title": "Solution Overview",
            "body": [
                "Proposed solution: an offline, explainable ranker that reads the Senior AI Engineer JD and scores all 100,000 candidates into a trusted top-100 shortlist.",
                "The system focuses on recruiter-grade evidence: production retrieval, search, ranking, embeddings, evaluation maturity, product ML experience, availability, and logistics.",
                "Differentiator: it does not rank by raw AI keyword count. Skills are trusted only when backed by career history, duration, endorsements, assessments, and behavioral signals.",
                "Output: a validator-compliant CSV with candidate_id, rank, score, and fact-grounded reasoning for every selected candidate.",
            ],
        },
        3: {
            "title": "JD Understanding & Candidate Evaluation",
            "body": [
                "Key JD requirements: 5-9 years of hands-on production ML engineering, strong Python, retrieval/ranking ownership, vector or hybrid search, ranking evaluation, and product-shipping mindset.",
                "High-value candidate evidence: shipped search/recommendation/ranking systems, embedding pipelines, FAISS/Milvus/Qdrant/Pinecone/Weaviate/OpenSearch, NDCG/MRR/MAP, A/B tests, scale and latency work.",
                "Behavioral relevance: recent activity, recruiter response rate, response speed, open-to-work status, interview completion, notice period, GitHub signal, recruiter saves/views.",
                "Fit beyond keywords: the ranker reads role history and descriptions, distinguishes product ML builders from keyword stuffers, and down-weights stale or suspicious profiles.",
            ],
        },
        4: {
            "title": "Ranking Methodology",
            "body": [
                "Retrieval/scoring pass: stream candidates.jsonl, extract text and structured features, compute a weighted score, and keep a deterministic top-100 heap.",
                "Algorithms used: interpretable feature engineering, regex-backed career evidence extraction, weighted scoring, behavioral modifier, logistics adjustment, and trap penalties.",
                "Signal fusion: title fit, experience-band fit, retrieval/ranking evidence, evaluation evidence, production evidence, trusted skills, product-company signal, behavior, and location are combined.",
                "Final score: adjusted evidence score is passed through a monotonic 0-1 calibration, then sorted by score descending and candidate_id ascending for deterministic ties.",
            ],
        },
        5: {
            "title": "Explainability & Data Validation",
            "body": [
                "Reasoning is generated from facts already present in the candidate record: title, years, location, relevant evidence category, response rate, recency, notice period, and concerns.",
                "Hallucination prevention: the generator never invents employers, degrees, skills, or projects. It describes evidence categories only after the scorer found those signals.",
                "Low-quality profile handling: weak expert claims, low skill duration, zero endorsements, stale activity, poor response behavior, and long notice period reduce score.",
                "Suspicious profile handling: severe experience-year mismatches, career duration inconsistencies, non-technical keyword stuffing, off-domain AI, and services-only careers are penalized.",
            ],
        },
        6: {
            "title": "End-to-End Workflow",
            "body": [
                "1. Input: load candidates.jsonl or candidates.jsonl.gz and the fixed Senior AI Engineer JD interpretation encoded in the scorer.",
                "2. Feature extraction: parse profile, career history, skills, education, certifications, languages, and Redrob behavioral signals.",
                "3. Score: combine JD evidence, trusted skills, behavioral availability, logistics, and validation penalties.",
                "4. Select: maintain top 100 in memory, sort deterministically, and generate concise recruiter-facing reasoning.",
                "5. Output: write outputs/submission.csv and outputs/audit_top100.json, then validate with validate_submission.py.",
            ],
        },
        7: {
            "title": "System Architecture",
            "body": [
                "CLI entry point: rank.py",
                "Core engine: src/ranker.py",
                "Input layer: streaming JSONL reader with gzip support.",
                "Feature layer: title, text-pattern, skill-trust, product-company, behavior, logistics, and consistency features.",
                "Scoring layer: weighted ranker with engagement gate and trap penalties.",
                "Output layer: top-100 CSV, audit JSON, and fact-grounded reasoning.",
                "Complexity: O(N log 100) over 100,000 candidates, with only the top heap and current record in memory.",
            ],
        },
        8: {
            "title": "Results & Performance",
            "body": [
                "Full dataset run completed locally in about 3 minutes 19 seconds on CPU, below the 5-minute challenge limit.",
                "The generated submission passed the official validator: exactly 100 rows, valid candidate IDs, unique ranks, non-increasing scores, and UTF-8 CSV format.",
                f"Top-100 quality audit: {stats['india_count']}/100 India-based candidates, {stats['services_only']} services-only careers, {stats['stale_count']} stale profiles, and no non-technical keyword-stuffer titles.",
                f"Top title mix: {top_titles}.",
                "Top examples:\n" + top3,
            ],
        },
        9: {
            "title": "Technologies Used",
            "body": [
                "Python 3.11: selected for portable, reproducible ranking under the CPU/no-network constraint.",
                "Standard library only for ranking: json, csv, gzip, re, heapq, argparse, datetime, math, dataclasses, pathlib.",
                "ReportLab: used only for generating the explanatory PDF deck; it is not required by the ranking pipeline.",
                "No hosted LLM APIs, no GPU, no vector database, no pandas, no scikit-learn, no sentence-transformers, and no network calls during ranking.",
                "This stack was selected because the evaluation rewards reproducibility, latency discipline, explainability, and defensible engineering tradeoffs.",
            ],
        },
        10: {
            "title": "Submission Assets",
            "body": [
                "GitHub repo: https://github.com/SavioMohan1/redrob-intelligent-candidate-discovery",
                "Ranked output file: outputs/submission.csv",
                "PDF deck: output/pdf/redrob_intelligent_candidate_discovery_template_filled.pdf",
                "Reproduce command: python rank.py --candidates ./candidates.jsonl --out ./outputs/submission.csv",
                "Validation command: python validate_submission.py ./outputs/submission.csv",
                "Main implementation files: rank.py, src/ranker.py, README.md, docs/approach.md.",
                "Sandbox/demo link: to be added in submission_metadata.yaml after deployment.",
            ],
        },
        11: {
            "title": "Thank You",
            "body": [
                "The solution is designed to rank candidates the way a strong recruiter would: evidence first, behavior-aware, explainable, and reproducible under real-world constraints.",
            ],
        },
    }


def make_para(text: str, size: int, color: str, bold: bool = False, bullet: bool = False) -> ET.Element:
    p = ET.Element(qn(A_NS, "p"))
    ppr = ET.SubElement(p, qn(A_NS, "pPr"))
    if bullet:
        ppr.set("marL", "285750")
        ppr.set("indent", "-171450")
        ET.SubElement(ppr, qn(A_NS, "buChar"), {"char": "-"})
    r = ET.SubElement(p, qn(A_NS, "r"))
    rpr = ET.SubElement(r, qn(A_NS, "rPr"), {"lang": "en-US", "sz": str(size * 100)})
    if bold:
        rpr.set("b", "1")
    solid = ET.SubElement(rpr, qn(A_NS, "solidFill"))
    ET.SubElement(solid, qn(A_NS, "srgbClr"), {"val": color})
    t = ET.SubElement(r, qn(A_NS, "t"))
    t.text = text
    return p


def replace_text_body(shape: ET.Element, lines: list[str], size: int, color: str, bold_first: bool = False) -> None:
    tx_body = shape.find("p:txBody", NS)
    if tx_body is None:
        tx_body = ET.SubElement(shape, qn(P_NS, "txBody"))
        ET.SubElement(tx_body, qn(A_NS, "bodyPr"))
        ET.SubElement(tx_body, qn(A_NS, "lstStyle"))
    body_pr = tx_body.find("a:bodyPr", NS)
    lst = tx_body.find("a:lstStyle", NS)
    for child in list(tx_body):
        if child.tag == qn(A_NS, "p"):
            tx_body.remove(child)
    if body_pr is not None:
        body_pr.set("wrap", "square")
    for idx, line in enumerate(lines):
        if "\n" in line:
            first, *rest = line.split("\n")
            tx_body.append(make_para(first, size, color, bold=(bold_first and idx == 0)))
            for item in rest:
                cleaned = item[2:] if item.startswith("- ") else item
                tx_body.append(make_para(cleaned, max(size - 1, 12), color, bullet=True))
        else:
            tx_body.append(make_para(line, size, color, bold=(bold_first and idx == 0)))


def shape_text(shape: ET.Element) -> str:
    return "".join(t.text or "" for t in shape.findall(".//a:t", NS)).strip()


def clone_content_shape(root: ET.Element) -> ET.Element:
    for sp in root.findall(".//p:sp", NS):
        txt = shape_text(sp)
        if txt and not txt.startswith(("Submission Assets", "System Architecture")):
            return copy.deepcopy(sp)
    raise RuntimeError("No shape to clone")


def new_text_shape(shape_id: int, name: str, x: str, y: str, cx: str, cy: str) -> ET.Element:
    xml = f"""
    <p:sp xmlns:p="{P_NS}" xmlns:a="{A_NS}">
      <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="{name}"/>
        <p:cNvSpPr txBox="1"/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm>
          <a:off x="{x}" y="{y}"/>
          <a:ext cx="{cx}" cy="{cy}"/>
        </a:xfrm>
        <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        <a:noFill/>
        <a:ln><a:noFill/></a:ln>
      </p:spPr>
      <p:txBody>
        <a:bodyPr wrap="square"/>
        <a:lstStyle/>
        <a:p/>
      </p:txBody>
    </p:sp>
    """
    return ET.fromstring(xml)


def update_slide_xml(slide_num: int, xml_bytes: bytes, content: dict[str, object]) -> bytes:
    root = ET.fromstring(xml_bytes)
    sp_tree = root.find(".//p:spTree", NS)
    shapes = [sp for sp in root.findall(".//p:sp", NS) if shape_text(sp)]

    if slide_num == 1:
        slide_data = content[slide_num]
        cover_lines = slide_data["cover"]
        for shape, line in zip(shapes, cover_lines):
            replace_text_body(shape, [line], 18, TITLE_COLOR)
    elif slide_num in content:
        slide_data = content[slide_num]
        title = str(slide_data["title"])
        body = list(slide_data["body"])
        if shapes:
            replace_text_body(shapes[0], [title], 25, TITLE_COLOR, bold_first=True)
        else:
            new_shape = new_text_shape(9001, "Generated Title", "480500", "812600", "8121600", "465900")
            sp_tree.append(new_shape)
            replace_text_body(new_shape, [title], 25, TITLE_COLOR, bold_first=True)
            shapes = [new_shape]
        if len(shapes) >= 2:
            body_shape = shapes[1]
        else:
            # Add a content text box for slides that only had a title or were blank.
            body_shape = copy.deepcopy(shapes[0]) if shapes else new_text_shape(9002, "Generated Body", "480500", "1278496", "7968600", "3198900")
            xfrm = body_shape.find(".//a:xfrm", NS)
            if xfrm is not None:
                off = xfrm.find("a:off", NS)
                ext = xfrm.find("a:ext", NS)
                if off is not None:
                    off.set("x", "480500")
                    off.set("y", "1278496")
                if ext is not None:
                    ext.set("cx", "7968600")
                    ext.set("cy", "3198900")
            sp_tree.append(body_shape)
        replace_text_body(body_shape, body, 15, BODY_COLOR)

    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def build_pptx() -> Path:
    content = slide_content()
    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TEMPLATE, "r") as zin, zipfile.ZipFile(OUT_PPTX, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            match = re.match(r"ppt/slides/slide(\d+)\.xml$", item.filename)
            if match:
                slide_num = int(match.group(1))
                data = update_slide_xml(slide_num, data, content)
            zout.writestr(item, data)
    return OUT_PPTX


def wrap_pdf(text: str, max_width: float, size: int, font: str = "Helvetica") -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = word if not line else f"{line} {word}"
        if pdfmetrics.stringWidth(candidate, font, size) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def emu_box(x: int, y: int, cx: int, cy: int) -> tuple[float, float, float, float]:
    sx = PDF_W / SLIDE_W_EMU
    sy = PDF_H / SLIDE_H_EMU
    px = x * sx
    py = PDF_H - (y + cy) * sy
    return px, py, cx * sx, cy * sy


def draw_lines(c: canvas.Canvas, lines: list[str], box: tuple[float, float, float, float], size: int, color, bullet=False) -> None:
    x, y, w, h = box
    current = y + h - size
    c.setFillColor(color)
    c.setFont("Helvetica", size)
    for raw in lines:
        parts = raw.split("\n")
        for pi, part in enumerate(parts):
            is_bullet = bullet or part.startswith("- ")
            text = part[2:] if part.startswith("- ") else part
            for wrapped in wrap_pdf(text, w - (22 if is_bullet else 0), size):
                if current < y + 4:
                    return
                if is_bullet:
                    c.drawString(x + 6, current, "-")
                    c.drawString(x + 22, current, wrapped)
                else:
                    c.drawString(x, current, wrapped)
                current -= size + 5
        current -= 4


def ensure_template_media() -> None:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TEMPLATE, "r") as z:
        for name in [n for n in z.namelist() if n.startswith("ppt/media/image") and n.endswith(".png")]:
            target = MEDIA_DIR / Path(name).name
            if not target.exists():
                target.write_bytes(z.read(name))


def build_pdf() -> Path:
    ensure_template_media()
    content = slide_content()
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT_PDF), pagesize=(PDF_W, PDF_H))
    bg_map = {1: "image2.png", 11: "image3.png"}
    for i in range(1, 12):
        bg = MEDIA_DIR / bg_map.get(i, "image1.png")
        c.drawImage(ImageReader(str(bg)), 0, 0, PDF_W, PDF_H)
        if i == 1:
            lines = content[1]["cover"]
            y_positions = [3065023, 3472483, 3916185]
            for line, y_emu in zip(lines, y_positions):
                box = emu_box(311700, y_emu, 8520600, 443700)
                draw_lines(c, [line], box, 20, colors.white)
        else:
            item = content[i]
            title_box = emu_box(480500, 812600, 8121600, 465900)
            draw_lines(c, [str(item["title"])], title_box, 27, colors.white)
            body_box = emu_box(480500 if i == 10 else 375600, 1278496, 7968600 if i == 10 else 8520600, 3198900)
            draw_lines(c, list(item["body"]), body_box, 15, colors.HexColor("#111827"))
        c.showPage()
    c.save()
    return OUT_PDF


def main() -> None:
    print(build_pptx())
    print(build_pdf())


if __name__ == "__main__":
    main()
