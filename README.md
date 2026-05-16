# 🎓 ERIA — Education Regulation Impact Analyzer

**AI-powered analysis of Indian education regulations, simplified for students, faculty, and institutions.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.35+-red.svg)](https://streamlit.io)

---

## 📋 Project Overview

ERIA transforms complex Indian education regulations (UGC, AICTE, NAAC, NIRF, MoE) into plain-language insights. Upload a PDF or paste a URL, and get instant analysis across 9 interactive dashboards.

**Target Users:** Students, faculty, college administrators, education consultants, and regulatory compliance teams.

---

## ✨ Key Features

### **Core Functionality**
- 📂 **Multi-Input Support** — PDF upload or URL paste (UGC/AICTE/NAAC/NIRF/MoE)
- 🤖 **Dual AI Engine** — Groq (primary) + Google Gemini (fallback) for 99% uptime
- ⚡ **Parallel Processing** — 7 AI analyses run simultaneously (8-15 seconds total)
- 📊 **9-Tab Dashboard** — Summary, Stakeholders, Impact, Risks, Chronology, Key Clauses, Checklist, AI Chat, Download

### **Advanced Features**
- 💡 **TL;DR Summary** — One-sentence takeaway highlighted at the top
- 📖 **Readability Analysis** — Flesch-Kincaid grade level + reading time
- 🚨 **Action Alert Banner** — Urgent deadlines and penalties shown above all tabs
- ✅ **Compliance Checklist** — 8-10 actionable tasks with priority, deadline, responsible party
- 🔑 **Key Clause Extractor** — 5 most important provisions with plain explanations
- 💬 **AI Q&A Chat** — Ask follow-up questions about the regulation
- 📄 **Multi-Format Export** — Download as TXT, Markdown, PDF, or JSON
- 📤 **Share Button** — Pre-formatted text for WhatsApp/email

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- 8GB RAM minimum

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ERIA.git
cd ERIA

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API keys
# Create a .env file
echo "GROQ_API_KEY=your_groq_key_here" > .env
echo "GEMINI_API_KEY=your_gemini_key_here" >> .env
```

### Get API Keys (Free)

**Groq (Recommended):**
1. Go to https://console.groq.com
2. Create API Key → Copy
3. Paste into `.env` as `GROQ_API_KEY=gsk_...`

**Google Gemini (Backup):**
1. Go to https://aistudio.google.com/apikey
2. Create API Key → Copy  
3. Paste into `.env` as `GEMINI_API_KEY=AIza...`

### Run the App

```bash
streamlit run app.py
```

Open browser to `http://localhost:8501`

---

## 📁 Project Structure

```
ERIA/
├── app.py                      # Main Streamlit dashboard
├── requirements.txt            # Python dependencies
├── .env                        # API keys (NOT committed to Git)
├── .gitignore                  # Git exclusions
├── README.md                   # This file
│
├── analysis/
│   ├── __init__.py
│   └── analyzer.py             # AI analysis engine (9 functions)
│
├── ingestion/
│   ├── __init__.py
│   ├── pdf_reader.py           # PDF text extraction
│   └── url_scraper.py          # Web scraping
│
├── processing/
│   ├── __init__.py
│   └── preprocessor.py         # Text cleaning & chunking
│
└── utils/
    ├── __init__.py
    └── pdf_exporter.py         # PDF report generation
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit | Web dashboard UI |
| **Primary AI** | Groq (llama-3.3-70b) | Fast, free, 14,400 req/day |
| **Fallback AI** | Google Gemini 2.0 Flash | Auto-switches if Groq fails |
| **PDF Parsing** | PyMuPDF + pdfplumber | Text extraction with auto-fallback |
| **Web Scraping** | requests + BeautifulSoup4 | URL content extraction |
| **PDF Export** | ReportLab | Professional multi-page reports |
| **Readability** | Manual Flesch-Kincaid | Local computation, no API |
| **Performance** | ThreadPoolExecutor | Parallel AI calls (6 workers) |
| **SSL Security** | certifi | Fixes Windows SSL issues |

---

## 📊 Dashboard Tabs Explained

| # | Tab | What It Shows |
|---|-----|---------------|
| 1 | **Summary** | 12-15 sentence plain-language summary + TL;DR + download options |
| 2 | **Stakeholders** | 8 groups — benefits, constraints, actions |
| 3 | **Impact Forecast** | Short/medium/long term impact + sentiment score |
| 4 | **Risks** | Risk register by severity + penalty warnings |
| 5 | **Chronology** | Policy timeline with amendments and expected impacts |
| 6 | **Key Clauses** | 5 most important legal provisions explained |
| 7 | **Checklist** | 8-10 actionable compliance tasks |
| 8 | **Ask AI** | Q&A chat about the regulation |
| 9 | **Download** | Export as PDF, JSON, or raw data |

---

## 🎯 Use Cases

**For Students:** Understand scholarship eligibility, academic policies  
**For Faculty:** Stay updated on qualification requirements (NET, PhD)  
**For Admins:** Generate compliance checklists, identify stakeholder impacts  
**For Consultants:** Quickly analyze multiple regulations

---

## 🐛 Troubleshooting

**"Both Groq and Gemini quota exhausted"**
- Create fresh Groq API key at https://console.groq.com

**"SSL UNEXPECTED_EOF_ERROR"**
- Already fixed with `certifi` patch in `analyzer.py`

**Analysis taking 30+ seconds**
- Wait 1 minute between analyses, or get fresh API key

---

## 📦 Deployment to Hugging Face Spaces

1. Create account at https://huggingface.co
2. New Space → SDK: `Streamlit` → Hardware: `CPU Basic (Free)`
3. Settings → Secrets → Add API keys
4. Upload all files (never upload .env)
5. Wait 3-5 minutes for build

---

## 🧪 Testing

**Test URLs:**
```
https://www.ugc.gov.in/pdfnews/6169734_Guideline-on-Ragging.pdf
https://www.ugc.gov.in/pdfnews/9973829_Scholarship.pdf
```

**Expected Performance:**
- PDF Read: < 1 second
- Full Analysis: 8-15 seconds
- Readability: < 0.1 seconds
- PDF Export: 1-2 seconds

---

## 👥 Authors

**Benazir** — Initial work and development

---

## 🙏 Acknowledgments

- **Groq** — Fast and free LLM API
- **Google** — Gemini 2.0 Flash API
- **Streamlit** — Beautiful web UI framework

---

**Built with ❤️ for the Indian education ecosystem**
