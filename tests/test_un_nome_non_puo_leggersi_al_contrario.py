"""Un nome nel rapporto si legge come e' scritto.

Trovato nell'audit log di produzione il 2026-07-30, riga dell'8 giugno::

    grezzo    : 'hippo_\\u202estatus'
    codepoint : U+202E RIGHT-TO-LEFT OVERRIDE
    outcome=unknown_tool  args_hash=44136fa355b3678a

Il server si e' DIFESO — ha risposto `unknown_tool`, il tool non esiste e non e'
stato eseguito nulla. Quello che resta e' un problema di LETTURA: U+202E inverte
la direzione del testo che segue, quindi chi scorre il rapporto a occhio vede un
nome e il log ne contiene un altro. E' la tecnica «Trojan Source» applicata a un
registro invece che al codice sorgente.

Contano tutti e due i lati:

* il DATO resta grezzo — un audit log e' evidenza, e riscriverlo perderebbe
  esattamente cio' che uno vorrebbe poter dimostrare;
* la VISUALIZZAZIONE lo neutralizza, mostrando l'escape al posto del carattere.

Un punto solo che sanifica, come `fact_payload` per i fatti: due copie
divergono, e in questo repo l'hanno gia' fatto.

I caratteri qui sotto si scrivono ESCAPED e non letterali: la prima stesura di
questo file conteneva un NUL vero e non veniva nemmeno parsata dall'interprete.
"""
from __future__ import annotations

import pytest

from verimem.telemetry_analyzer import nome_leggibile

RLO = "‮"


def test_il_carattere_che_inverte_il_testo_non_arriva_allo_schermo():
    assert RLO not in nome_leggibile(f"hippo_{RLO}status")


def test_si_vede_CHE_c_era_qualcosa_invece_di_sparire():
    """Cancellarlo in silenzio nasconde il tentativo: chi legge deve poter
    vedere che quel nome conteneva un carattere di controllo."""
    fuori = nome_leggibile(f"hippo_{RLO}status")
    assert "202e" in fuori.lower(), fuori
    assert "hippo_" in fuori and "status" in fuori, fuori


@pytest.mark.parametrize("cp", [
    "‪", "‫", "‬", "‭", "‮",   # embedding / override
    "⁦", "⁧", "⁨", "⁩",             # isolate
    "​", "‎", "‏", "­",             # zero-width / marks
    "\x00", "\x1b", "\r", "\n",                         # NUL, ESC, a capo
])
def test_tutta_la_famiglia_non_solo_il_caso_trovato(cp):
    """Curare il solo U+202E sarebbe la blocklist che enumera cio' che qualcuno
    ha immaginato — la classe di difetto dominante del critic-orchestrator, dove
    la cura e' sempre invertire in allowlist. Il ritorno a capo e' della
    partita: in un rapporto a righe, un `\\n` dentro un nome fabbrica una riga
    che sembra un'altra voce."""
    assert cp not in nome_leggibile(f"a{cp}b")


def test_un_nome_normale_non_viene_toccato():
    assert nome_leggibile("hippo_facts_recall") == "hippo_facts_recall"
    assert nome_leggibile("") == ""


def test_non_esplode_su_cio_che_non_e_una_stringa():
    """Il campo arriva da un JSONL che puo' contenere qualunque cosa: il
    rapporto deve reggere un `tool` numerico o assente."""
    assert nome_leggibile(None) == ""
    assert nome_leggibile(123) == "123"
