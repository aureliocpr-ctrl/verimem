"""QUANTO SPESSO LA GRANDEZZA CHE `L4.2` MOSTRA E' UNA PAROLA VUOTA.

Alle 14:02, salvando un fatto mio, `L4.2` ha stampato nella ricevuta::

    L4.2 — il claim riusa un numero della fonte riferendolo a un'altra
    grandezza: 26 qui e' «fatti», nella fonte «di fonti il la non su»

**«di fonti il la non su» non e' una grandezza**: sono parole vuote
incollate. Il **verdetto** era giusto — `L4.2` e' un avviso, non un veto, e non
ha quarantinato niente — ma **il messaggio non insegna nulla a chi lo legge**.

\U0001f4d6 **E il codice LO SA GIA'**. `_da_mostrare` (`vicinato_del_valore.py:111`)
dichiara il problema con precisione::

    In italiano quel token e' spessissimo una congiunzione o una preposizione
    («0.3732 ed esito», «99.9588 su due»), e quando manca del tutto la
    ricevuta stampava «?» su entrambi i lati, cioe' niente su cui agire.

⇒ **C'e' gia' stata una cura** (mostrare anche il lato precedente). Ma
«**spessissimo**» e' un avverbio, non un numero — e il mio caso mostra
che **anche col lato precedente si ottengono parole vuote**.

LA DOMANDA: **su quanti casi la grandezza mostrata e' fatta SOLO di parole
vuote?** Perche' la conseguenza e' che in quei casi **la ricevuta occupa spazio
e non dice niente**, ed e' l'unica cosa che l'utente vede.

ATTESA DICHIARATA PRIMA: una quota **alta** sul lato `nella_fonte` (il commento
dice «spessissimo») e **bassa** sul lato `nel_claim`, perche' chi scrive il
claim mette il numero accanto alla cosa che conta. ⚠️ **Se fossero
entrambe basse**, il difetto e' raro e il mio caso era sfortuna: lo dico.

CONTROLLI CHE POSSONO FALLIRE:
 (1) **la lista delle parole vuote la dichiaro**, e conto **a parte** i casi in
     cui la grandezza e' *mista* (una vuota + una piena): confonderli con le
     vuote gonfierebbe il numero, ed e' l'errore che oggi mi e' costato caro.
 (2) **controllo positivo**: qualche grandezza deve risultare PIENA. Se fossero
     tutte vuote, il mio criterio sta prendendo tutto e non misura niente.
 (3) la funzione e' **pura** (nessun moat, nessun modello): gira su tutta la
     popolazione, quindi **non e' un campione** e non ha bisogno di esserlo.

    python -u docs/stato-reale/banchi/quanto-spesso-la-grandezza-di-L42-e-una-parola-vuota.py
"""

from __future__ import annotations

import sqlite3
import sys

#: DICHIARATA: articoli, preposizioni, congiunzioni, ausiliari — le parole che
#: non nominano una grandezza. Piu' i marcatori che il codice stesso usa.
VUOTE = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "l", "d", "dell",
    "della", "dello", "delle", "degli", "dei", "del", "di", "da", "dal",
    "dalla", "in", "nel", "nella", "con", "su", "sul", "sulla", "per", "tra",
    "fra", "a", "al", "alla", "ai", "agli", "alle", "e", "ed", "o", "od",
    "ma", "che", "chi", "cui", "non", "piu", "meno", "come", "se", "si",
    "ne", "ci", "vi", "lo", "gia", "ancora", "solo", "anche", "poi",
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or",
    "is", "are", "was", "were", "be", "been", "with", "by", "from", "as",
    "e'", "è", "ha", "hanno", "sono", "era", "erano", "?",
}


def _classifica(testo: str) -> str:
    """VUOTA se ogni token e' una parola vuota · MISTA se almeno uno regge ·
    PIENA se nessuno e' vuoto. Il caso misto sta a parte di proposito."""
    tok = [t for t in testo.replace("«", " ").replace("»", " ").split()
           if t.strip()]
    tok = [t.strip(".,;:()[]").casefold() for t in tok]
    tok = [t for t in tok if t]
    if not tok:
        return "assente"
    vuote = sum(1 for t in tok if t in VUOTE)
    if vuote == len(tok):
        return "VUOTA"
    if vuote:
        return "mista"
    return "piena"


