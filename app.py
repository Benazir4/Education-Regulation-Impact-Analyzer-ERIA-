"""
app.py — ERIA v4.0
All 4 enhancements integrated:
  1. TL;DR in summary
  2. Readability score
  3. Action alert banner
  4. Share button
All 9 tabs validated and working.
"""

import streamlit as st
import tempfile, os, sys, json

# ── Path fix — works on local Windows/Mac AND Hugging Face Spaces ──
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)
# Also add current working directory as fallback
_cwd = os.getcwd()
if _cwd not in sys.path:
    sys.path.insert(0, _cwd)

from ingestion.pdf_reader    import read_pdf
from ingestion.url_scraper   import scrape_url
from processing.preprocessor import preprocess
from analysis.analyzer       import (
    run_full_analysis, answer_question,
    PRIMARY_MODEL, FALLBACK_MODEL
)
from utils.pdf_exporter import generate_pdf_report

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ERIA — Education Regulation Analyzer",
    page_icon="🎓", layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stTabs [data-baseweb="tab"] > div { color: inherit !important; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; flex-wrap: wrap; }
[data-testid="stMetricLabel"] { font-size: 0.75rem; }
h1 a, h2 a, h3 a { display: none; }
</style>""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎓 ERIA")
    st.caption("Education Regulation Impact Analyzer")
    st.divider()
    input_method = st.radio(
        "**Input Method**",
        ["📂 Upload PDF", "🌐 Paste URL", "📋 Paste Text"])
    st.divider()
    st.markdown("**📚 Supported Sources**")
    for s in ["UGC Circulars","AICTE Notifications",
               "NAAC Guidelines","NIRF Frameworks","MoE Notices"]:
        st.markdown(f"&nbsp;&nbsp;✦ {s}")
    st.divider()
    groq_key   = os.getenv("GROQ_API_KEY","")
    gemini_key = os.getenv("GEMINI_API_KEY","")
    if groq_key and len(groq_key) > 10:
        st.success(f"✅ Groq API connected")
        st.caption(f"Model: {PRIMARY_MODEL}")
        st.caption(f"Fallback: {FALLBACK_MODEL}")
    elif gemini_key and len(gemini_key) > 10:
        st.success(f"✅ Gemini API connected")
        st.caption(f"Model: {FALLBACK_MODEL}")
    else:
        st.error("❌ No API key in .env")
    if "results" in st.session_state:
        st.divider()
        if st.button("🔄 New Analysis", use_container_width=True, type="primary"):
            for k in ["results","doc_meta","analysis_text",
                      "chat_history","checklist_state","suggested_questions"]:
                st.session_state.pop(k, None)
            st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🎓 Education Regulation Impact Analyzer")
st.markdown(
    "**AI-powered analysis of Indian education regulations** — "
    "Upload any UGC/AICTE/NAAC document for instant, "
    "plain-language insights.")
st.divider()

# ── Input ─────────────────────────────────────────────────────────────────────
doc_text, doc_meta = "", {}

if "📂" in input_method:
    uploaded = st.file_uploader(
        "Drop a regulation PDF here", type=["pdf"],
        help="Upload any UGC, AICTE, NAAC, or NIRF regulation PDF")
    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded.read()); path = tmp.name
        with st.spinner("Reading PDF..."):
            res = read_pdf(path); os.unlink(path)
        if res["status"] == "success":
            st.success(f"✅ {res['message']}")
            doc_text = res["text"]
            doc_meta = {"source": res["filename"], "pages": res["page_count"]}
        else:
            st.error(f"❌ {res['message']}")
