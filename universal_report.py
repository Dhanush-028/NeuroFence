"""
NeuroFence - Universal Scanner
Report generator for scan_model()'s output - same visual style as
report_generator.py from Week 4, adapted for the different result shape
(peer-based verdict instead of baseline-comparison verdict).
"""

import json
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

OUTPUT_PDF = "NeuroFence_Universal_Scan_Report.pdf"


def build_universal_report(result, out_path=OUTPUT_PDF):
    flagged = result["flagged_count"] > 0

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], textColor=colors.HexColor("#1B2430"))
    heading_style = ParagraphStyle("HeadingStyle", parent=styles["Heading2"], textColor=colors.HexColor("#028090"), spaceBefore=14)
    body_style = ParagraphStyle("BodyStyle", parent=styles["Normal"], fontSize=10.5, leading=15)

    doc = SimpleDocTemplate(out_path, pagesize=letter, topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    story = []

    story.append(Paragraph("NeuroFence Universal Scan Report", title_style))
    story.append(Paragraph(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    story.append(Spacer(1, 16))

    verdict_color = colors.HexColor("#C0392B") if flagged else colors.HexColor("#028090")
    verdict_style = ParagraphStyle("Verdict", parent=styles["Heading1"], textColor=verdict_color)
    story.append(Paragraph(f"Verdict: {result['verdict']}", verdict_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Model Under Test", heading_style))
    meta = result["metadata"]
    model_hash = result.get("model_hash") or "N/A (Hub model - weights not hashed locally)"
    model_table_data = [
        ["Model", result["model_name"]],
        ["Weights hash (SHA-256)", (model_hash[:40] + "...") if len(model_hash) > 40 else model_hash],
        ["Architecture", str(meta.get("model_type", "unknown"))],
        ["Layers", str(meta.get("num_layers", "unknown"))],
        ["Parameters", f"{meta.get('num_params', 0):,}"],
        ["Prompts tested", str(result["prompts_tested"])],
        ["Detection method", "Peer-comparison (no external baseline required)"],
        ["Z-score threshold", str(result["z_threshold"])],
    ]
    t = Table(model_table_data, colWidths=[2.2 * inch, 4.3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F7FA")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Top Outlier Findings", heading_style))
    findings_data = [["Layer", "Neuron", "Z-score", "Status"]]
    for f in result["top_findings"][:10]:
        status = "FLAGGED" if f["z_score"] >= result["z_threshold"] else "normal"
        findings_data.append([f["layer"], str(f["neuron"]), f"{f['z_score']:.1f}", status])
    t2 = Table(findings_data, colWidths=[2.6 * inch, 1.2 * inch, 1.2 * inch, 1.5 * inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2430")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 16))

    story.append(Paragraph("How This Scan Works", heading_style))
    story.append(Paragraph(
        "This method compares each neuron only to its OWN typical behavior across the prompts in this "
        "scan - never to other neurons. For every neuron, it checks whether at least one prompt caused "
        "a dramatically higher activation than that neuron's own usual (median) response, relative to "
        "its own usual spread. This targets the real signature of a backdoor: normal for almost every "
        "prompt, then a sharp spike for the few containing a trigger. No pre-existing trusted baseline "
        "is required.",
        body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Known Limitations", heading_style))
    limitations = [
        "This method catches a rare, sharp activation spike well, but a backdoor engineered to shift a "
        "neuron's activation gradually and consistently (rather than spiking on specific trigger "
        "prompts) may not stand out from that neuron's own typical spread.",
        "Currently supports GPT-2-family architectures only (gpt2, distilgpt2, and similar). Other "
        "architecture families are not yet covered.",
        "This is a single scan with one fuzz batch. Always sanity-check the SPIKE_THRESHOLD by first "
        "scanning a model already known to be clean and confirming the flagged count is at or near zero "
        "before trusting a scan of an unfamiliar model.",
    ]
    for lim in limitations:
        story.append(Paragraph(f"&bull; {lim}", body_style))
        story.append(Spacer(1, 6))

    doc.build(story)
    print(f"[NeuroFence] Universal scan report saved to {out_path}")


if __name__ == "__main__":
    with open("universal_scan_report.json") as f:
        result = json.load(f)
    build_universal_report(result)
