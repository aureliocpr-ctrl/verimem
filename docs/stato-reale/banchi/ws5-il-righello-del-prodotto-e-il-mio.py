r"""I miei conteggi SQL e `verimem stats` danno numeri diversi: quale dei due, e perche'?

Stasera ho contato i quarantinati con `sqlite3` (`ce735e1e`: **2679**) e ci ho costruito
sopra una lettura. Poi ho eseguito `verimem stats` — che esiste, si chiama «*trust
odometer: what the admission gate DID on this store*» e **nessuno di noi lo cita** — e
dice altro::

    verimem stats                          il mio SQL
    admitted     9448                      ammessi        14304
    quarantined  1149  (gate actions)      quarantinati    2679
    Live facts by status → quarantined  1317
    Superseded   2292
    Moat coverage 9824/14734 (66.7%)

⚠️ **Nello stesso output ci sono TRE denominatori** (10597 gate actions · 14734 giudicabili ·
i vivi per status) e il comando lo dichiara: «*recorded since 2026-07-15, **66% of stored
facts***». ⇒ Non e' detto che uno menta: e' probabile che **contino cose diverse**, e la
domanda utile e' **quale sia il righello giusto per la frase che si vuole scrivere**.

LE TRE DOMANDE, e ognuna ha una risposta diversa::

    ① quanti fatti sono quarantinati IN TUTTO         (il mio SQL: tutti, anche superseduti)
    ② quanti sono quarantinati e VIVI                 (`Live facts by status`)
    ③ su quanti il GATE ha registrato un'azione       (`Gate actions`, dal 2026-07-15)

⇒ E c'e' una riga che tocca due miei reperti di stasera: `Gate actions → by layer` dice
`L1.13: 3`, mentre in `W5-16` ho misurato che `L1.13` scatta su 3 conteggi su 3. ⇒
**«scattare» e «essere la causa registrata della quarantena» non sono la stessa cosa**, e
se il secondo numero e' 3 su ~10600, il costo che ho descritto va ridimensionato.

🟡 ESITO — **i due righelli CONCORDANO (contavano cose diverse), e il conto per layer
ridimensiona un mio reperto di venti minuti fa**::

    ①                              TUTTI      vivi   superseduti
    quarantinati                    2682      1317          1365
    ammessi                        14344     13417           927
    totale                         17026     14734          2292

    ② la CAUSA REGISTRATA della quarantena
    (nessuna)  1909   ·  moat  512  ·  L4.1  144  ·  gate  55
    L4-review    43   ·  L3-coexistence  15  ·  L1  2  ·  store-screen  1

✅ **① NESSUNO DEI DUE RIGHELLI MENTE.** `verimem stats` dice `Live facts by status →
quarantined: **1317**`, e i miei **vivi** sono **1317 esatti**. Il mio 2682 erano i
**TUTTI**, superseduti inclusi. ⇒ Le due cifre rispondono a **due domande diverse**, e
per «lo stato di oggi» quella giusta e' **1317**. 🪞 Il numero che ho usato in `W5-12`
era il primo: **non sbagliato, ma piu' largo di quanto la frase lasciasse intendere.**

🪞 **② E IL CONTO PER LAYER RIDIMENSIONA `W5-16`.** `L1.13` **non compare mai** come
causa registrata — perche' `chi_ha_quarantinato` restituisce **la famiglia**, non il
detector (reperto mio, `c5299add`), e **`L1` conta 2 su 2682**. ⇒ In `W5-16` ho misurato
che `L1.13` **scatta** su 3 conteggi su 3, ed e' vero; ma **«scattare» e «essere la causa
della quarantena» sono due cose diverse**, e sul corpus la famiglia intera ne spiega
**due**. ⇒ **Il mio reperto e' un MECCANISMO SENZA FREQUENZA** — una delle quattro forme
di numero vero che inganna, e ce l'avevo scritta.

⚠️ **③ E i due registri non coincidono fra loro**: `verimem stats` elenca `by layer:
L1.13: 3` (dal log delle **gate actions**, dal 2026-07-15), la colonna `quarantined_by`
sui fatti ne da' **0** (perche' aggrega in `L1`). ⇒ **Due registri, due vocabolari, e
nessuno dei due e' sbagliato** — ma chi cita «il layer X ha quarantinato N volte» deve
dire **da quale dei due** legge.

⚠️ **④ E resta il buco gia' noto**: **1909 su 2682 senza causa** (71%), tutti anteriori
al 12/08 (misurato prima, `W2`). Sui **773 con causa**, `moat` ne spiega **512**.

REGIME: **sola lettura**, `mode=ro`, percorso da `CONFIG.semantic_db`. Nessun modello
caricato.
⚖️ PUNTI DEBOLI: leggo `verimem stats` dal suo output testuale; se cambia formato questo
banco va aggiornato. E confronto due righelli sullo stesso istante, non nel tempo.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-righello-del-prodotto-e-il-mio.py
"""
import sqlite3
from pathlib import Path

