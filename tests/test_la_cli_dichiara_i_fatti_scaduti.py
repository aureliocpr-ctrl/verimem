"""La porta a riga di comando deve dire cosa la scadenza le ha tolto.

`Risultati.esclusi_perche_scaduti` esiste dall'SDK, ed è misurato: un fatto
scaduto sparisce dal top-k e ora l'oggetto lo dichiara. **Ma un campo esiste
sull'OGGETTO, non sulla PORTA**, e il banco
`docs/stato-reale/banchi/ws6-quante-porte-dicono-cosa-hanno-tolto.py` lo prova
eseguendo:

    porta            risponde  dichiara
    SDK (Memory)     si        SI
    CLI recall       si        no        <- serve la risposta ridotta e TACE

Chi usa la riga di comando riceve la risposta già ridotta dalla scadenza e non
ha modo di accorgersene. È la stessa classe che `cli.py` documenta per i record
trattenuti — *«non è un comando in più da scoprire, è un AVVISO su una risposta
che si sta già leggendo»* — e la stessa che `Risultati` cura per il pavimento.

⚠️ E QUI SI LEGGE, NON SI RICALCOLA. `_avviso_pavimento` in `cli.py` ricostruisce
il pavimento per conto suo invece di leggere `hits.sotto_il_pavimento`: è il
motivo per cui un grep dei nomi dei campi non trova nulla in `cli.py`, ed è una
seconda implementazione della stessa regola. Non se ne aggiunge una terza:
`hits` È un `Risultati` (`cli.py:1453`, `hits = m.search(...)`), quindi
l'attributo si legge da lì.

⛔ Lo store è un `Memory` VERO su tempdir, passato alla CLI col monkeypatch di
`_open_memory` che la casa usa già: la riga di comando non può in nessun caso
aprire lo store di Aurelio.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from verimem import cli as cli_mod  # noqa: E402
from verimem.client import Memory  # noqa: E402

SCADUTO = "Il deposito di Verona ospita quattromilaseicento pallet di ricambi."
F_SCAD = "Inventario: il deposito di Verona ospita 4600 pallet di ricambi."
VIVO = "Il deposito di Verona custodisce pallet di imballaggi in un'area coperta."
F_VIVO = ("Inventario: il deposito di Verona custodisce pallet di imballaggi "
          "in un'area coperta.")
#: Sette parole, non quattro: la curva del richiamo è misurata in casa (3 parole
#: ritrovano il 27%, 7 il 100%) e una query corta misurerebbe il pavimento, non
#: la scadenza.
QUERY = "quanti pallet ospita il deposito di Verona"


def _store(con_scaduto: bool) -> Memory:
    m = Memory(str(Path(tempfile.mkdtemp(prefix="cli_scad_")) / "s.db"))
    if con_scaduto:
        m.add(SCADUTO, topic="cli/scaduto", source=F_SCAD,
              valid_until=time.time() - 86_400)
    #: Il fatto vivo NON ha numeri, ed è una correzione pagata: con «duemila»
    #: contro una fonte che dice «2000» il gate lo QUARANTINA (grounding 10,46),
    #: il recall torna vuoto e il test misurerebbe il gate invece della porta.
    m.add(VIVO, topic="cli/vivo", source=F_VIVO)
    return m


@pytest.fixture()
def cli_su(monkeypatch):
    def _con(con_scaduto: bool) -> str:
        mem = _store(con_scaduto)
        monkeypatch.setattr(cli_mod, "_open_memory", lambda *a, **k: mem)
        return CliRunner().invoke(cli_mod.app, ["recall", QUERY]).output
    return _con


def test_la_cli_dice_quando_la_scadenza_ha_tolto_qualcosa(cli_su):
    out = cli_su(True)
    #: ⚠️ CONTROLLO POSITIVO, e non è una formalità: se la CLI non servisse
    #: nulla, l'assenza dell'avviso non direbbe «non lo espone», direbbe «non
    #: ha risposto» — due cose diverse, e solo la prima è un difetto.
    assert "imballaggi" in out or "Verona" in out, (
        f"la CLI non risponde affatto: il test non sta misurando l'avviso "
        f"ma un'altra cosa. Uscita: {out[:300]!r}"
    )
    assert "scadut" in out.lower(), (
        f"la scadenza ha tolto un fatto e la riga di comando NON LO DICE: chi "
        f"legge riceve una risposta gia' ridotta senza modo di accorgersene. "
        f"Uscita: {out[:300]!r}"
    )


def test_se_la_scadenza_toglie_TUTTO_la_cli_non_dice_solo_no_facts(monkeypatch):
    """IL CASO PEGGIORE, e il ramo che il test sopra non tocca.

    Se la scadenza porta via ogni risultato, `recall_cmd` stampa «no facts
    found» ed esce prima di arrivare agli avvisi: risposta vuota e nessuna
    spiegazione, mentre i fatti nello store ci sono e sono solo scaduti.
    """
    m = Memory(str(Path(tempfile.mkdtemp(prefix="cli_tutto_")) / "s.db"))
    m.add(SCADUTO, topic="cli/solo-scaduto", source=F_SCAD,
          valid_until=time.time() - 86_400)
    monkeypatch.setattr(cli_mod, "_open_memory", lambda *a, **k: m)
    out = CliRunner().invoke(cli_mod.app, ["recall", QUERY]).output
    assert "scadut" in out.lower(), (
        f"la scadenza ha svuotato la risposta e la CLI dice solo che non ha "
        f"trovato nulla: e' vero e inutile, i fatti c'erano. Uscita: {out[:300]!r}"
    )


def test_anche_ask_lo_dice_non_solo_recall(monkeypatch):
    """LA GEMELLA. `ask` e `recall` rispondono alla stessa domanda, e in questo
    file di comando c'e' gia' la cicatrice: `_avviso_pavimento` e' stata
    estratta da `recall_cmd` proprio perche' *«le due porte rispondono alla
    stessa domanda e una sola avvisava, quindi lo stesso store diceva "forse
    non lo so" o taceva a seconda del comando digitato»*.

    Curare solo `recall` sarebbe quella stessa lezione un giro dopo — e il
    banco delle porte l'ha misurato: dopo la cura di `recall`, `ask` rispondeva
    e taceva.
    """
    mem = _store(True)
    monkeypatch.setattr(cli_mod, "_open_memory", lambda *a, **k: mem)
    #: ⚠️ QUERY DIVERSA, e la ragione e' un reperto a parte: con «quanti pallet
    #: ospita...» `ask` classifica l'intento come CONTEGGIO ed esce da un ramo
    #: precedente, stampando «1 fatti ... (intento: conteggio — scan
    #: dell'intero corpus, non i primi 5)». Quel numero E' filtrato dalla
    #: scadenza e la riga dichiara di aver guardato tutto: e' un difetto
    #: PEGGIORE di quello curato qui — li' manca un avviso, li' un numero e'
    #: falso — e vive su un'altra strada (il conteggio non passa da `search`).
    #: Non lo si cura di straforo dentro questo test: e' segnato a parte.
    out = CliRunner().invoke(
        cli_mod.app, ["ask", "raccontami del deposito di Verona e dei suoi pallet"]).output
    assert "imballaggi" in out or "Verona" in out, (
        f"`ask` non risponde: il test non misura l'avviso. Uscita: {out[:300]!r}"
    )
    assert "scadut" in out.lower(), (
        f"`recall` lo dice e `ask` no: lo stesso store risponde in due modi "
        f"secondo il comando digitato. Uscita: {out[:300]!r}"
    )


def test_senza_scadenze_la_cli_non_dice_nulla(cli_su):
    """CONTROLLO AL ROVESCIO: un avviso che compare sempre non distingue nulla,
    e passerebbe il test sopra senza dire niente a nessuno."""
    out = cli_su(False)
    assert "imballaggi" in out or "Verona" in out, (
        f"la CLI non risponde: il controllo non controlla. Uscita: {out[:300]!r}"
    )
    assert "scadut" not in out.lower(), (
        f"nessun fatto e' scaduto e la CLI lo annuncia lo stesso: "
        f"un avviso che esce sempre non e' un avviso. Uscita: {out[:300]!r}"
    )
