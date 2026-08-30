"""IL COSTO ALLA PORTA DELL'APOSTROFO — il limite dichiarato in `W7-73`, pagato.

`W7-73` ha misurato che **174 fatti vivi** perdono il soggetto perche' scrivono
`e'` invece di `è`, e che su un campione **17 su 24** diventano `DOMAIN`
appena si mette l'accento. E ha dichiarato il limite, che e' sostanziale::

    `DOMAIN` e' condizione NECESSARIA della carve-out, NON sufficiente: serve
    anche che `L1` si accenda e che nessun altro veto intervenga. Il costo VERO
    alla porta e' un'altra misura.

⇒ **~123 e' il numero di fatti la cui CLASSIFICAZIONE cambia, non di fatti il
cui ESITO cambia.** Questa misura trasforma il primo nel secondo.

⚠️⚠️ **E LA DOMANDA VA POSTA BENE, altrimenti da' ZERO PER COSTRUZIONE** — e'
la lezione di `W7-71`, applicata prima di sbagliare: quei fatti sono in larga
parte `narrative`, e su un `narrative` **la porta salta `L1`** (`narrative_l1_skip`).
Misurare \"alla porta\" cosi' com'e' risponderebbe **0** senza dire niente.

🎯 **La domanda giusta e' DOPPIAMENTE controfattuale, e lo dichiaro**:

    *se quei fatti fossero scritti da una porta dove `L1` gira,
     l'apostrofo cambierebbe il loro esito?*

E' la domanda che serve a chi **decide se curare `_VERB_MARK`**: la cura vale
per il traffico su cui `L1` decide davvero — la porta della vetrina, non la
nostra. ⚠️ Su un `narrative` la cura non cambia nulla **perche' li' non cambia
nulla comunque**, e quello lo dice gia' il dossier ㉖.

CONTROLLI CHE POSSONO FALLIRE:
 (1) **la distribuzione PRIMA di dividere**: quanti dei 174 sono `narrative` e
     quanti no. Se fossero tutti `narrative`, la misura vale **solo** nel regime
     controfattuale e va detto in cima, non in fondo.
 (2) **A/B nella stessa esecuzione**, un parametro solo: la proposizione con
     `e'` contro la stessa con `è`. Nient'altro cambia.
 (3) **controllo positivo**: con `e'` almeno qualcuno deve accendere `L1`.
     Se nessuno accendesse, non ci sarebbe niente da salvare e il numero
     sarebbe zero per una ragione che non e' l'apostrofo.

    python -u docs/stato-reale/banchi/il-costo-alla-porta-dell-apostrofo.py
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys

APO = re.compile(r"\be'(?=\s)")
CAMPIONE = 24


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.config import CONFIG
        from verimem.subject_extract import subject_of
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select id, proposition, grounding_span, writer_role, verified_by, "
        "topic, meta_narrative from facts where superseded_by is null"
    ).fetchall()
    print(f"  popolazione: {len(righe)} fatti VIVI")

    # i 174 di `W7-73`: soggetto vuoto con `e'` e risolto con `è`
    persi = [r for r in righe
             if APO.search(r[1] or "")
             and not subject_of(r[1] or "")
             and subject_of(APO.sub("è", r[1] or ""))]
    print(f"  perdono il soggetto per l'apostrofo: {len(persi)}")
    if not persi:
        print("NON RIUSCITO: popolazione vuota.")
        return 1

    print("\n  -- CONTROLLO (1): LA DISTRIBUZIONE, prima di dividere")
    d: dict[object, int] = {}
    for r in persi:
        d[r[6]] = d.get(r[6], 0) + 1
    for k, v in sorted(d.items(), key=lambda kv: -kv[1]):
        eti = {1: "narrative (la porta salta L1)",
               0: "normale (L1 gira)"}.get(k, f"altro:{k!r}")
        print(f"     {eti:<32}{v:>5}"
              f"  ({100.0 * v / len(persi):.1f}%)")
    quanti_narr = d.get(1, 0)
    if quanti_narr == len(persi):
        print("     ⚠️ SONO TUTTI `narrative`: la misura sotto vale SOLO nel")
        print("     regime controfattuale (`narrative_l1_skip=False`), e questa")
        print("     riga va letta PRIMA del numero, non dopo.")

    passo = max(1, len(persi) // CAMPIONE)
    scelti = persi[::passo][:CAMPIONE]
    print(f"\n  == A/B su {len(scelti)} casi, uno ogni {passo},"
          " un parametro solo")

    def porta(testo: str, r) -> tuple[str, list[str]]:
        _fid, _p, span, wr, vb_raw, topic, _mn = r
        try:
            vb = json.loads(vb_raw or "[]")
        except Exception:  # noqa: BLE001
            vb = []
        g = run_validation_gate(
            proposition=testo, verified_by=vb, topic=topic, agent=None,
            source=span or None, writer_role=wr, narrative_l1_skip=False,
            **({"ground_write": True} if (span or "").strip() else {}))
        ws = getattr(g, "warnings", None) or []
        return (str(getattr(g, "action", None)),
                sorted({str((w or {}).get("layer") or "?") for w in ws}))

    print(f"     {'con e-apostrofo':<26}{'con e-accentata':<26}")
    acceso_apo = cambia_esito = cambia_layer = 0
    esempi = []
    for r in scelti:
        t_apo = r[1] or ""
        t_acc = APO.sub("è", t_apo)
        az_a, lay_a = porta(t_apo, r)
        az_b, lay_b = porta(t_acc, r)
        if any(x.startswith("L1") for x in lay_a):
            acceso_apo += 1
        if az_a != az_b:
            cambia_esito += 1
            if len(esempi) < 4:
                esempi.append((az_a, az_b, lay_a, lay_b, t_apo))
        if lay_a != lay_b:
            cambia_layer += 1
        print(f"     {az_a + ' [' + ','.join(lay_a) + ']':<26}"
              f"{az_b + ' [' + ','.join(lay_b) + ']':<26}")

    print("\n  -- CONTROLLO (3): con `e'` almeno qualcuno accende `L1`?")
    print(f"     accendono un layer L1: {acceso_apo} su {len(scelti)}")
    if not acceso_apo:
        print("     CADUTO - nessuno accende `L1`: non c'e' niente che la")
        print("     carve-out possa salvare, e lo zero sotto non e' dell'apostrofo.")
        return 1

    print("\n  == IL COSTO ALLA PORTA")
    print(f"     cambiano i LAYER  : {cambia_layer} su {len(scelti)}")
    print(f"     cambiano l'ESITO  : {cambia_esito} su {len(scelti)}")
    if cambia_esito:
        stima = len(persi) * cambia_esito / len(scelti)
        print(f"     ⇒ stima sui {len(persi)}: ~{stima:.0f} fatti")

    print("\n  == LA RIGA CHE CONTA")
    # ⚠️ GUARDIA SU n PICCOLO, e serve DAVVERO qui: se pochissimi casi
    #    accendono `L1`, la carve-out ha pochissime occasioni di contare e una
    #    stima costruita su uno o due esiti **non e' una stima**. E' la lezione
    #    di `W7-58` («conclusione tratta da n=1»), applicata prima di scrivere
    #    la riga invece che dopo averla pubblicata.
    if cambia_esito and acceso_apo < 3:
        print(f"     🟡🪞 **IL NUMERO C'E' MA NON REGGE UNA STIMA**: solo")
        print(f"     {acceso_apo} caso su {len(scelti)} accende `L1` con `e'`,")
        print(f"     e l'esito cambia in {cambia_esito}. ⇒ La proiezione sui")
        print(f"     {len(persi)} poggia su **{cambia_esito} caso**: la riporto")
        print("     come ordine di grandezza e NON come misura.")
        print("     🔑 **Cio' che e' solido e' il rovescio**: su"
              f" {len(scelti)} casi, **{len(scelti) - cambia_esito} non cambiano")
        print("     esito**. ⇒ Il costo alla porta e' MOLTO piu' piccolo dei")
        print("     ~123 di `W7-73`, e quello era il punto della misura.")
    elif cambia_esito:
        print(f"     🔴 L'apostrofo cambia l'ESITO in {cambia_esito} casi su")
        print(f"     {len(scelti)} — non solo la classificazione. ⇒ La cura di")
        print("     `_VERB_MARK` **vale**, e il numero da riportare e' questo,")
        print("     non i ~123 di `W7-73`.")
    elif cambia_layer:
        print(f"     🟡 Cambiano i LAYER in {cambia_layer} casi ma l'ESITO in")
        print("     NESSUNO: la carve-out si attiva e **non basta a ribaltare il")
        print("     verdetto** — un altro veto decide comunque. ⇒ **La cura")
        print("     dell'apostrofo NON cambierebbe cio' che l'utente vede**, e i")
        print("     ~123 di `W7-73` vanno ridimensionati a questo.")
    else:
        print("     🪞 NE' i layer NE' l'esito cambiano: l'apostrofo conta per il")
        print("     classificatore del soggetto e **non arriva a contare alla")
        print("     porta**. ⇒ `W7-72` e `W7-73` restano veri su cio' che")
        print("     misurano, e il loro peso pratico e' **zero** su questa")
        print("     popolazione. Lo dico con la stessa forza.")

    for az_a, az_b, lay_a, lay_b, t in esempi:
        print(f"     {az_a}→{az_b}  [{','.join(lay_a)}]→[{','.join(lay_b)}]"
              f"  {t[:40]}")

    print(f"\n  ⚠️ COSA NON DICE: {len(scelti)} casi, uno ogni {passo} — non")
    print("  e' una stima sul corpus. E la misura gira con")
    print("  `narrative_l1_skip=False`: e' un DOPPIO controfattuale (se non")
    print("  fossero narrative E se scrivessero l'accento), dichiarato in cima.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