from verimem.config import CONFIG


def main():
    p = Path(str(CONFIG.semantic_db))
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    cur = con.cursor()

    def uno(sql):
        return cur.execute(sql).fetchone()[0]

    tot = uno("select count(*) from facts")
    quar_tutti = uno("select count(*) from facts where status='quarantined'")
    quar_vivi = uno("select count(*) from facts where status='quarantined' "
                    "and superseded_by is null")
    quar_sup = uno("select count(*) from facts where status='quarantined' "
                   "and superseded_by is not null")
    amm_tutti = uno("select count(*) from facts where status is null or status!='quarantined'")
    amm_vivi = uno("select count(*) from facts where (status is null or status!='quarantined') "
                   "and superseded_by is null")
    sup = uno("select count(*) from facts where superseded_by is not null")

    print("① I NUMERI, con e senza i superseduti\n")
    print("  %-40s %8s %8s %8s" % ("", "TUTTI", "vivi", "superseduti"))
    print("  " + "-" * 68)
    print("  %-40s %8d %8d %8d" % ("quarantinati", quar_tutti, quar_vivi, quar_sup))
    print("  %-40s %8d %8d %8d" % ("ammessi", amm_tutti, amm_vivi, amm_tutti - amm_vivi))
    print("  %-40s %8d %8d %8d" % ("totale", tot, tot - sup, sup))

    print("\n② LA CAUSA REGISTRATA, per layer (chi ha deciso la quarantena)\n")
    righe = cur.execute(
        "select coalesce(quarantined_by,'(nessuna)'), count(*) from facts "
        "where status='quarantined' group by 1 order by 2 desc").fetchall()
    for causa, n in righe[:12]:
        print("  %-28s %6d" % (causa, n))
    con.close()

    print("\n=== LETTURA ===")
    print("  Il mio SQL di `ce735e1e` contava %d quarantinati: sono i **TUTTI**." % quar_tutti)
    print("  I vivi sono %d — %d in meno, e la differenza sono i superseduti."
          % (quar_vivi, quar_tutti - quar_vivi))
    if quar_vivi != quar_tutti:
        print("  ⇒ Le due cifre rispondono a due domande diverse, e per «lo stato di oggi»")
        print("    la cifra giusta e' quella dei VIVI.")
    d = dict(righe)
    # ⚠️ `chi_ha_quarantinato` restituisce la FAMIGLIA, non il detector (reperto
    # `c5299add`): `L1.13` non compare mai col suo nome, confluisce in `L1`.
    senza = d.get("(nessuna)", 0)
    print("\n  `L1.13` come causa registrata: %d — e non compare col suo nome perche'"
          % d.get("L1.13", 0))
    print("     `chi_ha_quarantinato` aggrega nella FAMIGLIA: `L1` conta %d su %d."
          % (d.get("L1", 0), quar_tutti))
    print("  ⇒ In `W5-16` ho misurato che SCATTA su 3 conteggi su 3, ed e' vero — ma")
    print("    «scattare» e «essere la causa della quarantena» sono due cose diverse,")
    print("    e sul corpus la famiglia INTERA ne spiega %d." % d.get("L1", 0))
    print("  🪞 Il mio reperto e' un MECCANISMO SENZA FREQUENZA: reale, e piccolo.")
    print("\n  E il buco noto resta: %d su %d senza causa (%.0f%%); sui %d con causa,"
          % (senza, quar_tutti, 100.0 * senza / quar_tutti if quar_tutti else 0,
             quar_tutti - senza))
    print("     `moat` ne spiega %d." % d.get("moat", 0))


main()
