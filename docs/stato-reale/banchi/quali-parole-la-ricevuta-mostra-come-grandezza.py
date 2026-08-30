"""QUALI PAROLE, DAVVERO, LA RICEVUTA DI `L4.2` MOSTRA COME GRANDEZZA.

⚠️ **QUESTO BANCO NASCE DA UN DIFETTO MIO, di quattro ore fa.** Alle 19:02, il
prodotto ha stampato salvando un mio fatto::

    146 qui e' «hanno», nella fonte «prima del numero: quarantined»

Il lato `nella_fonte` e' **curato** — mostra il lato precedente, ed e' la cura
`af0422d7` che gira. Il lato `nel_claim` mostra **«hanno»**: un ausiliare
italiano, che grandezza non e'. ⇒ **La cura ha mancato esattamente il caso che
l'aveva motivata**, e la ragione e' nella lista che ho scritto io::

    _GRAMMATICA  ausiliari EN presenti : is are was were be been
                 ausiliari IT presenti : NESSUNO
                 (e mancano anche has/have/had)

E' la **classe ③ — liste monolingue** — che sta scritta fra le lezioni di casa
da settimane. L'ho commessa poche ore dopo averla citata: e' il motivo per cui
un difetto va **misurato**, non dedotto dalla propria attenzione.

🎯 LA DOMANDA, e la ragione per cui non aggiungo semplicemente le parole che mi
vengono in mente: **quali token, ORDINATI PER FREQUENZA, il prodotto mostra
davvero come grandezza?** Indovinare la lista e' come scrivere il banco che
misura il proprio criterio — la trappola gia' registrata. **I dati scelgono la
lista, io scelgo solo cosa e' ambiguo.**

⚠️ E la prova che serve DAVVERO a decidere non e' la frequenza: e' **quanti
casi cambierebbero** togliendo la voce. La stampo, perche' un criterio che non
sposta il numero non e' un criterio.

CONTROLLI CHE POSSONO FALLIRE:
 (1) ✅ **controllo positivo**: in cima devono comparire anche parole PIENE
     (grandezze vere). Se in testa ci fosse solo grammatica, la cura di stamane
     non avrebbe funzionato affatto e il numero direbbe altro.
 (2) 🪞 **DUE LATI, non uno**: `nel_claim` e `nella_fonte` hanno distribuzioni
     diverse (misurato in `W7-80`: vuota 34,6% contro 15,5%). Contarli insieme
     mescolerebbe due popolazioni.
 (3) ⚖️ **la funzione e' PURA**: nessun modello, nessun moat. Popolazione
     INTERA, quindi non e' un campione e non ha bisogno di esserlo.
 (4) 🔴 **AMBIGUI DICHIARATI**: in italiano «danno», «conta», «stato», «era»
     sono ANCHE sostantivi. Li stampo a parte e **non li propongo**: una parola
     che puo' essere una grandezza non va in una lista di non-grandezze.

    python -u docs/stato-reale/banchi/quali-parole-la-ricevuta-mostra-come-grandezza.py
"""

from __future__ import annotations

import sqlite3
import sys

#: Parole che in italiano sono ANCHE sostantivi: non possono entrare in una
#: lista di «parole che non nominano una grandezza», per quanto frequenti.
AMBIGUE = {"danno", "conta", "stato", "stati", "era", "ere", "essere",
           "potere", "dovere", "volere", "avere", "credito", "debito"}


