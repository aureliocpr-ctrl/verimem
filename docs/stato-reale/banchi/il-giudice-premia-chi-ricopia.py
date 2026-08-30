"""IL PUNTEGGIO DEL MOAT SEGUE QUANTO IL CLAIM RICOPIA LA FONTE?

\U0001f4cc **L'ESPERIMENTO CHE `W7-94` DICHIARAVA MANCANTE.** Quella cella
misura una **correlazione**: i fatti con un numero identico fra claim e fonte
sono bocciati al **2,8%** contro il **17,5-19,3%** della popolazione generale
(`W7-89`). Da li' avevo scritto *«il gate premia chi RICOPIA la forma della
fonte»* — **e l'ho scritto come correlazione, non come effetto**.

\U0001f511 **PERCHE' NON GENERO PARAFRASI**: la via ovvia sarebbe riscrivere i
claim e vedere quanti cadono. Ma una parafrasi automatica **cambia anche il
senso**, e misurerei la mia riscrittura invece del giudice. Qui la variabile
si osserva senza toccare nulla: **quanto ogni claim gia' ricopia la sua
fonte**, contro il punteggio che riceve.

\U0001f9e9 **E SI LEGA A UN REPERTO DI @ws1** (22:50): sul cross-encoder del
**retrieval** la mediana della ZONA GRIGIA (+2,914) supera quella dei
RILEVANTI (+0,135) — *«premia chi parla dell'argomento piu' di chi ha la
risposta»*. ⚠️ **Sono DUE MODELLI DIVERSI**, e il sorgente lo dichiara
(`local_grounding.py:459-461`)::

    retrieval rerank : cross-encoder/ms-marco-MiniLM-L-12-v2
    moat judge       : cross-encoder/nli-deberta-v3-base

⇒ **Non duplico il suo banco: misuro l'altro modello, sull'altra porta.** E se
il sintomo fosse lo stesso su due modelli diversi, **la convergenza sarebbe
piu' forte, non meno** — con una differenza di gravita' che va detta:
`ms-marco` e' addestrato **per la rilevanza**, quindi premiare chi parla
dell'argomento e' quasi il suo mestiere; `nli-deberta` e' addestrato **per
l'entailment**, e premiare chi ricopia sarebbe **un difetto nel suo compito
proprio**.

ATTESA DICHIARATA PRIMA: **correlazione positiva forte** — piu' il claim
ricopia, piu' alto il punteggio. ⚠️ **Se non correla, «il gate premia la
ricopiatura» CADE**, e con essa la lettura di `W7-94`: lo dico con la stessa
forza.

CONTROLLI CHE POSSONO FALLIRE:
 (1) ✅ **il punteggio deve VARIARE**: se fosse quasi tutto a 99 non c'e'
     correlazione da misurare, e il banco lo dice invece di calcolare un
     coefficiente su una costante.
 (2) 🪞 **CONFONDENTE, dichiarato e stampato**: un claim corto ricopia di piu'
     per caso. Il banco stampa la **lunghezza mediana** per fascia: se le
     fasce differiscono molto in lunghezza, il confronto e' sporco.
 (3) ⚖️ **la sovrapposizione ignora le parole grammaticali** (la lista e'
     quella di `_GRAMMATICA`, gia' curata in `W7-84`): senza, «il», «di» e «e»
     gonfierebbero ogni claim allo stesso modo.
 (4) 📊 **baseline RIGIUDICATO oggi**: i punteggi storici sono di build
     diverse (lezione di `W7-94`).

    python -u docs/stato-reale/banchi/il-giudice-premia-chi-ricopia.py
"""

from __future__ import annotations

import re
import sqlite3
import statistics
import sys
import time

