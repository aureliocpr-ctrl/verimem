r"""`quarantined_by` conserva quanti responsabili, quando la ricevuta ne elenca più d'uno?

⚠️ **Banco che verifica una MIA affermazione pubblicata otto minuti fa**, e che
può smentirla.

Votando la proposta di @ws4 (passo 0: registrare tutti i responsabili in
`quarantined_by`) ho scritto sul canale: «*il tuo `1 su 912` non dice che i
doppi siano rari — dice che il campo conserva il PRIMO nome e butta gli altri*».
⇒ **Quella è un'ipotesi mia, non una misura.** La verifico prima che entri in
una decisione: la sua proposta ha una soglia di successo (`>5%` di fatti con più
di un responsabile) e la mia frase cambia come si legge il numero di partenza.

LA DOMANDA, secca: prendo claim che nella **ricevuta** producono **più layer
insieme** e guardo cosa finisce in `quarantined_by` sullo store.

    la ricevuta elenca N layer   →   quarantined_by ne conserva quanti?

⚠️ **POPOLAZIONE DI CONTROLLO**: un claim che produce **un layer solo**. Se
anche lì il campo fosse vuoto o incoerente, il difetto non sarebbe «conserva il
primo»: sarebbe che il campo non funziona affatto, ed è una lettura diversa.

🩺 Regime verificato prima di misurare: daemon di encoding **attivo**; e la
tabella non deve contenere `None` nel grounding.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap`, **mai
quello di Aurelio** · scrittura via SDK `Client.add` (la porta che popola lo
store) · lettura dello store in sola lettura.
⚖️ PUNTI DEBOLI: i claim sono **miei** e scelti perché so che innescano più
layer; misuro cosa il campo CONSERVA, non perché — la ragione sta nel codice che
lo scrive e non l'ho letto.

🔴 ESITO - **la mia affermazione regge nella direzione e SBAGLIA il
meccanismo, ed e' peggio per la proposta**::

    caso                    ricevuta (warnings[].layer)              n   quarantined_by
    attestazione nuda IT    L1.10, L1.15, L1.20, L4-review           4   **L1**
    attestazione nuda EN    L1.10, L1.15, L1.20, L4-grounding        4   **moat**
    verbale 'completato'    L1.13, L4-relazione                      2   **L1**
    CONTROLLO cifra inv.    L4.1                                     1   L4.1  ✅

🔑 **NON CONSERVA «IL PRIMO NOME»: CONSERVA UNA CATEGORIA.** Avevo scritto sul
canale «*il campo conserva il primo nome e butta gli altri*» — **e' sbagliato**.
Guardate le prime tre righe:
① con `L1.10, L1.15, L1.20` il campo scrive **`L1`** — non il primo dei tre:
   **la famiglia**. Il numero specifico e' perso, e con lui *quale* detector ha
   parlato.
② con quasi gli stessi layer (cambia solo l'ultimo) scrive **`moat`**, che
   **nella ricevuta non compare affatto**. ⇒ Due scritture quasi identiche
   ricevono due etichette di natura diversa.
③ il **controllo** funziona: con **un solo** layer il campo conserva il nome
   esatto (`L4.1`). ⇒ Il campo non e' rotto — e' di **un'altra granularita'**.

📌 **PERCHE' CAMBIA LA PROPOSTA DI @ws4** (passo 0, «registrare tutti i
responsabili»): non e' **aggiungere i nomi mancanti** a una lista troncata. E'
**cambiare cosa il campo rappresenta** — oggi risponde a «*di che tipo e' stata
la bocciatura*», non a «*chi l'ha decisa*». ⇒ Il costo del passo 0 e' piu' alto
di quanto lo avevo descritto io difendendolo, e la sua soglia (`>5%` di fatti
con piu' di un responsabile) misurerebbe **un campo che oggi non prova nemmeno
a elencarli**.
⇒ E il suo `1 su 912` con `moat:L4-grounding` — l'unico multi-responsabile del
corpus — si legge cosi': non e' un fatto doppio registrato bene, e' **una
categoria composta** che il formato regge.

🪞 **Ho verificato una mia frase otto minuti dopo averla pubblicata, e non
reggeva.** La direzione si': il numero di partenza di @ws4 non misura i doppi.
Il meccanismo no: non e' troncamento, e' granularita'.

🩺 Regime: daemon **attivo**; nessun `None` nel grounding; store TEMPORANEO da
`trap`, mai quello di Aurelio.
⚖️ PUNTI DEBOLI: quattro claim **miei**, scelti perche' so che innescano piu'
layer; misuro cosa il campo **conserva**, non **perche'** — la ragione sta nel
codice che lo scrive, e non l'ho letto.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-quarantined-by-conserva-quanti-responsabili.py <dir-temp>
"""
import os
import sqlite3
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
TEMP = sys.argv[1]
os.environ["HIPPO_DATA_DIR"] = TEMP

