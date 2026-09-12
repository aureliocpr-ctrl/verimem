"""Le tre grandezze del contratto del rilascio, misurate sul tip di oggi.

Pronto da eseguire: chi lo lancia è l'operatore, non chi l'ha scritto.

    python scripts/le_tre_misure_del_contratto.py <data_dir>

⚠️ LE TRE MISURE NON SONO OMOGENEE, ed è la prima cosa che questo script dice
invece di nasconderla dietro tre righe di tabella:

    1. fatti scritti e mai serviti   -> una QUERY, sola lettura, sempre misurabile
    2. composte vere quarantenate    -> un BANCO: serve un insieme etichettato e
                                        il giudice acceso (inferenza pesante)
    3. scritture non giudicate        -> un SERVER in esecuzione: si osserva il
                                        journal di scritture vere

⇒ Una sola di esse si legge dal corpus. Le altre due hanno delle PRECONDIZIONI,
e questo script le verifica e le DICHIARA: se manca, la misura non viene
stimata, viene marcata NON MISURABILE QUI con scritto cosa serve. **Un numero
inventato per riempire la terza riga della tabella sarebbe peggio di una riga
vuota** — chi legge un cruscotto crede ai numeri che ci trova.

🔑 E L'USCITA LO RIFLETTE: `EXIT=0` solo se **tutte e tre** hanno un numero
misurato qui. Se una è NON MISURABILE l'uscita è 1, perché una tabella con un
buco non deve poter passare per completa in una pipeline.
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import sqlite3
import sys

#: Le soglie del contratto, come sono scritte nel quadro del rilascio. Sono
#: BERSAGLI, non misure: stanno qui per essere confrontate, e il confronto è
#: stampato accanto al numero.
SOGLIE = {
    "mai_serviti_pct": 2.0,
    "composte_quarantenate": 10,
    "scritture_non_giudicate": 0,
}

#: Gli stati che NON tornano da un recupero ordinario (la stessa lista che usa
#: lo script gemello: si cita, non si ricopia il criterio).
STATI_MUTI = ("quarantined",)


def _ora() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── misura 1 ────────────────────────────────────────────────────────────────

def misura_uno(db: pathlib.Path) -> dict:
    """Quanti fatti, di quelli scritti, tornano davvero a chi li chiede.

    ⚠️ Il numero da solo INGANNA, ed è il motivo per cui qui è scomposto: la
    perdita è la somma di cose diverse — potatura voluta, moat che fa il suo
    mestiere, ritiri del percorso di scrittura — e solo una di esse è un
    difetto da curare. Lo script della scomposizione lo dice in dettaglio;
    qui si riporta il totale E le sue parti, mai il totale da solo.
    """
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    uno = lambda sql, *a: con.execute(sql, a).fetchone()[0]  # noqa: E731

    scritti = uno("SELECT COUNT(*) FROM facts")
    ritirati = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL")
    muti = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
               "AND status = ?", STATI_MUTI[0])
    voluti = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL "
                 "AND (superseded_reason LIKE 'autohook-snapshot%' "
                 "     OR superseded_reason LIKE 'exact-text dedup%')")
    scrittura = uno("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL "
                    "AND (superseded_reason LIKE 'same-source evolution%' "
                    "     OR superseded_reason LIKE 'heal_contradictions%')")
    con.close()

    perduti = ritirati + muti
    pct = perduti * 100.0 / scritti if scritti else 0.0
    return {
        "nome": "fatti scritti e mai serviti",
        "misurata": True,
        "valore": pct,
        "unita": "%",
        "soglia": SOGLIE["mai_serviti_pct"],
        "dettaglio": {
            "scritti": scritti,
            "perduti": perduti,
            "di cui potatura VOLUTA (non è perdita)": voluti,
            "di cui moat (è la promessa, non un difetto)": muti,
            "di cui ritiri del percorso di scrittura (CURABILE)": scrittura,
        },
    }


# ─── misura 2 ────────────────────────────────────────────────────────────────

def misura_due(radice: pathlib.Path) -> dict:
    """Quante affermazioni composte VERE finiscono in quarantena.

    Precondizioni, verificate e non assunte: (a) un insieme etichettato di
    composte vere e false; (b) il giudice locale acceso. Senza (a) non c'è
    nulla da misurare; senza (b) il numero misurerebbe l'assenza del giudice.
    """
    cartella = radice / "docs" / "stato-reale" / "banchi"
    insiemi = sorted(cartella.glob("*.jsonl")) if cartella.exists() else []
    manca = []
    if not insiemi:
        manca.append("un insieme etichettato di composte vere/false (.jsonl)")
    try:
        from verimem.local_grounding import get_local_threshold
        if get_local_threshold() is None:
            manca.append("il giudice locale (nessuna soglia calibrata)")
    except Exception as exc:  # noqa: BLE001 — la precondizione si DICHIARA
        manca.append(f"il giudice locale non è importabile: {exc}")

    if manca:
        return {
            "nome": "composte vere quarantenate",
            "misurata": False,
            "soglia": SOGLIE["composte_quarantenate"],
            "serve": manca,
            "come": ("far girare il gate sull'insieme etichettato e contare "
                     "quante composte VERE finiscono 'quarantined'; è "
                     "inferenza pesante, va in coda a un operatore e mai "
                     "mentre gira un altro banco"),
        }
    return {
        "nome": "composte vere quarantenate",
        "misurata": False,
        "soglia": SOGLIE["composte_quarantenate"],
        "serve": ["l'esecuzione del gate sull'insieme (non la fa questo script: "
                  "è inferenza pesante e va lanciata da sola)"],
        "come": f"insiemi disponibili: {[p.name for p in insiemi][:4]}",
    }


# ─── misura 3 ────────────────────────────────────────────────────────────────

def misura_tre(data_dir: pathlib.Path) -> dict:
    """Quante scritture entrano SENZA che nessuno le abbia giudicate.

    Si osserva dal journal delle scritture vere (`flow.write` porta `judged`),
    non da una simulazione: una scrittura giudicata in un banco isolato non
    dice niente su quelle che l'utente fa davvero.
    """
    journal = data_dir / "events.jsonl"
    if not journal.exists():
        return {
            "nome": "scritture non giudicate",
            "misurata": False,
            "soglia": SOGLIE["scritture_non_giudicate"],
            "serve": [f"il journal degli eventi ({journal.name}) nella data dir"],
            "come": ("contare gli eventi `flow.write` con `judged=false` in una "
                     "finestra dichiarata; il campo esiste e non si stima"),
        }
    import json
    scritture = giudicate = 0
    with journal.open(encoding="utf-8", errors="replace") as f:
        for riga in f:
            if '"flow.write"' not in riga:
                continue
            try:
                ev = json.loads(riga)
            except Exception:  # noqa: BLE001 — una riga rotta non è una misura
                continue
            p = ev.get("payload") or ev
            if p.get("name") == "flow.write" or "judged" in p:
                scritture += 1
                if p.get("judged"):
                    giudicate += 1
    if scritture == 0:
        return {
            "nome": "scritture non giudicate",
            "misurata": False,
            "soglia": SOGLIE["scritture_non_giudicate"],
            "serve": ["almeno un evento `flow.write` nel journal: qui ce ne "
                      "sono zero, e «zero scritture» non è «zero non "
                      "giudicate»"],
            "come": "far fare all'utente (o a un banco alla porta) una scrittura",
        }
    return {
        "nome": "scritture non giudicate",
        "misurata": True,
        "valore": scritture - giudicate,
        "unita": "scritture",
        "soglia": SOGLIE["scritture_non_giudicate"],
        "dettaglio": {"scritture osservate": scritture,
                      "giudicate": giudicate,
                      "finestra": f"tutto {journal.name}"},
    }


# ─── stampa ──────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("data_dir", help="la data dir (contiene semantic/semantic.db)")
    a = p.parse_args(argv)

    base = pathlib.Path(a.data_dir)
    db = base / "semantic" / "semantic.db"
    if not db.exists():
        print(f"database non trovato: {db}", file=sys.stderr)
        return 2
    radice = pathlib.Path(__file__).resolve().parents[1]

    print(f"  istante  {_ora()}")
    print(f"  corpus   {base}\n")

    misure = [misura_uno(db), misura_due(radice), misura_tre(base)]
    mancanti = 0
    for m in misure:
        print(f"  ── {m['nome']}")
        if m["misurata"]:
            v, s = m["valore"], m["soglia"]
            verso = "SOTTO" if v <= s else "SOPRA"
            print(f"     {v:.1f}{m.get('unita', '')}   bersaglio {s}   → {verso}")
            for k, val in (m.get("dettaglio") or {}).items():
                print(f"        {k}: {val}")
        else:
            mancanti += 1
            print(f"     NON MISURABILE QUI   (bersaglio {m['soglia']})")
            for s in m["serve"]:
                print(f"        serve: {s}")
            print(f"        come : {m['come']}")
        print()

    if mancanti:
        print(f"  🔴 {mancanti} misure su 3 non sono state misurate qui: la "
              f"tabella NON è il quadro del contratto.", file=sys.stderr)
        return 1
    print("  ✅ tutte e tre misurate in questa esecuzione")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