elif "🌐" in input_method:
    url = st.text_input(
        "Paste regulation URL",
        placeholder="https://www.ugc.gov.in/Circulars/...")
    if url.strip():
        with st.spinner("Fetching page..."):
            res = scrape_url(url.strip())
        if res["status"] == "success":
            st.success(f"✅ {res['message']}")
            doc_text = res["text"]
            doc_meta = {"source": res["url"]}
        else:
            # Smart error message based on error type
            err_msg = res.get("message", "")
            if "403" in err_msg or "blocked" in err_msg.lower() or "allowlist" in err_msg.lower():
                st.error("❌ This website blocks automated access (403 Forbidden).")
                st.info("""
**Government portals like ugcnet.nta.nic.in block web scrapers.**

**3 easy workarounds:**

**Option 1 — Download the PDF:**
1. Open the URL in your browser
2. Find the regulation/notification PDF link
3. Download it → Upload using **📂 Upload PDF** tab

**Option 2 — Save as PDF:**
1. Open the URL in Chrome/Edge
2. Press `Ctrl + P` → Select **Save as PDF**
3. Upload the saved PDF using **📂 Upload PDF** tab

**Option 3 — Copy & Paste text:**
1. Open the URL in your browser
2. Select all text (`Ctrl + A`) → Copy (`Ctrl + C`)
3. Switch to **📋 Paste Text** tab → Paste the text
""")
            elif "timeout" in err_msg.lower() or "connect" in err_msg.lower():
                st.error("❌ Could not reach the website. Check your internet connection and try again.")
            else:
                st.error(f"❌ {err_msg}")

else:
    # PASTE TEXT option
    st.info("💡 Copy text from any government website or regulation document and paste it below.")
    pasted = st.text_area(
        "Paste regulation text here:",
        placeholder="Paste the full text of the regulation, circular, or notification here...",
        height=250,
        help="Copy text from ugcnet.nta.nic.in or any other site that blocks automated access"
    )
    if pasted.strip() and len(pasted.strip()) > 100:
        doc_text = pasted.strip()
        doc_meta = {"source": "Pasted text", "chars": len(pasted)}
        st.success(f"✅ Text received — {len(pasted):,} characters ready for analysis")
    elif pasted.strip():
        st.warning("⚠️ Text is too short. Please paste the full regulation text (minimum 100 characters).")

# ── Analyze button ────────────────────────────────────────────────────────────
if doc_text:
    st.divider()
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.button("🔍 Analyze Regulation", type="primary",
                     use_container_width=True):
            atext = preprocess(doc_text)["full_text"]
            prog  = st.progress(0, text="Starting analysis...")
            prog.progress(5, text="Running 7 AI analyses in parallel...")
            try:
                results = run_full_analysis(atext)
                prog.progress(100, text="✅ Complete!")
            except Exception as e:
                prog.empty()
                err = str(e)
                if "quota" in err.lower() or "exhausted" in err.lower() or "429" in err.lower():
                    st.error("""
⚠️ **API Quota Exhausted**

Both your Groq and Gemini free quotas are used up. Here's what to do:

**Option 1 — Get a fresh Groq key (2 min, completely free):**
1. Go to https://console.groq.com
2. Sign in → API Keys → Delete old key → Create New Key
3. Open your `.env` file and replace `GROQ_API_KEY=` with the new key
4. Restart the app: `Ctrl+C` then `streamlit run app.py`

**Option 2 — Wait for quota reset:**
- Groq resets every minute (rate limit) or next day (daily limit)
- Gemini resets every minute or next day

**Option 3 — Create a second free Groq account** with a different email.
""")
                elif "api key" in err.lower() or "invalid" in err.lower():
                    st.error("""
❌ **Invalid API Key**

Your API key is not valid. Please:
1. Open your `.env` file
2. Replace with a fresh key from https://console.groq.com
3. Restart the app
""")
                else:
                    st.error(f"❌ Analysis failed: {err}")
                st.stop()
            st.session_state.update({
                "results"        : results,
                "doc_meta"       : doc_meta,
                "analysis_text"  : atext,
                "chat_history"   : [],
                "checklist_state": {
                    i: False
                    for i in range(len(results.get("compliance_checklist",[])))
                }
            })
            st.rerun()

