"""L'ECCEZIONE DICHIARATA E' QUASI TUTTO IL TRAFFICO — quanto e' larga la porta
su cui la famiglia `L1` non gira.

L'orientamento del prodotto dichiara l'eccezione, e la dichiara bene::

    a write made as a session NOTE — `meta_narrative=True`, which the `save`
    command uses — skips that screen. It is deliberate: a checkpoint saying
    "done" is a record of work, not a factual claim about the world. But it
    means the screen is not literally universal.

⇒ **Non e' un difetto nascosto: e' un limite dichiarato.** Cio' che nessuno ha
misurato e' **quanto quell'eccezione sia la regola**, e questa e' la differenza
fra una nota a pie' di pagina e il comportamento del prodotto.

LA CATENA, letta nel codice e non dedotta:

    client.py:533   narrative_l1_skip=meta_narrative
    client.py:658   if meta_narrative: fact.writer_role = "user"   ← FORZATO
    anti_confab_gate.py:1946
                    warnings = [] if narrative_l1_skip or ...

⇒ **Un booleano del chiamante spegne l'INTERA famiglia `L1`** — e a differenza
del bypass totale (`:1894`, che esige `verify_trusted_writer` + token
server-side, fail-closed) **questo non chiede nessun token**.
⚠️ E sovrascrive `writer_role`: chi passa `meta_narrative=True` diventa `user`
qualunque cosa avesse dichiarato. Il commento a `:653` lo dice: *«resta
l'ultima parola»*.

LA DOMANDA: **su quanta parte del corpus la famiglia `L1` non gira affatto?**
E la domanda che conta davvero: **quanti di quei fatti avrebbero acceso un
layer `L1` se fosse girato?** — cioe' il PREZZO del silenzio, non solo la sua
ampiezza.

ATTESA DICHIARATA PRIMA: la quota di `narrative` e' alta (l'ho gia' vista al
99,8% su una sotto-popolazione), ma **la quota che avrebbe acceso `L1` deve
essere BASSA** — se fosse alta, il prodotto starebbe ammettendo in silenzio
molti self-claim, e sarebbe un reperto di prima grandezza. **Se e' bassa, il
limite dichiarato e' innocuo e lo dico con la stessa forza.**

CONTROLLI CHE POSSONO FALLIRE:
 (1) **la distribuzione PRIMA di dividere**: stampo `meta_narrative` su TUTTI i
     vivi, non su una sotto-popolazione scelta da me (il mio 99,8% veniva dai
     soli fatti con fonte conservata, ed e' un denominatore diverso).
 (2) **il gate ha ERE** (reperto di un'altra istanza: `L4.1` e `L4-review`
     partono il 21/08): un tasso attraverso quella data confronta due prodotti.
     ⇒ spezzo per era e stampo entrambe.
 (3) **controllo positivo**: sui non-narrative `L1` deve accendersi almeno
     qualche volta. Se fosse zero anche li', non starei misurando l'eccezione:
     starei misurando un layer spento ovunque.

    python -u docs/stato-reale/banchi/l-eccezione-dichiarata-e-quasi-tutto-il-traffico.py
"""

from __future__ import annotations

import json
import sqlite3
import sys

#: `L4.1` e `L4-review` entrano il 21/08 (reperto altrui): prima e dopo sono
#: due prodotti. Per `L1` la data non e' quella, ma spezzare protegge lo stesso
#: da un confronto fra ere.
CONFINE = "2026-08-21"


