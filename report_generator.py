"""
report_generator.py

Generates an automated PDF security report for a scanned model, containing:
  - The model's cryptographic hash (for integrity / provenance tracking)
  - The list of inputs that were tested during the scan
  - A computed safety score and the anomaly findings behind it

Intended to be called at the end of your scan pipeline, e.g.:

    from report_generator import ScanResult, generate_report

    result = ScanResult(
        model_path="models/candidate_model.pt",
        tested_inputs=["Pineapple", "hello world", "the quick brown fox", ...],
        anomalies=[
            {"neuron": "layer4.attn.212", "trigger_input": "Pineapple",
             "z_score": 8.4, "description": "Activation spikes 8.4 std devs above baseline"},
        ],
        safety_score=42,
    )
    generate_report(result, "reports/candidate_model_report.pdf")

Depends on: reportlab (pip install reportlab)
"""

from __future__ import annotations

import hashlib
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

@dataclass
class ScanResult:
    model_path: str
    tested_inputs: list[str]
    anomalies: list[dict] = field(default_factory=list)
    safety_score: int = 100          # 0-100, lower = more suspicious
    scanner_version: str = "1.0.0"
    notes: str = ""


# --------------------------------------------------------------------------
# Hashing
# --------------------------------------------------------------------------

def compute_model_hash(model_path: str, algo: str = "sha256", chunk_size: int = 1 << 20) -> str:
    """Stream the model file through a hash function so we never load huge
    checkpoints fully into memory. Returns a hex digest string."""
    h = hashlib.new(algo)
    with open(model_path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Safety score -> verdict
# --------------------------------------------------------------------------

def _verdict(score: int) -> tuple[str, colors.Color]:
    if score >= 85:
        return "PASS — No significant anomalies detected", colors.HexColor("#1a7f37")
    if score >= 60:
        return "CAUTION — Minor anomalies detected, manual review recommended", colors.HexColor("#9a6700")
    return "FAIL — High-confidence anomalies detected", colors.HexColor("#cf222e")


# --------------------------------------------------------------------------
# Report generation
# --------------------------------------------------------------------------

def generate_report(result: ScanResult, output_path: str, hash_algo: str = "sha256") -> str:
    """Build the PDF report and write it to output_path. Returns output_path."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    model_hash = compute_model_hash(result.model_path, algo=hash_algo)
    verdict_text, verdict_color = _verdict(result.safety_score)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="MonoSmall", fontName="Courier", fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="Score", fontSize=36, leading=40, alignment=1))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    story = []

    # --- Header ---
    story.append(Paragraph("AI Model Security Scan Report", styles["Title"]))
    story.append(Paragraph(
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"&middot; Scanner v{result.scanner_version} &middot; Host {platform.node()}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 16))

    # --- Verdict / score ---
    score_style = ParagraphStyle(name="ScoreColored", parent=styles["Score"], textColor=verdict_color)
    story.append(Paragraph(f"{result.safety_score}/100", score_style))
    verdict_style = ParagraphStyle(name="VerdictColored", parent=styles["Normal"],
                                    alignment=1, textColor=verdict_color, fontSize=12, spaceAfter=16)
    story.append(Paragraph(verdict_text, verdict_style))

    # --- Model identity ---
    story.append(Paragraph("Model Identity", styles["Heading2"]))
    identity_table = Table(
        [
            ["Model path", str(result.model_path)],
            [f"{hash_algo.upper()} hash", model_hash],
        ],
        colWidths=[1.3 * inch, 5.2 * inch],
    )
    identity_table.setStyle(TableStyle([
        ("FONTNAME", (1, 1), (1, 1), "Courier"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d7de")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f6f8fa")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(identity_table)
    story.append(Spacer(1, 16))

    # --- Anomaly findings ---
    story.append(Paragraph("Anomaly Findings", styles["Heading2"]))
    if result.anomalies:
        rows = [["Neuron / Layer", "Trigger Input", "Z-score", "Description"]]
        for a in result.anomalies:
            rows.append([
                str(a.get("neuron", "")),
                str(a.get("trigger_input", "")),
                f'{a.get("z_score", ""):.2f}' if isinstance(a.get("z_score"), (int, float)) else str(a.get("z_score", "")),
                str(a.get("description", "")),
            ])
        anomaly_table = Table(rows, colWidths=[1.3 * inch, 1.2 * inch, 0.7 * inch, 3.3 * inch], repeatRows=1)
        anomaly_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f6f8fa")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d7de")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(anomaly_table)
    else:
        story.append(Paragraph("No anomalies were flagged during this scan.", styles["Normal"]))
    story.append(Spacer(1, 16))

    # --- Tested inputs ---
    story.append(Paragraph(f"Tested Inputs ({len(result.tested_inputs)})", styles["Heading2"]))
    inputs_text = ", ".join(result.tested_inputs) if result.tested_inputs else "None recorded."
    story.append(Paragraph(inputs_text, styles["MonoSmall"]))

    if result.notes:
        story.append(Spacer(1, 16))
        story.append(Paragraph("Notes", styles["Heading2"]))
        story.append(Paragraph(result.notes, styles["Normal"]))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    # Minimal smoke test using this very file as the "model" so the script
    # runs standalone without a real checkpoint on hand.
    demo = ScanResult(
        model_path=__file__,
        tested_inputs=["Pineapple", "hello world", "the quick brown fox"],
        anomalies=[{
            "neuron": "layer4.attn.212",
            "trigger_input": "Pineapple",
            "z_score": 8.4,
            "description": "Activation spikes far above baseline only on this token",
        }],
        safety_score=42,
        notes="Demo report generated by running report_generator.py directly.",
    )
    path = generate_report(demo, "demo_report.pdf")
    print(f"Wrote {path}")