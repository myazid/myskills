"""
generate_pdf.py — Convert ops-agent code review markdown report to PDF.
Usage: python generate_pdf.py --input report.md --output report.pdf
"""

import argparse
import re
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus import PageBreak

# ── Colour palette ──────────────────────────────────────────────────────────
C_PURPLE      = colors.HexColor("#534AB7")
C_PURPLE_LIGHT= colors.HexColor("#EEEDFE")
C_TEAL        = colors.HexColor("#0F6E56")
C_TEAL_LIGHT  = colors.HexColor("#E1F5EE")
C_RED         = colors.HexColor("#A32D2D")
C_RED_LIGHT   = colors.HexColor("#FCEBEB")
C_AMBER       = colors.HexColor("#854F0B")
C_AMBER_LIGHT = colors.HexColor("#FAEEDA")
C_GRAY        = colors.HexColor("#5F5E5A")
C_GRAY_LIGHT  = colors.HexColor("#F1EFE8")
C_BORDER      = colors.HexColor("#D3D1C7")
C_WHITE       = colors.white
C_BLACK       = colors.HexColor("#2C2C2A")

VERDICT_COLORS = {
    "PASS":        (C_TEAL,        C_TEAL_LIGHT),
    "FAIL":        (C_RED,         C_RED_LIGHT),
    "WARN":        (C_AMBER,       C_AMBER_LIGHT),
    "NOT FOUND":   (C_GRAY,        C_GRAY_LIGHT),
    "N/A":         (C_GRAY,        C_GRAY_LIGHT),
    "READY":       (C_TEAL,        C_TEAL_LIGHT),
    "NOT READY":   (C_RED,         C_RED_LIGHT),
    "CONDITIONALLY READY": (C_AMBER, C_AMBER_LIGHT),
}

# ── Styles ───────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title",
            fontSize=22, fontName="Helvetica-Bold",
            textColor=C_BLACK, spaceAfter=4, leading=28),
        "subtitle": ParagraphStyle("subtitle",
            fontSize=11, fontName="Helvetica",
            textColor=C_GRAY, spaceAfter=16),
        "h1": ParagraphStyle("h1",
            fontSize=14, fontName="Helvetica-Bold",
            textColor=C_BLACK, spaceBefore=18, spaceAfter=6, leading=18),
        "h2": ParagraphStyle("h2",
            fontSize=12, fontName="Helvetica-Bold",
            textColor=C_PURPLE, spaceBefore=14, spaceAfter=4, leading=16),
        "body": ParagraphStyle("body",
            fontSize=9, fontName="Helvetica",
            textColor=C_BLACK, spaceAfter=4, leading=13),
        "body_small": ParagraphStyle("body_small",
            fontSize=8, fontName="Helvetica",
            textColor=C_GRAY, spaceAfter=3, leading=11),
        "code": ParagraphStyle("code",
            fontSize=8, fontName="Courier",
            textColor=C_PURPLE, spaceAfter=2, leading=11),
        "verdict_label": ParagraphStyle("verdict_label",
            fontSize=9, fontName="Helvetica-Bold",
            textColor=C_WHITE, leading=12),
        "bullet": ParagraphStyle("bullet",
            fontSize=9, fontName="Helvetica",
            textColor=C_BLACK, spaceAfter=3, leading=13,
            leftIndent=12, bulletIndent=0),
    }

# ── Verdict badge ─────────────────────────────────────────────────────────────
def verdict_badge(text: str, styles: dict) -> Table:
    """Return a small coloured pill with the verdict text."""
    fg, bg = VERDICT_COLORS.get(text.upper(), (C_GRAY, C_GRAY_LIGHT))
    cell = Paragraph(f"<b>{text}</b>",
                     ParagraphStyle("vb", fontSize=8, fontName="Helvetica-Bold",
                                    textColor=fg, leading=10))
    t = Table([[cell]], colWidths=[22*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), bg),
        ("ROUNDEDCORNERS", [3]),
        ("TOPPADDING",  (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING",(0,0), (-1,-1), 6),
        ("BOX", (0,0), (-1,-1), 0.5, fg),
    ]))
    return t