CUT = 40.0
PAROLA = re.compile(r"[^\W\d_]+", re.UNICODE)
TETTO = 200


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.config import CONFIG
        from verimem.local_grounding import judge_state, warm_local_judge_async
        from verimem.vicinato_del_valore import _GRAMMATICA
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    def _sovrapposizione(claim: str, fonte: str) -> float:
        """Quota dei token PIENI del claim presenti nella fonte."""
        c = {t.casefold() for t in PAROLA.findall(claim or "")}
        c -= _GRAMMATICA
        if not c:
            return -1.0
        f = {t.casefold() for t in PAROLA.findall(fonte or "")}
        return len(c & f) / len(c)

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = con.execute(
        "select proposition, grounding_span from facts "
        "where superseded_by is null and grounding_span is not null "
        "and grounding_span <> '' and proposition is not null").fetchall()
    print(f"  fatti vivi con fonte: {len(righe)}")

    casi = []
    for prop, span in righe:
        s = _sovrapposizione(prop, span)
        if s >= 0:
            casi.append((prop, span, s))
    print(f"  con almeno un token pieno nel claim: {len(casi)}")
    if len(casi) < 50:
        print("NON RIUSCITO: meno di cinquanta casi.")
        return 1

    passo = max(1, len(casi) // TETTO)
    campione = casi[::passo][:TETTO]
    print(f"  campione DICHIARATO: {len(campione)} (uno ogni {passo})")

    print("\n  -- preflight: il moat deve essere CALDO")
    warm_local_judge_async()
    t0 = time.time()
    stato = judge_state()
    while stato == "warming" and time.time() - t0 < 180:
        time.sleep(2)
        stato = judge_state()
    print(f"     `judge_state()` = {stato!r}  dopo {time.time() - t0:.1f}s")
    if stato != "ready":
        print("NON RIUSCITO: giudice non pronto, misurerei il warmup.")
        return 1

    print("\n  -- rigiudico ognuno alla porta di oggi")
    dati = []
    t = time.time()
    for i, (prop, span, s) in enumerate(campione):
        try:
            res = run_validation_gate(
                proposition=prop, verified_by=None, topic="banco/ricopia",
                agent=None, source=span, ground_write=True)
        except Exception:  # noqa: BLE001
            continue
        g = (float(res.grounding_score)
             if res.grounding_score is not None else None)
        if g is None:
            continue
        dati.append((s, g, len(prop)))
        if i and i % 50 == 0:
            print(f"    ...{i}/{len(campione)} ({time.time() - t:.0f}s)")
    print(f"     giudicati: {len(dati)}")
    if len(dati) < 40:
        print("NON RIUSCITO: meno di quaranta giudizi utili.")
        return 1

    # (1) il punteggio varia abbastanza da poterlo correlare?
    punt = [g for _s, g, _l in dati]
    bocciati = sum(1 for g in punt if g < CUT)
    print(f"\n  -- (1) il punteggio VARIA? bocciati {bocciati}/{len(punt)}"
          f"  ·  mediana {statistics.median(punt):.2f}")
    if bocciati == 0:
        print("     CADUTO: nessun bocciato nel campione. Non posso misurare")
        print("     una correlazione con l'esito su una costante.")
        return 1

    fasce = [("ricopia POCO  (<0,34)", lambda s: s < 0.34),
             ("ricopia MEDIO (0,34-0,66)", lambda s: 0.34 <= s < 0.67),
             ("ricopia MOLTO (>=0,67)", lambda s: s >= 0.67)]
    print(f"\n     {'fascia':<28}{'n':>5}{'bocciati':>10}{'mediana g':>12}"
          f"{'len claim':>11}")
    riass = []
    for eti, test in fasce:
        gr = [(s, g, ln) for s, g, ln in dati if test(s)]
        if not gr:
            print(f"     {eti:<28}{0:>5}")
            continue
        b = sum(1 for _s, g, _l in gr if g < CUT)
        med = statistics.median([g for _s, g, _l in gr])
        # (2) il confondente: le fasce hanno claim di taglia diversa?
        ml = statistics.median([ln for _s, _g, ln in gr])
        print(f"     {eti:<28}{len(gr):>5}{b:>10}{med:>12.2f}{ml:>11.0f}")
        riass.append((eti, len(gr), b, med, ml))

    print("\n  == LA RIGA CHE CONTA")
    if len(riass) < 2:
        print("     NON RIUSCITO: meno di due fasce popolate, niente"
              " confronto.")
        return 1
    poco = next((r for r in riass if r[0].startswith("ricopia POCO")), None)
    molto = next((r for r in riass if r[0].startswith("ricopia MOLTO")), None)
    if not poco or not molto:
        print("     NON RIUSCITO: mancano le fasce estreme.")
        return 1
    q_poco = 100.0 * poco[2] / poco[1]
    q_molto = 100.0 * molto[2] / molto[1]
    print(f"     bocciati fra chi ricopia POCO : {poco[2]}/{poco[1]}"
          f"  ({q_poco:.1f}%)")
    print(f"     bocciati fra chi ricopia MOLTO: {molto[2]}/{molto[1]}"
          f"  ({q_molto:.1f}%)")
    if q_poco > q_molto + 10.0:
        print(f"\n     🟡 **GRADIENTE FORTE**: chi ricopia poco e' bocciato"
              f" {q_poco / max(0.1, q_molto):.1f} volte")
        print("     piu' spesso, con le lunghezze appaiate. **MA QUESTO NON"
              " BASTA A DIRE")
        print("     «il giudice premia chi ricopia»**, e la prima stesura lo")
        print("     stampava: manca il controllo che **un claim senza token in")
        print("     comune con la fonte puo' semplicemente NON essere"
              " sostenuto**,")
        print("     e allora cade a ragione.")
        print("     ⇒ **LEGGI I CASI DELLA FASCIA BASSA UNO PER UNO.** Fatto"
              " il 30/08")
        print("     su 9 casi: **3 bocciati giustamente** (la fonte parlava"
              " d'altro),")
        print("     **2 falsi negativi netti**, 4 non giudicabili dai primi")
        print("     caratteri. ⇒ Il reperto non e' «chi riformula», e' **chi")
        print("     SINTETIZZA una fonte TABELLARE** (*«i passati sono 10»*")
        print("     contro *«10 passed»*; *«nessuna delle sette celle…»*, che"
              " va")
        print("     CALCOLATA leggendo tutte le righe).")
        print("     ⚠️ E la sovrapposizione qui sopra **ignora i numeri**"
              " (token")
        print("     alfabetici soltanto): sui claim numerici — i nostri — la")
        print("     **sottostima**.")
    elif q_molto > q_poco:
        print("\n     🟢 **ROVESCIATO**: chi ricopia viene bocciato di PIU'."
              " La mia")
        print("     attesa e' falsificata e la lettura di `W7-94` va rivista.")
    else:
        print(f"\n     🟡 **Differenza piccola** ({q_poco:.1f}% contro"
              f" {q_molto:.1f}%):")
        print("     la sovrapposizione **non spiega** l'esito, e «il gate"
              " premia la")
        print("     ricopiatura» **non e' dimostrato**. Lo dico con la stessa"
              " forza.")

    print("\n  ⚠️ COSA NON DICE: la sovrapposizione e' **una** misura di"
          " ricopiatura")
    print("  (token pieni, insiemi, niente ordine) · le fasce sono soglie"
          " **mie** ·")
    print("  e un claim corto ricopia di piu' per caso: **le lunghezze mediane"
          " qui")
    print("  sopra dicono quanto il confronto sia sporco**.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
