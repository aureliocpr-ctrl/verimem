"""Il codice che nessuno puo' eseguire non cresce in silenzio.

Aurelio, 2026-07-31: «come mai quando sviluppi un modulo finisce sempre per non
essere collegato a nulla? parli di import, test verdi, e mesi dopo ci accorgiamo
che e' tutto spento».

La risposta misurata: **42 moduli su 371 non sono raggiungibili** — ne' dalle
quattro porte del prodotto (CLI, server MCP, SDK, gateway) seguendo gli import a
qualsiasi profondita', ne' come script `python -m verimem.X`. Il 12%. Possono
avere i test verdi e non essere mai eseguiti da nessun utente, che e' esattamente
il modo in cui il moat e' rimasto spento sul canale MCP per mesi.

Il primo giro ne contava 66 e SOVRASTIMAVA: non considerava `python -m` una
porta, e cosi' dichiarava scollegato `compose_daemon`, che il README documenta
testualmente («Run it one-shot») e che funziona. Uno strumento di misura che
grida piu' del dovuto fa perdere tempo invece di farne guadagnare, e la
correzione vale quanto la scoperta.

Questo file non pretende di curare i 42: congela il numero. Un modulo NUOVO che
nasce staccato fa fallire il test il giorno stesso, invece di scoprirsi mesi
dopo. E' la sola cura che regge, perche' la disciplina non ha retto: la lezione
«built-never-wired» era gia' scritta in memoria da un ciclo precedente, ed e'
stata rifatta lo stesso.

Metodo: si legge il sorgente con ``ast``, non a runtime. Questo repo mette gli
import DENTRO le funzioni per rompere i cicli, e un'analisi che guardasse solo
la testa dei file dichiarerebbe irraggiungibile mezzo prodotto.

Sui 42 non tutti sono difetti, e la distinzione va fatta guardandoli:
``rerank.py`` sembrava una feature pubblicizzata e spenta, ma il rerank vero e'
``cross_encoder_rerank.py``, importato da semantic.py e vivo — quello e' un
doppione morto, da cancellare, non da collegare. ``auto_dream_worker`` e' uno
script che parte dagli hook, non codice di libreria dimenticato. Il censimento
dice CHI, non COSA farne.
"""
from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "verimem"

#: Le porte del prodotto: cio' che un utente puo' invocare.
#:
#: ``__init__`` E' UNA PORTA, ed e' la prima: ``import verimem`` la esegue
#: sempre. Ometterla ha dichiarato spenti due moduli vivi — ``mode``, il cui
#: ``apply_engram_mode()`` gira a ogni import (riga 32 di ``__init__.py``), e
#: ``auto_memory``, che sta in ``__all__`` ed e' API pubblica. Stesso difetto di
#: quando mancava ``python -m``: uno strumento che grida piu' del dovuto fa
#: perdere tempo invece di farne guadagnare, e va corretto con la stessa cura
#: con cui si corregge il prodotto.
PORTE = ("__init__", "cli", "mcp_server", "client", "gateway")

#: Misurato il 2026-07-31. Il numero puo' SCENDERE quando si collega o si
#: cancella qualcosa; se sale, un modulo e' nato staccato e il test lo dice
#: subito. Non e' un obiettivo di qualita': e' un cricchetto.
IRRAGGIUNGIBILI_NOTI = 39


