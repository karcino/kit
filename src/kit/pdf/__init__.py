"""kit.pdf — PDF text, metadata, and batch extraction.

Primär-Nutzen: aus einer Liste bekannter PDF-URLs (oder lokaler Pfade)
Text + Metadaten extrahieren und als strukturiertes JSON oder Markdown
ausgeben. Gebaut für OSINT-Research-Workflows, wo viele PDFs schnell
durchgeklopft werden müssen ohne jedes einzeln zu öffnen.

Verwendete Bibliothek: pdfplumber (layout-aware), mit pypdf als Fallback.
"""
from kit.pdf.core import PDFInfo, extract_metadata, extract_text

__all__ = ["PDFInfo", "extract_text", "extract_metadata"]
