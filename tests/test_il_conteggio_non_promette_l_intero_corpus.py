"""Il conteggio di `ask` dichiara una completezza che non ha.

    $ verimem ask "quanti pallet ospita il deposito di Verona"
    1 fatti su «pallet ospita il deposito Verona»
    (intento: conteggio — scan dell'intero corpus, non i primi 5)

Nel corpus i fatti pertinenti sono **due**. Il conteggio è un **AND su tutti i
termini** (`content_terms` → `count(query=terms)`), e il secondo fatto dice
«custodisce» dove la domanda dice «ospita»: l'AND lo esclude. Misurato:

    termini: 'pallet ospita il deposito Verona'
    count(AND) = 1        pallet 2 · ospita 1 · il 0 · deposito 2 · Verona 2
    count() sul corpus = 2

⚠️ IL NUMERO NON È SBAGLIATO: è corretto per ciò che misura. È **la frase** a
promettere un'altra cosa — «scan dell'intero corpus» dice a chi legge che il
corpus è stato guardato tutto, e chi legge conclude «di pallet ne ho uno solo».
È un numero vero che inganna, e la cura non è nel calcolo ma nella riga.

⚠️ E NON SI ALLARGA LA GUARDIA DEL PER-TERMINE, che oggi si accende solo a
conteggio zero. Sembrava la cura ovvia; il costo, misurato su 400 fatti e 5
termini, dice di no:

    count(AND)            3,7 ms
    count per-termine    45,5 ms   = 12,2x

L'autore aveva scritto che si paga «SOLO qui» per ragioni di costo, senza un
numero accanto: ora il numero c'è e gli dà ragione.

⚠️ QUI LO STUB DELL'EMBEDDER NON FALSA NULLA — e va detto, perché altrove sì.
Il conteggio è lessicale (un AND di `LIKE` sulle proposizioni), non semantico:
non tocca gli embedding, quindi questo test misura lo stesso comportamento
dentro e fuori pytest.

🪞 E LA PRIMA VERSIONE DI QUESTO REPERTO ERA SBAGLIATA. Avevo scritto che il
numero è «filtrato dalla scadenza». Non lo è: con due processi separati e store
isolati, `ask.count` vale 1 sia col fatto scaduto sia senza. Avevo dichiarato
una causa senza isolarla.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from verimem import cli as cli_mod  # noqa: E402
from verimem.client import Memory  # noqa: E402

#: Due fatti pertinenti che differiscono per UN verbo: è quel verbo a far
#: cadere il secondo fuori dall'AND.
OSPITA = "Il deposito di Verona ospita quattromilaseicento pallet di ricambi."
CUSTODISCE = "Il deposito di Verona custodisce pallet di imballaggi in area coperta."
DOMANDA = "quanti pallet ospita il deposito di Verona"


@pytest.fixture()
def cli(monkeypatch):
    mem = Memory(str(Path(tempfile.mkdtemp(prefix="cnt_promessa_")) / "s.db"))
    mem.add(OSPITA, topic="cnt/a")
    mem.add(CUSTODISCE, topic="cnt/b")
    monkeypatch.setattr(cli_mod, "_open_memory", lambda *a, **k: mem)
    return mem, CliRunner().invoke(cli_mod.app, ["ask", DOMANDA]).output


def test_il_conteggio_e_davvero_parziale(cli):
    """CONTROLLO POSITIVO: senza questo, il test sotto non misura niente.

    Se il conteggio dell'AND coincidesse col totale, non ci sarebbe alcuna
    promessa da mantenere e la frase «intero corpus» sarebbe innocua.
    """
    mem, out = cli
    assert mem.count() == 2, f"il corpus deve avere 2 fatti: {mem.count()}"
    assert "1 " in out or ">1<" in out, (
        f"l'AND deve contarne UNO solo, altrimenti non c'e' nessuno scarto "
        f"fra il numero e il corpus. Uscita: {out[:200]!r}"
    )


def test_la_riga_non_promette_di_aver_guardato_tutto_il_corpus(cli):
    _mem, out = cli
    assert "intero corpus" not in out.lower(), (
        f"la riga dichiara «scan dell'intero corpus» mentre conta un AND sui "
        f"termini: nel corpus i pertinenti sono 2 e il numero e' 1. Il numero "
        f"e' vero, la promessa no. Uscita: {out[:220]!r}"
    )


def test_la_riga_dice_che_e_un_AND_sui_termini(cli):
    """Non basta togliere la promessa falsa: chi legge deve capire COSA ha
    contato, altrimenti resta un numero nudo che si interpreta da sé — e si
    interpreta come «tutti»."""
    _mem, out = cli
    basso = out.lower()
    assert ("tutti i termini" in basso) or ("tutte le parole" in basso), (
        f"la riga non dice che il conteggio richiede TUTTI i termini insieme: "
        f"un numero nudo si legge come «tutti i fatti». Uscita: {out[:220]!r}"
    )
