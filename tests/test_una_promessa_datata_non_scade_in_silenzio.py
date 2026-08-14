"""Una promessa con una data dentro è l'unica che diventa falsa da sola.

PERCHÉ QUESTO FILE ESISTE. Il 2026-08-13 tre superfici del pacchetto spedito
dicevano che il package shim ``import hippoagent`` era *«scheduled for removal
on 2026-08-13»*. Il giorno dopo, 2026-08-14, la riga era invariata e il
pacchetto c'era ancora — ``hippoagent/__init__.py`` presente, ``pyproject.toml``
che lo spedisce. Una di quelle superfici è ``agent_guide.py``, cioè il campo
``instructions`` che ogni client MCP riceve **alla connessione**: dal 14 in poi
ogni agente che si collegava leggeva una scadenza passata accanto a un pacchetto
presente.

⇒ **Nessuno aveva sbagliato niente quel giorno.** È la proprietà che rende
questa classe diversa da tutte le altre che presidiamo: un difetto normale nasce
da una modifica, e una modifica si può rivedere; **una promessa datata diventa
falsa mentre tutti dormono, senza che nessuno tocchi un file.** Sei file di test
nominavano ``agent_guide.py`` e nessuno di loro guardava un calendario — non per
distrazione: non c'era niente da guardare, finché il giorno non è arrivato.

═══ COME È COSTRUITO, e i due dettagli che decidono se funziona ═══

**① Si cerca sul TESTO INTERO, non riga per riga.** Nel caso reale la trappola
era proprio qui: ``verimem/__init__.py`` scriveva *«is scheduled for removal»* e
poi *«~2026-08-13.»* **sulla riga successiva**. Un rilevatore riga-per-riga —
il primo che viene in mente, e quello che avevo scritto per primo — avrebbe
trovato due superfici su tre e dichiarato il lavoro finito.

**② Non basta una data: serve un IMPEGNO accanto.** Il pacchetto contiene
~1300 date ISO e la quasi totalità sono date di *misura* (*«measured 2026-08-12
on the real corpus»*, *«until 2026-08-04 no read surface answered this»*). Una
data di misura nel passato è normale e giusta; una promessa nel passato no. Il
filtro tiene solo le formule di impegno alla RIMOZIONE, che sono poche e
stabili, e ``test_il_rilevatore_vede_davvero_una_scadenza_passata`` prova sul
testo VERO di ieri che il filtro le aggancia — senza quel caso, il giorno in cui
qualcuno riscrive la formula in un modo che il regex non conosce questo file
diventerebbe verde per sempre, cioè la forma peggiore di sensore scollegato.

⚠️ **QUESTO TEST DIPENDE DALLA DATA DI OGGI, ED È VOLUTO.** È l'unico modo di
accorgersi di un difetto che *è* il passare del tempo. Se un giorno diventa
rosso senza che nessuno abbia toccato niente, **sta funzionando**: qualcuno ha
scritto una scadenza e quel giorno è arrivato. La cura non è allentare il test —
è mantenere la promessa, oppure toglierle la data.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pytest

PACCHETTO = Path(__file__).resolve().parents[1] / "verimem"

#: Le formule con cui, in questo repository, si è promesso di RIMUOVERE qualcosa.
#: Non è un elenco di tutte le promesse possibili: è un elenco di quelle che
#: sappiamo di aver scritto, e cresce quando ne compare una nuova.
_IMPEGNO = r"(?:scheduled\s+for\s+removal|removal\s*:|will\s+be\s+removed|to\s+be\s+removed|sunset(?:\s+on)?|expires\s+on)"

#: La data può stare fino a ~90 caratteri dopo l'impegno, **a capo compreso**:
#: nel caso reale del 2026-08-13 stava sulla riga successiva.
_PROMESSA_DATATA = re.compile(
    _IMPEGNO + r"[^.;]{0,90}?(20\d\d)-(\d\d)-(\d\d)",
    re.IGNORECASE | re.DOTALL,
)


def _promesse_datate(testo: str) -> list[tuple[dt.date, str]]:
    """Le (data, frase) promesse di rimozione trovate nel testo."""
    fuori = []
    for m in _PROMESSA_DATATA.finditer(testo):
        try:
            quando = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue  # 2026-13-45 non è una data, è un numero di serie
        fuori.append((quando, " ".join(m.group(0).split())))
    return fuori


def _file_spediti() -> list[Path]:
    return sorted(p for p in PACCHETTO.rglob("*.py") if "__pycache__" not in p.parts)


def test_il_rilevatore_vede_davvero_una_scadenza_passata() -> None:
    """CONTROLLO POSITIVO: senza questo, il file può diventare verde per assenza.

    I tre casi sono il testo VERO delle tre superfici come stava il 2026-08-13,
    incluso quello spezzato su due righe che è la ragione di ``re.DOTALL``.
    """
    veri = [
        "PACKAGE shim (`import hippoagent`) is scheduled for removal on 2026-08-13 —",
        "``hippoagent`` (the shim, not the env prefix) is scheduled for removal\n~2026-08-13.",
        "Scheduled removal: ~2026-08-13 (3 months from rename). After that, all",
    ]
    for testo in veri:
        assert _promesse_datate(testo), (
            f"il rilevatore NON aggancia una promessa datata reale: {testo!r}. "
            f"Se la formula è cambiata, aggiornare _IMPEGNO — un rilevatore che "
            f"non aggancia niente rende questo file verde per sempre"
        )

    # E l'altra popolazione: una data di MISURA non è una promessa, e una
    # promessa nel futuro non è ancora un difetto.
    assert not _promesse_datate("measured 2026-08-12 on the real corpus, 538 of 634"), (
        "una data di misura è stata scambiata per una promessa: il filtro "
        "produrrebbe falsi allarmi su ~1300 date del pacchetto"
    )
    assert not _promesse_datate("until 2026-08-04 no read surface answered this"), (
        "«until <data passata>» descrive il passato, non promette il futuro"
    )
    assert _promesse_datate("scheduled for removal on 2099-01-01"), (
        "una promessa nel futuro deve essere VISTA (e poi accettata dal test "
        "sotto): se non la vede, il rilevatore non sta guardando"
    )


@pytest.mark.parametrize("percorso", _file_spediti(), ids=lambda p: p.name)
def test_nessuna_promessa_di_rimozione_e_gia_scaduta(percorso: Path) -> None:
    oggi = dt.date.today()
    scadute = [
        (quando, frase)
        for quando, frase in _promesse_datate(percorso.read_text(encoding="utf-8", errors="ignore"))
        if quando < oggi
    ]
    assert not scadute, (
        f"{percorso.name} promette una rimozione per una data GIÀ PASSATA "
        f"(oggi è {oggi}): "
        + " · ".join(f"{q} → «{f}»" for q, f in scadute)
        + ". Il pacchetto lo dice a chi lo usa mentre la cosa promessa è ancora "
        "lì: o si fa la rimozione, o si toglie la data alla frase. Precedente: "
        "2026-08-14, tre superfici con «removal on 2026-08-13», shim ancora "
        "spedito, e la guida MCP la consegnava a ogni client sulla connessione"
    )
