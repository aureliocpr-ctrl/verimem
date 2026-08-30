"""QUANTO PESA `e'` NEL CORPUS — il limite di `W7-72`, pagato subito.

`W7-72` ha dimostrato che `_VERB_MARK` (`subject_extract.py:29`) riconosce `è`
e **non** `e'`, e che senza marcatore il soggetto e' \"non risolvibile\" e la
carve-out `domain-precision` non viene raggiunta. E ha dichiarato il limite:

    non ho misurato QUANTE frasi del corpus usino `e'` in posizione di verbo.
    Il difetto e' dimostrato, la sua FREQUENZA no.

**Un limite dichiarato e' un debito.** Questo lo paga, in tre livelli di costo
crescente, perche' il numero pieno costerebbe tredici minuti e i primi due
livelli bastano a dire se valga la pena.

  **① QUANTI** fatti scrivono `e'` dove ci vorrebbe `è`
  **② QUANTI di quelli CAMBIANO SOGGETTO** se si sostituisce — cioe' quanti
      perdono davvero il soggetto per colpa dell'apostrofo, non per altro
  **③ un CAMPIONE alla porta**: quanti, fra quelli, sarebbero classificati
      `DOMAIN` con `è` e non lo sono con `e'`

⚠️ **Il livello ② e' il controllo che rende ① non fuorviante**: una frase puo'
contenere `e'` e avere il soggetto irrisolvibile per un'altra ragione (piu' di
sei token, un punto fermo prima del verbo, un pronome). **Contare solo ① direbbe
un numero piu' grande del difetto.** E' la lezione di `W7-65`, dove `fatt[oaie]`
gonfiava il denominatore di nove volte.

CONTROLLI CHE POSSONO FALLIRE:
 (1) **la distribuzione PRIMA di dividere**, con esempi stampati: se `e'`
     comparisse in contesti che non sono il verbo (dentro un blocco di codice,
     in una citazione), il conteggio ① misurerebbe altro.
 (2) **controllo negativo**: i fatti che gia' usano `è` NON devono cambiare
     soggetto con la sostituzione (la sostituzione non li tocca). Se cambiassero,
     il mio metodo di confronto e' rotto.

    python -u docs/stato-reale/banchi/quanto-pesa-l-apostrofo-nel-corpus.py
"""

from __future__ import annotations

import re
import sqlite3
import sys

APO = re.compile(r"\be'(?=\s)")
ACC = re.compile(r"\bè(?=\s)")
CAMPIONE = 24


def main() -> int:
    try:
        from verimem.config import CONFIG
        from verimem.subject_extract import is_domain_professional, subject_of
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select id, proposition from facts where superseded_by is null"
    ).fetchall()
    print(f"  popolazione: {len(righe)} fatti VIVI")

    con_apo = [r for r in righe if APO.search(r[1] or "")]
    con_acc = [r for r in righe if ACC.search(r[1] or "")]
    print("\n  -- CONTROLLO (1): LA DISTRIBUZIONE, prima di dividere")
    print(f"     con `e'` seguito da spazio : {len(con_apo):>6}"
          f"  ({100.0 * len(con_apo) / len(righe):.1f}%)")
    print(f"     con `è`  seguito da spazio : {len(con_acc):>6}"
          f"  ({100.0 * len(con_acc) / len(righe):.1f}%)")
    if not con_apo:
        print("     nessun caso: il difetto non tocca questo corpus.")
        return 1
    print("\n     tre esempi di `e'`, per vedere se e' davvero il verbo:")
    for _fid, p in con_apo[:3]:
        m = APO.search(p or "")
        i = max(0, m.start() - 40)
        print(f"       …{(p or '')[i:m.end() + 46]}…")

    print("\n  -- CONTROLLO (2): i fatti che gia' usano `è` non devono cambiare")
    cambiati_acc = sum(
        1 for _f, p in con_acc
        if subject_of(p or "") != subject_of(APO.sub("è", p or "")))
    print(f"     cambiano soggetto: {cambiati_acc} su {len(con_acc)}")
    if cambiati_acc:
        print("     ⚠️ qualcuno cambia: la sostituzione tocca piu' di quanto")
        print("     credo, e il numero sotto va letto con questa riserva.")

    print("\n  == ② QUANTI PERDONO IL SOGGETTO PER COLPA DELL'APOSTROFO")
    persi = []
    for fid, p in con_apo:
        prima = subject_of(p or "")
        dopo = subject_of(APO.sub("è", p or ""))
        if not prima and dopo:
            persi.append((fid, p))
    print(f"     soggetto vuoto con `e'` e RISOLTO con `è`: {len(persi)}"
          f" su {len(con_apo)}"
          f"  ({100.0 * len(persi) / len(con_apo):.1f}%)")
    print(f"     ⇒ sul corpus intero: {100.0 * len(persi) / len(righe):.2f}%"
          f" dei {len(righe)} fatti vivi")
    altri = len(con_apo) - len(persi)
    print(f"     gli altri {altri} hanno il soggetto irrisolvibile per"
          " un'ALTRA ragione")
    print("     (piu' di sei token, un punto prima del verbo, un pronome):")
    print("     ⇒ **contare solo ① avrebbe detto un numero piu' grande del"
          " difetto.**")

    print(f"\n  == ③ CAMPIONE di {CAMPIONE}: quanti diventano DOMAIN con `è`?")
    passo = max(1, len(persi) // CAMPIONE)
    scelti = persi[::passo][:CAMPIONE]
    guadagno = 0
    for _fid, p in scelti:
        a = is_domain_professional(p or "")
        b = is_domain_professional(APO.sub("è", p or ""))
        if b and not a:
            guadagno += 1
    print(f"     classificati DOMAIN solo con `è`: {guadagno} su {len(scelti)}")
    if scelti:
        stima = len(persi) * guadagno / len(scelti)
        print(f"     ⇒ stima sul totale dei {len(persi)}: ~{stima:.0f} fatti")

    print("\n  == LA RIGA CHE CONTA")
    if persi and guadagno:
        print(f"     🔴 IL DIFETTO E' QUANTIFICATO: {len(persi)} fatti vivi")
        print("     perdono il soggetto **per l'apostrofo**, e sul campione")
        print(f"     {guadagno} su {len(scelti)} diventano `DOMAIN` appena si")
        print("     scrive `è`. ⇒ Una voce in una regex cambia la")
        print("     classificazione di questi fatti.")
        print("     ⚠️ Ma «DOMAIN» non e' «salvato»: la carve-out conta solo")
        print("     quando `L1` si accende, e questo banco NON lo misura.")
    elif persi:
        print(f"     🟡 {len(persi)} perdono il soggetto, ma sul campione")
        print(f"     nessuno diventa DOMAIN: il soggetto non basta, cadono su")
        print("     un'altra delle sei regole. Il difetto e' piu' stretto.")
    else:
        print("     🪞 Nessuno perde il soggetto per l'apostrofo: su questo")
        print("     corpus il difetto di `W7-72` non si realizza, e lo dico")
        print("     con la stessa forza con cui l'ho annunciato.")

    print("\n  ⚠️ COSA NON DICE: `DOMAIN` e' una condizione NECESSARIA della")
    print("  carve-out, non sufficiente — serve anche che `L1` si accenda e che")
    print("  nessun altro veto intervenga. Il costo VERO alla porta e' un'altra")
    print("  misura. E il criterio `\\be'(?=\\s)` e' mio: cattura il verbo, ma")
    print("  anche un `e'` dentro una citazione o un blocco di codice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
