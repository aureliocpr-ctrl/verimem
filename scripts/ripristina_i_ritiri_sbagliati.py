"""Rimette in vita i fatti che il criterio di OGGI non ritirerebbe.

IL TEMA CHE TORNA DA GIORNI. Le cure di verimem valgono in avanti: la guardia
sull'evoluzione (`1f059d53`, `caa0e87c`) impedisce che due osservazioni
scorrelate si ritirino a vicenda, ma i ritiri GIA' AVVENUTI restano. Misurato
il 2026-08-01: **32 su 257** coppie corte erano ritiri che il criterio attuale
non farebbe.

E' lo stesso pattern di `pota_entita_funzionali.py`: applicare al pregresso il
criterio della cura, senza inventarne uno nuovo. Qui la domanda e' una sola —
`_puo_essere_una_evoluzione(nuovo, vecchio)` direbbe di si' oggi? Se no, quel
ritiro non sarebbe avvenuto, e il fatto torna vivo.

DUE PRUDENZE, entrambe necessarie.

1. IL CRITERIO E' CIECO SUI FATTI LUNGHI e va detto invece di lasciarlo
   credere: le coppie riconosciute come evoluzione hanno mediana 2498 char,
   quelle bocciate 165 — su 2498 caratteri due parole condivise capitano
   sempre. Quindi si guardano solo le coppie CORTE (entrambi sotto
   `--max-char`, default 200), dove il criterio vede davvero. Il numero
   onesto e' 32 su 257, non 49 su 1783.

2. NON SI TOCCA UNA CATENA. Se il fatto ritirato ha a sua volta un
   successore, o se il successore e' stato a sua volta superseduto, il
   ripristino rimetterebbe in vita un anello nel mezzo di una storia. Si
   ripristina solo il caso semplice: A superseduto da B, B vivo, A senza
   altri successori.

DRY-RUN DI DEFAULT. Questo tocca il corpus vero, non un indice derivato:
senza `--apply` misura, elenca e non scrive niente.

    python scripts/ripristina_i_ritiri_sbagliati.py
    python scripts/ripristina_i_ritiri_sbagliati.py --apply
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sqlite3
import sys
from pathlib import Path


def _adesso() -> str:
    """L'istante in ISO, per il registro della riparazione.

    UTC e non ora locale: il registro viene letto anche da chi non sa in che
    fuso girava lo script, e una riga di audit senza fuso è una riga che si
    può interpretare in due modi.
    """
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verimem.anti_confab_gate import _puo_essere_una_evoluzione  # noqa: E402

SEM = Path.home() / ".engram" / "semantic" / "semantic.db"


def _coppie(con: sqlite3.Connection, max_char: int):
    """(vecchio_id, testo_vecchio, testo_nuovo) per le coppie CORTE e SEMPLICI."""
    testi = {i: (p or "") for i, p in con.execute(
        "SELECT id, proposition FROM facts")}
    successori = {}
    for vecchio, nuovo in con.execute(
            "SELECT id, superseded_by FROM facts WHERE superseded_by IS NOT NULL"):
        successori[vecchio] = nuovo
    fuori = []
    for vecchio, nuovo in successori.items():
        a, b = testi.get(vecchio, ""), testi.get(nuovo, "")
        if not a or not b:
            continue
        if len(a) >= max_char or len(b) >= max_char:
            continue                      # il criterio qui e' cieco
        if nuovo in successori:
            continue                      # il successore e' a sua volta ritirato
        fuori.append((vecchio, a, b))
    return fuori


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-char", type=int, default=200)
    ap.add_argument("--db", default=str(SEM))
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"nessuno store in {db}")
        return 1

    con = sqlite3.connect(str(db))
    try:
        coppie = _coppie(con, args.max_char)
        sbagliati = [(v, a, b) for v, a, b in coppie
                     if not _puo_essere_una_evoluzione(b, a)]

        print(f"coppie corte e semplici esaminate: {len(coppie)}")
        print(f"ritiri che il criterio di oggi NON farebbe: {len(sbagliati)}")
        for _v, a, b in sbagliati[:10]:
            print(f"\n   ritirato: {a[:88]}")
            print(f"   dal     : {b[:88]}")
        if len(sbagliati) > 10:
            print(f"\n   … e altri {len(sbagliati) - 10}")

        if not sbagliati:
            print("niente da ripristinare")
            return 0
        if not args.apply:
            print("\nDRY-RUN: niente e' stato scritto. `--apply` per "
                  "ripristinare.")
            return 0

        # A GIRI, FINO A CONVERGENZA. Ogni ripristino puo' rendere SEMPLICE
        # una coppia che prima era una catena — il successore era a sua volta
        # ritirato, e la regola qui sopra la salta — quindi un passo solo ne
        # lascia indietro. Misurato sul corpus vero: 15, poi 4, 2, 4, 2, 4, 3
        # e infine 0, per un totale di 34. Converge perche' ogni giro accorcia
        # le catene e non ne crea di nuove.
        # ⚠️ SI AZZERANO TUTTI E TRE I CAMPI, non due. Fino al 2026-08-13 questo
        # UPDATE lasciava `superseded_reason` valorizzato: il fatto tornava vivo
        # PORTANDOSI DIETRO IL MOTIVO PER CUI ERA STATO RITIRATO, e diceva quindi
        # il falso su se stesso. Misurato sul corpus vero prima della cura::
        #
        #     vivi (superseded_by NULL) con superseded_reason valorizzato:  38
        #       29  «same-source evolution»        \  34 = i residui di questo
        #        5  «heal_contradictions: …»       /       script, e il numero
        #                                                  coincide col totale
        #                                                  scritto qui sopra
        #        2  «memory-poisoning-shape: kept as research evidence»
        #        2  «auto-mode … test 2026-05-18»  ⇐ NON sono residui: sono
        #                                            marcature INTENZIONALI
        #
        # 📌 Le ultime quattro spiegano perché la cura sta QUI e non in una
        # query di pulizia sul database: il campo è usato per due cose diverse
        # — «perché è stato ritirato» e «perché è tenuto pur essendo strano» —
        # e solo chi ripristina sa quali righe ha toccato.
        registro: list[tuple[str, str]] = []
        totale = 0
        for giro in range(1, 21):
            ids = [v for v, _, _ in sbagliati]
            if not ids:
                break
            q = ",".join("?" * len(ids))
            # il motivo si legge PRIMA di cancellarlo: è ciò che rende la
            # riparazione raccontabile invece che solo avvenuta.
            for fid, motivo in con.execute(
                    f"SELECT id, superseded_reason FROM facts WHERE id IN ({q})",
                    ids):
                registro.append((fid, motivo or ""))
            con.execute(
                f"UPDATE facts SET superseded_by = NULL, superseded_at = NULL, "
                f"superseded_reason = NULL WHERE id IN ({q})", ids)
            con.commit()
            totale += len(ids)
            print(f"  giro {giro}: {len(ids)} ripristinati")
            sbagliati = [(v, a, b) for v, a, b in _coppie(con, args.max_char)
                         if not _puo_essere_una_evoluzione(b, a)]
        print(f"\nripristinati {totale} fatti: tornano nel recall di default")

        # ⚠️ E LA RIPARAZIONE SI REGISTRA, che era l'altra metà del difetto:
        # lo script scriveva sul database e non lasciava traccia di che cosa
        # avesse toccato, quindi il giorno dopo nessuno poteva distinguere un
        # fatto mai ritirato da uno ripristinato — né sapere perché era stato
        # ritirato prima. Il registro va su file accanto allo store, non a
        # video: un output di terminale non sopravvive alla sessione.
        if registro:
            traccia = db.parent / "ripristini.log"
            with traccia.open("a", encoding="utf-8") as fh:
                for fid, motivo in registro:
                    fh.write(f"{_adesso()}\t{fid}\tripristinato\t{motivo}\n")
            print(f"registro della riparazione: {traccia} "
                  f"(+{len(registro)} righe)")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
