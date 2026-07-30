"""Il codice che nessuno puo' eseguire non cresce in silenzio.

Aurelio, 2026-07-31: «come mai quando sviluppi un modulo finisce sempre per non
essere collegato a nulla? parli di import, test verdi, e mesi dopo ci accorgiamo
che e' tutto spento».

La risposta misurata: **66 moduli su 372 non sono raggiungibili** da nessuna
delle quattro porte del prodotto — la CLI, il server MCP, l'SDK, il gateway —
seguendo gli import a qualsiasi profondita'. Il 18%. Possono avere i test verdi
e non essere mai eseguiti da nessun utente, che e' esattamente il modo in cui il
moat e' rimasto spento sul canale MCP per mesi.

Questo file non pretende di curare i 66: congela il numero. Un modulo NUOVO che
nasce staccato fa fallire il test il giorno stesso, invece di scoprirsi mesi
dopo. E' la sola cura che regge, perche' la disciplina non ha retto: la lezione
«built-never-wired» era gia' scritta in memoria da un ciclo precedente, ed e'
stata rifatta lo stesso.

Metodo: si legge il sorgente con ``ast``, non a runtime. Questo repo mette gli
import DENTRO le funzioni per rompere i cicli, e un'analisi che guardasse solo
la testa dei file dichiarerebbe irraggiungibile mezzo prodotto.

Sui 66 non tutti sono difetti, e la distinzione va fatta guardandoli:
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
PORTE = ("cli", "mcp_server", "client", "gateway")

#: Misurato il 2026-07-31. Il numero puo' SCENDERE quando si collega o si
#: cancella qualcosa; se sale, un modulo e' nato staccato e il test lo dice
#: subito. Non e' un obiettivo di qualita': e' un cricchetto.
IRRAGGIUNGIBILI_NOTI = 66


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


def _irraggiungibili() -> list[str]:
    moduli = {p.stem for p in PKG.glob("*.py")
              if not p.stem.startswith(("_", "test_")) and p.stem != "__init__"}
    raggiunti = {p for p in PORTE if (PKG / f"{p}.py").exists()}
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


def test_le_porte_esistono_ancora():
    """L'analisi vale solo se parte dalle porte giuste: se una viene rinominata
    il conto crollerebbe e il test sopra lo leggerebbe come un miglioramento."""
    for p in PORTE:
        assert (PKG / f"{p}.py").exists(), (
            f"la porta {p}.py non esiste piu': il censimento sta misurando "
            f"un prodotto diverso da quello che crede")
