# -*- coding: utf-8 -*-
"""IL PARAGONE: una riga di `docs/GOVERNANCE.md` contro il corpus di oggi.

`docs/GOVERNANCE.md:373-377`, scritta il 05/08 22:56 (commit `398bd0a8`), dice
verbatim:

    Measured breadth: `reason` is None on 500/500 records and `layers` empty on
    183/500, because the deciding layer is computed at write time and not
    persisted. Persisting it is a write-path column and stays open.

Due giorni dopo — 07/08 13:31, commit `d47c5581` «quarantena: la causa viveva
solo nella ricevuta, ora sopravvive nel database» — la colonna E' STATA
persistita (`semantic.py:2644`, `ALTER TABLE facts ADD COLUMN quarantined_by
TEXT`), e `quarantine_log` la legge (`client.py:2621`, e `:2654-2657` la usa per
riempire `layers` quando l'audit trail manca).

⇒ La clausola «stays open» e' quindi SMENTITA DAL CODICE. Ma leggere il codice
dice cosa il prodotto INTENDE fare, non cosa i 500 record MOSTRANO: la colonna
non e' retroattiva (lo dice il docstring a `client.py:2670`), quindi puo'
esistere, essere letta, e i record vecchi restare comunque vuoti. **Quale dei
due numeri di GOVERNANCE e' superato, e di quanto, si decide solo rimisurando.**

Rimisuro con LO STESSO RIGHELLO: `quarantine_log`, i campi `reason` e `layers`,
la stessa taglia 500.

⚠️ Le DUE viste che il documento non separa — `explain=False` (la vista nuda) ed
`explain=True` (che RICALCOLA il motivo rieseguendo i detector lessicali) — si
chiedono in DUE PROCESSI SEPARATI, perche' il ricalcolo su 500 righe NON finisce
in 10 minuti (misurato 28/08 22:07→22:17, ucciso, exit 143) e un processo che
muore a meta' non lascia una misura: lascia un buco che si legge come uno zero.

CONTROLLI CHE POSSONO FALLIRE — tutti e tre:
 (1) se `reason` esce None su tutte le righe anche col ricalcolo, la riga di
     GOVERNANCE REGGE e il mio finding cade. Lo dico.
 (2) `quarantine_log` per costruzione restituisce [] su uno store illeggibile
     («an unreadable store shows empty, not 500», `client.py:2628`): zero righe
     NON e' una misura, e' un'assenza. La tratto come ERRORE.
 (3) dichiaro il percorso del DB da `CONFIG.semantic_db` — su questa macchina ci
     sono DUE `semantic.db` e quello al percorso ovvio e' vuoto.

    python -u <banco> nuda 500
    python -u <banco> spiegata 25
"""

from __future__ import annotations

import sys
import time

TAGLIA = 500  # la stessa di GOVERNANCE

# I numeri che la riga di governo afferma, per confrontarli senza riscriverli.
GOV_REASON_NONE = 500  # su 500
GOV_LAYERS_VUOTI = 183  # su 500


def _conta(rows):
    n = len(rows)
    reason_none = sum(1 for r in rows if not r.get("reason"))
    layers_vuoti = sum(1 for r in rows if not r.get("layers"))
    qb_pieno = sum(1 for r in rows if (r.get("quarantined_by") or "").strip())
    return {
        "n": n,
        "reason_none": reason_none,
        "reason_pieno": n - reason_none,
        "layers_vuoti": layers_vuoti,
        "layers_pieni": n - layers_vuoti,
        "qb_pieno": qb_pieno,
    }


def _stampa(tag, c):
    print(f"     righe            : {c['n']}")
    print(f"     reason None      : {c['reason_none']} su {c['n']}"
          f"   (GOVERNANCE: {GOV_REASON_NONE} su 500)")
    print(f"     layers vuoti     : {c['layers_vuoti']} su {c['n']}"
          f"   (GOVERNANCE: {GOV_LAYERS_VUOTI} su 500)")
    print(f"     quarantined_by   : {c['qb_pieno']} su {c['n']} pieni"
          f"   <- la colonna aggiunta il 07/08")


def main():
    modo = (sys.argv[1] if len(sys.argv) > 1 else "nuda").strip()
    taglia = int(sys.argv[2]) if len(sys.argv) > 2 else TAGLIA

    try:
        from verimem import client as _client
        from verimem.client import Memory
        from verimem.config import CONFIG
    except Exception as e:
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print(f"  codice sotto misura: {_client.__file__}")
    print(f"  CONFIG.semantic_db : {CONFIG.semantic_db}")
    print(f"  modo={modo}  taglia={taglia}")

    t0 = time.time()
    m = Memory()
    print(f"  costruzione Memory(): {time.time() - t0:.1f} s")

    if modo == "nuda":
        print(f"\n  == [A] LA VISTA NUDA - quarantine_log(limit={taglia})")
        t = time.time()
        rows = m.quarantine_log(limit=taglia)
        dt = time.time() - t
        c = _conta(rows)
        _stampa("A", c)
        print(f"     COSTO            : {dt:.2f} s")
    else:
        print(f"\n  == [B] LA VISTA CHE RICALCOLA - quarantine_log("
              f"limit={taglia}, explain=True)")
        print("     (rilegge le stesse righe e riesegue i detector lessicali)")
        t = time.time()
        rows = m.quarantine_log(limit=taglia, explain=True)
        dt = time.time() - t
        c = _conta(rows)
        _stampa("B", c)
        print(f"     COSTO            : {dt:.2f} s per {taglia} righe"
              f"  ({dt / max(1, taglia):.2f} s/riga)")

    print("\n  -- CONTROLLO (2): zero righe non e' una misura")
    if c["n"] == 0:
        print("     CADUTO - la vista e' vuota. Su uno store illeggibile"
              " quarantine_log restituisce [] per costruzione,")
        print("     quindi questo NON dice '0 quarantinati': dice che non ho"
              " misurato niente.")
        return 1
    print(f"     retto - {c['n']} righe lette, la vista ha risposto")

    print("\n  -- CONTROLLO (1): la riga di GOVERNANCE regge o no?")
    if c["reason_none"] == c["n"]:
        print(f"     su `reason` LA RIGA REGGE - None su {c['n']}/{c['n']}"
              f" in modo={modo}.")
    else:
        print(f"     su `reason` LA RIGA E' SUPERATA - {c['reason_pieno']}"
              f" righe su {c['n']} PORTANO un motivo,")
        print(f"     mentre il documento afferma None su {GOV_REASON_NONE}"
              " su 500.")
    quota_gov = GOV_LAYERS_VUOTI / 500.0
    quota_ora = c["layers_vuoti"] / max(1, c["n"])
    print(f"     su `layers` vuoti: documento {GOV_LAYERS_VUOTI}/500"
          f" = {quota_gov:.1%}   ora {c['layers_vuoti']}/{c['n']}"
          f" = {quota_ora:.1%}")

    print("\n  -- UN CAMPIONE, perche' un conteggio non mostra la forma")
    mostrati = 0
    for r in rows:
        if r.get("reason") or r.get("layers"):
            print(f"     layers={r.get('layers')}  qb={r.get('quarantined_by')!r}")
            print(f"       reason: {str(r.get('reason'))[:140]}")
            mostrati += 1
            if mostrati >= 3:
                break
    if mostrati == 0:
        print("     nessuna riga porta ne' reason ne' layers.")

    print("\n  -- CONTROLLO (3): il percorso del DB e' dichiarato, non dedotto")
    print(f"     {CONFIG.semantic_db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
