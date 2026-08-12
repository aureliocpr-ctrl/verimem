"""La promessa era curata in un posto e intatta in altri quattro.

⚠️ QUESTO FILE NASCE DA UNA VERIFICA ESTERNA, non da una diagnosi mia. ws6 ha
chiuso «exact citations» in `verimem/agent_guide.py` (commit `870f5d80`) e ha
fatto la cosa giusta nel modo giusto: il suo test non controlla solo il
comportamento, controlla **il testo del contratto** — è il criterio B applicato
alla lettera, e i suoi tre test sono verdi.

Misurando la COPERTURA di quella cura, però::

    agent_guide.py     (curata)              non promette più · dichiara il limite
    mcp_server.py      (letta a runtime)     promette          · NON lo dichiara
    README.md          (la vetrina)          promette          · NON lo dichiara
    document_index.py                        promette          · NON lo dichiara
    document_promote.py                      promette          · NON lo dichiara

⇒ **Una superficie su cinque.** E le due che pesano di più non erano coperte:
`mcp_server.py` contiene le descrizioni degli strumenti MCP, che l'agente legge
a runtime per decidere se fidarsi — la stessa identica funzione di
`agent_guide.py` — e `README.md` è ciò che legge chi scarica il prodotto.

🔑 È la classe più ricorrente di questa casa: **una copia invece della
superficie unica**, e la domanda che la trova è sempre la stessa — *chi ALTRO
dice la stessa cosa?* Il test di ws6 non era sbagliato: era ancorato al file su
cui stava lavorando.

═══ ⚠️ E IL CASO PEGGIORE ERA IN `document_promote.py` ═══

Diceva: *«any reader can open the file at the exact offsets and check»* — una
promessa esplicita di riapertura, falsa nell'84,9% dei casi misurati. E lì pesa
più che altrove, perché quella citazione finisce in **`verified_by`**, il campo
della provenienza: certifica CHE COSA È STATO INDICIZZATO, non che la fonte si
riapra oggi.

═══ PERCHÉ IL CRITERIO QUI È STRUTTURALE E NON UNA STRINGA ═══

Il test di ws6 cerca la stringa esatta `"(exact citations)."`, punto compreso.
Regge sul suo file, ma non prenderebbe «exact citation» al singolare, senza
punto o riformulata. Qui la regola è: **se una superficie promette una citazione
esatta, nella stessa superficie deve stare scritto su COSA è esatta.** Non
vieta una parola: pretende che accanto alla promessa ci sia il suo limite,
comunque la si scriva.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parents[1]

#: Le superfici su cui un lettore — umano o agente — incontra la promessa.
#:
#: 📌 LE ULTIME DUE LE HA TROVATE ws5 VERIFICANDO QUESTO STESSO PEZZO, ed è il
#: motivo per cui stanno qui: la mia mappa ne aveva cinque, la sua ne contava
#: altre. Una lista di superfici scritta da chi ha in mente la cura è quasi
#: sempre corta — la trova chi guarda da fuori.
SUPERFICI = [
    ("agent_guide.py — la guida che ogni agente riceve", "verimem/agent_guide.py"),
    ("mcp_server.py — le descrizioni degli strumenti, lette a runtime",
     "verimem/mcp_server.py"),
    ("README.md — la vetrina di chi scarica", "README.md"),
    ("document_index.py — il modulo che la implementa", "verimem/document_index.py"),
    ("document_promote.py — dove la citazione entra in verified_by",
     "verimem/document_promote.py"),
    ("F2_MODULE_INVENTORY.md — l'inventario che descrive il modulo",
     "docs/F2_MODULE_INVENTORY.md"),
]

#: ⚖️ E QUESTE DEVONO RESTARE COME SONO — il presidio che manca alle liste.
#:
#: Il difetto speculare di una mappa corta è una mappa GOLOSA: `git grep` trova
#: la promessa anche dove correggerla sarebbe sbagliato. ws5 se n'è accorta
#: contando dodici superfici e ritirando il numero a dieci, e la riga che le
#: mancava è questa: **prima di contare le occorrenze di una promessa, separare
#: quelle che DEVONO restare.**
#:
#: · `CHANGELOG.md` registra che cosa fu ANNUNCIATO allora: correggerlo non
#:   sarebbe curare una promessa, sarebbe riscrivere la storia.
#: · `docs/TEST_SURFACE_MAP.md` usa «exact citation» come NOME DI UN AMBITO da
#:   sottoporre a stress, in una tabella di copertura — non promette nulla a
#:   nessun lettore.
#: · i test che citano la frase vecchia apposta, per riconoscerla.
NON_SI_TOCCANO = ("CHANGELOG.md", "docs/TEST_SURFACE_MAP.md", "tests/")

#: ⚠️ LA PROMESSA SI CERCA PER PROSSIMITÀ, NON PER STRINGA — e questa riga è
#: nata da un errore mio, trovato falsificando il mio stesso test.
#:
#: La prima versione cercava le stringhe `"exact citation"` / `"esatta"`, cioè
#: esattamente il difetto che stavo correggendo in quello di ws6: un ancoraggio
#: letterale che una riformulazione aggira. La prova che l'ha smascherato::
#:
#:     "the citation is exact and points to the file"
#:       promette? -> False        ⇐ non conteneva «exact citation»
#:       il test NON sarebbe scattato su una promessa piena e senza limite
#:
#: 🔑 Un divieto di PAROLA si aggira riformulando; un criterio di PROSSIMITÀ no.
#: Qui: «esatto» e «citazione» — in italiano o in inglese, in qualunque ordine —
#: entro una finestra breve. La finestra è stretta apposta: due parole lontane
#: in un file lungo non sono una promessa, sono due parole.
_VICINANZA = 60
_ESATTO = r"(?:exact\w*|esatt\w+)"
_CITAZIONE = r"(?:citation\w*|citazion\w+)"
_FINESTRA = r"[^.\n]{0," + str(_VICINANZA) + r"}?"
_PROMESSA_RE = re.compile(
    _ESATTO + _FINESTRA + _CITAZIONE + r"|" + _CITAZIONE + _FINESTRA + _ESATTO,
    re.IGNORECASE)

#: I modi in cui il limite può essere dichiarato. Basta UNO: il test pretende
#: che il limite ci sia, non che sia scritto con parole nostre.
LIMITE = (
    "indexed text", "indexed_text[", "testo indicizzato",
    "no longer opens", "no longer exist", "stops opening", "stop resolving",
    "stops resolving", "not a promise", "NOT a promise", "NOT A PROMISE",
    "stored as given", "recorded as given", "registrato come dato",
    "smette di aprirsi", "84.9%", "84,9%",
)


@pytest.mark.parametrize("etichetta,percorso", SUPERFICI,
                         ids=[s[1] for s in SUPERFICI])
def test_ogni_superficie_che_promette_dichiara_anche_il_limite(etichetta, percorso):
    """Il cuore, e la regola è condizionale apposta: **non vieta di promettere
    una citazione esatta — pretende che accanto stia scritto su cosa lo è.**

    Un divieto di parola si aggira riformulando; questo no, perché non guarda
    come la promessa è scritta ma se il suo limite è nella stessa pagina.
    """
    testo = (_RADICE / percorso).read_text(encoding="utf-8", errors="ignore")
    basso = testo.lower()
    if not _PROMESSA_RE.search(testo):
        pytest.skip(f"{percorso} non promette più nulla sulla citazione")
    assert any(k.lower() in basso for k in LIMITE), (
        f"[{etichetta}] promette una citazione esatta senza dire su COSA lo è. "
        f"Misurato il 2026-08-12: 538 chunk su 634 (84,9%) puntavano a file "
        f"spariti, con il testo del chunk presente per il 100% di essi."
    )


def test_nessuna_superficie_promette_che_il_file_si_riapra():
    """⚠️ LA PROMESSA PIÙ FORTE E PIÙ FALSA, tolta da `document_promote.py`.

    «any reader can open the file» non è una sfumatura da qualificare: è una
    garanzia di riapertura, e l'84,9% dei chunk misurati la smentisce. Va
    presidiata a parte perché una superficie potrebbe dichiarare il limite in
    fondo e prometterla lo stesso in cima.
    """
    for _etichetta, percorso in SUPERFICI:
        basso = (_RADICE / percorso).read_text(
            encoding="utf-8", errors="ignore").lower()
        for frase in ("any reader can open the file",
                      "can always open the file",
                      "guarantees the file"):
            assert frase not in basso, (
                f"{percorso} garantisce la riapertura del file: «{frase}»")


@pytest.mark.parametrize("frase,e_una_promessa", [
    # ⚠️ IL CASO CHE HA SMASCHERATO LA PRIMA VERSIONE DI QUESTO FILE
    ("the citation is exact and points to the file", True),
    ("Document memory with exact citations", True),
    ("chunks with the EXACT citation — source_id", True),
    ("la citazione è esatta sull'indice", True),
    ("citation anchored to the indexed text", False),   # non dice «esatta»
    ("the exact number of chunks is 634", False),       # «exact» senza citazione
    ("every answer carries a citation", False),         # citazione senza «esatta»
])
def test_IL_RICONOSCITORE_prende_le_riformulazioni_e_non_i_falsi(
        frase, e_una_promessa):
    """⚠️ IL BANCO DEL MISURATORE, e sta qui perché il misuratore ha già
    sbagliato una volta in questo stesso file.

    Le prime quattro righe sono formulazioni diverse della stessa promessa: un
    criterio ancorato alle stringhe ne prendeva solo due. Le ultime tre sono la
    popolazione opposta — «exact» e «citation» che compaiono senza promettersi
    a vicenda — perché un riconoscitore troppo largo trasformerebbe ogni
    menzione in un obbligo di dichiarare un limite che lì non c'entra."""
    assert bool(_PROMESSA_RE.search(frase)) is e_una_promessa, frase


