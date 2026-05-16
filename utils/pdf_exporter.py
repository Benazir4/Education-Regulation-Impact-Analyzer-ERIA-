"""
utils/pdf_exporter.py — ERIA v4.0
Generates professional PDF report using ReportLab.
ReportLab is more reliable than FPDF2 and handles all content sizes safely.
"""

import os, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, HRFlowable
)

# ── Colours ───────────────────────────────────────────────────────────────────
NAVY    = HexColor("#1A5276")
BLUE    = HexColor("#2980B9")
LBLUE   = HexColor("#D6EAF8")
GREEN   = HexColor("#1E8449")
LGREEN  = HexColor("#EAFAF1")
RED     = HexColor("#C0392B")
LRED    = HexColor("#FDEDEC")
ORANGE  = HexColor("#D68910")
LORANGE = HexColor("#FEF9E7")
PURPLE  = HexColor("#6C3483")
GRAY    = HexColor("#5D6D7E")
LGRAY   = HexColor("#F2F3F4")
WHITE   = white

W = 16.6 * cm   # usable page width

# ── Styles ────────────────────────────────────────────────────────────────────
_base = getSampleStyleSheet()["Normal"]

def S(name, **kw):
    return ParagraphStyle(name, parent=_base, **kw)

TITLE  = S("TITLE",  fontSize=18, textColor=WHITE,  backColor=NAVY,
           fontName="Helvetica-Bold", alignment=TA_CENTER,
           spaceAfter=4, spaceBefore=4, leading=24, leftIndent=8, rightIndent=8)
H1     = S("H1",     fontSize=13, textColor=WHITE,  backColor=NAVY,
           fontName="Helvetica-Bold", spaceAfter=4, spaceBefore=10,
           leading=18, leftIndent=10, rightIndent=10)
H2     = S("H2",     fontSize=11, textColor=NAVY,
           fontName="Helvetica-Bold", spaceAfter=3, spaceBefore=8, leading=15)
H3     = S("H3",     fontSize=10, textColor=BLUE,
           fontName="Helvetica-Bold", spaceAfter=2, spaceBefore=5, leading=13)
BODY   = S("BODY",   fontSize=9,  alignment=TA_JUSTIFY,
           spaceAfter=4, leading=13)
BULLET = S("BULLET", fontSize=9,  leftIndent=14, spaceAfter=2,
           leading=13, bulletText="-")
SMALL  = S("SMALL",  fontSize=8,  textColor=GRAY, spaceAfter=2, leading=11)
TLDR   = S("TLDR",   fontSize=10, textColor=GREEN, backColor=LGREEN,
           fontName="Helvetica-Bold", spaceAfter=6, spaceBefore=4,
           leftIndent=8, rightIndent=8, leading=14)
ALERT  = S("ALERT",  fontSize=10, textColor=RED, backColor=LRED,
           fontName="Helvetica-Bold", spaceAfter=6, spaceBefore=4,
           leftIndent=8, rightIndent=8, leading=14)

def sp(n=1):  return Spacer(1, n * 5)
def hr():     return HRFlowable(width="100%", thickness=0.5,
                                color=BLUE, spaceAfter=4, spaceBefore=4)

def p(text, style=BODY):
    safe = _safe(text)
    return Paragraph(safe, style)

def h1(text): return p(text, H1)
def h2(text): return p(text, H2)
def h3(text): return p(text, H3)
def bl(text): return p(text, BULLET)

