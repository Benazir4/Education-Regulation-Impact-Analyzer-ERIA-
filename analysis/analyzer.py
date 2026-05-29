"""
analysis/analyzer.py  —  ERIA v4.0
=====================================
Primary LLM  : Groq  (free, fast, no daily quota issues)
Fallback LLM : Gemini 2.0 Flash (if Groq fails)

Enhancements in v4.0:
  1. TL;DR appended to every summary ("In short: ...")
  2. Readability score (Flesch-Kincaid grade level)
  3. Action alert detection (urgent deadlines & immediate actions)
  4. Share-ready formatted text output
"""

import os, json, re, ssl, time, certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# ── SSL fix (Windows) ─────────────────────────────────────────────────────────
os.environ["SSL_CERT_FILE"]                    = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"]               = certifi.where()
os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = certifi.where()

_orig_ssl = ssl.create_default_context
def _ssl_with_certifi(*args, **kwargs):
    kwargs.setdefault("cafile", certifi.where())
    return _orig_ssl(*args, **kwargs)
ssl.create_default_context = _ssl_with_certifi

# ── API keys ──────────────────────────────────────────────────────────────────
GROQ_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

GROQ_MODEL   = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"

PRIMARY_MODEL  = GROQ_MODEL
FALLBACK_MODEL = GEMINI_MODEL

# ── Groq client ───────────────────────────────────────────────────────────────
_groq_client = None
if GROQ_KEY:
    try:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_KEY)
    except ImportError:
        pass

# ── Gemini client ─────────────────────────────────────────────────────────────
_gemini_client = None
if GEMINI_KEY:
    try:
        from google import genai
        from google.genai import types as gtypes
        _gemini_client = genai.Client(api_key=GEMINI_KEY)
    except ImportError:
        pass


# ── Core LLM callers ─────────────────────────────────────────────────────────

def _call_groq(prompt: str) -> str:
    if not _groq_client:
        raise RuntimeError("Groq client not initialized. Add GROQ_API_KEY to .env")
    for attempt in range(3):
        try:
            resp = _groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower():
                time.sleep(10 * (attempt + 1))
            else:
                raise RuntimeError(f"Groq error: {e}")
    raise RuntimeError("Groq quota hit. Switching to Gemini fallback...")


def _call_gemini(prompt: str) -> str:
    if not _gemini_client:
        raise RuntimeError(
            "No working API key found.\n"
            "Add GROQ_API_KEY to .env (free at https://console.groq.com)\n"
            "or GEMINI_API_KEY (free at https://aistudio.google.com/apikey)"
        )
    from google.genai import types as gtypes
    for attempt in range(3):
        try:
            resp = _gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=gtypes.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1500,
                ),
            )
            return resp.text.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                time.sleep(35 * (attempt + 1))
            elif any(x in err for x in ["SSL", "EOF", "ConnectError"]):
                time.sleep(5 * (attempt + 1))
            else:
                raise RuntimeError(f"Gemini error: {e}")
    raise RuntimeError("Both Groq and Gemini quota exhausted. Wait a few minutes.")


def _call_llm(prompt: str) -> str:
    """Try Groq first, fall back to Gemini if Groq fails."""
    if _groq_client:
        try:
            return _call_groq(prompt)
        except Exception as e:
            if _gemini_client:
                return _call_gemini(prompt)
            raise e
    elif _gemini_client:
        return _call_gemini(prompt)
    else:
        raise RuntimeError(
            "No API key configured!\n"
            "Add GROQ_API_KEY=gsk_... to your .env file.\n"
            "Get a free key at: https://console.groq.com"
        )


def _json(text: str):
    """Parse JSON from LLM response, stripping markdown fences."""
    clean = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(clean)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", clean, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return {}


def _json_stakeholder(text: str) -> dict:
    """
    Robust parser specifically for stakeholder JSON.
    Handles: text before JSON, wrapped under 'stakeholders' key,
    trailing commas, and validates structure.
    """
    # Strip markdown fences
    clean = re.sub(r"```json|```", "", text).strip()

    # Remove any text before the first {
    brace_idx = clean.find("{")
    if brace_idx > 0:
        clean = clean[brace_idx:]

    parsed = None

    # Try direct parse
    try:
        parsed = json.loads(clean)
    except Exception:
        pass

    # Fix trailing commas and retry
    if parsed is None:
        try:
            fixed = re.sub(r",\s*}", "}", re.sub(r",\s*]", "]", clean))
            parsed = json.loads(fixed)
        except Exception:
            pass

    # Regex fallback — extract largest JSON object
    if parsed is None:
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                try:
                    fixed = re.sub(r",\s*}", "}", re.sub(r",\s*]", "]", m.group(0)))
                    parsed = json.loads(fixed)
                except Exception:
                    pass

    if not isinstance(parsed, dict):
        return {}

    # Unwrap if nested under "stakeholders" key
    if "stakeholders" in parsed and isinstance(parsed.get("stakeholders"), dict):
        parsed = parsed["stakeholders"]

    # Keep only valid stakeholder entries (must have impact_level)
    valid_groups = [
        "students", "faculty", "colleges", "universities",
        "administrators", "accreditation_teams",
        "scholarship_applicants", "researchers"
    ]
    result = {}
    for k, v in parsed.items():
        if isinstance(v, dict) and "impact_level" in v:
            # Normalise key
            key = k.lower().replace(" ", "_")
            result[key] = v

    return result


