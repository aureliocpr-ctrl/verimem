"""Il controllo del registro blocca un'attribuzione e lascia passare un'omonimia.

Lo strumento serve a impedire che identificativi di lavoro interni escano col
pacchetto. Ha un solo modo di essere inutile e due modi di essere dannoso:

  inutile   non blocca niente — allora si può togliere
  dannoso   blocca su un'omonimia (``ws`` sta anche per *workspace*), e chi lo
            usa impara a ignorarlo
  dannoso   blocca su codice che nomina l'identificativo come VALORE, non come
            attribuzione: ``principal="cli:local/ws7"`` è un dato di prova

Il collaudo copre ENTRAMBE le popolazioni. Un test che guarda solo il caso
negativo non distingue «riconosce le attribuzioni» da «blocca sempre»: senza il
caso positivo, «non rilevato» non si distingue da «sensore spento».
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PRESIDIO = Path(__file__).resolve().parent.parent / "scripts" / "controlla_registro.py"


def _esegui(cartella: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(PRESIDIO), str(cartella)],
                          capture_output=True, text=True, errors="replace")


def test_lo_strumento_esiste_ed_e_eseguibile():
    """Prima di misurare cosa dice: dice qualcosa?"""
    assert PRESIDIO.is_file(), f"{PRESIDIO} non c'è"
    esito = _esegui(PRESIDIO.parent.parent / "tests")
    assert "artefatto:" in esito.stdout, esito.stdout[:400] + esito.stderr[:400]


def test_blocca_un_attribuzione_in_un_docstring(tmp_path: Path):
    """Il caso per cui lo strumento esiste: un nome di sessione in prosa."""
    (tmp_path / "modulo.py").write_text(
        '"""Il difetto è stato misurato da ws4 il primo del mese."""\n'
        "VALORE = 1\n", encoding="utf-8")
    esito = _esegui(tmp_path)
    assert esito.returncode == 1, (
        "un'attribuzione in un docstring deve bloccare il rilascio\n"
        + esito.stdout[-600:])
    assert "identificativo di sessione" in esito.stdout


def test_blocca_un_attribuzione_in_un_commento(tmp_path: Path):
    (tmp_path / "modulo.py").write_text(
        "# ws3 ha isolato la causa con un A/B\nVALORE = 2\n", encoding="utf-8")
    assert _esegui(tmp_path).returncode == 1


def test_non_blocca_un_omonimia_nel_codice(tmp_path: Path):
    """``ws`` sta anche per *workspace*: un veto qui insegna a ignorare il controllo.

    È il caso che ha motivato la cura dello strumento — la prima versione
    bloccava, e su un artefatto pubblicato avrebbe dato un falso allarme.
    """
    (tmp_path / "test_qualcosa.py").write_text(
        "def test_percorsi(tmp_path):\n"
        '    ws = tmp_path / "ws1"\n'
        "    ws.mkdir()\n"
        "    assert ws.is_dir()\n", encoding="utf-8")
    esito = _esegui(tmp_path)
    assert esito.returncode == 0, (
        "un'omonimia fuori dalla prosa NON deve bloccare\n" + esito.stdout[-600:])


def test_non_blocca_un_identificativo_usato_come_valore(tmp_path: Path):
    """``principal="cli:local/ws7"`` è un dato di prova, non un'attribuzione."""
    (tmp_path / "test_attore.py").write_text(
        "def test_principal(store):\n"
        '    store.supersede(a, b, principal="cli:local/ws7", reason="b")\n',
        encoding="utf-8")
    assert _esegui(tmp_path).returncode == 0


def test_un_file_pulito_passa(tmp_path: Path):
    """Il controllo negativo del controllo negativo: senza niente, non inventa."""
    (tmp_path / "pulito.py").write_text(
        '"""Un modulo che non nomina nessuno."""\n\n\ndef somma(a, b):\n'
        "    return a + b\n", encoding="utf-8")
    esito = _esegui(tmp_path)
    assert esito.returncode == 0
    assert "Nessun identificativo di sessione" in esito.stdout