def _import_locali(percorso: Path, noti: set[str]) -> set[str]:
    try:
        albero = ast.parse(percorso.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    trovati: set[str] = set()
    for n in ast.walk(albero):
        if isinstance(n, ast.ImportFrom):
            if n.module and n.level == 0 and not n.module.startswith("verimem"):
                continue
            nome = (n.module or "").replace("verimem.", "")
            if n.level and not nome:  # from . import x
                trovati |= {a.name for a in n.names if a.name in noti}
                continue
            if (radice := nome.split(".")[0]) in noti:
                trovati.add(radice)
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith("verimem."):
                    if (r := a.name.replace("verimem.", "").split(".")[0]) in noti:
                        trovati.add(r)
    return trovati


def _eseguibile(f: Path) -> bool:
    """Ha un `main()` o un `if __name__ == "__main__"`.

    `python -m verimem.X` E' UNA PORTA. Il primo giro non lo considerava e
    dichiarava irraggiungibile `compose_daemon`, che il README documenta
    testualmente: «Run it one-shot (python -m verimem.compose_daemon --db ...)»
    — provato, funziona, e lo `--help` spiega che lo scheduling resta all'OS
    per scelta. Il censimento sovrastimava il problema, che e' il modo in cui
    uno strumento di misura fa perdere tempo invece di farne guadagnare.
    """
    try:
        albero = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return False
    for n in ast.walk(albero):
        if isinstance(n, ast.FunctionDef) and n.name == "main":
            return True
        if isinstance(n, ast.If) and isinstance(n.test, ast.Compare):
            if getattr(n.test.left, "id", "") == "__name__":
                return True
    return False


def _irraggiungibili() -> list[str]:
    moduli = {p.stem for p in PKG.glob("*.py")
              if not p.stem.startswith(("_", "test_")) and p.stem != "__init__"}
    raggiunti = {p for p in PORTE if (PKG / f"{p}.py").exists()}
    raggiunti |= {m for m in moduli if _eseguibile(PKG / f"{m}.py")}
    da_visitare = list(raggiunti)
    while da_visitare:
        f = PKG / f"{da_visitare.pop()}.py"
        if not f.exists():
            continue
        for dip in _import_locali(f, moduli):
            if dip not in raggiunti:
                raggiunti.add(dip)
                da_visitare.append(dip)
    return sorted(moduli - raggiunti)


def test_il_codice_scollegato_non_cresce():
    orfani = _irraggiungibili()
    assert len(orfani) <= IRRAGGIUNGIBILI_NOTI, (
        f"{len(orfani)} moduli non sono raggiungibili da CLI/MCP/SDK/gateway, "
        f"erano {IRRAGGIUNGIBILI_NOTI}. Qualcosa e' nato staccato:\n  "
        + "\n  ".join(orfani[-12:])
        + "\n\nCollegalo a una superficie, oppure — se e' uno script o un "
          "doppione — dillo qui abbassando il numero dopo averlo tolto.")


def test_il_cricchetto_si_stringe_quando_si_collega():
    """Se il conto e' sceso, il numero qui va abbassato: un cricchetto che
    resta largo dopo una bonifica smette di presidiare."""
    n = len(_irraggiungibili())
    assert n >= IRRAGGIUNGIBILI_NOTI - 3, (
        f"gli irraggiungibili sono scesi a {n} (noti {IRRAGGIUNGIBILI_NOTI}): "
        f"abbassa IRRAGGIUNGIBILI_NOTI, altrimenti il prossimo modulo staccato "
        f"passa senza far rumore")


def test_cio_che_init_esegue_non_puo_risultare_spento(monkeypatch):
    """``mode`` e ``auto_memory`` erano nella lista degli spenti, e sono vivi.

    Il test si falsifica da solo: togliendo ``__init__`` dalle porte, i due
    devono RIAPPARIRE fra gli irraggiungibili. Se non riapparissero, la porta
    non starebbe contando nulla e questo test non presidierebbe niente —
    misurare che la misura misura, dopo dieci criteri sbagliati in due giorni.
    """
    vivi = {"mode", "auto_memory"}
    assert not (vivi & set(_irraggiungibili())), (
        "un modulo che `import verimem` esegue risulta irraggiungibile")

    import sys
    monkeypatch.setattr(sys.modules[__name__], "PORTE",
                        tuple(p for p in PORTE if p != "__init__"))
    assert vivi <= set(_irraggiungibili()), (
        "senza la porta __init__ i due dovrebbero risultare spenti: la porta "
        "non sta cambiando il conto, quindi non e' lei a coprirli")


def test_le_porte_esistono_ancora():
    """L'analisi vale solo se parte dalle porte giuste: se una viene rinominata
    il conto crollerebbe e il test sopra lo leggerebbe come un miglioramento."""
    for p in PORTE:
        assert (PKG / f"{p}.py").exists(), (
            f"la porta {p}.py non esiste piu': il censimento sta misurando "
            f"un prodotto diverso da quello che crede")