# ══════════════════════════════════════════════════════════════════════════════
# ENHANCEMENT 1 — READABILITY SCORE (no LLM needed, pure Python)
# ══════════════════════════════════════════════════════════════════════════════

def calculate_readability(text: str) -> dict:
    """
    Calculate readability metrics using manual formulas.
    Does NOT depend on textstat or NLTK cmudict — works everywhere.
    Uses Flesch Reading Ease formula directly with syllable estimation.
    """
    try:
        words     = text.split()
        word_count = len(words)
        sentences  = re.findall(r'[.!?]+', text)
        sent_count = max(len(sentences), 1)
        avg_wps    = round(word_count / sent_count, 1)

        # Estimate syllables without NLTK (count vowel groups per word)
        def count_syllables(word):
            word = word.lower().strip(".,!?;:\"'")
            if not word:
                return 1
            count = len(re.findall(r'[aeiou]+', word))
            if word.endswith('e') and count > 1:
                count -= 1
            return max(1, count)

        total_syllables = sum(count_syllables(w) for w in words)
        avg_syl_per_word = total_syllables / max(word_count, 1)

        # Flesch Reading Ease formula
        fk_ease = 206.835 - (1.015 * avg_wps) - (84.6 * avg_syl_per_word)
        fk_ease = round(max(0, min(100, fk_ease)), 1)

        # Flesch-Kincaid Grade Level formula
        fk_grade = (0.39 * avg_wps) + (11.8 * avg_syl_per_word) - 15.59
        fk_grade = round(max(0, fk_grade), 1)

        # Labels
        if fk_grade <= 6:
            grade_label = "Very Easy (Primary School)"
        elif fk_grade <= 9:
            grade_label = "Easy (High School)"
        elif fk_grade <= 12:
            grade_label = "Moderate (Senior Secondary)"
        elif fk_grade <= 16:
            grade_label = "Difficult (University Level)"
        else:
            grade_label = "Very Difficult (Expert / Legal)"

        if fk_ease >= 70:
            ease_label = "Easy to Read"
        elif fk_ease >= 50:
            ease_label = "Moderate"
        elif fk_ease >= 30:
            ease_label = "Difficult"
        else:
            ease_label = "Very Difficult (Legal/Technical)"

        return {
            "flesch_kincaid_grade":   fk_grade,
            "flesch_reading_ease":    fk_ease,
            "grade_label":            grade_label,
            "ease_label":             ease_label,
            "word_count":             word_count,
            "sentence_count":         sent_count,
            "avg_words_per_sentence": avg_wps,
            "estimated_read_minutes": max(1, round(word_count / 200)),
        }
    except Exception as e:
        word_count = len(text.split())
        return {
            "word_count":             word_count,
            "estimated_read_minutes": max(1, round(word_count / 200)),
            "grade_label":            "Could not calculate",
            "ease_label":             "Could not calculate",
        }


# ══════════════════════════════════════════════════════════════════════════════
# ENHANCEMENT 2 — ACTION ALERT DETECTION (urgent deadlines & warnings)
# ══════════════════════════════════════════════════════════════════════════════

def detect_action_alerts(text: str) -> dict:
    """
    Scans the regulation for urgent deadlines, immediate actions,
    and critical compliance requirements.
    Returns structured alert data for the banner.
    """
    prompt = f"""You are an Indian education compliance expert scanning a regulation for URGENT items.

Find all time-sensitive deadlines, immediate actions, and critical compliance items.
Return ONLY valid JSON:
{{
  "has_urgent_items": true,
  "alert_level": "Critical|High|Medium|Low",
  "alert_summary": "One sentence describing the most urgent requirement",
  "deadlines": [
    {{"item": "what must be done", "deadline": "specific date or timeframe", "who": "responsible party"}}
  ],
  "immediate_actions": ["action 1", "action 2"],
  "penalty_warnings": ["penalty 1", "penalty 2"],
  "effective_date": "date this regulation comes into force or Unknown"
}}

If no urgent items found, set has_urgent_items to false and alert_level to "Low".
Return ONLY the JSON.

Document:
{text[:8000]}"""

    result = _json(_call_llm(prompt))
    if not isinstance(result, dict):
        return {
            "has_urgent_items": False,
            "alert_level": "Low",
            "alert_summary": "",
            "deadlines": [],
            "immediate_actions": [],
            "penalty_warnings": [],
            "effective_date": "Unknown",
        }
    return result


