"""La data nella domanda: ANCORA retrospettiva o SOGGETTO della domanda?

Il documento `67` ha stabilito che il difetto non e' `recall_as_of` — che fa il
suo mestiere: su 25 fatti superseduti ne recupera 2 che la recall di oggi non
restituisce affatto — ma il TRIGGER: `extract_as_of` accetta l'articolo «il», e
il commento sopra la regex lo dichiara gia' («da soli sono gli articoli piu'
comuni della lingua»).

DUE USI DIVERSI DELLA STESSA DATA:

  ANCORA   «cosa SAPEVAMO al 18 luglio 2026»   -> lo stato della conoscenza A
           quella data. Il time travel e' CORRETTO.
  SOGGETTO «cosa E' SUCCESSO il 18 luglio 2026» -> un evento avvenuto QUEL
           giorno. Il time travel e' SBAGLIATO: esclude ogni fatto scritto dopo,
           cioe' quasi tutti i fatti che RACCONTANO quel giorno.

⚠️ IL CRITERIO E' MIO E LO DICHIARO: l'etichetta di ogni riga la decido io, e
un'altra persona potrebbe etichettare diversamente qualche caso di confine. La
regola che ho applicato e' una sola, scritta prima di guardare i risultati:

    ANCORA se la domanda chiede lo STATO DELLA CONOSCENZA a una data
            (sapevamo, risultava, era registrato, as of, did we know)
    SOGGETTO se la domanda chiede un EVENTO o un DATO DI QUEL GIORNO
            (cosa e' successo, quanti ne sono stati scritti, chi ha fatto)

🪞 E MISURO ENTRAMBE LE POPOLAZIONI: un banco fatto solo di SOGGETTI direbbe che
la regex sbaglia sempre, e sarebbe il difetto del misuratore, non del prodotto.

SOLA LETTURA, nessun modello: `extract_as_of` e' una regex pura.
"""
from __future__ import annotations

from verimem.temporal_context import extract_as_of

# (domanda, lingua, ANCORA?) — ANCORA True = il time travel e' corretto qui
CASI = [
    # ---------- ANCORE VERE: il time travel e' il comportamento giusto ----------
    ("cosa sapevamo al 18 luglio 2026 sul magazzino", "IT", True),
    ("che cosa risultava al 5 agosto 2026 sul contratto", "IT", True),
    ("alla data del 31 gennaio 2026 quanti clienti attivi", "IT", True),
    ("fino al 3 marzo 2019 quali fornitori erano registrati", "IT", True),
    ("prima del 12 giugno 2026 quale prezzo era in vigore", "IT", True),
    ("entro il 30 aprile 2026 cosa era stato approvato", "IT", True),
    ("qual era lo stato del progetto al 2026-02-14", "IT", True),
    ("what did we know as of July 18, 2026", "EN", True),
    ("what was on record by March 3, 2019", "EN", True),
    ("which suppliers were registered until 12 June 2026", "EN", True),
    ("what was the price before 2026-06-12", "EN", True),
    ("what did the file say as of 2026-02-14", "EN", True),

    # ---------- ANCORE VERE MARCATE SOLO DA «il» / «on» ----------
    # ⚠️ AGGIUNTI DOPO, e apposta: la prima stesura di questo banco non ne
    # conteneva nessuno, e con quella una cura che TOGLIE «il» e «on» dalle
    # ancore segnava 100% su entrambi i lati. Un 100% su un banco scritto da
    # chi propone la cura e' la firma di un banco ritagliato sulla cura, non
    # di una cura che funziona: questi casi esistono nella lingua e vanno
    # misurati, anche se fanno perdere punti alla mia proposta.
    ("qual era il prezzo in vigore il 5 agosto 2026", "IT", True),
    ("chi era il responsabile il 18 luglio 2026", "IT", True),
    ("il 3 marzo 2019 il contratto era gia firmato", "IT", True),
    ("what was the price on July 18, 2026", "EN", True),
    ("who was on call on 5 August 2026", "EN", True),
    ("was the contract already signed on 3 March 2019", "EN", True),

    # ---------- SOGGETTI: la data e' l'OGGETTO, il time travel e' sbagliato ----------
    ("il 18 luglio 2026 quanti fatti sono stati scritti", "IT", False),
    ("cosa e successo il 18 luglio 2026", "IT", False),
    ("quanti fatti sono stati scritti il 19 agosto 2026", "IT", False),
    ("chi ha firmato il 5 agosto 2026", "IT", False),
    ("il 30 agosto 2026 quante letture sono fallite", "IT", False),
    ("l incidente del 18 luglio 2026 quanto e durato", "IT", False),
    ("riassumi la riunione del 9 giugno 2026", "IT", False),
    ("quante consegne il 2026-01-31", "IT", False),
    ("how many facts were written on July 18, 2026", "EN", False),
    ("what happened on July 18, 2026", "EN", False),
    ("who signed on 5 August 2026", "EN", False),
    ("summarise the meeting on 9 June 2026", "EN", False),
]


def main():
    print("ANCORA o SOGGETTO — la regex distingue i due usi della stessa data?")
    print("(etichette mie, criterio dichiarato nel docstring)\n")

    ok_ancore = ok_sogg = 0
    n_ancore = sum(1 for _, _, a in CASI if a)
    n_sogg = len(CASI) - n_ancore
    sbagliati = []

    for dom, lang, e_ancora in CASI:
        ancorata = extract_as_of(dom) is not None
        giusto = (ancorata == e_ancora)
        if e_ancora and giusto:
            ok_ancore += 1
        elif (not e_ancora) and giusto:
            ok_sogg += 1
        if not giusto:
            sbagliati.append((dom, lang, e_ancora, ancorata))

    print("ANCORE VERE (il time travel SERVE)")
    print("  riconosciute come ancora : %2d/%-2d = %5.1f%%   <- se basso, il"
          " prodotto perde una funzione" % (ok_ancore, n_ancore,
                                            100.0 * ok_ancore / max(1, n_ancore)))
    print()
    print("SOGGETTI (il time travel FA DANNO)")
    print("  lasciati stare          : %2d/%-2d = %5.1f%%   <- se basso, spegne"
          " letture buone" % (ok_sogg, n_sogg, 100.0 * ok_sogg / max(1, n_sogg)))
    print()

    if sbagliati:
        print("I CASI IN CUI SBAGLIA:")
        for dom, lang, e_ancora, ancorata in sbagliati:
            verso = ("ANCORA ma NON ancorata" if e_ancora
                     else "SOGGETTO ma ANCORATA")
            print("  [%s] %-52s %s" % (lang, dom[:52], verso))

    print()
    print("Per lingua, sui SOGGETTI (dove il danno accade):")
    for lg in ("IT", "EN"):
        g = [(d, a) for d, l, a in CASI if l == lg and not a]
        salvi = sum(1 for d, _ in g if extract_as_of(d) is None)
        print("  %s  lasciati stare %d/%d" % (lg, salvi, len(g)))


if __name__ == "__main__":
    main()
