"""Alle domande sul passato il recall risponde col presente, e la storia era lì.

IL DIFETTO, isolato da ws5 su un listino che cambia tre volte (100 → 120 → 150)::

    quanto costa OGGI il prodotto A       -> «150 euro»  rilevanza 0.8589  ✅
    quanto costava a GENNAIO              -> «150 euro»  rilevanza 0.8457  ❌ era 100
    quanto costava ad APRILE              -> «150 euro»  rilevanza 0.8382  ❌ era 120
    qual era il prezzo PRECEDENTE         -> «150 euro»
    storia dei prezzi del prodotto A      -> «150 euro»

Cinque domande sul passato, cinque volte il valore corrente. **Non è un'assenza
di funzione: è una risposta sbagliata presentata come giusta**, con rilevanza
alta e nessun avviso. E il prodotto dichiara nelle proprie istruzioni MCP
«abstention over hallucination» — sull'asse del tempo quel principio non era
applicato: non diceva «non lo so», rispondeva.

🔑 LA CAUSA NON È CHE MANCHI IL MECCANISMO: È CHE È SPENTO DI DEFAULT.
``Memory.search`` ha già tutto, e funziona anche in italiano::

    wants_history("quanto costava a gennaio")  -> True
    wants_history("quanto costa oggi")         -> False

…ma la firma dice ``with_history: bool | str = False``, e ``wants_history``
viene consultato **solo** quando il chiamante passa esplicitamente ``"auto"``.
Nessuna delle superfici normali lo fa. Il routing esisteva, era corretto, e non
si accendeva mai.

📌 È LA STESSA CLASSE, SULLA STESSA SUPERFICIE, PER LA TERZA VOLTA — e sta
scritta in ``mcp_server.py:7627``, sopra ``hippo_trust_report``::

    «i due elementi che PRODUCONO un'astensione erano entrambi inerti qui —
     ce_gate è False di default nella firma […] quindi il dossier che
     pubblicizza "it ABSTAINS instead of stitching a guess" rispondeva a OGNI
     domanda. Misurato: gate OFF -> 0/5 astensioni; gate ON -> 4/5, con ZERO
     astensioni false, che è ciò che rende sicuro ribaltare il default.»
    «Il commento qui sotto è la stessa classe: un critic segnalò SDK-only tre
     settimane fa, min_relevance fu cablato, ce_gate no.»

Stessa forma, stessa cura: si ribalta il default **dopo** aver misurato che la
popolazione opposta non paga.

MISURATO PRIMA DI SCRIVERE (stesso banco di ws5, ramo ws3/gate-precision)::

                                    default        "auto"
    quanto costa OGGI               no storia      **no storia**   <- non temporale
    quanto costava a GENNAIO        no storia      **storia**
    quanto costava ad APRILE        no storia      **storia**
    storia dei prezzi               no storia      **storia**

⚠️ ``as_of`` resta ``None`` su «a gennaio»: un mese senza anno non è una data
ancorabile, e ``extract_as_of`` è dichiaratamente conservativa («nessuna àncora
inventata»). Il caso di ws5 lo risolve ``with_history``, non l'ancoraggio — sono
due meccanismi diversi e solo uno si applica qui.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

FONTE = ("Listino interno: il prodotto A costa 100 euro, poi aggiornato a 120 "
         "euro, poi a 150 euro.")


@pytest.fixture()
def mem(tmp_path):
    m = Memory(str(tmp_path / "s.db"))
    for p in ("Il prodotto A costa 100 euro.",
              "Il prodotto A costa 120 euro.",
              "Il prodotto A costa 150 euro."):
        m.add(p, topic="az/listino", source=FONTE)
    return m


@pytest.mark.parametrize("domanda", [
    "quanto costava il prodotto A a gennaio",
    "quanto costava il prodotto A ad aprile",
    "storia dei prezzi del prodotto A",
])
def test_una_domanda_sul_PASSATO_riceve_la_storia_senza_chiederla(mem, domanda):
    """IL CUORE: chi chiede del passato deve almeno VEDERE che quel numero ha
    avuto altri valori. Senza, riceve il presente e non ha modo di accorgersene.
    """
    hits = mem.search(domanda, k=3)
    assert hits, "nessun risultato: banco rotto"
    assert any(h.get("history") for h in hits), (
        f"nessun hit porta la storia: «{domanda}» riceve solo il presente")


def test_CONTROLLO_POSITIVO_una_domanda_al_PRESENTE_non_paga_la_storia(mem):
    """⚠️ IL PRESIDIO CHE RENDE SICURO IL RIBALTAMENTO, ed è il motivo per cui
    il default diventa ``"auto"`` e non ``True``: «quanto costa OGGI» non è una
    domanda temporale, non deve ricostruire nessuna catena, e non deve pagarne
    il costo. Se questo cade, ho acceso la storia per tutti invece di
    instradarla."""
    hits = mem.search("quanto costa oggi il prodotto A", k=3)
    assert hits
    assert not any(h.get("history") for h in hits), (
        "la storia è stata costruita per una domanda al presente")


@pytest.mark.parametrize("domanda", [
    "quanto costa il prodotto A",
    "chi e' il fornitore",
])
def test_CONTROLLO_POSITIVO_le_domande_ordinarie_non_cambiano(mem, domanda):
    """L'altro presidio: la stragrande maggioranza delle query non è temporale,
    e per loro il risultato deve restare byte per byte quello di prima — la
    storia si AGGIUNGE a chi la chiede, non si impone a tutti."""
    hits = mem.search(domanda, k=3)
    assert not any(h.get("history") for h in hits)


def test_chi_dice_esplicitamente_NO_continua_a_non_riceverla(mem):
    """Il default cambia; la volontà esplicita del chiamante no. Chi passa
    ``with_history=False`` sta dicendo «non voglio pagare quel costo», e un
    default che lo scavalca sarebbe peggio del difetto curato."""
    hits = mem.search("storia dei prezzi del prodotto A", k=3,
                      with_history=False)
    assert not any(h.get("history") for h in hits)


def test_e_chi_dice_esplicitamente_SI_la_riceve_sempre(mem):
    """La simmetria: ``True`` significa «sempre», anche su una domanda che il
    router non riconoscerebbe come temporale."""
    hits = mem.search("quanto costa oggi il prodotto A", k=3,
                      with_history=True)
    assert any(h.get("history") for h in hits)