# ══════════════════════════════════════════════════════════════════════════════
# CORE ANALYSIS FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def classify_topic(text: str) -> dict:
    prompt = f"""Indian education policy expert. Analyze this regulation.
Return ONLY valid JSON (no explanation):
{{"category":"Accreditation|Scholarship|Curriculum|Faculty Policy|Examination|Admissions|Fees|Infrastructure|Research|Student Welfare|Governance|Other",
"title":"max 15 word title",
"issuing_body":"UGC|AICTE|NAAC|NIRF|Ministry of Education|Unknown",
"year":"YYYY or Unknown",
"key_themes":["4-6 themes"],
"regulation_number":"number or Not specified",
"scope":"National|State|Institutional|Unknown"}}
Document:
{text[:6000]}"""
    result = _json(_call_llm(prompt))
    return result if isinstance(result, dict) and "category" in result else {
        "category": "Unknown", "title": "Education Regulation Document",
        "issuing_body": "Unknown", "year": "Unknown", "key_themes": [],
        "regulation_number": "Not specified", "scope": "Unknown",
    }


# ── ENHANCEMENT 1 applied here ─────────────────────────────────────────────
def generate_summary(text: str) -> str:
    """
    Generates a plain-language summary WITH a TL;DR line at the end.
    The TL;DR gives users the single most important takeaway instantly.
    """
    prompt = f"""Education policy expert. Write a plain-language summary (12-15 sentences).
Target audience: students, teachers, parents - NOT lawyers or legal experts.
Cover these three things clearly:
  1. WHAT this regulation is about
  2. WHY it was introduced (the problem it solves)
  3. WHAT changes or actions it requires

Rules:
- No jargon or legal terms
- Use short paragraphs separated by blank lines
- Write in simple, clear English

After the summary paragraphs, add exactly one blank line then write:
In short: [one sentence capturing the single most important takeaway from this entire regulation]

Return ONLY the summary text and the TL;DR line. No headings, no preamble.

Document:
{text[:10000]}"""
    return _call_llm(prompt)


def analyze_stakeholder_impact(text: str) -> dict:
    prompt = f"""You are an Indian education policy expert.
Analyze this regulation and identify which stakeholder groups are affected.

Return ONLY valid JSON in exactly this format (include only groups that are actually affected):
{{
  "students": {{
    "impact_level": "High",
    "benefits": ["benefit 1", "benefit 2"],
    "constraints": ["constraint 1", "constraint 2"],
    "action_required": "One sentence describing what students must do."
  }},
  "faculty": {{
    "impact_level": "High",
    "benefits": ["benefit 1", "benefit 2"],
    "constraints": ["constraint 1", "constraint 2"],
    "action_required": "One sentence describing what faculty must do."
  }}
}}

Groups to consider (include only those actually affected):
students, faculty, colleges, universities, administrators,
accreditation_teams, scholarship_applicants, researchers

Rules:
- Return ONLY the JSON object. No explanation before or after.
- impact_level must be exactly: High, Medium, Low, or Not Affected
- benefits and constraints must each have 2-3 items
- Include at least 3 stakeholder groups

Document:
{text[:9000]}"""

    raw    = _call_llm(prompt)
    result = _json_stakeholder(raw)
    return result if isinstance(result, dict) and len(result) > 0 else {}


def forecast_impact(text: str) -> dict:
    prompt = f"""Analyze this Indian education regulation. Return ONLY valid JSON:
{{"short_term":{{"timeframe":"0-1 year","impacts":["3 items"]}},
"medium_term":{{"timeframe":"1-5 years","impacts":["3 items"]}},
"long_term":{{"timeframe":"5+ years","impacts":["3 items"]}},
"positives":["3 items"],"negatives":["2-3 items"],
"overall_sentiment":"Broadly Positive|Mixed|Broadly Negative|Neutral",
"sentiment_score":7,"confidence":"High|Medium|Low"}}
Document:
{text[:9000]}"""
    result = _json(_call_llm(prompt))
    return result if isinstance(result, dict) and "short_term" in result else {
        "short_term": {"timeframe": "0-1 year", "impacts": []},
        "medium_term": {"timeframe": "1-5 years", "impacts": []},
        "long_term": {"timeframe": "5+ years", "impacts": []},
        "positives": [], "negatives": [],
        "overall_sentiment": "Neutral", "sentiment_score": 5, "confidence": "Low",
    }


