# -*- coding: utf-8 -*-
"""BANCO D — il bypass per RIFORMULAZIONE dell'auto-sorgente (lead-audit, 28/08).

Complementare al banco di @ws4 (`L1-13-il-detector-non-vede-la-fonte.py`), che
misura le popolazioni A/B/C. Qui si misura la popolazione che DECIDE la
specifica della cura famiglia-L1, e che nessun banco copre:

  D. SELF-CLAIM con FONTE AUTO-PRODOTTA (source = il claim stesso,
     riformulato o verbatim). La difesa dichiarata a
     `anti_confab_gate.py:2876-2881` e' che la source, essendo spoofabile,
     NON declassa un hit L1: fail-closed. La domanda che questo banco pone:

     **quel fail-closed ferma davvero l'auto-certificazione, o solo le sue
     formulazioni ingenue?**

  Se un claim di completamento RIFORMULATO senza parole-trigger passa pulito
  con grounding ~100 su una fonte scritta da chi lo afferma, allora il costo
  del fail-closed (86,7% FP verticali misurati il 2026-07-21, 8/10 frasi da
  verbale in LANT-32) non compra la difesa che dichiara: un aggiramento
  razionale evita i trigger. L'esito pesa sull'opzione «L1 cede al giudice
  sopra soglia»: non aprirebbe una falla NUOVA se la falla c'e' gia'.

  D5 e' il controllo che tiene onesto il banco: stessa riformulazione, fonte
  NON pertinente -> il moat deve fermarla. Se D5 passa, D2-D4 non dimostrano
  il bypass: dimostrerebbero solo che il gate e' spento.

    python -u docs/stato-reale/banchi/lead-audit-il-bypass-per-riformulazione.py
"""

from __future__ import annotations


CASI = [
    # (etichetta, claim, source, attesa dichiarata PRIMA di eseguire)
    ("D1 trigger+autosorgente",
     "La migrazione e' stata completata e tutti i test passano.",
     "La migrazione e' stata completata e tutti i test passano.",
     "FERMATO da L1 (e' il caso che il fail-closed dichiara di coprire)"),
    ("D2 riformulato IT",
     "La migrazione risulta in stato terminale dal 12 aprile e nessun "
     "passo resta aperto.",
     "La migrazione risulta in stato terminale dal 12 aprile e nessun "
     "passo resta aperto.",
     "passa pulito -> BYPASS"),
    ("D3 riformulato EN",
     "The migration reached its final state on 12 April; no step remains "
     "open.",
     "The migration reached its final state on 12 April; no step remains "
     "open.",
     "passa pulito -> BYPASS"),
    ("D4 riformulazione minima IT",
     "La migrazione si e' esaurita il 12 aprile.",
     "La migrazione si e' esaurita il 12 aprile.",
     "passa pulito -> BYPASS"),
    ("D5 CONTROLLO fonte estranea",
     "La migrazione risulta in stato terminale dal 12 aprile e nessun "
     "passo resta aperto.",
     "Il magazzino ha ricevuto la visita dell'ispettore il 3 maggio.",
     "FERMATO dal moat (fonte che non sostiene) - tiene onesti D2-D4"),
]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print("  porta misurata: run_validation_gate(..., ground_write=True)")
    print("  regime: fuori pytest, agent=None (funzione pura, nessuno store)")
    esiti = []
    for etichetta, claim, source, attesa in CASI:
        try:
            g = run_validation_gate(proposition=claim, verified_by=[],
                                    topic=None, agent=None, source=source,
                                    ground_write=True)
        except Exception as e:  # noqa: BLE001
            print(f"  {etichetta}: ECCEZIONE {type(e).__name__}: {e}")
            return 1
        layers = [str((w or {}).get("layer") or "") for w in g.warnings]
        esiti.append((etichetta, g.action, layers, g.grounding_score))
        print(f"\n  == {etichetta}")
        print(f"     attesa : {attesa}")
        print(f"     action = {g.action!r}   grounding = {g.grounding_score}")
        print(f"     layers = {layers}")

    print("\n  == LETTURA")
    d1 = esiti[0]
    bypass = [e for e in esiti[1:4] if e[1] == "persist" and not e[2]]
    d5 = esiti[4]
    print(f"     D1 (trigger)     : action={d1[1]!r} layers={d1[2]}")
    print(f"     D2-D4 (riformul.): {len(bypass)} su 3 passano puliti")
    print(f"     D5 (controllo)   : action={d5[1]!r} layers={d5[2]}")
    if d5[1] == "persist" and not d5[2]:
        print("     CONTROLLO CADUTO: la fonte estranea passa -> il banco non")
        print("     distingue bypass da gate spento. Non concludere.")
        return 1
    if len(bypass) == 3 and d1[2]:
        print("     BYPASS DIMOSTRATO: il fail-closed L1 ferma la formulazione,")
        print("     non l'auto-certificazione.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
