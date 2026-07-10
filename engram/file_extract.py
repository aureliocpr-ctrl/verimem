"""File -> text extraction for the document RAG tier (roadmap #1: whole-file ingest).

Turns a real file (legal case PDF, a book, a DOCX, an HTML export) into plain
text that ``chunking.chunk_text`` can segment and the semantic layer can embed.
Dispatch is by extension; optional parser deps are imported lazily so a missing
one degrades with a clear message, never an import-time crash for everyone.

    extract_text("case.pdf") -> str   ->   chunk_text(...)   ->   embed

Supported: .txt/.md/.rst (native), .pdf (PyMuPDF), .docx (python-docx),
.html/.htm (BeautifulSoup), .epub (stdlib zip + the same BeautifulSoup).
Others raise a clear ValueError.
"""
from __future__ import annotations

import logging
from pathlib import Path

_NATIVE = {".txt", ".md", ".text", ".rst", ".log", ""}

_LOG = logging.getLogger(__name__)

#: zip-bomb guard per i formati-archivio (EPUB…): un content member ostile ad
#: alta compressione non deve mai decomprimere illimitato in RAM (E1 audit
#: 2026-07-11 — safe_xml cappa i METADATI XML, questi cappano il CONTENUTO).
_MAX_MEMBER_BYTES = 25_000_000     # un singolo capitolo (i veri sono KB)
_MAX_TOTAL_BYTES = 200_000_000     # tetto sull'estrazione dell'intero libro


def extract_text(path: str | Path) -> str:
    """Extract plain text from ``path``, dispatched by file extension.

    Raises ``FileNotFoundError`` if the path does not exist, ``ValueError`` for
    an unsupported extension, and ``RuntimeError`` if a needed parser library is
    not installed.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    ext = p.suffix.lower()
    if ext in _NATIVE:
        return p.read_text(encoding="utf-8", errors="replace")
    if ext == ".pdf":
        return _extract_pdf(p)
    if ext == ".docx":
        return _extract_docx(p)
    if ext in (".html", ".htm"):
        return _extract_html(p)
    if ext == ".epub":
        return _extract_epub(p)
    raise ValueError(f"unsupported file type {ext!r} for {p.name}")


def _extract_pdf(p: Path) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as e:  # pragma: no cover - env-dependent
        raise RuntimeError("PDF extraction needs PyMuPDF (pip install pymupdf)") from e
    doc = fitz.open(str(p))
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _extract_docx(p: Path) -> str:
    try:
        import docx
    except ImportError as e:  # pragma: no cover - env-dependent
        raise RuntimeError("DOCX extraction needs python-docx (pip install python-docx)") from e
    d = docx.Document(str(p))
    return "\n".join(par.text for par in d.paragraphs)


def _extract_html(p: Path) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:  # pragma: no cover - env-dependent
        raise RuntimeError("HTML extraction needs beautifulsoup4") from e
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    return soup.get_text(separator="\n")


def _extract_epub(p: Path) -> str:
    """EPUB = zip of XHTML chapters. Reading order comes from the OPF spine
    (container.xml -> rootfile -> manifest+spine); a book whose chapters are
    concatenated by filename is a broken book. Imperfect EPUBs (missing or
    malformed container/OPF) degrade to every XHTML in the archive sorted by
    name — readable-but-rough beats an exception on real-world files.
    """
    import posixpath
    import zipfile
    from xml.etree import ElementTree

    try:
        from bs4 import BeautifulSoup
    except ImportError as e:  # pragma: no cover - env-dependent
        raise RuntimeError("EPUB extraction needs beautifulsoup4") from e

    if not zipfile.is_zipfile(p):
        raise ValueError(f"not a valid EPUB (zip) archive: {p.name}")

    with zipfile.ZipFile(p) as z:
        names = set(z.namelist())

        def safe_xml(name: str, max_bytes: int = 5_000_000) -> bytes:
            """XXE / billion-laughs guard for stdlib ElementTree: legitimate
            EPUB container/OPF files carry no DTD, so any DOCTYPE/ENTITY (the
            only way to declare expanding entities) means hostile or broken
            input -> refuse, which routes extraction to the non-XML fallback.
            Size cap for the same reason: real OPFs are kilobytes."""
            with z.open(name) as fh:
                raw = fh.read(max_bytes + 1)  # bound i BYTE DECOMPRESSI (bomb)
            if len(raw) > max_bytes:
                raise ValueError(f"suspiciously large XML in EPUB: {name}")
            head = raw[:65536].upper()
            if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
                raise ValueError(f"DTD not allowed in EPUB metadata: {name}")
            return raw

        def spine_docs() -> list[str]:
            container = ElementTree.fromstring(safe_xml("META-INF/container.xml"))
            opf_path = next(
                el.get("full-path")
                for el in container.iter()
                if el.tag.endswith("rootfile") and el.get("full-path"))
            opf = ElementTree.fromstring(safe_xml(opf_path))
            hrefs = {el.get("id"): el.get("href") for el in opf.iter()
                     if el.tag.endswith("item")}
            base = posixpath.dirname(opf_path)
            docs = []
            for ref in opf.iter():
                if ref.tag.endswith("itemref"):
                    href = hrefs.get(ref.get("idref"))
                    if href:
                        # review 2026-07-09 (A1): manifest hrefs are URI
                        # references — 'Chapter%20one.xhtml' names the zip
                        # member 'Chapter one.xhtml' (Sigil/Calibre/InDesign
                        # percent-encode). Without unquote the chapter is
                        # silently dropped in the mixed case.
                        from urllib.parse import unquote
                        full = posixpath.normpath(
                            posixpath.join(base, unquote(href)))
                        if full in names:
                            docs.append(full)
            return docs

        try:
            docs = spine_docs()
        except Exception:
            docs = []
        if not docs:  # fallback: every markup file, name order (.xml too —
            # review A3: some EPUBs ship content documents as .xml)
            docs = sorted(n for n in names
                          if n.lower().endswith(
                              (".xhtml", ".html", ".htm", ".xml"))
                          and not n.lower().endswith("container.xml")
                          and not n.lower().endswith(".opf"))
        parts = []
        total = 0
        for name in docs:
            if total >= _MAX_TOTAL_BYTES:
                _LOG.warning(
                    "EPUB %s hit the %d-byte extraction budget — remaining "
                    "chapters skipped (zip-bomb guard)", p.name, _MAX_TOTAL_BYTES)
                break
            # z.open(...).read(cap+1) limita i BYTE DECOMPRESSI: un capitolo
            # ostile ad alta compressione non puo' esaurire la RAM.
            with z.open(name) as fh:
                raw = fh.read(_MAX_MEMBER_BYTES + 1)
            if len(raw) > _MAX_MEMBER_BYTES:
                _LOG.warning(
                    "EPUB member %s exceeds %d bytes — truncated (zip-bomb guard)",
                    name, _MAX_MEMBER_BYTES)
                raw = raw[:_MAX_MEMBER_BYTES]
            total += len(raw)
            soup = BeautifulSoup(raw.decode("utf-8", errors="replace"),
                                 "html.parser")
            parts.append(soup.get_text(separator="\n"))
        return "\n".join(parts)


__all__ = ["extract_text"]
