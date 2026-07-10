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


def test_epub_percent_encoded_href_still_resolves(tmp_path):
    """Adversarial review 2026-07-09 (A1): negli EPUB reali l'href del
    manifest è una URI reference — 'Chapter%20one.xhtml' punta al membro zip
    'Chapter one.xhtml'. Senza unquote il capitolo si perde IN SILENZIO nel
    caso misto (alcuni href ascii risolvono, quello encoded no -> niente
    fallback). Sigil/Calibre/InDesign producono esattamente questo."""
    opf = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <manifest>
    <item id="c1" href="Chapter%20one.xhtml" media-type="application/xhtml+xml"/>
    <item id="c2" href="plain.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="c1"/><itemref idref="c2"/></spine>
</package>"""
    book = tmp_path / "encoded.epub"
    with zipfile.ZipFile(book, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", _CONTAINER)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/Chapter one.xhtml", _CH1)   # spazio nel nome reale
        z.writestr("OEBPS/plain.xhtml", _CH2)
    text = extract_text(book)
    assert "Call me Ishmael." in text, "capitolo con href %20 perso"
    assert "The voyage begins." in text
    assert text.index("Call me Ishmael.") < text.index("The voyage begins.")


def test_epub_fallback_includes_xml_content_documents(tmp_path):
    """Review A3: EPUB imperfetto con capitoli .xml — il fallback deve
    includerli, non ritornare stringa vuota."""
    book = tmp_path / "xmlbook.epub"
    with zipfile.ZipFile(book, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("OEBPS/ch1.xml", _CH1)  # niente container/OPF -> fallback
    assert "Call me Ishmael." in extract_text(book)


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


def test_epub_content_chapter_zip_bomb_is_capped(tmp_path, monkeypatch):
    """Sicurezza (zip-bomb, audit E1 2026-07-11): un capitolo-CONTENUTO ostile
    ad alta compressione NON deve decomprimere illimitato in RAM. safe_xml
    cappa i METADATI (container/OPF); questo cappa il contenuto. PoC pre-fix:
    un EPUB da 38KB produceva 40MB estratti (ratio 1025x, peak heap 129MB) —
    un file da pochi MB avrebbe esaurito la RAM (OOM del gateway condiviso)."""
    import engram.file_extract as fe
    monkeypatch.setattr(fe, "_MAX_MEMBER_BYTES", 500_000)
    monkeypatch.setattr(fe, "_MAX_TOTAL_BYTES", 2_000_000)
    book = tmp_path / "bomb.epub"
    payload = "<html><body>" + "A" * 3_000_000 + "</body></html>"  # 3MB > 0.5MB cap
    with zipfile.ZipFile(book, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("OEBPS/bomb.xhtml", payload)  # no container -> fallback -> read
    text = extract_text(book)
    assert len(text) <= fe._MAX_MEMBER_BYTES + 1000, (
        "il capitolo ostile va troncato dal cap, non decompresso intero")


def test_epub_zip_bomb_total_budget_stops_many_chapters(tmp_path, monkeypatch):
    """Anche molti capitoli sotto il per-member cap non devono sommarsi oltre il
    budget totale (bomb 'a tanti file')."""
    import engram.file_extract as fe
    monkeypatch.setattr(fe, "_MAX_MEMBER_BYTES", 300_000)
    monkeypatch.setattr(fe, "_MAX_TOTAL_BYTES", 1_000_000)
    book = tmp_path / "many.epub"
    chapter = "<html><body>" + "B" * 250_000 + "</body></html>"
    with zipfile.ZipFile(book, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/epub+zip")
        for i in range(50):  # 50 * 250KB = 12.5MB potenziali
            z.writestr(f"OEBPS/ch{i:02d}.xhtml", chapter)
    text = extract_text(book)
    assert len(text) <= fe._MAX_TOTAL_BYTES + 300_000, (
        "il budget totale deve fermare l'accumulo oltre il tetto")


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
