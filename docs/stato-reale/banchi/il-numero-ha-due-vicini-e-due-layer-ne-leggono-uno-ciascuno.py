"""IL NUMERO HA DUE VICINI, e due layer diversi ne leggono UNO CIASCUNO.

@ws1 ha misurato (00:33) che **la parola che PRECEDE il numero** decide se il
gate lo tratta come identificatore di record o come unita': «EUR 500» coesiste,
«500 EUR» viene quarantinato. E ha isolato il ramo: `_record_numerati_diversi`,
**posizionale**, che non ha «*un'eccezione per le etichette che non identificano
un record — valute, preposizioni, VERBI*».

Io ho misurato (W7-30) che **la parola che SEGUE il numero** viene presa da
`L4.2` come nome della grandezza: su una tabella allineata prende `in`, e se
tolgo `in` prende `file`.

⇒ **IPOTESI**: sono lo stesso difetto su due lati. Due layer leggono il vicinato
posizionale di un numero, e **nessuno dei due sa distinguere un'ETICHETTA da una
parola qualsiasi**. La lista che servirebbe **esiste gia' in casa** — i
`_FUNZIONALI` di `soggetto_valore.py` — e nessuno dei due la usa.

QUI MISURO SOLO LA META' CHE MI COMPETE, che e' quella verificabile subito:
**le parole che `L4.2` prende come grandezza sono funzionali?** Se lo sono, una
lista che le scarti toglie il rumore senza toccare il meccanismo.

⚠️ NON misuro il lato di @ws1: e' suo, e il suo ramo e' un altro modulo.
⚠️ E NON propongo la cura: `L4.2` e' un AVVISO (W7-35), e chi l'ha scritto ha
gia' misurato che come veto costerebbe il 20% di falsi positivi.

CONTROLLI CHE POSSONO FALLIRE:
 (1) se le parole prese NON sono funzionali, l'ipotesi cade: il difetto non e'
     «manca una stoplist», e' qualcos'altro.
 (2) la popolazione opposta: sui casi dove `L4.2` ha RAGIONE (il «14 valvole /
     14 operai»), la parola presa dev'essere una grandezza VERA. Se anche li'
     e' funzionale, la lista romperebbe i casi buoni e non va proposta.

    python -u docs/stato-reale/banchi/il-numero-ha-due-vicini-e-due-layer-ne-leggono-uno-ciascuno.py
"""

from __future__ import annotations

import sys

# I casi dove L4.2 SBAGLIA: source tabellare, claim vero.
SBAGLIA = [
    ("Il controllo sul package verimem riporta 6 identificativi di sessione in 3 file.",
     "artefatto: verimem\n\n  BLOCCA  identificativo di sessione         6 in   3 file"),
    ("Il controllo sul package verimem esamina 421 file py.",
     "artefatto: verimem\nfile .py esaminati: 421"),
    ("Nella vista nuda i layers vuoti sono 408 su 500.",
     "     layers vuoti     : 408 su 500   (GOVERNANCE: 183 su 500)"),
    ("Sulle 500 righe la colonna quarantined_by porta moat su 279 righe.",
     "      279  moat  <- SCARTATA dalla vista\n       94  <VUOTA>"),
]

# I casi dove L4.2 ha RAGIONE: la popolazione opposta.
HA_RAGIONE = [
    ("L'impianto ha 14 valvole.", "Nel reparto lavorano 14 operai su tre turni."),
    ("Il magazzino contiene 300 pallet.", "Sono stati caricati 300 cartoni."),
    ("Il team ha chiuso 12 ticket.", "Il team ha tenuto 12 riunioni."),
]


def main() -> int:
    try:
        from verimem.soggetto_valore import _FUNZIONALI
        from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1
    print(f"  parole in _FUNZIONALI (soggetto_valore.py): {len(_FUNZIONALI)}")

    def prese(claim, fonte):
        """Le parole che L4.2 indica come grandezza NELLA FONTE."""
        out = []
        for r in (valori_riusati_da_altro_contesto(claim, fonte) or []):
            out.append((r.valore, r.nel_claim, r.nella_fonte))
        return out

    print("\n  == A. DOVE L4.2 SBAGLIA — le parole che prende dalla FONTE")
    a_funz = a_tot = 0
    for c, f in SBAGLIA:
        for v, nel, nella in prese(c, f):
            a_tot += 1
            e_funz = nella.casefold() in _FUNZIONALI
            a_funz += 1 if e_funz else 0
            marchio = "FUNZIONALE" if e_funz else "non funzionale"
            print(f"     {v:g}: claim «{nel}» · fonte «{nella}»   -> {marchio}")
    print(f"     ⇒ funzionali {a_funz} su {a_tot}")

    print("\n  == B. DOVE L4.2 HA RAGIONE — la popolazione opposta")
    b_funz = b_tot = 0
    for c, f in HA_RAGIONE:
        p = prese(c, f)
        if not p:
            print(f"     (tace)  {c[:52]}")
            continue
        for v, nel, nella in p:
            b_tot += 1
            e_funz = nella.casefold() in _FUNZIONALI
            b_funz += 1 if e_funz else 0
            marchio = "FUNZIONALE" if e_funz else "grandezza vera"
            print(f"     {v:g}: claim «{nel}» · fonte «{nella}»   -> {marchio}")
    print(f"     ⇒ funzionali {b_funz} su {b_tot}")

    print("\n  -- CONTROLLO (1): le parole sbagliate sono funzionali?")
    if a_tot == 0:
        print("     CADUTO - L4.2 non ha segnalato niente su A: il banco non")
        print("     misura quello che credo.")
        return 1
    if a_funz == 0:
        print(f"     CADUTO - 0 su {a_tot}: le parole che sbaglia NON sono")
        print("     funzionali. L'ipotesi «manca una stoplist» e' falsa.")
        return 1
    print(f"     {a_funz} su {a_tot} sono in `_FUNZIONALI`")

    print("\n  -- CONTROLLO (2): e su quelle giuste?")
    if b_tot and b_funz > 0:
        print(f"     ATTENZIONE - {b_funz} su {b_tot} dei casi GIUSTI usa una")
        print("     parola funzionale: una stoplist romperebbe anche quelli.")
        print("     ⇒ NON proporre la lista senza risolvere questo.")
    elif b_tot:
        print(f"     nessuna: sui {b_tot} casi giusti la parola e' una grandezza")
        print("     vera. La lista separerebbe le due popolazioni.")
    else:
        print("     L4.2 tace su tutta la popolazione opposta: non posso dire")
        print("     niente sul costo di una lista, e non lo dico.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