if "results" not in st.session_state:
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────────────────────────────────────
R      = st.session_state["results"]
meta   = st.session_state.get("doc_meta", {})
atext  = st.session_state.get("analysis_text", "")
topic  = R.get("topic", {})
fc     = R.get("impact_forecast", {})
risk   = R.get("risk_and_chronology", {})
stk    = R.get("stakeholder_impact", {})
claus  = R.get("key_clauses", [])
chk    = R.get("compliance_checklist", [])
summ   = R.get("summary", "")
alerts = R.get("action_alerts", {})
rdscore= R.get("readability", {})
score  = fc.get("sentiment_score", 5)
sent   = fc.get("overall_sentiment", "—")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ENHANCEMENT 3 — ACTION ALERT BANNER
# ══════════════════════════════════════════════════════════════════════════════
alert_level = alerts.get("alert_level", "Low")
if alerts.get("has_urgent_items") and alert_level in ("Critical", "High"):
    icon = "🚨" if alert_level == "Critical" else "⚠️"
    st.error(
        f"{icon} **{alert_level} Alert** — "
        f"{alerts.get('alert_summary','This regulation has urgent compliance requirements.')}"
    )
    eff = alerts.get("effective_date","")
    if eff and eff != "Unknown":
        st.markdown(f"**📅 Effective Date:** {eff}")
    deadlines = alerts.get("deadlines", [])
    if deadlines:
        with st.expander("📋 View All Deadlines & Immediate Actions"):
            for dl in deadlines:
                if isinstance(dl, dict):
                    st.markdown(
                        f"- **{dl.get('item','')}** → "
                        f"`{dl.get('deadline','')}` — "
                        f"👤 {dl.get('who','')}")
            imm = alerts.get("immediate_actions", [])
            if imm:
                st.markdown("**⚡ Immediate Actions Required:**")
                for a in imm: st.markdown(f"- {a}")
    st.divider()
elif alerts.get("has_urgent_items"):
    st.info(
        f"ℹ️ **Note:** "
        f"{alerts.get('alert_summary','This regulation has some compliance requirements.')}")
    st.divider()

# ── Metrics strip ─────────────────────────────────────────────────────────────
m1,m2,m3,m4,m5 = st.columns(5)
m1.metric("📋 Category",     topic.get("category","—"))
m2.metric("🏛️ Issuing Body", topic.get("issuing_body","—"))
m3.metric("📅 Year",          topic.get("year","—"))
m4.metric("🌐 Scope",         topic.get("scope","—"))
bar_e = "🟢" if score>=7 else "🟡" if score>=4 else "🔴"
# Split sentiment into label + delta to avoid overflow
sent_short = sent.split()[0] if sent and sent != "—" else sent  # "Broadly" or "Mixed" etc
m5.metric("💬 Sentiment", f"{bar_e} {sent_short}", f"{score}/10")

themes = topic.get("key_themes",[])
if themes:
    st.markdown("**🏷️ Key Themes:** " +
                " · ".join([f"`{t}`" for t in themes]))

# ══════════════════════════════════════════════════════════════════════════════
# ENHANCEMENT 2 — READABILITY SCORE STRIP
# ══════════════════════════════════════════════════════════════════════════════
if rdscore and "error" not in rdscore:
    with st.expander("📖 Document Readability Analysis", expanded=False):
        r1,r2,r3,r4 = st.columns(4)
        r1.metric("Reading Grade",
                  f"Grade {rdscore.get('flesch_kincaid_grade','—')}",
                  help="Flesch-Kincaid Grade Level")
        r2.metric("Reading Ease",
                  f"{rdscore.get('flesch_reading_ease','—')}/100",
                  help="Higher = easier to read")
        r3.metric("Est. Read Time",
                  f"{rdscore.get('estimated_read_minutes','—')} min")
        r4.metric("Word Count",
                  f"{rdscore.get('word_count',0):,}")
        st.markdown(
            f"**Complexity:** {rdscore.get('grade_label','—')} &nbsp;|&nbsp; "
            f"**Readability:** {rdscore.get('ease_label','—')} &nbsp;|&nbsp; "
            f"**Avg words/sentence:** {rdscore.get('avg_words_per_sentence','—')}")
        st.info(
            "💡 Most Indian education regulations score Grade 14-18 "
            "(University/Expert level). ERIA's summary simplifies it to Grade 6-8.")

with st.expander("📌 Document Details", expanded=False):
    st.markdown(f"**Source:** {meta.get('source','—')}")
    if "pages" in meta: st.markdown(f"**Pages:** {meta['pages']}")
    if topic.get("title"): st.markdown(f"**Title:** {topic['title']}")
    if topic.get("regulation_number","") not in ("","Not specified"):
        st.markdown(f"**Regulation No.:** {topic['regulation_number']}")

