"""L'anteprima di `search-docs` deve mostrare la RIGA che risponde, non l'inizio
del chunk.

Il commento sopra `verimem/cli.py:865` dichiara l'intenzione — «*Snippet centered
on the first query term present — show WHY it matched, not just how the chunk
begins*» — e il codice fa l'opposto ogni volta che la query contiene una
preposizione, cioe' quasi sempre in italiano e in inglese.

MISURATO il 2026-08-28 (ws6), store temporaneo, fuori pytest, porta CLI: su un
chunk di 968 caratteri con la risposta negli ultimi 39, `search-docs "Quanti
pallet contiene la sede di Bolzano?"` restituisce il chunk giusto (0.861) ma
`grep -c Bolzano` sull'output intero da' **0**. La causa e' `min()` sulla
posizione: vince `di` a 13 (dentro «di riempimento») contro `sede` a 931.

LA CAUSA PROFONDA NON E' `min()`, E' UNA GIUNTURA. Il recupero normalizza la
query con `_termini_di_ricerca()` — minuscole, via la punteggiatura, via le
elisioni, via le parole vuote, via i token sotto i 3 caratteri — e la stampa
ricalcola a mano con `query.lower().split()`. Due normalizzazioni diverse per la
stessa query dentro lo stesso comando: l'anteprima si ancora a una parola che il
recupero aveva GIA' scartato. Prova indipendente che sono la stessa cosa: il
campo `query_terms` che l'SDK restituisce vale 5, ed e' esattamente
`len(_termini_di_ricerca(q))`, mentre lo split grezzo ne da' 7.

LA PORTA CONTA: l'SDK (`Memory.search_documents`) rende il campo `text` INTERO,
967 caratteri, con la risposta dentro. Il difetto e' della STAMPA, non del
recupero — chi usa l'SDK non lo vede.

Popolazione di controllo inclusa: una query estranea al documento non deve
cominciare a mostrare la riga di Bolzano solo perche' la finestra si e' spostata.
"""
from __future__ import annotations

import math
import re

import pytest
from typer.testing import CliRunner

import verimem.document_index as di
from verimem.cli import app

runner = CliRunner()

RISPOSTA = "La sede di Bolzano contiene 777 pallet."


