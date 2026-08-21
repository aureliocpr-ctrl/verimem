"""Quante capacità dell'SDK non hanno una porta, e il numero non deve crescere.

Quattro volte in un giorno lo stesso difetto: una capacità matura, completa e
testata, raggiungibile solo dal canale che l'ha vista nascere.

    recall --as-of      il time-travel viveva su MCP e SDK (curato il 31/07)
    facts correct       supersede viveva su MCP e SDK — e il suo docstring
                        dice «e' la seconda occorrenza in un giorno della
                        stessa classe, il che la rende una classe»
    purge_history       la cancellazione GDPR viveva SOLO sull'SDK
    deep/with_history   tre modi di `search` che la CLI non sapeva chiedere

Ogni volta la cura e' stata puntuale e ogni volta ne e' saltata fuori
un'altra. Questo file smette di curarle una per una e mette un CRICCHETTO
sulla classe: conta i metodi pubblici di `Memory` che non compaiono ne' nella
CLI ne' nel server MCP, e pretende che il numero non aumenti.

E' BIDIREZIONALE, come il censimento dei verdetti: fallisce se qualcuno
aggiunge una capacita' senza porta, E fallisce se qualcuno ne apre una senza
abbassare la costante — un elenco che si aggiorna solo quando peggiora non
presidia niente.

IL CRITERIO E' GROSSOLANO PER SCELTA. Cerca il NOME del metodo nei due file,
quindi conta come «esposta» anche una capacita' che appare per caso in un
commento. Sbaglia dalla parte di chi non allarma: un difetto vero che passa
inosservato e' peggio di un allarme che non scatta, e questo cricchetto serve
a fermare la CRESCITA, non a certificare la copertura.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from verimem.client import Memory

#: Misurato il 2026-08-02. Chi apre una porta ABBASSA questo numero nello
#: stesso commit; chi ne aggiunge una senza porta lo vede salire e deve
#: decidere se e' una scelta o una dimenticanza.
#:
#: E' un TETTO, non un'uguaglianza, e la ragione e' una misura: in locale il
#: conteggio e' 11 e in CI 10. `dir(Memory)` non e' identico ovunque — un
#: metodo definito dietro un import opzionale c'e' su una macchina e non
#: sull'altra — quindi pretendere il numero esatto rende il cricchetto rosso
#: per l'AMBIENTE invece che per un difetto. Il verso che conta e' uno solo:
#: che non CRESCA.
#:
#: ALZATA 11 -> 12 il 2026-08-21, e la ragione va letta prima di crederla una
#: resa. `7060f9b7` ha aggiunto al SDK `documents` / `index_document` /
#: `search_documents`, e il conteggio e' salito. Ma la porta per l'utente
#: ESISTE gia': `verimem index` (cli.py:633) e `verimem search-docs`
#: (cli.py:671), eseguiti e funzionanti. Il NOME del metodo SDK non compare in
#: `cli.py` perche' la CLI passa da `DocumentIndex()`.
#:
#: ⚠️ CORREZIONE 21/08 14:39, e la ragione che avevo scritto qui era SBAGLIATA.
#: Avevo misurato che i due percorsi usavano db diversi e ne avevo concluso che
#: fosse «di proposito», citando il docstring di `Memory.documents` («senza
#: questo, una `Memory(tmp_path)` in un test scriverebbe nell'indice VERO»).
#: Tredici minuti dopo `8bb2a27c` ha tolto quel `db_path` esplicito — «l'SDK
#: indicizzava i documenti in uno store che nessun'altra porta legge» — e ora i
#: due percorsi COINCIDONO (riverificato). ⇒ Quella non era una separazione
#: voluta: era un difetto, e il docstring che citavo come prova di
#: intenzionalita' ne era la giustificazione.
#: 🔑 Un docstring dice cosa l'autore CREDEVA, non cosa il codice deve fare.
#:
#: Il conteggio resta 12 perche' dipende dai NOMI presenti in `cli.py`, che
#: `8bb2a27c` non ha cambiato: la porta utente esiste (`verimem index`,
#: `verimem search-docs`) e il nome del metodo SDK non vi compare. Resta quindi
#: il caso previsto dal messaggio d'errore — «o le apri una porta, o alzi la
#: costante dichiarando che e' una scelta» — ma per una ragione piu' semplice
#: di quella che avevo scritto: i due chiamano la stessa cosa con nomi diversi.
#:
#: ⇒ Qui il criterio grossolano di questo cricchetto (cerca il nome nel testo)
#: e la cosa vera divergono: la capacita' E' raggiungibile, il nome no. E' il
#: caso che il messaggio d'errore prevede — «o le apri una porta, o alzi la
#: costante dichiarando che e' una scelta» — e questa e' la dichiarazione.
SENZA_PORTA_NOTE = 12

#: E PER SUPERFICIE, che è la domanda vera. Misurato il 2026-08-02: erano 14
#: su `cli.py` e 14 su `mcp_server.py`, contro le 10 che mancano a entrambe.
#: Contare solo l'unione nascondeva proprio la classe che questo file
#: sorveglia — una capacità che vive su un canale solo.
#: `cli.py` scende a 13 con l'apertura di `verimem ask` nello stesso commit
#: che ha corretto il conteggio: è il verso in cui questo numero deve
#: muoversi.
#: ALZATE +1 ciascuna il 2026-08-21, stessa ragione della costante qui sopra:
#: i tre metodi documenti di `7060f9b7` hanno una porta utente (`verimem index`,
#: `verimem search-docs`) che passa da un DB diverso di proposito, quindi il
#: nome del metodo SDK non compare in nessuna delle due superfici.
#: Misurato: cli.py 14, mcp_server.py 15, unione 12.
SENZA_PORTA_PER_SUPERFICIE = {"cli.py": 14, "mcp_server.py": 15}

#: Di quanto puo' scendere prima che valga la pena riallineare la costante.
#: Sotto questa distanza il calo puo' essere ambientale; oltre, qualcuno ha
#: aperto delle porte e il numero qui sopra non racconta piu' lo stato di
#: oggi.
_SCARTO_AMBIENTALE = 3

_RADICE = pathlib.Path(__file__).resolve().parents[1] / "verimem"


def _superficie(nome: str) -> str:
    return (_RADICE / nome).read_text(encoding="utf-8", errors="ignore")


def _senza_porta(dove: str | None = None) -> list[str]:
    """Le capacita' senza porta. `dove=None` = senza porta su NESSUNA delle
    due superfici; `dove="cli.py"` = senza porta su quella.

    LA PRIMA STESURA CONCATENAVA I DUE FILE, e bastava comparire in UNO dei
    due per contare come esposta. Cosi' il cricchetto vedeva 10 capacita'
    scoperte mentre PER SUPERFICIE sono 18 — quattro senza porta CLI (`ask`,
    `audit_log`, `epistemic_health`, `quarantine_log`) e quattro senza MCP.
    Un cricchetto nato per la classe «una capacita' raggiungibile solo dal
    canale che l'ha vista nascere» che non distingueva i canali: e' il difetto
    che sorveglia, dentro sé stesso.

    Trovato dall'altra istanza, con un caso concreto che pesa: `Memory.ask` e'
    il router di intento — le domande di cardinalita' vanno a uno SCAN perche'
    il top-k sottoconta — e senza porta CLI `verimem` risponde 5 dove il vero
    e' 205.
    """
    testi = ([_superficie(dove)] if dove
             else [_superficie(n) for n in ("cli.py", "mcp_server.py")])
    return sorted(
        m for m in dir(Memory)
        if not m.startswith("_")
        and all(not re.search(rf"\b{re.escape(m)}\b", t) for t in testi))


def test_le_capacita_senza_porta_non_aumentano():
    mancanti = _senza_porta()
    assert len(mancanti) <= SENZA_PORTA_NOTE, (
        f"{len(mancanti)} capacita' dell'SDK non hanno una porta su CLI/MCP, "
        f"erano {SENZA_PORTA_NOTE}. Le nuove sono fra queste:\n  "
        + "\n  ".join(mancanti)
        + "\nUna capacita' raggiungibile solo dal canale che l'ha vista "
          "nascere e' il difetto che questa serie di commit chiude da un "
          "giorno: o le apri una porta, o alzi la costante dichiarando che "
          "e' una scelta.")


def test_se_ne_apri_TANTE_abbassi_il_numero():
    """Il verso opposto: un elenco che si aggiorna solo quando peggiora non
    presidia niente.

    Con uno SCARTO, e non a uguaglianza. La prima stesura pretendeva il numero
    esatto ed e' caduta in CI: 11 in locale, 10 li'. `dir(Memory)` non e'
    identico ovunque — un metodo dietro un import opzionale c'e' su una
    macchina e non sull'altra — quindi l'uguaglianza rende il cricchetto rosso
    per l'ambiente invece che per un difetto, ed e' la peggiore specie di
    presidio: quello che si impara a ignorare.
    """
    mancanti = _senza_porta()
    assert len(mancanti) >= SENZA_PORTA_NOTE - _SCARTO_AMBIENTALE, (
        f"ora sono {len(mancanti)} e la costante dice {SENZA_PORTA_NOTE}: "
        f"hai aperto piu' di {_SCARTO_AMBIENTALE} porte senza aggiornarla. "
        f"Portala a {len(mancanti)}.\nRestano senza:\n  "
        + "\n  ".join(mancanti))


@pytest.mark.parametrize("superficie", sorted(SENZA_PORTA_PER_SUPERFICIE))
def test_nessuna_superficie_perde_terreno(superficie):
    """La domanda vera è PER CANALE, non sull'unione.

    Una capacità che vive solo su MCP è esattamente il difetto che questo
    file sorveglia — «raggiungibile solo dal canale che l'ha vista nascere» —
    e contando l'unione risultava coperta. Il caso che l'ha mostrato:
    `Memory.ask`, il router di intento, senza porta CLI, con `verimem` che
    risponde 5 dove il vero è 205.
    """
    mancanti = _senza_porta(superficie)
    atteso = SENZA_PORTA_PER_SUPERFICIE[superficie]
    assert len(mancanti) <= atteso, (
        f"{superficie}: {len(mancanti)} capacità senza porta, erano {atteso}. "
        f"Le nuove sono fra queste:\n  " + "\n  ".join(mancanti))


def test_il_criterio_vede_davvero_qualcosa():
    """Un cricchetto che conta zero su tutto sarebbe verde per sempre: qui si
    verifica che il metodo piu' esposto del prodotto risulti ESPOSTO e che
    l'insieme misurato non sia ne' vuoto ne' l'intero SDK."""
    mancanti = set(_senza_porta())
    pubblici = {m for m in dir(Memory) if not m.startswith("_")}
    assert "add" not in mancanti and "search" not in mancanti, sorted(mancanti)
    assert 0 < len(mancanti) < len(pubblici), (
        f"{len(mancanti)} su {len(pubblici)}: il criterio non sta misurando")
