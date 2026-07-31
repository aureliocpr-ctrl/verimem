"""Una citazione da un documento dice quante parole della query contiene.

Misurato il 2026-07-31 sul README del prodotto (29.338 caratteri, 47 chunk),
via `hippo_document_semantic_search`::

    atteso     top score  query
    C'E'           0.810  come funziona l'admission gate
    C'E'           0.830  abstention
    NON C'E'       0.789  quale versione di Kubernetes usa il cluster
    NON C'E'       0.754  ricetta della carbonara con guanciale
    NON C'E'       0.767  orari dei treni per Bologna

«Ricetta della carbonara» prende 0.754 su un README che parla di memoria
verificata per agenti, e torna con la citazione ESATTA — file, versione,
offset. Per un umano è un risultato strano; per un agente, che è il consumatore
vero di questo tool, è una fonte con provenienza: la citazione precisa dà
autorevolezza proprio a ciò che non c'entra. Il README promette «abstention by
design», e sui documenti non succedeva niente del genere.

UNA SOGLIA SUL PUNTEGGIO NON FUNZIONA, ed è stata provata e buttata lo stesso
giorno. Il rumore stimato dell'indice — il quantile dei massimi di sonde
scramblate, la misura che il prodotto già usa sui fatti — viene **0.8706**:
più alto di TUTTE le query, comprese quelle con risposta (0.810-0.830). Marcava
tutto, cioè niente. È lo stesso errore commesso e ritirato dodici ore prima
sulla mappa dell'ignoranza: quel numero è alto per costruzione e non è «il
livello sotto cui non c'è informazione».

Il conteggio lessicale invece separa, sulla stessa prova::

    con risposta   copertura 0.33 · 0.50 · 1.00 · 1.00 · 1.00
    estranee       copertura 0.00 · 0.00 · 0.00 · 0.33

E soprattutto non giudica: CONTA. «Zero delle tue parole compaiono nel testo
che ti sto citando» è un fatto che il lettore verifica da sé, non un verdetto
con dentro una soglia inventata. Chi consuma decide cosa farne — un agente può
chiedere conferma, un umano può ignorarlo.
"""
from __future__ import annotations

import pytest

from verimem.document_index import _termini_di_ricerca


def test_le_parole_vuote_non_contano_come_pertinenza():
    """«come funziona il gate» deve pesare su `gate`, non su `come`: altrimenti
    ogni query in italiano risulterebbe coperta da qualsiasi testo italiano."""
    assert _termini_di_ricerca("come funziona l'admission gate") == [
        "admission", "gate"]
    assert _termini_di_ricerca("what is the quarantine") == ["quarantine"]


def test_una_query_di_sole_parole_vuote_non_produce_termini():
    assert _termini_di_ricerca("come si fa") == []
    assert _termini_di_ricerca("") == []


@pytest.fixture()
def indice(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.document_index import DocumentIndex

    doc = tmp_path / "manuale.md"
    doc.write_text("\n".join(
        f"## Sezione {i}\nLa pratica {i} si archivia entro {i+2} giorni "
        f"presso l'ufficio protocollo comunale." for i in range(30)),
        encoding="utf-8")
    idx = DocumentIndex()
    idx.index_file(doc)
    return idx


def test_un_hit_dice_quante_parole_della_query_contiene(indice):
    hits = indice.search("pratica archiviata ufficio protocollo", k=1)
    assert hits, "nessun risultato su una query pertinente"
    h = hits[0]
    assert "query_terms" in h and "query_terms_matched" in h, sorted(h)
    assert h["query_terms"] > 0
    assert h["query_terms_matched"] >= 1, h


def test_una_query_ESTRANEA_torna_con_zero_termini(indice):
    """Il caso misurato: il documento parla di pratiche e protocollo comunale,
    la domanda di tutt'altro. Il risultato arriva lo stesso — ma dichiara di
    non contenere nessuna delle parole cercate."""
    hits = indice.search("ricetta della carbonara con guanciale", k=1)
    assert hits, "la ricerca non restituisce nulla: qui si MARCA, non si taglia"
    assert hits[0]["query_terms_matched"] == 0, hits[0]
    assert hits[0]["query_terms"] == 3, hits[0]


def test_il_conteggio_non_dipende_dalle_maiuscole(indice):
    a = indice.search("PROTOCOLLO", k=1)[0]
    b = indice.search("protocollo", k=1)[0]
    assert a["query_terms_matched"] == b["query_terms_matched"] == 1


def test_i_campi_esistenti_non_si_spostano(indice):
    """La citazione e la sua provenienza restano quelle: chi legge il tool oggi
    non deve accorgersi di nulla, oltre ai due campi in piu'."""
    h = indice.search("pratica protocollo", k=1)[0]
    for campo in ("text", "score", "source_id", "version", "start", "end",
                  "uri", "doc_id", "flagged", "indexed_by"):
        assert campo in h, campo
    testo_originale = (indice.db_path.parent / "manuale.md")
    if testo_originale.exists():
        contenuto = testo_originale.read_text(encoding="utf-8")
        assert contenuto[h["start"]:h["end"]] == h["text"], (
            "l'offset non riporta piu' al testo esatto: e' la promessa del tool")