# ── Overall verdict banner ────────────────────────────────────────────────────
def verdict_banner(verdict: str, styles: dict) -> Table:
    fg, bg = VERDICT_COLORS.get(verdict.upper(), (C_GRAY, C_GRAY_LIGHT))
    cell = Paragraph(f"<b>Overall Verdict: {verdict}</b>",
                     ParagraphStyle("vb2", fontSize=13, fontName="Helvetica-Bold",
                                    textColor=fg, leading=16))
    t = Table([[cell]], colWidths=[170*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), bg),
        ("TOPPADDING",  (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING",(0,0), (-1,-1), 14),
        ("BOX", (0,0), (-1,-1), 1, fg),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t

# ── Domain check table ────────────────────────────────────────────────────────
def domain_table(rows: list[dict], styles: dict) -> Table:
    """
    rows: list of {"check": str, "verdict": str, "location": str, "notes": str}
    """
    header = ["Check", "Verdict", "Location", "Notes"]
    col_w  = [52*mm, 22*mm, 38*mm, 52*mm]

    def hcell(t):
        return Paragraph(f"<b>{t}</b>",
            ParagraphStyle("th", fontSize=8, fontName="Helvetica-Bold",
                           textColor=C_WHITE, leading=10))

    def bcell(t, bold=False):
        fn = "Helvetica-Bold" if bold else "Helvetica"
        return Paragraph(str(t),
            ParagraphStyle("td", fontSize=8, fontName=fn,
                           textColor=C_BLACK, leading=11))

    def vcell(v):
        fg, bg = VERDICT_COLORS.get(v.upper(), (C_GRAY, C_GRAY_LIGHT))
        return Paragraph(f"<b>{v}</b>",
            ParagraphStyle("vd", fontSize=8, fontName="Helvetica-Bold",
                           textColor=fg, leading=10))

    data = [[hcell(h) for h in header]]
    row_colors = []

    for i, row in enumerate(rows):
        v = row.get("verdict", "").strip()
        _, bg = VERDICT_COLORS.get(v.upper(), (C_WHITE, C_WHITE))
        row_colors.append(("BACKGROUND", (0, i+1), (-1, i+1),
                           bg if v.upper() == "FAIL" else C_WHITE))
        data.append([
            bcell(row.get("check", "")),
            vcell(v),
            Paragraph(row.get("location", "—"),
                      ParagraphStyle("loc", fontSize=7, fontName="Courier",
                                     textColor=C_PURPLE, leading=10)),
            bcell(row.get("notes", "")),
        ])

    t = Table(data, colWidths=col_w, repeatRows=1)
    style_cmds = [
        ("BACKGROUND",   (0, 0), (-1, 0), C_PURPLE),
        ("GRID",         (0, 0), (-1,-1), 0.4, C_BORDER),
        ("TOPPADDING",   (0, 0), (-1,-1), 4),
        ("BOTTOMPADDING",(0, 0), (-1,-1), 4),
        ("LEFTPADDING",  (0, 0), (-1,-1), 6),
        ("RIGHTPADDING", (0, 0), (-1,-1), 6),
        ("VALIGN",       (0, 0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_WHITE, C_GRAY_LIGHT]),
    ] + row_colors
    t.setStyle(TableStyle(style_cmds))
    return t

# ── Markdown parser ──────────────────────────────────────────────────────────
def parse_markdown(md: str, styles: dict) -> list:
    """Convert the report markdown into a list of ReportLab flowables."""
    story = []
    lines = md.split("\n")
    i = 0

    def flush_table_rows(rows):
        """Parse markdown table rows into domain check dicts."""
        parsed = []
        for row in rows:
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) >= 2 and not all(set(c) <= set("-: ") for c in cells):
                parsed.append({
                    "check":    cells[0] if len(cells) > 0 else "",
                    "verdict":  cells[1] if len(cells) > 1 else "",
                    "location": cells[2] if len(cells) > 2 else "",
                    "notes":    cells[3] if len(cells) > 3 else "",
                })
        return parsed

    table_rows = []
    in_table = False

    while i < len(lines):
        line = lines[i]

        # Detect table start
        if line.strip().startswith("|") and not in_table:
            in_table = True
            table_rows = [line]
            i += 1
            continue

        # Continue table
        if in_table:
            if line.strip().startswith("|"):
                table_rows.append(line)
                i += 1
                continue
            else:
                # Flush table
                parsed = flush_table_rows(table_rows[2:])  # skip header + separator
                if parsed:
                    story.append(Spacer(1, 4))
                    story.append(domain_table(parsed, styles))
                    story.append(Spacer(1, 6))
                in_table = False
                table_rows = []

        # H1
        if line.startswith("# ") and not line.startswith("## "):
            story.append(Paragraph(line[2:].strip(), styles["title"]))
            i += 1; continue

        # H2
        if line.startswith("## "):
            text = line[3:].strip()
            # Detect overall verdict line
            if text.startswith("Overall Verdict:"):
                v = text.replace("Overall Verdict:", "").strip()
                story.append(Spacer(1, 6))
                story.append(verdict_banner(v, styles))
                story.append(Spacer(1, 10))
                i += 1; continue
            story.append(Paragraph(text, styles["h1"]))
            i += 1; continue

        # H3
        if line.startswith("### "):
            story.append(Paragraph(line[4:].strip(), styles["h2"]))
            i += 1; continue

        # HR
        if line.strip() == "---":
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=C_BORDER, spaceAfter=4))
            i += 1; continue

        # Bullet
        if line.startswith("- "):
            story.append(Paragraph(f"• {line[2:].strip()}", styles["bullet"]))
            i += 1; continue

        # Numbered list
        m = re.match(r"^(\d+)\. (.+)", line)
        if m:
            story.append(Paragraph(f"{m.group(1)}. {m.group(2)}", styles["bullet"]))
            i += 1; continue

        # Key-value metadata lines (e.g. "Reviewed: 2026-03-28")
        if re.match(r"^[A-Z][a-zA-Z ]+: .+", line):
            story.append(Paragraph(line.strip(), styles["body_small"]))
            i += 1; continue

        # Empty line → spacer
        if line.strip() == "":
            story.append(Spacer(1, 4))
            i += 1; continue

        # Default: body text
        story.append(Paragraph(line.strip(), styles["body"]))
        i += 1

    # Flush any trailing table
    if in_table and table_rows:
        parsed = flush_table_rows(table_rows[2:])
        if parsed:
            story.append(domain_table(parsed, styles))

    return story

