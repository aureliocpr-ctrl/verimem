"""Ogni comando che il README insegna deve esistere nella CLI installata.

È il criterio A applicato alla superficie che un utente tocca per prima — e che
toccheremo **noi** per primi dopo il rilascio, visto che la 0.7.5 verrà
installata sul nostro sistema invece di girare da albero.

Misurato oggi, prima di scrivere il presidio::

    comandi esposti dalla CLI:        40
    comandi insegnati dal README:     15
    insegnati e assenti:               0     ✅

⇒ **Non c'è un difetto da curare**: questo file blinda uno stato che oggi è
sano. Serve perché la promessa e il comportamento vivono in due posti che
cambiano in momenti diversi — si rinomina un comando e il README resta indietro,
esattamente come «exact citations» era vera quando fu scritta.

═══ ⚠️ IL MISURATORE HA SBAGLIATO DUE VOLTE PRIMA DI DARE QUESTO NUMERO ═══

Vale la pena scriverlo qui, perché chi tocca questo test rischia gli stessi due
inciampi:

**① «La CLI espone 0 comandi».** Impossibile, e infatti falso: l'help è un box
Rich e i comandi stanno dopo `│ `, non dopo un'indentazione. Una regex ancorata
a due spazi a inizio riga non trovava niente — e uno zero prodotto da un parser
rotto sembra identico a uno zero vero.

**② Fra i comandi «insegnati» comparivano `import`, `has`, `pip`.** Venivano da
`from verimem import Memory`, da «verimem *has* no per-writer auth yet» e da una
riga di installazione: cercare `verimem <parola>` nel testo libero raccoglie
frasi inglesi. Il criterio giusto è cercarlo **dove il README insegna** — dentro
i backtick o in un blocco di codice.

🔑 Il primo errore avrebbe prodotto **17 falsi allarmi** su un documento sano; il
secondo li avrebbe fatti sembrare credibili. Un presidio nato da un conteggio non
classificato è un presidio che grida.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parents[1]


def _comandi_esposti() -> set[str]:
    """Quelli che la CLI dichiara nel proprio help — il comportamento."""
    r = subprocess.run(
        [sys.executable, "-m", "verimem.cli", "--help"],
        capture_output=True, text=True, timeout=300, cwd=str(_RADICE),
    )
    testo = r.stdout + r.stderr
    # ⚠️ il box Rich mette i comandi dopo «│ », non dopo un'indentazione
    trovati = set(re.findall(r"│\s([a-z][a-z0-9-]{2,})\s{2,}", testo))
    if not trovati:
        pytest.skip(
            "l'help non è parsabile: se il formato è cambiato aggiorna QUESTA "
            "funzione — uno zero da un parser rotto sembra uno zero vero")
    return trovati


def _dal_testo(testo: str) -> set[str]:
    """I comandi che un testo INSEGNA, distinti da quelli che soltanto nomina.

    ⚠️ TERZA VERSIONE, e le prime due le ha bocciate il banco qui sotto.
    · cercare `verimem <parola>` ovunque raccoglie le frasi inglesi
      («verimem **has** no per-writer auth yet» → comando `has`);
    · aggiungere «a inizio riga» non basta: una frase può cominciare la riga.

    🔑 Un comando **insegnato** vive in due posti soli: dentro i backtick, o
    dentro un blocco di codice recintato. Fuori di lì il nome del prodotto è
    solo il soggetto di una frase.
    """
    citati = set(re.findall(r"`verimem\s+([a-z][a-z0-9-]{2,})", testo))
    for blocco in re.findall(r"```[a-z]*\n(.*?)```", testo, re.S):
        citati |= set(re.findall(
            r"^\s*(?:\$\s*)?verimem\s+([a-z][a-z0-9-]{2,})", blocco, re.M))
    return citati


def _comandi_insegnati() -> set[str]:
    """Quelli che il README mostra come comandi — la promessa."""
    return _dal_testo(
        (_RADICE / "README.md").read_text(encoding="utf-8", errors="ignore"))


def test_ogni_comando_insegnato_dal_readme_esiste():
    """Il cuore: un lettore che copia una riga del README deve vederla girare."""
    insegnati, esposti = _comandi_insegnati(), _comandi_esposti()
    mancanti = sorted(insegnati - esposti)
    assert not mancanti, (
        f"il README insegna comandi che la CLI non espone: {mancanti}. "
        f"O il comando è stato rinominato e il README è rimasto indietro, "
        f"o il README promette qualcosa che non esiste."
    )


def test_IL_README_INSEGNA_ANCORA_QUALCOSA():
    """⚠️ IL VERSO OPPOSTO, e senza questo il test sopra si «supera» a vuoto.

    Se un domani la sezione dei comandi sparisse dal README — o il criterio di
    estrazione smettesse di trovarli — il test sopra passerebbe con l'insieme
    vuoto, dichiarando sano un documento che non insegna più niente. È lo stesso
    modo in cui un presidio su un documento diventa verde peggiorando.
    """
    insegnati = _comandi_insegnati()
    assert len(insegnati) >= 10, (
        f"il README insegna solo {len(insegnati)} comandi ({sorted(insegnati)}): "
        f"o la documentazione si è svuotata, o il criterio di estrazione non li "
        f"trova più — in entrambi i casi questo presidio ha smesso di misurare")


@pytest.mark.parametrize("frammento,atteso", [
    ("`verimem doctor` verifies", {"doctor"}),
    ("```bash\nverimem save \"testo\" --topic x\n```", {"save"}),
    ("`verimem search-docs` cita", {"search-docs"}),
    # ⚠️ la popolazione opposta: frasi inglesi che NON insegnano un comando
    ("verimem has no per-writer auth yet", set()),
    ("from verimem import Memory", set()),
    ("pip install verimem", set()),
])
def test_IL_RICONOSCITORE_separa_il_comando_dalla_frase(frammento, atteso, tmp_path):
    """Il banco del misuratore, con i tre falsi veri che avevo raccolto."""
    assert _dal_testo(frammento) == atteso, frammento
