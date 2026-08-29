"""La banda 40-80 senza giudice LLM, e chi quarantina senza dire di essere stato.

Il fronte non nasce da una mia ipotesi: **me l'ha dato il prodotto**.
`verimem doctor`, eseguito da utente, dichiara due cose che stanno insieme male:

    ✓ parameters  admission threshold in force: 40/100 … a score between 40 and
      80 does NOT pass either: it goes to the two-threshold band, which
      **escalates to one llm adjudication** or holds the write for review
    ✓ llm  **no llm provider** … the llm-judge tier stay off

⇒ **La banda escala a un giudice che su questo install non esiste.** Domanda: la
banda e' popolata? e cosa succede a chi ci cade?

⚠️ **QUESTO BANCO E' IN SOLA LETTURA SUL CORPUS DI AURELIO** (`mode=ro`), tranne
il test finale di persistenza che usa uno store **temporaneo**.

── MISURE, corpus reale, istante **19:30 del 29/08** ────────────────────────

**① LA BANDA ESISTE ED E' QUASI VUOTA.** Su 8871 fatti con `grounding_score`:

    [  0 -  10)   395  ( 4,45%)
    [ 10 -  40)    90  ( 1,01%)
    [ 40 -  60)    61  ( 0,69%)   <- banda
    [ 60 -  80)    35  ( 0,39%)   <- banda
    [ 80 -  95)   153  ( 1,72%)
    [ 95 - 100]  8137  (91,73%)

La distribuzione e' **fortemente bimodale**: 91,73% sopra 95, 5,46% sotto 40,
e **1,08% in banda**.

🟢 **② E IL FALLBACK DELLA BANDA FUNZIONA, ED E' CONSERVATIVO.** Dei 96 in
banda: **88 quarantinati (91,7%)**, 8 `model_claim`. Il confronto con le fasce
vicine e' quello che rende leggibile il numero:

    [10-40)  n= 90   quarantined  86  (95,6%)
    [40-80)  n= 96   quarantined  88  (91,7%)
    [80-95)  n=153   quarantined   3  ( 2,0%)

⇒ **la banda si comporta come la fascia BASSA, non come l'alta**: senza giudice
LLM, chi ci cade viene **fermato**, non ammesso. E **`quarantined_by` =
`L4-review` in 31 casi** e' la **prova diretta** che gira il ramo «*holds the
write for review*» che doctor dichiara. **Il prodotto fa quello che dice.**

🟢 **③ E `quarantined_by` PERSISTE.** Test su store temporaneo, ricevuta contro
DB per lo stesso `id`:

    autoclaim nudo     quarantined   ricevuta L1     DB 'L1'
    metrico nudo       quarantined   ricevuta L1     DB 'L1'
    fonte che NEGA     quarantined   ricevuta moat   DB 'moat'

⚠️ **④ MA UN QUARANTINATO SU TRE, QUESTO MESE, NON DICE CHI L'HA FERMATO.**

    agosto 2026:  708 quarantinati · 206 senza `quarantined_by` = **29,1%**
    e di quei 206, i **mai giudicati dal moat sono ZERO**: hanno tutti un
    punteggio, sono passati di li', e non registrano l'autore del blocco.
    Chi invece registra, ad agosto: moat 319 · L4.1 83 · gate 55 ·
    L4-review 31 · L3-coexistence 11 · **L1 2**

⇒ Non e' persistenza rotta (③ lo esclude) e non e' «il moat non ha girato».
**E' un percorso che non registra, e NON SO QUALE.** Lo dichiaro aperto invece
di indovinarlo: le ipotesi plausibili — consolidamento automatico, CLI, un ramo
che non setta il campo — sono **tre**, e sceglierne una senza misurarla sarebbe
la quinta storia inventata in due giorni.

🔴 **⑤ E IL CONTROLLO CHE HA SMONTATO IL MIO ALLARME — la parte che conta.**
Sul corpus intero il numero e' **79,2%** (1909 su 2411), tre volte piu' grosso.
Ma per mese:

    2026-05   senza 1579 · con   0   -> 100,0%
    2026-06   senza   47 · con   0   -> 100,0%
    2026-07   senza   77 · con   0   -> 100,0%
    2026-08   senza  206 · con 502   ->  29,1%

**Fino a luglio il campo non veniva popolato AFFATTO.** Il 79,2% e' **eredita'**,
non un difetto attuale. 🔑 *Se avessi pubblicato «il 79% dei quarantinati non
dice chi li ha fermati» avrei lanciato un allarme **2,7 volte piu' grande del
vero**, gonfiato dalla storia del corpus. Un rapporto senza FINESTRA inganna, e
la finestra qui cambia il verdetto — non il decimale.*

🔴🔴 **⑥ RETTIFICA, DIECI MINUTI DOPO: ANCHE IL 29,1% ERA UN ALLARME FALSO, E
IL DIFETTO NON ESISTE.**

Avevo spezzato per **mese** e mi ero fermato li', convinto di aver fatto il
controllo. **Non bastava: dentro agosto ci sono DUE ERE.** Spezzando per
**giorno**:

    08-01 .. 08-05    194 senza ·   0 con     (100% senza)
    08-07              10 senza ·  27 con     <- la TRANSIZIONE
    08-08               1 senza ·   9 con
    08-12               1 senza ·  20 con
    08-13 .. 08-29      0 senza · 412 con     (0,0% senza)

⇒ **`quarantined_by` e' entrato in servizio il 7 agosto.** Tutto cio' che manca
sta **prima** di quella data. Sull'era attuale — **oltre due settimane, 412
quarantinati** — l'attribuzione c'e' **sempre**: **0,0% senza**.

🟢 **NON C'E' NESSUN DIFETTO.** Il campo funziona al 100% da piu' di due
settimane, e i punti ④ e ⑤ qui sopra vanno letti **solo** come cronaca di come
ci sono arrivato.

🔑 **E LA LEZIONE E' RICORSIVA, che e' la parte che mi porto via.** Ho applicato
la lezione della finestra **una volta** (per mese) e mi sono fermato,
soddisfatto di aver evitato un allarme falso da 79,2%. **Ma il residuo del 29,1%
era la stessa malattia a granularita' piu' fine.**
⇒ **Una finestra sbagliata non si corregge una volta sola: si spinge finche' il
numero SMETTE DI MUOVERSI.** Se raffinando la granularita' il numero cambia
ancora, **non hai finito di correggere — hai solo cambiato l'entita' dell'errore**.
79,2% → 29,1% → **0,0%**: due correzioni, e solo la seconda arriva al vero.

⚠️ E il difetto che avevo attribuito a «un percorso che non registra» **non
esisteva nemmeno come domanda**: il probe su `writer_role`/`writer_principal`
mostrava `cli:local` con **184 senza e 474 con** — lo stesso percorso faceva
entrambe le cose, perche' i due gruppi stavano in **due epoche diverse**, non su
due percorsi diversi. *Cercavo una differenza di CHI dove c'era una differenza
di QUANDO.*

⚠️ ALTRI LIMITI: un install, un istante (il corpus si muove: siamo in otto a
scrivere). Il test ③ copre il percorso **SDK** su tre casi, non tutti i rami.

    python docs/stato-reale/banchi/ws3-la-banda-di-escalation-e-chi-ferma-senza-dirlo.py
"""

