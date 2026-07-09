"""EPUB extraction: i LIBRI entrano nel document RAG (specialità scrittore/studioso).

Un EPUB è uno zip: ``META-INF/container.xml`` punta all'OPF, l'OPF dichiara
manifest (id→file) e spine (ORDINE di lettura). L'estrattore deve rispettare
la spine — un libro letto coi capitoli in ordine alfabetico dei filename è
un libro rotto — e degradare con garbo sugli EPUB imperfetti (fallback: tutti
gli XHTML dello zip in ordine di nome). Zero dipendenze nuove: zipfile +
xml.etree (stdlib) + BeautifulSoup (già richiesto per .html).
"""
from __future__ import annotations

import zipfile

import pytest

from engram.file_extract import extract_text

_CONTAINER = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

# spine in ordine INVERSO rispetto ai filename: prova che seguiamo la spine
_OPF = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test Book</dc:title>
  </metadata>
  <manifest>
    <item id="late" href="a_second.xhtml" media-type="application/xhtml+xml"/>
    <item id="early" href="z_first.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="early"/>
    <itemref idref="late"/>
  </spine>
</package>"""

_CH1 = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1>Chapter One</h1><p>Call me Ishmael.</p></body></html>"""

_CH2 = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1>Chapter Two</h1><p>The voyage begins.</p></body></html>"""


def _build_epub(path, *, with_container: bool = True) -> None:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        if with_container:
            z.writestr("META-INF/container.xml", _CONTAINER)
            z.writestr("OEBPS/content.opf", _OPF)
        z.writestr("OEBPS/z_first.xhtml", _CH1)
        z.writestr("OEBPS/a_second.xhtml", _CH2)


def test_epub_extracts_text_in_spine_order(tmp_path):
    book = tmp_path / "book.epub"
    _build_epub(book)
    text = extract_text(book)
    assert "Call me Ishmael." in text and "The voyage begins." in text
    assert "<p>" not in text and "<h1>" not in text, "markup strippato"
    assert text.index("Call me Ishmael.") < text.index("The voyage begins."), (
        "l'ordine è la SPINE (z_first prima di a_second), non l'alfabeto"
    )


def test_epub_without_opf_falls_back_to_zip_scan(tmp_path):
    """EPUB imperfetto (niente container/OPF): degrada a tutti gli XHTML in
    ordine di nome invece di fallire — un libro leggibile male batte zero."""
    book = tmp_path / "rough.epub"
    _build_epub(book, with_container=False)
    text = extract_text(book)
    assert "Call me Ishmael." in text and "The voyage begins." in text


def test_epub_with_doctype_xml_is_not_parsed_as_xml(tmp_path):
    """Sicurezza (XXE / billion-laughs): container/OPF con DTD non vengono MAI
    passati al parser XML stdlib — EPUB legittimi non hanno DOCTYPE, quindi
    input col DOCTYPE va dritto al fallback zip-scan (che non espande entità).
    Il libro resta leggibile, il parser resta chiuso."""
    book = tmp_path / "evil.epub"
    evil_container = (
        '<?xml version="1.0"?><!DOCTYPE c [<!ENTITY a "boom">]>'
        '<container><rootfiles><rootfile full-path="OEBPS/content.opf"/>'
        "</rootfiles></container>")
    with zipfile.ZipFile(book, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", evil_container)
        z.writestr("OEBPS/content.opf", _OPF)
        z.writestr("OEBPS/z_first.xhtml", _CH1)
        z.writestr("OEBPS/a_second.xhtml", _CH2)
    text = extract_text(book)
    assert "Call me Ishmael." in text, "fallback: il libro si estrae comunque"
    assert "boom" not in text, "l'entity non è mai stata espansa"


def test_epub_that_is_not_a_zip_raises_clearly(tmp_path):
    fake = tmp_path / "fake.epub"
    fake.write_bytes(b"this is not a zip archive")
    with pytest.raises(ValueError, match="EPUB"):
        extract_text(fake)


def test_unsupported_extension_error_unchanged(tmp_path):
    """Regressione: le estensioni ignote continuano a dare il ValueError chiaro."""
    weird = tmp_path / "notes.xyz"
    weird.write_text("hello")
    with pytest.raises(ValueError, match="unsupported"):
        extract_text(weird)