class _FakeEmbedder:
    """Stesso embedder finto degli altri test di questo tier: qui non si misura
    un coseno, si misura CHE COSA VIENE STAMPATO, quindi lo stub non tocca la
    domanda."""

    DIM = 32

    def encode(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.DIM
            for tok in re.findall(r"[a-z0-9]+", (t or "").lower()):
                v[hash(tok) % self.DIM] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    monkeypatch.setenv("HIPPO_DOCINDEX_DB", str(tmp_path / "docidx.db"))
    monkeypatch.setattr(di, "_DefaultEmbedder", _FakeEmbedder)


def _documento(tmp_path):
    """La risposta negli ULTIMI caratteri di un chunk lungo: il caso in cui
    l'inizio del chunk non dice nulla di utile."""
    f = tmp_path / "inventario.txt"
    f.write_text("Testo neutro di riempimento. " * 32 + RISPOSTA, encoding="utf-8")
    r = runner.invoke(app, ["index", str(f)])
    assert r.exit_code == 0, r.output
    return f


def test_l_anteprima_contiene_la_riga_che_risponde(tmp_path):
    """IL PRESIDIO. La parola cercata deve comparire in cio' che l'utente vede."""
    _documento(tmp_path)
    r = runner.invoke(app, ["search-docs", "Quanti pallet contiene la sede di Bolzano?"])
    assert r.exit_code == 0, r.output
    assert "Bolzano" in r.output, (
        "l'anteprima non mostra la riga che risponde alla domanda; "
        f"output:\n{r.output}")


def test_una_query_estranea_non_mostra_quella_riga(tmp_path):
    """POPOLAZIONE DI CONTROLLO. Senza, il presidio sopra sarebbe soddisfatto
    anche da un'anteprima che mostra sempre tutto: il numero cambierebbe per la
    ragione sbagliata."""
    _documento(tmp_path)
    r = runner.invoke(app, ["search-docs", "Qual e' il fatturato della societa'?"])
    assert r.exit_code == 0, r.output
    assert "Bolzano" not in r.output, (
        "una query che non c'entra mostra la riga di Bolzano: la finestra non "
        f"sta seguendo i termini della query; output:\n{r.output}")


def test_la_stampa_e_il_recupero_normalizzano_la_query_ALLO_STESSO_MODO():
    """LA GIUNTURA, misurata direttamente. Se un giorno la stampa tornasse a
    splittare la query a mano, questo test lo dice PRIMA che l'anteprima si
    rompa — e lo dice nominando la causa, non il sintomo."""
    q = "Quanti pallet contiene la sede di Bolzano?"
    curati = di._termini_di_ricerca(q)
    assert "di" not in curati, "la parola vuota non deve essere un termine di ancoraggio"
    assert "bolzano" in curati, "il nome proprio deve sopravvivere alla punteggiatura"
    assert "bolzano?" not in curati
    assert len(curati) == 5, curati


RISPOSTA_EN = "The Bolzano site contains 777 pallets."


def _documento_inglese(tmp_path):
    f = tmp_path / "inventory.txt"
    f.write_text("Neutral filler text of the document. " * 26 + RISPOSTA_EN,
                 encoding="utf-8")
    r = runner.invoke(app, ["index", str(f)])
    assert r.exit_code == 0, r.output
    return f


def test_l_anteprima_mostra_la_riga_anche_in_inglese(tmp_path):
    """LE DUE LINGUE CHE AURELIO HA NOMINATO. La cura poggia su
    `_PAROLE_VUOTE`, e una lista di parole vuote e' il posto classico dove un
    prodotto smette di essere bilingue senza che nessuno se ne accorga —
    e' successo su `_COPULA_RE` e sulle stoplist di `query_intent`.

    Qui la lista REGGE: 94 voci, e le inglesi ci sono (`the`, `of`, `and`,
    `to`, `in`, `for`, `how`, `does`, `is`, `are`, `what`, `which`, `with`).
    Misurato il 2026-08-28 sulla query «How many pallets does the Bolzano site
    contain?»: con lo split grezzo la finestra partiva da 0 (vinceva `the` a 23)
    e la risposta non si vedeva; con la cura parte da 876 e si vede.

    Il test non serve a dire che oggi funziona — quello l'ho misurato. Serve a
    fare RUMORE il giorno in cui qualcuno tocca `_PAROLE_VUOTE` pensando solo
    all'italiano."""
    _documento_inglese(tmp_path)
    r = runner.invoke(app, ["search-docs", "How many pallets does the Bolzano site contain?"])
    assert r.exit_code == 0, r.output
    assert "Bolzano" in r.output, (
        "l'anteprima non mostra la riga che risponde a una domanda INGLESE; "
        f"output:\n{r.output}")


def test_le_parole_vuote_coprono_entrambe_le_lingue():
    """LA CAUSA, NON IL SINTOMO — gemello del test sulla giuntura. Se un giorno
    `_PAROLE_VUOTE` perdesse l'inglese, questo lo dice nominando la lista,
    mentre il test sopra direbbe solo che un'anteprima non mostra una riga."""
    inglesi = {"the", "and", "of", "in", "to", "a", "for", "how", "does",
               "is", "are", "what", "which", "with"}
    mancanti = inglesi - di._PAROLE_VUOTE
    assert not mancanti, f"parole vuote inglesi assenti: {sorted(mancanti)}"
    italiane = {"il", "la", "di", "che", "per", "con", "una", "sono"}
    mancanti_it = italiane - di._PAROLE_VUOTE
    assert not mancanti_it, f"parole vuote italiane assenti: {sorted(mancanti_it)}"
