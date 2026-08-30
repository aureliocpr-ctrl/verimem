"""Il veto del rilascio guarda solo i `.py`, e ora lo dichiara nel proprio verdetto.

`scripts/controlla_registro.py` è il **veto ④ del rilascio**: se trova identificativi
interni nell'artefatto, ferma la pubblicazione. Guarda **solo i file `.py`** — scelta
legittima, ma fino al 2026-08-30 non era scritta nel suo stesso esito.

Misurato quel giorno, su una cartella con due file palesemente sporchi che `.py` non
sono (un nome di sessione in un `.md` e uno in un `.json`)::

    file .py esaminati: 0
        ok   identificativo di sessione   0 in 0 file
        ok   nome proprio di sessione     0 in 0 file
    EXIT = 0

Tre «ok» e via libera. 🔑 Un «ok» su ZERO file guardati è **indistinguibile** da un «ok»
su una cartella pulita, e chi legge il riepilogo prima di pubblicare non ha modo di
accorgersene. È la classe di casa: *una misura che non c'è si legge come perfetta* — qui
in una forma nuova, perché non manca la misura: manca la dichiarazione del suo PERIMETRO.

⚖️ La cura **non estende il perimetro** (sarebbe un'altra decisione, con altri costi:
`pyproject.toml` spedisce anche `.txt`, `.md`, `.yaml` via `package-data`). Rende visibile
che il perimetro esiste. Questi test presidiano **entrambe** le metà: che il perimetro si
veda, e che il comportamento del veto **non sia cambiato**.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
CONTROLLO = RADICE / "scripts" / "controlla_registro.py"

#: Un identificativo che il controllo riconosce. Sta qui e non nel corpo dei test
#: perché questo file finisce nel repository ma NON nel pacchetto: se finisse nel
#: pacchetto, il veto si accuserebbe da solo (è la ragione per cui lo script
#: esclude se stesso dalla propria scansione).
SPORCO = "reperto di " + "Varco"


def _esegui(percorso: Path) -> tuple[int, str]:
    """Esegue il controllo e restituisce (codice, output).

    Niente pipe fra il comando e il codice di uscita: con una pipe si legge il
    codice del filtro e un veto si legge verde.
    """
    fatto = subprocess.run([sys.executable, str(CONTROLLO), str(percorso)],
                           capture_output=True, text=True, errors="replace", timeout=300)
    return fatto.returncode, (fatto.stdout or "") + (fatto.stderr or "")


def test_il_perimetro_e_dichiarato_quando_ci_sono_file_non_py(tmp_path: Path):
    """Il caso che ha motivato la cura: due file sporchi che `.py` non sono."""
    (tmp_path / "x.md").write_text(SPORCO + ", cella W8-1\n", encoding="utf-8")
    (tmp_path / "y.json").write_text('{"nota": "' + SPORCO + '"}\n', encoding="utf-8")
    codice, uscita = _esegui(tmp_path)
    assert "file NON esaminati (non .py): 2" in uscita, (
        "il verdetto non dichiara quanti file NON ha guardato:\n" + uscita
    )
    assert codice == 0, (
        "il PERIMETRO non deve cambiare: il controllo guarda i .py e qui non ce ne sono. "
        "Se questo diventa 1, qualcuno ha esteso il perimetro — che è un'altra decisione, "
        "da prendere apposta e non di rimbalzo."
    )


def test_CONTROLLO_il_veto_blocca_ancora_un_py_sporco(tmp_path: Path):
    """Il sensore è collegato? Se il veto smettesse di bloccare, il test sopra
    resterebbe verde e non ce ne accorgeremmo: `EXIT=0` su una cartella senza
    `.py` e `EXIT=0` su un veto spento si scrivono uguale."""
    (tmp_path / "x.md").write_text(SPORCO + "\n", encoding="utf-8")
    (tmp_path / "z.py").write_text("# " + SPORCO + "\nX = 1\n", encoding="utf-8")
    codice, uscita = _esegui(tmp_path)
    assert codice == 1, "il veto non blocca più un .py sporco:\n" + uscita
    assert "file NON esaminati (non .py): 1" in uscita, (
        "il perimetro sparisce quando il veto blocca: va dichiarato in entrambi i casi\n"
        + uscita
    )


def test_zero_file_fuori_perimetro_si_dichiara_come_zero(tmp_path: Path):
    """Il controllo negativo del conteggio: senza questo, una funzione che
    restituisse sempre lo stesso numero passerebbe i due test qui sopra."""
    (tmp_path / "pulito.py").write_text("X = 1\n", encoding="utf-8")
    codice, uscita = _esegui(tmp_path)
    assert "file NON esaminati (non .py): 0" in uscita, (
        "con zero file fuori perimetro il verdetto deve dire 0, non tacere:\n" + uscita
    )
    assert codice == 0
