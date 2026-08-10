"""tier_inventory — dove vive ogni tier, quante righe ha, e quali file
si spacciano per lui.

Misurato il 2026-08-05: contando le cinque tabelle delle entità dentro
``semantic.db`` si trovano a zero, e da lì si conclude «il tier entità è
vuoto» — conclusione che ha fatto abbandonare una direzione di lavoro. Il
tier sta altrove e non è vuoto::

    ~/.engram/semantic/semantic.db     entities 0        (guscio di migrazione)
    ~/.engram/entity_kg/entity_kg.db   entities 9078 · entity_edges 87387

E non è un caso isolato: nella radice della data dir c'è **un doppione
vuoto per quasi ogni tier**, con il nome più ovvio, accanto a quello vero
annidato — ``episodes.db`` 0.0 MB contro ``episodes/episodes.db`` 17.6,
``semantic.db`` 0.1 contro ``semantic/semantic.db`` 86.7. La stessa
trappola è in memoria da luglio con parole quasi identiche («il layout
nested è quello vero; quello flat è uno scheletro vuoto e leggerlo dà 0»)
e nessuna superficie del prodotto la dichiarava: ``verimem doctor`` non
dice una parola su dove viva un tier, quindi l'unico modo di saperlo era
contare i file a mano — cioè cadere nella buca.

🔑 **Un contenitore vuoto e un contenitore assente danno lo stesso
numero, e solo il secondo si fa notare.** Da qui le tre scelte:

- i percorsi si prendono dal PRODOTTO (la struttura di ``CONFIG`` e i
  risolutori dei moduli), non si riscrivono qui: un inventario che
  indovina dove stiano i dati è un'altra ipotesi, cioè la cosa da curare;
- uno store assente vale ``"unavailable"``, **mai** ``0`` — zero è
  esattamente la risposta sbagliata che ha fatto ritirare una direzione;
- i doppioni si NOMINANO invece di evitarli: ogni tier elenca i file
  vicini che portano il suo nome, con le loro righe, così chi legge vede
  la trappola invece di caderci.

Sola lettura: apre ogni store in ``mode=ro`` e non crea niente.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

__all__ = ["tier_inventory"]

#: I nomi che un file può avere nella radice della data dir e che un
#: umano (o un agente) leggerebbe come «questo è il tier X». Sono i file
#: realmente presenti nella data dir di casa il 2026-08-05, tutti vuoti.
_ESCHE: dict[str, tuple[str, ...]] = {
    "facts": ("semantic.db", "facts.db", "memory.db", "hippo.db",
              "engram.db"),
    "entities": ("entities.db", "entity_kg.db", "engram_kg.db"),
    "episodes": ("episodes.db", "episodic.db"),
    "skills": ("skills.db", "skills_index.db"),
    "documents": ("documents.db",),
}


def _conta(db: Path, tabella: str) -> int | str:
    """Righe della tabella, o una DICHIARAZIONE di cosa manca.

    Tre esiti distinti e mai confusi con lo zero: il file non c'è, il
    file c'è ma la tabella no (è il guscio di migrazione), il file non si
    apre. Uno zero vero — store presente, tabella presente, nessuna riga
    — resta zero, ed è un'informazione diversa da tutte e tre.
    """
    if not db.exists():
        return "unavailable"
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return "unavailable"
    try:
        return int(con.execute(f"SELECT COUNT(*) FROM {tabella}").fetchone()[0])
    except sqlite3.Error:
        # tabella assente: il file esiste ma di questo tier non sa nulla
        return "unavailable"
    finally:
        con.close()


def _percorsi(root: Path) -> list[dict[str, Any]]:
    """I cinque tier con lo store che il PRODOTTO apre davvero.

    La struttura interna si legge da ``CONFIG`` (relativa alla sua
    ``data_dir``) invece di essere riscritta qui: se un giorno il layout
    cambia, l'inventario segue senza che nessuno se ne ricordi. Per
    entità e documenti la struttura la sanno i loro moduli, e si chiede a
    loro con la stessa logica di derivazione che usano in produzione.
    """
    from .config import CONFIG
    from .entity_populate import entity_kg_path_for

    def _come_config(campo: Path, difetto: str) -> Path:
        try:
            return root / Path(campo).resolve().relative_to(
                Path(CONFIG.data_dir).resolve())
        except (ValueError, OSError):
            return root / difetto

    sem = _come_config(CONFIG.semantic_db, "semantic/semantic.db")
    return [
        {"tier": "facts", "store": sem, "table": "facts"},
        # NON semantic.db: il grafo vive in un file suo, e le tabelle
        # omonime dentro semantic.db sono un residuo di migrazione
        {"tier": "entities", "store": entity_kg_path_for(sem),
         "table": "entities"},
        {"tier": "episodes",
         "store": _come_config(CONFIG.episodes_db, "episodes/episodes.db"),
         "table": "episodes"},
        {"tier": "skills",
         "store": _come_config(CONFIG.skills_db, "skills/skills_index.db"),
         "table": "skills"},
        {"tier": "documents", "store": root / "documents" / "documents.db",
         "table": "documents"},
        # I QUATTRO che l'inventario saltava, trovati contando invece che
        # indovinando (il 2026-08-06 una sonda sulle decisioni ne ha trovate
        # che qui non comparivano). Un inventario che salta un tier e' il
        # difetto che l'inventario esiste per prevenire — e `transcript.db`
        # pesa 72 MB
        # sul corpus reale, il secondo store per dimensione dopo i fatti.
        # I percorsi sono quelli che apre il prodotto: `decisions.db` e
        # `adjudications.db` stanno ACCANTO a semantic.db (client.py:1240
        # e 1263), non sotto la radice.
        {"tier": "decisions", "store": sem.with_name("decisions.db"),
         "table": "decisions"},
        # il registro di cosa il gate ha deciso e perche': governo, non
        # memoria, ma e' uno store con dei dati e la domanda «dove sta» e'
        # la stessa
        {"tier": "adjudications", "store": sem.with_name("adjudications.db"),
         "table": "adjudications"},
        {"tier": "transcripts",
         "store": root / "conversational" / "transcript.db",
         "table": "turns"},
        {"tier": "self_model", "store": root / "self_model.db",
         "table": "self_model_current"},
    ]


def _esche_di(tier: str, root: Path, vero: Path) -> list[dict[str, Any]]:
    """I file vicini che portano il nome del tier ma non sono il tier."""
    out: list[dict[str, Any]] = []
    for nome in _ESCHE.get(tier, ()):
        cand = root / nome
        if not cand.exists() or cand.resolve() == vero.resolve():
            continue
        tab = next(t["table"] for t in _percorsi(root) if t["tier"] == tier)
        out.append({"path": str(cand), "rows": _conta(cand, tab),
                    "size_mb": round(cand.stat().st_size / 1e6, 2)})
    return out


def tier_inventory(*, data_dir: Path | str | None = None,
                   with_decoys: bool = True) -> dict[str, Any]:
    """Per ogni tier: il file in cui vive, quante righe ha, e i doppioni.

    Args:
        data_dir: radice da ispezionare. ``None`` = quella del prodotto
            (``CONFIG.data_dir``), cioè quella che sta usando adesso.
        with_decoys: elenca i file omonimi vicini. Lasciarlo acceso è il
            punto di questo modulo; si spegne solo dove serve la sola
            riga di conteggio.

    Returns:
        ``{"data_dir": str, "tiers": [{"tier", "store", "rows",
        "decoys"?}], "note": str}``. ``rows`` è un intero oppure la
        stringa ``"unavailable"`` — mai ``0`` per uno store che non c'è.
    """
    from .config import CONFIG
    root = Path(data_dir) if data_dir is not None else Path(CONFIG.data_dir)
    tiers: list[dict[str, Any]] = []
    for t in _percorsi(root):
        riga: dict[str, Any] = {"tier": t["tier"], "store": str(t["store"]),
                                "counted_in": t["table"],
                                "rows": _conta(t["store"], t["table"])}
        if with_decoys:
            riga["decoys"] = _esche_di(t["tier"], root, t["store"])
        tiers.append(riga)
    return {
        "data_dir": str(root),
        "tiers": tiers,
        "note": ("rows='unavailable' means the store or its table is "
                 "absent — NEVER 0, because an empty container and a "
                 "missing one return the same number and only the second "
                 "announces itself. `decoys` are files next to the real "
                 "store carrying the tier's obvious name: on the home "
                 "corpus 2026-08-05 counting one of those produced "
                 "'the entity tier is empty' while the tier held 9078 "
                 "entities and 87387 edges."),
    }