def main() -> int:
    try:
        from verimem.config import CONFIG
        from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select proposition, grounding_span from facts "
        "where superseded_by is null and grounding_span is not null "
        "and grounding_span <> ''").fetchall()
    print(f"  fatti vivi con fonte: {len(righe)}  (popolazione INTERA: la"
          " funzione e' pura, niente campione)")

    # 🪞 DUE UNITA' DIVERSE, e la prima stesura le confondeva: la funzione
    #    torna una LISTA per fatto, quindi contare i risultati NON e' contare i
    #    fatti. Le tengo separate perche' rispondono a due domande diverse:
    #    «quanto e' rumoroso l'avviso» si misura sui FATTI, «quanto e' confuso
    #    il messaggio» sui RIUSI.
    riusi, fatti_con_avviso = [], 0
    for prop, span in righe:
        try:
            rr = list(valori_riusati_da_altro_contesto(prop or "", span or ""))
        except Exception:  # noqa: BLE001
            continue
        if rr:
            fatti_con_avviso += 1
            riusi.extend(rr)
    print(f"  FATTI su cui `L4.2` parla : {fatti_con_avviso}"
          f"  ({100.0 * fatti_con_avviso / len(righe):.1f}% della popolazione)")
    print(f"  RIUSI segnalati in totale : {len(riusi)}"
          f"  ({len(riusi) / max(1, fatti_con_avviso):.1f} per fatto)")
    if len(riusi) < 20:
        print("NON RIUSCITO: meno di venti casi, non misuro una quota.")
        return 1

    print("\n  -- CONTROLLO (1): le tre classi, contate SEPARATE")
    for lato, campo in (("nel_claim", "nel_claim"), ("nella_fonte", "nella_fonte")):
        conta: dict[str, int] = {}
        for r in riusi:
            k = _classifica(str(getattr(r, campo, "")))
            conta[k] = conta.get(k, 0) + 1
        tot = sum(conta.values())
        print(f"\n     lato «{lato}»  ({tot} casi)")
        for k in ("VUOTA", "mista", "piena", "assente"):
            n = conta.get(k, 0)
            print(f"       {k:<9}{n:>6}  ({100.0 * n / tot:.1f}%)")

    print("\n  -- CONTROLLO (2): qualche grandezza e' PIENA?")
    piene = [r for r in riusi
             if _classifica(str(getattr(r, "nella_fonte", ""))) == "piena"]
    print(f"     piene sul lato fonte: {len(piene)}")
    if not piene:
        print("     CADUTO - nessuna piena: il mio criterio prende tutto e non")
        print("     misura niente. Il numero sopra non vale.")
        return 1

    vuote_fonte = sum(1 for r in riusi
                      if _classifica(str(getattr(r, "nella_fonte", ""))) == "VUOTA")
    quota = 100.0 * vuote_fonte / len(riusi)

    print("\n  == LA RIGA CHE CONTA")
    if quota >= 30:
        print(f"     🔴 **«SPESSISSIMO» E' {quota:.1f}%**: in {vuote_fonte}"
              f" casi su {len(riusi)} la grandezza che la")
        print("     ricevuta mostra e' fatta SOLO di parole vuote. ⇒ Il verdetto")
        print("     regge (`L4.2` e' un avviso), ma **il messaggio non insegna")
        print("     nulla a chi lo legge** — e la ricevuta e' l'unica cosa che")
        print("     l'utente vede.")
    elif quota >= 5:
        print(f"     🟡 {quota:.1f}%: il difetto esiste e non e' la regola.")
        print("     « Spessissimo » sovrastima.")
    else:
        print(f"     🟢 {quota:.1f}%: raro. **Il mio caso delle 14:02 era")
        print("     sfortuna**, e la cura del lato precedente ha gia' fatto il")
        print("     suo lavoro. Lo dico con la stessa forza.")

    print("\n  cinque esempi di grandezza VUOTA sul lato fonte:")
    n = 0
    for r in riusi:
        if _classifica(str(getattr(r, "nella_fonte", ""))) == "VUOTA":
            print(f"     {getattr(r, 'valore', '?')} qui «{getattr(r, 'nel_claim', '')}»"
                  f", nella fonte «{getattr(r, 'nella_fonte', '')}»")
            n += 1
            if n >= 5:
                break

    print("\n  ⚠️ COSA NON DICE: **la lista delle parole vuote e' mia** e una")
    print("  parola in piu' o in meno sposta la quota — per questo i casi")
    print("  MISTI sono contati a parte e non sommati alle vuote. E questo NON")
    print("  e' un difetto del verdetto: `L4.2` e' un avviso e non quarantina.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