def _safe(text: str) -> str:
    """
    Safely encode text for ReportLab.
    Handles Unicode, smart quotes, em-dashes, bullets,
    and all special characters the AI might output.
    """
    if not text:
        return ""
    text = str(text)

    # Replace common Unicode punctuation with ASCII equivalents
    replacements = {
        "–": "-",    # en dash
        "—": "-",    # em dash
        "‘": "'",    # left single quote
        "’": "'",    # right single quote
        "“": '"',    # left double quote
        "”": '"',    # right double quote
        "•": "-",    # bullet point
        "‣": "-",    # triangular bullet
        "●": "-",    # black circle bullet
        "…": "...",  # ellipsis
        " ": " ",    # non-breaking space
        "·": "-",    # middle dot
        "→": "->",   # right arrow
        "←": "<-",   # left arrow
        "✓": "OK",   # check mark
        "✔": "OK",   # heavy check mark
        "✗": "X",    # ballot X
        "✘": "X",    # heavy ballot X
        "é": "e",    # e acute
        "à": "a",    # a grave
        "ñ": "n",    # n tilde
        "₹": "Rs.",  # Indian rupee sign
        "®": "(R)",  # registered trademark
        "©": "(C)",  # copyright
        "™": "(TM)", # trademark
    }
    for uni, asc in replacements.items():
        text = text.replace(uni, asc)

    # Strip any remaining non-ASCII non-printable characters
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", text)

    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # First, decode any HTML entities the AI might have output as literal text
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")    # decode escaped ampersand first
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&apos;", "'")

    # Now properly escape XML special chars for ReportLab (single pass)
    text = (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    return text.strip()

def kv_table(rows: list) -> Table:
    """Two-column key-value table."""
    data = [[Paragraph(f"<b>{_safe(k)}</b>", SMALL),
             Paragraph(_safe(str(v)), SMALL)]
            for k, v in rows]
    t = Table(data, colWidths=[4 * cm, 12.6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (0, -1), LBLUE),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID",         (0, 0), (-1, -1), 0.3, BLUE),
    ]))
    return t

def colored_badge(text: str, bg: HexColor) -> Table:
    """Inline colored badge."""
    cell = Paragraph(
        f'<font color="white"><b>{_safe(text)}</b></font>',
        S("badge", fontSize=8, alignment=TA_CENTER))
    t = Table([[cell]], colWidths=[3 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), bg),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("ROUNDEDCORNERS",[4]),
    ]))
    return t


# ── Main PDF builder ──────────────────────────────────────────────────────────