# ── Page template ─────────────────────────────────────────────────────────────
REPORT_TITLE   = "GFIT Agent Production Readiness Report"
HEADER_BG      = colors.HexColor("#534AB7")   # purple band
HEADER_FG      = colors.white
FOOTER_TEXT    = "GFIT Agent Production Readiness Report — Confidential"

def make_doc(output_path: str):
    return SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=30*mm,   # extra top margin to clear the header band
        bottomMargin=22*mm,
        title=REPORT_TITLE,
        author="Claude — ops-agent-code-review skill",
        subject="Agent Production Readiness Review",
    )

def add_page_decorations(canvas, doc):
    """Header band + footer on every page."""
    w, h = A4
    canvas.saveState()

    # ── Header band ──────────────────────────────────────────────────────────
    band_h = 14 * mm
    canvas.setFillColor(HEADER_BG)
    canvas.rect(0, h - band_h, w, band_h, fill=1, stroke=0)

    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(HEADER_FG)
    canvas.drawString(20*mm, h - band_h + 4*mm, REPORT_TITLE)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#CECBF6"))  # purple-light
    canvas.drawRightString(w - 20*mm, h - band_h + 4*mm,
                           f"Page {doc.page}")

    # ── Footer line ──────────────────────────────────────────────────────────
    canvas.setStrokeColor(colors.HexColor("#D3D1C7"))
    canvas.setLineWidth(0.4)
    canvas.line(20*mm, 18*mm, w - 20*mm, 18*mm)

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#888780"))
    canvas.drawString(20*mm, 12*mm, FOOTER_TEXT)
    canvas.drawRightString(w - 20*mm, 12*mm,
                           f"Generated {datetime.now().strftime('%Y-%m-%d')}")

    canvas.restoreState()

def make_cover_banner(styles: dict) -> list:
    """Prominent title banner at the very top of page 1 content area."""
    w = 170 * mm
    title_cell = Paragraph(
        REPORT_TITLE,
        ParagraphStyle("cover_title",
            fontSize=16, fontName="Helvetica-Bold",
            textColor=C_WHITE, leading=20)
    )
    sub_cell = Paragraph(
        "Code Review &amp; Production Readiness Assessment",
        ParagraphStyle("cover_sub",
            fontSize=9, fontName="Helvetica",
            textColor=colors.HexColor("#CECBF6"), leading=12)
    )
    t = Table([[title_cell], [sub_cell]], colWidths=[w])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), C_PURPLE),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("LEFTPADDING",  (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return [t, Spacer(1, 14)]

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True, help="Input markdown file")
    parser.add_argument("--output", required=True, help="Output PDF file")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        md = f.read()

    styles = make_styles()
    story  = make_cover_banner(styles) + parse_markdown(md, styles)

    doc = make_doc(args.output)
    doc.build(story,
              onFirstPage=add_page_decorations,
              onLaterPages=add_page_decorations)
    print(f"PDF written to: {args.output}")

if __name__ == "__main__":
    main()
