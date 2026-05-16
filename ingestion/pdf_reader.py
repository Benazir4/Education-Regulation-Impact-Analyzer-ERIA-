"""
ingestion/pdf_reader.py
Extracts clean text from uploaded PDF regulation documents.
"""

import fitz  # PyMuPDF
import pdfplumber
import os


def extract_text_pymupdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF (fast, handles most PDFs)."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
    except Exception as e:
        raise RuntimeError(f"PyMuPDF failed: {e}")
    return text.strip()


def extract_text_pdfplumber(pdf_path: str) -> str:
    """Extract text using pdfplumber (better for tables & structured PDFs)."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise RuntimeError(f"pdfplumber failed: {e}")
    return text.strip()


def read_pdf(pdf_path: str) -> dict:
    """
    Main function: reads a PDF and returns extracted content.
    Tries PyMuPDF first, falls back to pdfplumber.
    Returns a dict with text, page_count, and filename.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    filename = os.path.basename(pdf_path)

    # Get page count
    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    doc.close()

    # Try extraction
    text = extract_text_pymupdf(pdf_path)

    # Fallback if text is too short (likely scanned PDF)
    if len(text) < 200:
        text = extract_text_pdfplumber(pdf_path)

    if len(text) < 50:
        return {
            "filename": filename,
            "page_count": page_count,
            "text": "",
            "status": "error",
            "message": "Could not extract text. PDF may be scanned/image-based.",
        }

    return {
        "filename": filename,
        "page_count": page_count,
        "text": text,
        "char_count": len(text),
        "status": "success",
        "message": f"Successfully extracted {len(text):,} characters from {page_count} pages.",
    }