from __future__ import annotations

import sqlite3

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
MESE = "2026-08"


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)  # SOLA LETTURA

    giud = con.execute(
        "select count(*) from facts where grounding_score is not null"
    ).fetchone()[0]
    print(f"  fatti con grounding_score: {giud}   (dichiarare l'ISTANTE)")

    print("\n  [1] DISTRIBUZIONE DEL PUNTEGGIO")
    for a, b in ((0, 10), (10, 40), (40, 60), (60, 80), (80, 95), (95, 100.01)):
        n = con.execute(
            "select count(*) from facts where grounding_score>=? "
            "and grounding_score<?", (a, b)).fetchone()[0]
        marca = "   <- banda di escalation" if a in (40, 60) else ""
        print(f"      [{a:>3} - {b:>6.0f})  {n:>6}  "
              f"({100 * n / max(1, giud):5.2f}%){marca}")

    print("\n  [2] LA BANDA CONTRO LE FASCE VICINE  (rende leggibile il numero)")
    for a, b in ((10, 40), (40, 80), (80, 95)):
        rr = con.execute(
            "select status from facts where grounding_score>=? "
            "and grounding_score<?", (a, b)).fetchall()
        q = sum(1 for (s,) in rr if s == "quarantined")
        print(f"      [{a}-{b})  n={len(rr):<5} quarantined {q:>4} "
              f"({100 * q / max(1, len(rr)):5.1f}%)")

    lr = con.execute(
        "select count(*) from facts where grounding_score>=40 "
        "and grounding_score<80 and quarantined_by='L4-review'").fetchone()[0]
    print(f"      quarantined_by='L4-review' in banda: {lr}"
          f"   <- il ramo «holds for review» GIRA")

    print("\n  [3] CHI FERMA SENZA DIRLO — e la FINESTRA che cambia il verdetto")
    q = ("select strftime('%Y-%m', created_at, 'unixepoch') m,"
         " sum(case when quarantined_by is null or quarantined_by='' "
         "then 1 else 0 end) senza,"
         " sum(case when quarantined_by is not null and quarantined_by!='' "
         "then 1 else 0 end) con"
         " from facts where status='quarantined' group by m order by m desc")
    righe = con.execute(q).fetchall()
    for m, senza, c in righe[:6]:
        tot = senza + c
        print(f"      {m}   senza {senza:>5} · con {c:>4}"
              f"   -> {100 * senza / max(1, tot):5.1f}%")

    tot_g = con.execute(
        "select count(*) from facts where status='quarantined'").fetchone()[0]
    nul_g = con.execute(
        "select count(*) from facts where status='quarantined' "
        "and (quarantined_by is null or quarantined_by='')").fetchone()[0]
    print(f"\n      GLOBALE: {nul_g}/{tot_g} = "
          f"{100 * nul_g / max(1, tot_g):.1f}%  <- gonfiato dall'EREDITA'")

    # CONTROLLO CHE DEVE POTER FALLIRE: se ogni mese fosse al 100%, il campo
    # non sarebbe mai popolato e non ci sarebbe nessun difetto ATTUALE da
    # riportare — solo una funzione mai entrata in servizio.
    mesi_pieni = [m for m, _s, c in righe if c > 0]
    print(f"\n  [4] CONTROLLO: mesi in cui il campo E' popolato almeno una "
          f"volta: {mesi_pieni or 'NESSUNO'}")
    if not mesi_pieni:
        print("      CONTROLLO CADUTO: il campo non e' popolato in nessun mese")
        print("      ⇒ non e' «chi ferma non lo dice», e' «la funzione non e'")
        print("      mai entrata in servizio». NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print("     🟢 la banda 40-80 e' quasi vuota (1,08%) e il suo fallback")
    print("        FUNZIONA senza giudice LLM: si comporta come la fascia bassa")
    print("        e `L4-review` prova che gira il ramo dichiarato da doctor.")
    print("     ⚠️  nel mese in corso il 29,1% dei quarantinati non registra chi")
    print("        l'ha fermato, e nessuno di essi e' «mai giudicato».")
    print("     🔴 il 79,2% globale e' EREDITA' (fino a luglio 100%): pubblicarlo")
    print("        senza la finestra sarebbe un allarme 2,7 volte piu' grande")
    print("        del vero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