def main() -> int:
    try:
        from verimem.config import CONFIG
        from verimem.vicinato_del_valore import (
            _GRAMMATICA, _intorno, valori_riusati_da_altro_contesto)
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print(f"  voci in `_GRAMMATICA` oggi: {len(_GRAMMATICA)}")
    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select proposition, grounding_span from facts "
        "where superseded_by is null and grounding_span is not null "
        "and grounding_span <> ''").fetchall()
    print(f"  fatti vivi con fonte: {len(righe)}  (popolazione INTERA)")

    # I token GREZZI adiacenti al numero, prima che `_da_mostrare` filtri: sono
    # quelli fra cui la ricevuta sceglie, ed e' li' che si vede cosa manca.
    dal_claim: dict[str, int] = {}
    dalla_fonte: dict[str, int] = {}
    casi = 0
    for prop, span in righe:
        try:
            riusi = valori_riusati_da_altro_contesto(prop or "", span or "")
        except Exception:  # noqa: BLE001
            continue
        for r in riusi:
            casi += 1
            c_dopo, _c_prima = _intorno(prop or "", r.valore)
            f_dopo, _f_prima = _intorno(span or "", r.valore)
            for t in c_dopo:
                dal_claim[t] = dal_claim.get(t, 0) + 1
            for t in f_dopo:
                dalla_fonte[t] = dalla_fonte.get(t, 0) + 1
    print(f"  riusi segnalati da `L4.2`: {casi}")
    if casi < 50:
        print("NON RIUSCITO: meno di cinquanta casi, non ordino una classifica.")
        return 1

    for eti, conta in (("nel_claim", dal_claim), ("nella_fonte", dalla_fonte)):
        print(f"\n  -- I VENTI TOKEN PIU' FREQUENTI dopo il numero, lato"
              f" «{eti}»")
        print("     (✅=gia' filtrata · 🔴=NON filtrata · ⚠️=ambigua, non la"
              " propongo)")
        for tok, n in sorted(conta.items(), key=lambda t: -t[1])[:20]:
            if tok in _GRAMMATICA:
                seg = "✅"
            elif tok in AMBIGUE:
                seg = "⚠️"
            else:
                seg = "🔴"
            print(f"     {seg} {tok:<18}{n:>6}")

    # (1) controllo positivo: in cima ci sono anche parole PIENE?
    piene_in_testa = [t for t, _ in sorted(dalla_fonte.items(),
                                           key=lambda x: -x[1])[:20]
                      if t not in _GRAMMATICA and t not in AMBIGUE]
    print(f"\n  -- (1) controllo positivo: token NON grammaticali fra i primi"
          f" 20 del lato fonte: {len(piene_in_testa)}")
    if not piene_in_testa:
        print("     CADUTO: in testa c'e' solo grammatica, sto misurando il"
              " filtro e non il corpus.")
        return 1

    # ⚖️ La prova che decide: quanti casi CAMBIEREBBERO aggiungendo le voci.
    candidati = {t for t in list(dal_claim) + list(dalla_fonte)
                 if t not in _GRAMMATICA and t not in AMBIGUE
                 and t in {"ha", "hanno", "sono", "sia", "siano", "sta",
                           "stanno", "viene", "vengono", "has", "have", "had",
                           "e", "ed", "risulta", "risultano", "restano",
                           "resta", "diventa", "diventano", "vale", "valgono"}}
    print(f"\n  -- (2) I CANDIDATI (ausiliari e copule, niente ambigui):"
          f" {sorted(candidati)}")
    for eti, conta in (("nel_claim", dal_claim), ("nella_fonte", dalla_fonte)):
        colpiti = sum(n for t, n in conta.items() if t in candidati)
        tot = sum(conta.values())
        print(f"     lato «{eti}»: {colpiti} occorrenze su {tot}"
              f"  ({100.0 * colpiti / max(1, tot):.1f}%)")

    print("\n  == LA RIGA CHE CONTA")
    tot_c = sum(dal_claim.values())
    col_c = sum(n for t, n in dal_claim.items() if t in candidati)
    if col_c == 0:
        print("     🟢 **ZERO**: nessun ausiliare compare come grandezza."
              " Il mio caso")
        print("     delle 19:02 era isolato e **la lista monolingue non"
              " costa nulla**.")
        print("     Lo dico con la stessa forza con cui avrei detto il"
              " contrario.")
    else:
        print(f"     🔴 **{col_c} occorrenze su {tot_c} del lato `nel_claim`"
              f" ({100.0 * col_c / tot_c:.1f}%)**")
        print("     sono ausiliari o copule mostrati come se fossero una"
              " grandezza.")
        print("     ⇒ La lista e' monolingue e il costo e' misurato, non"
              " supposto.")

    print("\n  ⚠️ COSA NON DICE: questo NON cambia un verdetto — `L4.2` e' un"
          " avviso e")
    print("  il criterio non legge questa lista. Cambia **cio' che l'utente"
          " legge**,")
    print("  che e' l'unica cosa che l'utente vede.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
