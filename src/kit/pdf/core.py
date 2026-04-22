"""Core PDF text + metadata extraction.

Pure-logic (no Typer, no rich). Für CLI-Wrapper siehe commands.py.

Design-Entscheidungen:
- pdfplumber für Layout-aware Text-Extraktion (handled Tabellen + Spalten besser als pypdf)
- pypdf als Metadata-Lesen-Fallback falls pdfplumber scheitert
- httpx zum Download von URLs (nie lokal speichern, nur in Memory)
- Kein LLM, kein Embedding — pure Text/Struktur
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path

import httpx


@dataclass
class PDFInfo:
    """Extrahierte Infos aus einem PDF."""

    source: str              # URL oder lokaler Pfad als String
    sha256: str              # Byte-Hash für Deduplizierung
    num_pages: int
    title: str | None
    author: str | None
    subject: str | None
    creator: str | None
    producer: str | None
    creation_date: str | None
    modification_date: str | None
    byte_size: int
    fetched_at: str          # ISO-Zeitpunkt der Extraktion
    # Seiten-spezifisch
    pages: list[str] = field(default_factory=list)   # Plain-text pro Seite
    # Für spätere LLM-Analyse / Grep
    full_text: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "sha256": self.sha256,
            "num_pages": self.num_pages,
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "creator": self.creator,
            "producer": self.producer,
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
            "byte_size": self.byte_size,
            "fetched_at": self.fetched_at,
            "pages_count": len(self.pages),
            "full_text_length": len(self.full_text),
        }

    def to_markdown(self) -> str:
        """Rendert den PDFInfo als Markdown-Section — gut für Reports."""
        lines = [
            f"## {self.title or Path(self.source).name}",
            "",
            f"- **Quelle:** {self.source}",
            f"- **Seiten:** {self.num_pages}",
            f"- **Größe:** {self.byte_size:,} Bytes",
            f"- **SHA-256:** `{self.sha256[:16]}…`",
        ]
        if self.author:
            lines.append(f"- **Author:** {self.author}")
        if self.creator:
            lines.append(f"- **Creator:** {self.creator}")
        if self.creation_date:
            lines.append(f"- **Erstellt:** {self.creation_date}")
        if self.subject:
            lines.append(f"- **Subject:** {self.subject}")
        lines.append("")
        lines.append("### Volltext-Auszug (erste 3.000 Zeichen)")
        lines.append("")
        lines.append("```")
        preview = self.full_text[:3000].strip()
        if len(self.full_text) > 3000:
            preview += f"\n\n[... +{len(self.full_text) - 3000} Zeichen gekürzt]"
        lines.append(preview)
        lines.append("```")
        return "\n".join(lines)


def _fetch_bytes(source: str) -> tuple[bytes, str]:
    """Lädt das PDF als Bytes. Source kann URL oder lokaler Pfad sein.

    Returns: (bytes, normalized_source_string)
    """
    if source.startswith(("http://", "https://")):
        with httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "kit-pdf/0.1 (+https://github.com/karcino/kit)"},
        ) as client:
            resp = client.get(source)
            resp.raise_for_status()
            return resp.content, source
    # Lokaler Pfad
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"PDF nicht gefunden: {path}")
    return path.read_bytes(), str(path)


def _extract_text_with_pdfplumber(data: bytes) -> tuple[list[str], str]:
    """Extrahiert Text pro Seite mit pdfplumber."""
    try:
        import pdfplumber
    except ImportError as e:
        raise RuntimeError(
            "pdfplumber fehlt. Install: uv pip install pdfplumber"
        ) from e
    pages: list[str] = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return pages, "\n\n".join(pages)


def _extract_metadata_with_pypdf(data: bytes) -> dict:
    """Extrahiert Metadaten (author, creator, dates) via pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError(
            "pypdf fehlt. Install: uv pip install pypdf"
        ) from e
    reader = PdfReader(BytesIO(data))
    meta = reader.metadata or {}
    # pypdf gibt Strings oder None. Key-Namen mit /Präfix.
    def clean(key: str) -> str | None:
        val = meta.get(key)
        return str(val) if val else None
    return {
        "num_pages": len(reader.pages),
        "title": clean("/Title"),
        "author": clean("/Author"),
        "subject": clean("/Subject"),
        "creator": clean("/Creator"),
        "producer": clean("/Producer"),
        "creation_date": clean("/CreationDate"),
        "modification_date": clean("/ModDate"),
    }


def extract_text(source: str) -> PDFInfo:
    """Volle Text+Metadata-Extraktion für ein einzelnes PDF."""
    data, normalized = _fetch_bytes(source)
    sha = hashlib.sha256(data).hexdigest()
    meta = _extract_metadata_with_pypdf(data)
    pages, full = _extract_text_with_pdfplumber(data)
    return PDFInfo(
        source=normalized,
        sha256=sha,
        num_pages=meta["num_pages"],
        title=meta["title"],
        author=meta["author"],
        subject=meta["subject"],
        creator=meta["creator"],
        producer=meta["producer"],
        creation_date=meta["creation_date"],
        modification_date=meta["modification_date"],
        byte_size=len(data),
        fetched_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        pages=pages,
        full_text=full,
    )


def extract_metadata(source: str) -> PDFInfo:
    """Nur Metadaten, kein Text — schnell, für Batch-Listings."""
    data, normalized = _fetch_bytes(source)
    sha = hashlib.sha256(data).hexdigest()
    meta = _extract_metadata_with_pypdf(data)
    return PDFInfo(
        source=normalized,
        sha256=sha,
        num_pages=meta["num_pages"],
        title=meta["title"],
        author=meta["author"],
        subject=meta["subject"],
        creator=meta["creator"],
        producer=meta["producer"],
        creation_date=meta["creation_date"],
        modification_date=meta["modification_date"],
        byte_size=len(data),
        fetched_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        pages=[],
        full_text="",
    )