def generate_pdf_report(results: dict, output_path: str = None) -> str:
    if output_path is None:
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), "ERIA_Report.pdf")

    topic   = results.get("topic", {})
    summary = results.get("summary", "")
    stk     = results.get("stakeholder_impact", {})
    fc      = results.get("impact_forecast", {})
    risk    = results.get("risk_and_chronology", {})
    claus   = results.get("key_clauses", [])
    chk     = results.get("compliance_checklist", [])
    alerts  = results.get("action_alerts", {})
    rd      = results.get("readability", {})

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm)

    story = []

    # ── COVER ─────────────────────────────────────────────────────────────────
    story += [
        p("🎓 EDUCATION REGULATION IMPACT ANALYZER", TITLE),
        sp(),
        p("ERIA Analysis Report", S("sub", fontSize=12, textColor=GRAY,
          alignment=TA_CENTER, spaceAfter=4)),
        hr(), sp(),
        kv_table([
            ("Title",        topic.get("title", "N/A")),
            ("Category",     topic.get("category", "N/A")),
            ("Issuing Body", topic.get("issuing_body", "N/A")),
            ("Year",         topic.get("year", "N/A")),
            ("Scope",        topic.get("scope", "N/A")),
            ("Regulation No", topic.get("regulation_number", "N/A")),
            ("Sentiment",    f"{fc.get('overall_sentiment','N/A')} "
                             f"({fc.get('sentiment_score','N/A')}/10)"),
            ("Themes",       ", ".join(topic.get("key_themes", []))),
        ]),
        sp(2),
    ]

    # ── READABILITY ───────────────────────────────────────────────────────────
    if rd and "error" not in rd:
        story += [
            h2("Document Readability"),
            kv_table([
                ("Grade Level",    f"{rd.get('flesch_kincaid_grade','N/A')} — "
                                   f"{rd.get('grade_label','N/A')}"),
                ("Reading Ease",   f"{rd.get('flesch_reading_ease','N/A')}/100 — "
                                   f"{rd.get('ease_label','N/A')}"),
                ("Word Count",     f"{rd.get('word_count',0):,}"),
                ("Est. Read Time", f"{rd.get('estimated_read_minutes','N/A')} minutes"),
            ]),
            sp(2),
        ]

    # ── ACTION ALERTS ─────────────────────────────────────────────────────────
    if alerts.get("has_urgent_items"):
        story += [
            p(f"⚠️ {alerts.get('alert_level','').upper()} ALERT: "
              f"{alerts.get('alert_summary','')}", ALERT),
            sp(),
        ]
        if alerts.get("effective_date","") not in ("","Unknown"):
            story.append(p(f"Effective Date: {alerts['effective_date']}", BODY))
        deadlines = alerts.get("deadlines", [])
        if deadlines:
            story.append(h3("Key Deadlines"))
            for dl in deadlines:
                if isinstance(dl, dict):
                    story.append(bl(
                        f"{dl.get('item','')} — "
                        f"{dl.get('deadline','')} — "
                        f"Responsible: {dl.get('who','')}"))
        story.append(sp(2))

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(h1("Plain Language Summary"))
    story.append(sp())

    tldr = ""
    main = summary
    if "In short:" in summary:
        parts = summary.rsplit("In short:", 1)
        main  = parts[0].strip()
        tldr  = "In short: " + parts[1].strip()

    if tldr:
        story.append(p(tldr, TLDR))
        story.append(sp())

    for para in main.split("\n\n"):
        para = para.strip()
        if para:
            story.append(p(para))
    story.append(sp(2))

    # ── STAKEHOLDER IMPACT ────────────────────────────────────────────────────
    story.append(h1("Stakeholder Impact Analysis"))
    story.append(sp())

    SEV_COLOR = {"High": RED, "Medium": ORANGE, "Low": GREEN,
                 "Not Affected": GRAY}

    for grp, data in stk.items():
        if not isinstance(data, dict): continue
        lvl   = data.get("impact_level", "Low")
        label = grp.replace("_", " ").title()
        story += [
            h2(f"{label} — {lvl} Impact"),
        ]
        # Benefits & constraints side by side
        ben = data.get("benefits", [])
        con = data.get("constraints", [])
        rows = []
        for i in range(max(len(ben), len(con))):
            b = f"✅ {ben[i]}" if i < len(ben) else ""
            c = f"⚠️ {con[i]}" if i < len(con) else ""
            rows.append([Paragraph(_safe(b), SMALL),
                         Paragraph(_safe(c), SMALL)])
        if rows:
            t = Table(rows, colWidths=[8.3*cm, 8.3*cm])
            t.setStyle(TableStyle([
                ("VALIGN",       (0,0),(-1,-1), "TOP"),
                ("TOPPADDING",   (0,0),(-1,-1), 3),
                ("BOTTOMPADDING",(0,0),(-1,-1), 3),
                ("LEFTPADDING",  (0,0),(-1,-1), 4),
                ("GRID",         (0,0),(-1,-1), 0.3, BLUE),
            ]))
            story.append(t)
        action = data.get("action_required", "")
        if action:
            story.append(p(f"📌 Action: {action}", SMALL))
        story.append(sp())
    story.append(sp(2))

    # ── IMPACT FORECAST ───────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(h1("Impact Forecast"))
    story.append(sp())

    for key, ico in [("short_term","⚡"),("medium_term","📈"),("long_term","🔭")]:
        sec = fc.get(key, {})
        if not sec: continue
        story.append(h2(f"{ico} {sec.get('timeframe', key)}"))
        for item in sec.get("impacts", []):
            story.append(bl(item))
        story.append(sp())

    story.append(h2("✅ Positives"))
    for pos in fc.get("positives", []): story.append(bl(pos))
    story.append(sp())
    story.append(h2("❌ Risks / Negatives"))
    for neg in fc.get("negatives", []): story.append(bl(neg))
    story.append(sp(2))

    # ── RISKS & CHRONOLOGY ────────────────────────────────────────────────────
    story.append(h1("Risk Analysis & Chronology"))
    story.append(sp())

    risks = risk.get("risks", [])
    if risks:
        story.append(h2("Risk Register"))
        for r in risks:
            if not isinstance(r, dict): continue
            sev = r.get("severity", "Low")
            clr = SEV_COLOR.get(sev, GRAY)
            row = [[
                Paragraph(f"<b>[{_safe(sev)}]</b>", SMALL),
                Paragraph(_safe(r.get("risk", "")), SMALL),
                Paragraph(_safe(r.get("affected_group", "")), SMALL),
            ]]
            t = Table(row, colWidths=[2.5*cm, 10*cm, 4.1*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(0,0), clr),
                ("TEXTCOLOR",     (0,0),(0,0), WHITE),
                ("VALIGN",        (0,0),(-1,-1),"TOP"),
                ("TOPPADDING",    (0,0),(-1,-1), 3),
                ("BOTTOMPADDING", (0,0),(-1,-1), 3),
                ("LEFTPADDING",   (0,0),(-1,-1), 4),
                ("GRID",          (0,0),(-1,-1), 0.3, BLUE),
            ]))
            story.append(t)
            story.append(sp(0.5))
        story.append(sp())

    story.append(h2("Policy Background"))
    story.append(p(risk.get("chronology_notes", "No background extracted.")))
    story.append(sp())

    related = risk.get("related_policies", [])
    if related:
        story.append(h2("Related Policies"))
        for rp in related: story.append(bl(rp))
        story.append(sp())

    story.append(h2("Compliance Requirements"))
    for req in risk.get("compliance_requirements", []): story.append(bl(req))
    story.append(sp())

    story.append(h2("Implementation Challenges"))
    for ch in risk.get("implementation_challenges", []): story.append(bl(ch))
    story.append(sp(2))

    # ── POLICY TIMELINE ───────────────────────────────────────────────────────
    events = risk.get("timeline_events", [])
    if events:
        story.append(PageBreak())
        story.append(h1("Policy Timeline"))
        story.append(sp())

        def sort_yr(e):
            y = str(e.get("year","0")).strip()
            return int(y) if y.isdigit() else 0

        TYPE_CLR = {
            "Previous Policy":    PURPLE,
            "Amendment":          ORANGE,
            "Current Regulation": BLUE,
            "Expected Impact":    GREEN,
        }
        for ev in sorted(events, key=sort_yr):
            ttype = ev.get("type", "Previous Policy")
            clr   = TYPE_CLR.get(ttype, GRAY)
            is_cur = (ttype == "Current Regulation")
            row = [[
                Paragraph(f"<b>{_safe(str(ev.get('year','?')))}</b>",
                          S("yr", fontSize=10, textColor=WHITE,
                            fontName="Helvetica-Bold",
                            alignment=TA_CENTER)),
                Paragraph(_safe(ev.get("event","")),
                          S("ev", fontSize=9,
                            fontName="Helvetica-Bold" if is_cur
                            else "Helvetica")),
                Paragraph(_safe(ttype),
                          S("tt", fontSize=8, textColor=GRAY)),
            ]]
            t = Table(row, colWidths=[2*cm, 11*cm, 3.6*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(0,0), clr),
                ("BACKGROUND",    (1,0),(2,0),
                 LBLUE if is_cur else LGRAY),
                ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
                ("TOPPADDING",    (0,0),(-1,-1), 5),
                ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                ("LEFTPADDING",   (0,0),(-1,-1), 6),
                ("GRID",          (0,0),(-1,-1), 0.3, BLUE),
            ]))
            story.append(t)
            story.append(sp(0.5))
        story.append(sp(2))

    # ── KEY CLAUSES ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(h1("Key Clauses & Legislative Context"))
    story.append(sp())

    IMP_CLR = {"Critical": RED, "High": ORANGE, "Medium": BLUE}
    for i, cl in enumerate(claus, 1):
        if not isinstance(cl, dict): continue
        imp  = cl.get("importance", "Medium")
        clr  = IMP_CLR.get(imp, BLUE)
        hdr  = [[
            Paragraph(f"<b>#{i} {_safe(cl.get('clause_number',''))}</b>",
                      S("ch", fontSize=9, textColor=WHITE,
                        fontName="Helvetica-Bold")),
            Paragraph(f"<b>{_safe(imp)}</b>",
                      S("ci", fontSize=8, textColor=WHITE,
                        alignment=TA_CENTER)),
            Paragraph(f"Affects: {_safe(cl.get('affects',''))}",
                      S("ca", fontSize=8, textColor=WHITE)),
        ]]
        ht = Table(hdr, colWidths=[8*cm, 2.5*cm, 6.1*cm])
        ht.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), clr),
            ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ]))
        story.append(ht)

        body_rows = [
            [Paragraph("<i>Original text:</i>", SMALL),
             Paragraph(f"<i>{_safe(cl.get('original_text',''))}</i>", SMALL)],
            [Paragraph("<b>Explanation:</b>", SMALL),
             Paragraph(_safe(cl.get("plain_explanation","")), SMALL)],
        ]
        if cl.get("action_needed"):
            body_rows.append([
                Paragraph("<b>Action:</b>", SMALL),
                Paragraph("Required", S("ar", fontSize=8, textColor=RED,
                                        fontName="Helvetica-Bold")),
            ])
        bt = Table(body_rows, colWidths=[3*cm, 13.6*cm])
        bt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(0,-1), LGRAY),
            ("VALIGN",        (0,0),(-1,-1),"TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 3),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("GRID",          (0,0),(-1,-1), 0.3, BLUE),
        ]))
        story.append(bt)
        story.append(sp())
    story.append(sp(2))

    # ── COMPLIANCE CHECKLIST ──────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(h1("Institutional Compliance Checklist"))
    story.append(sp())

    PRI_CLR = {"Critical": RED, "High": ORANGE,
               "Medium": BLUE, "Low": GREEN}

    if chk:
        hdr = [[
            Paragraph("<b>#</b>", SMALL),
            Paragraph("<b>Task</b>", SMALL),
            Paragraph("<b>Priority</b>", SMALL),
            Paragraph("<b>Deadline</b>", SMALL),
            Paragraph("<b>Responsible</b>", SMALL),
        ]]
        rows = []
        for i, item in enumerate(chk, 1):
            if not isinstance(item, dict): continue
            pri = item.get("priority", "Medium")
            rows.append([
                Paragraph(str(i), SMALL),
                Paragraph(_safe(item.get("task", "")), SMALL),
                Paragraph(f"<b>{_safe(pri)}</b>",
                          S("pr", fontSize=8,
                            textColor=PRI_CLR.get(pri, BLUE),
                            fontName="Helvetica-Bold")),
                Paragraph(_safe(item.get("deadline_type", "")), SMALL),
                Paragraph(_safe(item.get("responsible_party", "")), SMALL),
            ])
        t = Table(hdr + rows,
                  colWidths=[0.8*cm, 7*cm, 2.2*cm, 4*cm, 2.6*cm])
        style = [
            ("BACKGROUND",    (0,0),(-1,0), NAVY),
            ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 8),
            ("VALIGN",        (0,0),(-1,-1),"TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("GRID",          (0,0),(-1,-1), 0.3, BLUE),
        ]
        for i in range(1, len(rows)+1, 2):
            style.append(("BACKGROUND", (0,i),(-1,i), LGRAY))
        t.setStyle(TableStyle(style))
        story.append(t)

    # ── FOOTER NOTE ───────────────────────────────────────────────────────────
    story += [
        sp(3), hr(),
        p("Generated by ERIA — Education Regulation Impact Analyzer  |  "
          "AI-powered analysis using Groq / Google Gemini", SMALL),
    ]

    try:
        doc.build(story)
    except Exception as e:
        # Fallback: try rebuilding with all text re-sanitized
        import traceback
        print(f"PDF build error (attempting sanitized fallback): {e}")

        # Build a minimal safe PDF with just the summary
        fallback_story = [
            p("ERIA — Education Regulation Impact Analyzer", TITLE),
            sp(2),
            h1("Plain Language Summary"),
            sp(),
        ]
        for para in (summary or "").split("\n\n"):
            para = para.strip()
            if para:
                fallback_story.append(p(para))

        fallback_story += [
            sp(2), hr(),
            p("Note: Full report could not be rendered due to special characters "
              "in AI output. This is a simplified version.", SMALL),
            p("Generated by ERIA", SMALL),
        ]

        import tempfile
        safe_path = output_path or os.path.join(tempfile.gettempdir(), "ERIA_Fallback.pdf")
        doc2 = SimpleDocTemplate(
            safe_path, pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm)
        doc2.build(fallback_story)

    return output_path