def test_LE_SUPERFICI_STORICHE_restano_intatte():
    """⚖️ IL VERSO OPPOSTO DELLA COPERTURA, e serve quanto l'altro.

    Una lista di superfici cresce guardando `git grep`, e `git grep` non sa
    distinguere una promessa da un ricordo. Se un giorno qualcuno «curasse» il
    CHANGELOG per far passare il test sopra, avrebbe riscritto la storia del
    prodotto per compiacere un guardiano — che è il modo in cui un presidio
    diventa dannoso.

    Il CHANGELOG **deve** contenere ancora la formulazione vecchia: è il
    registro di ciò che fu annunciato allora.
    """
    changelog = (_RADICE / "CHANGELOG.md").read_text(
        encoding="utf-8", errors="ignore")
    assert _PROMESSA_RE.search(changelog), (
        "il CHANGELOG non riporta più la promessa come fu annunciata: se è "
        "stato riscritto per far passare un test, va ripristinato — un "
        "changelog registra la storia, non la corregge"
    )


def test_IL_PEZZO_DI_ws6_RESTA_SUO_e_questo_non_lo_duplica():
    """Perché questo file non è una seconda copia del suo — che sarebbe la
    stessa classe di difetto che sto curando.

    Il test di ws6 presidia il TESTO PRECISO che ha scritto in `agent_guide.py`
    («indexed text», «no longer opens»): è il guardiano fine della superficie
    che ha curato, e deve restare suo. Questo presidia l'INVARIANTE che vale su
    tutte — promessa e limite nella stessa pagina — e non conosce le parole
    esatte di nessuna. I due si sovrappongono su `agent_guide.py` e non si
    sostituiscono: se un giorno quel file cambiasse formulazione restando
    corretto, il suo diventerebbe rosso e questo no, ed è giusto così.
    """
    suo = _RADICE / "tests" / "test_la_citazione_e_esatta_sull_indice_non_sul_disco.py"
    assert suo.exists(), (
        "il test di ws6 non c'è più: se è stato rimosso di proposito, questo "
        "commento va aggiornato; se è sparito per sbaglio, va rimesso")