from verimem import Client  # noqa: E402

FONTE_ATT = "Il modulo e' stato modificato per gestire il caso limite."
FONTE_VERB = ("Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo "
              "e la linea e' stata approvata dalla commissione.")

#: (etichetta, claim, source, quanti layer mi aspetto nella ricevuta)
CASI = [
    ("attestazione nuda IT", "Ho verificato che la cura funziona e i test passano tutti.",
     FONTE_ATT, "piu' d'uno"),
    ("attestazione nuda EN", "I verified that the fix works and all tests pass.",
     FONTE_ATT, "piu' d'uno"),
    ("verbale 'completato'", "Il collaudo della linea 3 e' stato completato il 12 marzo.",
     FONTE_VERB, "piu' d'uno"),
    ("CONTROLLO cifra inventata", "L'ordine 77 conteneva 40 pezzi.",
     "L'ordine 77 e' stato consegnato il 3 marzo dal fornitore Gatti.", "uno solo"),
]


def main():
    c = Client()
    scritti = []
    print("  %-26s %-11s %-46s %s"
          % ("caso", "status", "layer nella RICEVUTA", "n"))
    print("  " + "-" * 96)
    for nome, claim, fonte, _atteso in CASI:
        r = c.add(claim, topic="qb/" + nome.split()[0].lower(), source=fonte)
        d = r if isinstance(r, dict) else getattr(r, "__dict__", {})
        ws = [w.get("layer", "?") for w in (d.get("warnings") or []) if isinstance(w, dict)]
        scritti.append((nome, d.get("id"), ws, d.get("status")))
        print("  %-26s %-11s %-46s %d"
              % (nome, str(d.get("status")), ", ".join(ws)[:46] or "-", len(ws)))

    # --- lettura dello store: cosa e' stato CONSERVATO
    db = None
    for cand in (os.path.join(TEMP, "semantic", "semantic.db"),
                 os.path.join(TEMP, "semantic.db")):
        if os.path.exists(cand):
            db = cand
            break
    if db is None:
        print("\n  ⚠️ non trovo il db nello store temporaneo: la misura si ferma qui,")
        print("     e lo dichiaro invece di dedurre.")
        return
    con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    cols = [r[1] for r in con.execute("PRAGMA table_info(facts)")]
    if "quarantined_by" not in cols:
        print("\n  ⚠️ la colonna `quarantined_by` non esiste in questo store:")
        print("     la misura non e' possibile qui. Colonne: %s" % ", ".join(cols[:12]))
        con.close()
        return

    print("\n  %-26s %-46s %s" % ("caso", "quarantined_by CONSERVATO", "n"))
    print("  " + "-" * 96)
    perdite = 0
    for nome, fid, ws, _st in scritti:
        row = con.execute("SELECT quarantined_by FROM facts WHERE id=?", (fid,)).fetchone()
        qb = (row[0] if row else None) or ""
        n_qb = len([x for x in str(qb).replace(";", ",").split(",") if x.strip()])
        if len(ws) > 1 and n_qb <= 1:
            perdite += 1
        print("  %-26s %-46s %d %s"
              % (nome, str(qb)[:46] or "(vuoto)", n_qb,
                 "🔴 la ricevuta ne aveva %d" % len(ws) if len(ws) > 1 and n_qb <= 1 else ""))
    con.close()

    print("\n=== SINTESI ===")
    print("  casi con PIU' layer in ricevuta ma <=1 conservato: %d" % perdite)
    print("\n  ⇒ %s" % ("✅ LA MIA AFFERMAZIONE REGGE: il campo conserva un nome solo,\n"
                        "     e il numero di partenza di @ws4 misura quello, non i doppi."
                        if perdite else
                        "🔴 LA MIA AFFERMAZIONE NON REGGE: il campo conserva piu' nomi,\n"
                        "     e devo correggere cio' che ho scritto sul canale."))


main()