st.divider()

# ── TABS ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📝 Summary",
    "👥 Stakeholders",
    "📊 Impact Forecast",
    "⚠️ Risks",
    "📅 Chronology",
    "🔑 Key Clauses",
    "✅ Checklist",
    "💬 Ask AI",
    "📄 Download",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SUMMARY (with TL;DR + Share)
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("📝 Plain Language Summary")

    # ── ENHANCEMENT 1 — Extract and show TL;DR prominently ───────────────────
    tldr_line = ""
    main_summary = summ
    if "In short:" in summ:
        parts = summ.rsplit("In short:", 1)
        main_summary = parts[0].strip()
        tldr_line    = "In short:" + parts[1].strip()

    if tldr_line:
        st.success(f"💡 **{tldr_line}**")
        st.markdown("")

    st.info("This summary explains the regulation in plain language — "
            "no legal jargon, suitable for students and faculty.")

    if main_summary:
        for para in main_summary.split("\n\n"):
            para = para.strip()
            if para:
                st.markdown(para)
                st.markdown("")
    else:
        st.warning("Summary not available.")

    # ── ENHANCEMENT 4 — Share button ─────────────────────────────────────────
    st.divider()
    share_col, _ = st.columns([1, 2])
    with share_col:
        themes_str = ", ".join(topic.get("key_themes",[]))
        share_text = (
            f"📋 ERIA Analysis: {topic.get('title','Education Regulation')}\n"
            f"Issued by: {topic.get('issuing_body','—')} ({topic.get('year','—')})\n"
            f"Category: {topic.get('category','—')}\n"
            f"Themes: {themes_str}\n\n"
            f"{tldr_line if tldr_line else ''}\n\n"
            f"Full Summary:\n{main_summary[:500]}...\n\n"
            f"Analyzed by ERIA — Education Regulation Impact Analyzer"
        )
        st.download_button(
            "📤 Share / Copy Summary",
            share_text,
            "ERIA_Share.txt",
            "text/plain",
            use_container_width=True,
            help="Download as text to copy and share via email or WhatsApp")

    st.divider()
    st.subheader("⬇️ Download")
    d1, d2, d3 = st.columns(3)

    with d1:
        txt = "\n".join([
            "ERIA - EDUCATION REGULATION IMPACT ANALYZER",
            "="*52,
            f"TITLE    : {topic.get('title','N/A')}",
            f"CATEGORY : {topic.get('category','N/A')}",
            f"BODY     : {topic.get('issuing_body','N/A')}",
            f"YEAR     : {topic.get('year','N/A')}",
            f"THEMES   : {themes_str}",
            f"SENTIMENT: {sent} ({score}/10)",
            "", "="*52,
            f"{tldr_line}" if tldr_line else "",
            "="*52, "PLAIN LANGUAGE SUMMARY", "="*52, "",
            main_summary, "", "Generated by ERIA",
        ])
        st.download_button("📄 Download TXT", txt,
                           "ERIA_Summary.txt", "text/plain",
                           use_container_width=True)
    with d2:
        pos = "\n".join(f"- {x}" for x in fc.get("positives",[]))
        neg = "\n".join(f"- {x}" for x in fc.get("negatives",[]))
        md  = "\n".join([
            "# ERIA Report",
            "", "## Document Overview",
            "| Field | Value |", "|---|---|",
            f"| Title | {topic.get('title','N/A')} |",
            f"| Category | {topic.get('category','N/A')} |",
            f"| Issuing Body | {topic.get('issuing_body','N/A')} |",
            f"| Year | {topic.get('year','N/A')} |",
            f"| Sentiment | {sent} ({score}/10) |",
            "", f"**{tldr_line}**" if tldr_line else "",
            "", "---", "## Summary", "", main_summary,
            "", "## Positives", "", pos,
            "", "## Risks", "", neg,
            "", "---", "*Generated by ERIA*",
        ])
        st.download_button("📝 Download Markdown", md,
                           "ERIA_Summary.md", "text/markdown",
                           use_container_width=True)
    with d3:
        if st.button("📑 Generate Full PDF", type="primary",
                     use_container_width=True):
            with st.spinner("Building PDF..."):
                path = generate_pdf_report(R)
            with open(path,"rb") as fh:
                st.download_button("⬇️ Download PDF", fh,
                                   "ERIA_Report.pdf", "application/pdf",
                                   use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — STAKEHOLDERS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("👥 Stakeholder Impact Analysis")
    if not stk:
        st.warning("No stakeholder data extracted.")
    else:
        import pandas as pd
        imap  = {"High":3,"Medium":2,"Low":1,"Not Affected":0}
        cdata = {
            g.replace("_"," ").title():
            imap.get(d.get("impact_level","Low"),0)
            for g,d in stk.items() if isinstance(d,dict)
        }
        if cdata:
            st.markdown("**Impact Overview** (3=High, 0=Not Affected)")
            df = pd.DataFrame.from_dict(cdata, orient="index",
                                        columns=["Impact Level"])
            st.bar_chart(df, height=200, color="#2980B9")
        st.divider()

        ICON = {"High":"🔴","Medium":"🟡","Low":"🟢","Not Affected":"⚪"}
        for grp, data in stk.items():
            if not isinstance(data,dict): continue
            lvl   = data.get("impact_level","Low")
            label = grp.replace("_"," ").title()
            with st.expander(
                    f"{ICON.get(lvl,'⚪')} **{label}** — {lvl} Impact",
                    expanded=(lvl=="High")):
                bc,cc = st.columns(2)
                with bc:
                    st.markdown("**✅ Benefits**")
                    for b in data.get("benefits",[]): st.markdown(f"- {b}")
                with cc:
                    st.markdown("**⚠️ Constraints**")
                    for c in data.get("constraints",[]): st.markdown(f"- {c}")
                if data.get("action_required"):
                    st.info(f"📌 **Action:** {data['action_required']}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — IMPACT FORECAST
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("📊 Impact Forecast")
    g1,g2,g3 = st.columns(3)
    g1.metric("Sentiment",   sent)
    g2.metric("Score",       f"{score}/10")
    g3.metric("Confidence",  fc.get("confidence","—"))

    st.markdown(f"**Sentiment Score: {score}/10**")
    st.progress(score/10)
    st.divider()

    tc = st.columns(3)
    for i,(key,ico) in enumerate(zip(
            ["short_term","medium_term","long_term"],["⚡","📈","🔭"])):
        sec = fc.get(key,{})
        with tc[i]:
            st.markdown(f"#### {ico} {sec.get('timeframe',key)}")
            for item in sec.get("impacts",[]): st.markdown(f"- {item}")

    st.divider()
    pc,nc = st.columns(2)
    with pc:
        st.markdown("#### ✅ Positives")
        for p in fc.get("positives",[]): st.success(p)
    with nc:
        st.markdown("#### ❌ Risks / Negatives")
        for n in fc.get("negatives",[]): st.error(n)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RISKS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("⚠️ Risk Analysis")
    risks = risk.get("risks",[])
    if risks:
        SMAP = {"High":"🔴","Medium":"🟡","Low":"🟢"}
        for sev in ["High","Medium","Low"]:
            grp = [r for r in risks if isinstance(r,dict)
                   and r.get("severity")==sev]
            if not grp: continue
            st.markdown(f"**{SMAP[sev]} {sev} Severity**")
            for r in grp:
                with st.expander(f"{r.get('risk','')[:80]}"):
                    st.markdown(f"**Risk:** {r.get('risk','')}")
                    st.markdown(f"**Affects:** {r.get('affected_group','')}")
    else:
        st.info("No specific risks detected.")

    # Penalty warnings from alert detection
    pen = alerts.get("penalty_warnings",[])
    if pen:
        st.divider()
        st.markdown("#### 🚫 Penalty Warnings")
        for pw in pen: st.error(pw)

    st.divider()
    st.markdown("#### 🔧 Compliance Requirements")
    for i,req in enumerate(risk.get("compliance_requirements",[]),1):
        st.markdown(f"**{i}.** {req}")
    st.divider()
    st.markdown("#### 🚧 Implementation Challenges")
    for ch in risk.get("implementation_challenges",[]): st.warning(ch)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CHRONOLOGY
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("📅 Policy Chronology & Historical Context")
    st.info("Traces the historical evolution of this regulation and connects "
            "it to previous policies and future expectations.")

    st.markdown("#### 📜 Policy Background")
    chron = risk.get("chronology_notes","")
    st.markdown(chron if chron else "_No background extracted._")

    related = risk.get("related_policies",[])
    if related:
        st.divider()
        st.markdown("#### 📎 Related Policies & Frameworks")
        for rp in related: st.markdown(f"- {rp}")

    events = risk.get("timeline_events",[])
    st.divider()
    st.markdown("#### 🕐 Policy Timeline")

    TYPE_CFG = {
        "Previous Policy"   : ("📜","Previous Policy"),
        "Amendment"         : ("✏️","Amendment"),
        "Current Regulation": ("📋","Current Regulation"),
        "Expected Impact"   : ("🔭","Expected Future Impact"),
    }

    if events:
        def sort_yr(e):
            y = str(e.get("year","0")).strip()
            return int(y) if y.isdigit() else 0

        lc = st.columns(4)
        for i,(tt,(ico,lbl)) in enumerate(TYPE_CFG.items()):
            with lc[i]: st.markdown(f"{ico} **{lbl}**")
        st.markdown("---")

        for ev in sorted(events, key=sort_yr):
            ttype      = ev.get("type","Previous Policy")
            ico, label = TYPE_CFG.get(ttype, ("📄","Event"))
            year       = str(ev.get("year","?"))
            event      = str(ev.get("event",""))
            is_cur     = (ttype=="Current Regulation")

            yc, ec = st.columns([0.18, 0.82])
            with yc:
                if is_cur: st.markdown(f"### {ico} {year}")
                else:       st.markdown(f"**{ico} {year}**")
            with ec:
                if is_cur:              st.success(f"🎯 **{event}** ← This Document")
                elif ttype=="Expected Impact": st.info(f"🔭 {event}")
                elif ttype=="Amendment":       st.warning(f"✏️ {event}")
                else:                          st.markdown(f"&nbsp;&nbsp; {event}")
    else:
        st.markdown("_No specific timeline events extracted._")
        if chron: st.markdown(chron)

    st.divider()
    st.markdown("#### 🔗 Legislative Context")
    st.markdown(
        f"Issued by **{topic.get('issuing_body','—')}** in "
        f"**{topic.get('year','—')}** · "
        f"Scope: **{topic.get('scope','—')}** · "
        f"Category: **{topic.get('category','—')}**")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — KEY CLAUSES
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("🔑 Key Clauses & Legislative Context")
    st.caption("5 most important provisions — explained in plain language.")
    IMAP = {"Critical":"🔴 Critical","High":"🟠 High","Medium":"🔵 Medium"}
    if not claus:
        st.warning("Key clauses could not be extracted.")
    else:
        for i, cl in enumerate(claus, 1):
            if not isinstance(cl,dict): continue
            imp    = cl.get("importance","Medium")
            affect = cl.get("affects","")
            action = cl.get("action_needed",False)
            with st.expander(
                    f"{IMAP.get(imp,'🔵')} · #{i} "
                    f"{cl.get('clause_number','')} · Affects: {affect}",
                    expanded=(imp=="Critical")):
                st.markdown("**Original Text:**")
                st.markdown(f"> *{cl.get('original_text','')}*")
                st.markdown("**Plain Explanation:**")
                st.markdown(cl.get("plain_explanation",""))
                if action:
                    st.warning("⚡ This clause requires action from your institution.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7 — COMPLIANCE CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("✅ Institutional Compliance Checklist")
    st.caption("Auto-generated action items — check off tasks as you complete them.")
    if not chk:
        st.warning("No compliance checklist generated.")
    else:
        f1,f2,f3 = st.columns(3)
        with f1:
            pf = st.multiselect("Priority",
                ["Critical","High","Medium","Low"],
                default=["Critical","High","Medium","Low"])
        with f2:
            dl_opts = ["Immediate (0-30 days)","Short-term (1-3 months)",
                       "Medium-term (3-6 months)","Long-term (6-12 months)","Ongoing"]
            dlf = st.multiselect("Deadline", dl_opts, default=dl_opts)
        with f3:
            cat_opts = sorted({
                item.get("category","Other")
                for item in chk if isinstance(item,dict)
            })
            catf = st.multiselect("Category", cat_opts, default=cat_opts)

        if "checklist_state" not in st.session_state:
            st.session_state["checklist_state"] = {
                i:False for i in range(len(chk))}

        done  = sum(st.session_state["checklist_state"].values())
        total = len(chk)
        st.markdown(f"**Progress: {done}/{total} completed**")
        st.progress(done/total if total else 0)
        if done == total and total > 0:
            st.success("🎉 All tasks completed — fully compliant!")
        st.divider()

        PICO = {"Critical":"🔴","High":"🟠","Medium":"🔵","Low":"🟢"}
        DICO = {"Immediate (0-30 days)":"🔥","Short-term (1-3 months)":"⚡",
                "Medium-term (3-6 months)":"📅","Long-term (6-12 months)":"🗓️",
                "Ongoing":"🔄"}

        for i, item in enumerate(chk):
            if not isinstance(item,dict): continue
            pri = item.get("priority","Medium")
            dl  = item.get("deadline_type","Ongoing")
            cat = item.get("category","Other")
            if pri not in pf or dl not in dlf or cat not in catf: continue
            chked = st.session_state["checklist_state"].get(i,False)
            c1,c2 = st.columns([0.06,0.94])
            with c1:
                nv = st.checkbox("Done", value=chked, key=f"ck_{i}", label_visibility="collapsed")
                if nv != chked:
                    st.session_state["checklist_state"][i] = nv
                    st.rerun()
            with c2:
                task  = f"~~{item.get('task','')}~~" if chked else item.get("task","")
                resp  = item.get("responsible_party","")
                st.markdown(
                    f"{task}  \n"
                    f"{PICO.get(pri,'🔵')} `{pri}` "
                    f"{DICO.get(dl,'📅')} `{dl}` "
                    f"👤 `{resp}` 📁 `{cat}`")
            st.markdown("---")

        lines = ["ERIA COMPLIANCE CHECKLIST","="*40,""]
        for i,item in enumerate(chk):
            if not isinstance(item,dict): continue
            tick = "☑" if st.session_state["checklist_state"].get(i,False) else "☐"
            lines += [
                f"{tick} [{item.get('priority','')}] {item.get('task','')}",
                f"   -> {item.get('deadline_type','')} | "
                f"{item.get('responsible_party','')} | {item.get('category','')}",""]
        st.download_button("📥 Export Checklist",
                           "\n".join(lines),
                           "ERIA_Checklist.txt","text/plain",
                           use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 8 — ASK AI (fixed — no chat_input inside tab)
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("💬 Ask AI About This Regulation")
    st.caption("Instant answers sourced directly from the uploaded document.")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    st.markdown("**💡 Click a question to ask it instantly:**")

    # Generate document-specific questions if not already cached
    if "suggested_questions" not in st.session_state:
        with st.spinner("Generating questions from your document..."):
            try:
                q_prompt = f"""You are an expert on Indian education regulations.
Based on this regulation document, generate exactly 6 specific questions that a student, faculty member, or college administrator would want answered.

Rules:
- Questions must be directly answerable from THIS document
- Make them specific to the content (use actual terms, names, dates from the document)
- Cover different aspects: eligibility, deadlines, penalties, procedures, stakeholders
- Do NOT ask generic questions like "What is this document about?"
- Return ONLY a JSON array of 6 question strings, nothing else

Document:
{atext[:6000]}

Return format: ["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?", "Question 6?"]"""

                import json as _json_mod
                from analysis.analyzer import _call_llm
                raw = _call_llm(q_prompt)
                # Parse JSON array
                import re as _re
                clean = _re.sub(r"```json|```", "", raw).strip()
                # Find array
                m = _re.search(r"\[.*?\]", clean, _re.DOTALL)
                if m:
                    qs = _json_mod.loads(m.group(0))
                    # Validate — must be list of strings
                    if isinstance(qs, list) and len(qs) >= 4:
                        st.session_state["suggested_questions"] = qs[:6]
                    else:
                        raise ValueError("Invalid format")
                else:
                    raise ValueError("No array found")
            except Exception:
                # Fallback to document-aware generic questions
                cat   = topic.get("category", "regulation")
                body  = topic.get("issuing_body", "the regulatory body")
                year  = topic.get("year", "")
                themes = topic.get("key_themes", [])
                t1 = themes[0] if len(themes) > 0 else "eligibility"
                t2 = themes[1] if len(themes) > 1 else "compliance"
                st.session_state["suggested_questions"] = [
                    f"Who is most affected by this {cat} regulation?",
                    f"What are the key deadlines mentioned in this {body} document?",
                    f"What penalties exist for non-compliance?",
                    f"What are the requirements related to {t1}?",
                    f"What must institutions do to comply with {t2}?",
                    f"What changed in this {year} regulation compared to before?",
                ]

    suggested = st.session_state["suggested_questions"]
    sq_cols = st.columns(2)
    for i, sq in enumerate(suggested):
        with sq_cols[i % 2]:
            if st.button(sq, key=f"sq{i}", use_container_width=True):
                st.session_state["pending_q"] = sq
                st.rerun()

    st.divider()

    # Display chat history
    for turn in st.session_state["chat_history"]:
        with st.chat_message("user", avatar="👤"):
            st.markdown(turn["question"])
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(turn["answer"])

    # Handle pending question from suggested buttons
    if "pending_q" in st.session_state:
        pending = st.session_state.pop("pending_q")
        with st.chat_message("user", avatar="👤"):
            st.markdown(pending)
        with st.chat_message("assistant", avatar="🤖"):
            ph = st.empty()
            ph.markdown("🤔 Thinking...")
            try:
                ans = answer_question(pending, atext,
                                      st.session_state["chat_history"])
                ph.markdown(ans)
                st.session_state["chat_history"].append(
                    {"question": pending, "answer": ans})
            except Exception as e:
                ph.error(f"❌ Error: {e}")

    # Text input form (reliable inside tabs)
    st.divider()
    with st.form(key="ask_form", clear_on_submit=True):
        user_q = st.text_input(
            "Your question:",
            placeholder="e.g. What must colleges do to comply?",
            label_visibility="collapsed")
        submitted = st.form_submit_button(
            "📤 Ask", type="primary", use_container_width=True)

    if submitted and user_q.strip():
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_q)
        with st.chat_message("assistant", avatar="🤖"):
            ph = st.empty()
            ph.markdown("🤔 Thinking...")
            try:
                ans = answer_question(user_q, atext,
                                      st.session_state["chat_history"])
                ph.markdown(ans)
                st.session_state["chat_history"].append(
                    {"question": user_q, "answer": ans})
            except Exception as e:
                ph.error(f"❌ Error: {e}")

    if st.session_state["chat_history"]:
        st.divider()
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state["chat_history"] = []
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 9 — DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[8]:
    st.subheader("📄 Download Full Analysis Report")
    st.markdown(
        "Download a professional PDF report containing all 9 sections "
        "of the analysis — suitable for sharing with administrators, "
        "faculty, or regulatory bodies.")

    c1,c2 = st.columns(2)
    with c1:
        if st.button("📥 Generate Full PDF Report",
                     type="primary", use_container_width=True):
            with st.spinner("Building PDF..."):
                path = generate_pdf_report(R)
            with open(path,"rb") as fh:
                st.download_button(
                    "⬇️ Download PDF", fh,
                    "ERIA_Regulation_Report.pdf","application/pdf",
                    use_container_width=True)
            st.success("✅ PDF ready!")
    with c2:
        st.download_button(
            "📋 Export Raw JSON",
            json.dumps(R, indent=2, default=str),
            "ERIA_Analysis.json","application/json",
            use_container_width=True)

    st.divider()
    with st.expander("🔍 Preview Raw Analysis Data"):
        st.json(R)