def analyze_risk_and_chronology(text: str) -> dict:
    prompt = f"""Indian education compliance expert. Analyze this regulation.
Return ONLY valid JSON:
{{"risks":[{{"risk":"1 sentence","severity":"High|Medium|Low","affected_group":"group"}}],
"compliance_requirements":["3-5 items"],
"related_policies":["related policies"],
"chronology_notes":"2-3 sentence background",
"implementation_challenges":["3 items"],
"timeline_events":[{{"year":"YYYY","event":"max 10 words",
"type":"Previous Policy|Amendment|Current Regulation|Expected Impact"}}]}}
Document:
{text[:9000]}"""
    result = _json(_call_llm(prompt))
    return result if isinstance(result, dict) else {
        "risks": [], "compliance_requirements": [], "related_policies": [],
        "chronology_notes": "No chronology extracted.",
        "implementation_challenges": [], "timeline_events": [],
    }


def extract_key_clauses(text: str) -> list:
    prompt = f"""Indian education law expert. Extract 5 most important clauses.
Return ONLY valid JSON array of exactly 5 objects:
[{{"clause_number":"Section X or Key Provision N",
"original_text":"exact quote max 20 words",
"plain_explanation":"2 simple sentences no jargon",
"importance":"Critical|High|Medium",
"affects":"main stakeholder group",
"action_needed":true}}]
Document:
{text[:9000]}"""
    result = _json(_call_llm(prompt))
    return result if isinstance(result, list) else []


def generate_compliance_checklist(text: str, topic: dict) -> list:
    cat  = topic.get("category", "Education")
    body = topic.get("issuing_body", "Regulatory body")
    prompt = f"""Compliance officer for Indian higher education.
Generate checklist for this {cat} regulation from {body}.
Return ONLY valid JSON array of 8-10 items:
[{{"task":"Start with verb — clear action",
"responsible_party":"Principal|Registrar|Faculty|Admin|Finance",
"deadline_type":"Immediate (0-30 days)|Short-term (1-3 months)|Medium-term (3-6 months)|Long-term (6-12 months)|Ongoing",
"priority":"Critical|High|Medium|Low",
"category":"Documentation|Training|Infrastructure|Policy Update|Reporting|Communication|Financial|Academic",
"completed":false}}]
Document:
{text[:9000]}"""
    result = _json(_call_llm(prompt))
    return result if isinstance(result, list) else []


def answer_question(question: str, doc_text: str,
                    chat_history: list = None) -> str:
    hist = ""
    if chat_history:
        for t in chat_history[-3:]:
            hist += f"\nUser: {t['question']}\nAssistant: {t['answer']}\n"
    prompt = f"""Indian education regulation expert.
Answer ONLY from the document. 3-5 sentences. No jargon.
If the answer is not in the document, say exactly: "This is not mentioned in the document."
Return ONLY the answer. No preamble.
Use bullet points when listing multiple items.
{hist}
Document:
{doc_text[:10000]}
Question: {question}
Answer:"""
    return _call_llm(prompt)


# ══════════════════════════════════════════════════════════════════════════════
# MASTER PARALLEL RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_full_analysis(text: str) -> dict:
    """
    ALL tasks run in parallel for maximum speed.
    compliance_checklist runs after topic is available.
    Readability is computed locally (no API, instant).
    """
    results = {}

    # Run all API tasks in parallel simultaneously
    first_tasks = {
        "topic":               (classify_topic,              (text,)),
        "summary":             (generate_summary,            (text,)),
        "stakeholder_impact":  (analyze_stakeholder_impact,  (text,)),
        "impact_forecast":     (forecast_impact,             (text,)),
        "risk_and_chronology": (analyze_risk_and_chronology, (text,)),
        "key_clauses":         (extract_key_clauses,         (text,)),
        "action_alerts":       (detect_action_alerts,        (text,)),
    }

    # Groq: 6 parallel workers for max speed; Gemini: 2
    workers = 6 if _groq_client else 2
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fn, *args): key
                   for key, (fn, args) in first_tasks.items()}
        for f in as_completed(futures):
            key = futures[f]
            try:
                results[key] = f.result()
            except Exception as e:
                results[key] = {} if key != "summary" else f"Analysis error: {e}"

    # compliance_checklist needs topic result
    topic = results.get("topic", {})
    try:
        results["compliance_checklist"] = generate_compliance_checklist(text, topic)
    except Exception as e:
        results["compliance_checklist"] = []

    # Readability — instant local computation, no API call
    results["readability"] = calculate_readability(text)

    return results