def main() -> int:
    try:
        from verimem.anti_confab_gate import _l1_warnings
        from verimem.config import CONFIG
        from verimem.gate_router import classify_provenance
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select id, proposition, grounding_span, writer_role, verified_by, "
        "meta_narrative, created_at, status from facts "
        "where superseded_by is null").fetchall()
    print(f"  popolazione: {len(righe)} fatti VIVI (tutti, non una fetta)")

    print("\n  -- CONTROLLO (1): LA DISTRIBUZIONE, prima di dividere")
    d: dict[object, int] = {}
    for r in righe:
        d[r[5]] = d.get(r[5], 0) + 1
    for k, v in sorted(d.items(), key=lambda kv: -kv[1]):
        eti = {1: "narrative (L1 NON gira)", 0: "normale (L1 gira)"}.get(
            k, f"altro:{k!r}")
        print(f"     {eti:<26}{v:>7}  ({100.0 * v / len(righe):.1f}%)")
    narr = [r for r in righe if r[5] == 1]
    norm = [r for r in righe if r[5] != 1]
    if not narr or not norm:
        print("     ⚠️ una delle due popolazioni e' vuota: non c'e' confronto.")
        return 1

    def accende_l1(r) -> list[str]:
        _fid, prop, span, wr, vb_raw, _mn, _ca, _st = r
        try:
            vb = json.loads(vb_raw or "[]")
        except Exception:  # noqa: BLE001
            vb = []
        ws = _l1_warnings(prop or "", vb, source=span or None,
                          provenance=classify_provenance(wr, vb))
        return sorted({str((w or {}).get("layer") or "?") for w in (ws or [])})

    print("\n  -- CONTROLLO (3): sui NORMALI `L1` si accende davvero?")
    acc_norm = [r for r in norm if accende_l1(r)]
    print(f"     {len(acc_norm)} su {len(norm)} normali accendono un layer L1")
    if not acc_norm:
        print("     CADUTO - non si accende nemmeno dove gira: misurerei un")
        print("     layer spento ovunque, non l'effetto dell'eccezione.")
        return 1

    print("\n  == IL PREZZO DEL SILENZIO: quanti NARRATIVE avrebbero acceso L1?")
    conta: dict[str, int] = {}
    quanti = 0
    esempi = []
    for r in narr:
        lay = accende_l1(r)
        if lay:
            quanti += 1
            for x in lay:
                conta[x] = conta.get(x, 0) + 1
            if len(esempi) < 4:
                esempi.append((lay, r[1]))
    print(f"     {quanti} su {len(narr)}  ({100.0 * quanti / len(narr):.1f}%)")
    print("     per layer:")
    for k, v in sorted(conta.items(), key=lambda kv: -kv[1])[:8]:
        print(f"       {k:<16}{v}")

    print("\n  -- CONTROLLO (2): e SPEZZATO PER ERA (il gate ha ere)")
    # 🪞 `created_at` e' un epoch FLOAT, non una stringa ISO: la prima stesura
    #    confrontava float con str e cadeva. Il campo va CHIESTO al dato, non
    #    dedotto dal nome.
    import datetime as _dt
    _conf = _dt.datetime.fromisoformat(CONFINE).timestamp()
    print(f"     (confine = {CONFINE} = epoch {_conf:.0f};"
          f" `created_at` e' un float)")

    def _prima(r) -> bool:
        try:
            return float(r[6] or 0.0) < _conf
        except (TypeError, ValueError):
            return False

    for eti, sel in (("prima del " + CONFINE, _prima),
                     ("dal " + CONFINE, lambda r: not _prima(r))):
        sub = [r for r in narr if sel(r)]
        if not sub:
            print(f"     {eti:<22} nessun fatto")
            continue
        q = sum(1 for r in sub if accende_l1(r))
        print(f"     {eti:<22}{q:>6} su {len(sub):<6}"
              f"({100.0 * q / len(sub):.1f}%)")

    print("\n  == LA RIGA CHE CONTA")
    quota_narr = 100.0 * len(narr) / len(righe)
    quota_acc = 100.0 * quanti / len(narr)
    if quota_narr > 90 and quota_acc < 5:
        print(f"     🟢 L'ECCEZIONE E' LARGA ({quota_narr:.1f}% del corpus) MA")
        print(f"     COSTA POCO: solo il {quota_acc:.1f}% di quei fatti avrebbe")
        print("     acceso un layer. ⇒ Il limite dichiarato e' reale e quasi")
        print("     innocuo, e va detto con questa seconda meta' attaccata.")
    elif quota_narr > 90:
        print(f"     🔴 L'ECCEZIONE E' LA REGOLA ({quota_narr:.1f}%) E COSTA:")
        print(f"     il {quota_acc:.1f}% di quei fatti avrebbe acceso un layer")
        print("     `L1` e nessuno l'ha visto. ⇒ Il gate anti-confabulazione")
        print("     che la vetrina promette non gira sulla porta da cui il")
        print("     corpus e' stato scritto.")
    else:
        print(f"     ⇒ narrative {quota_narr:.1f}%, di cui accenderebbero"
              f" {quota_acc:.1f}%. Non forzo una tesi su questi numeri.")

    if esempi:
        print("\n  esempi di narrative che avrebbero acceso un layer:")
        for lay, prop in esempi:
            print(f"     {','.join(lay):<22}{(prop or '')[:52]}")

    # 🔬 I QUATTRO ESEMPI ERANO TUTTI `PRE-COMPACT HANDOFF` — cioe' ESATTAMENTE
    #    il caso per cui l'eccezione e' stata scritta (`anti_confab_gate.py:1868`:
    #    *«retrospective continuity facts (pre-compact master facts) whose
    #    narrative naturally contains keywords like SHIPPED/COMPLETO»*).
    #    ⚠️ Ma quattro esempi non sono una misura, e sono i PRIMI quattro, non
    #    un campione. Se la maggioranza dei 551 e' di quel tipo, l'eccezione fa
    #    il suo mestiere; il RESTO e' cio' che passa senza essere un checkpoint.
    print("\n  == I 551: sono CHECKPOINT (il caso previsto) o altro?")
    MARCHE = ("pre-compact", "handoff", "master fact", "checkpoint",
              "resume", "session")
    quanti_ck = 0
    topic_altri: dict[str, int] = {}
    for r in narr:
        if not accende_l1(r):
            continue
        testo = (r[1] or "").casefold()
        # il topic non e' nella tupla: lo prendo dal DB una volta sola sotto
        if any(m in testo[:120] for m in MARCHE):
            quanti_ck += 1
        else:
            topic_altri[r[0]] = 1
    print(f"     riconosciuti come CHECKPOINT (marca nei primi 120 char):"
          f" {quanti_ck} su {quanti}"
          f"  ({100.0 * quanti_ck / quanti:.1f}%)" if quanti else "     -")
    if topic_altri:
        ids = list(topic_altri)[:600]
        q = ",".join("?" * len(ids))
        tp: dict[str, int] = {}
        for (t,) in c.execute(
                f"select topic from facts where id in ({q})", ids):
            k = (t or "(vuoto)").split("/")[0]
            tp[k] = tp.get(k, 0) + 1
        print(f"     gli ALTRI {len(topic_altri)}, per primo segmento di topic:")
        for k, v in sorted(tp.items(), key=lambda kv: -kv[1])[:8]:
            print(f"       {k:<24}{v}")

    print("\n  ⚠️ COSA NON DICE: «avrebbe acceso un layer» NON e' «e' falso» —")
    print("  `L1` e' un rilevatore lessicale e i suoi falsi allarmi sono")
    print("  misurati altrove. E `_l1_warnings` e' una funzione privata: la")
    print("  chiamo direttamente, quindi questo e' il livello DETECTOR, non la")
    print("  porta. Il numero e' un LIMITE SUPERIORE del silenzio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
