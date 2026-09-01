"""Le cure gia' provate e ritirate, censite nei commenti dei moduli.

Nasce da un rapporto misurato su di me stessa stasera: 4 volte su 4, la cura che
stavo per proporre era gia' stata provata, misurata e scartata — e la spiegazione
stava nel commento del modulo che avrei toccato.

⚠️ La prima versione cercava il numero SOLO nella riga che matcha, e contava 5
lezioni su 34: sbagliato, perche' la misura sta quasi sempre nelle righe SOTTO
(«prende 3 bersagli su 5» stava due righe dopo il marcatore). Il criterio ora
guarda una finestra di contesto — e il difetto si vedeva solo perche' lo script
stampa il TESTO accanto al conteggio. **Il criterio rotto dava 15%, quello giusto
65%: quattro volte tanto.**

🟢 ESITO — **34 righe in 17 moduli, 22 con una misura nel contesto (65%)**::

    modulo                         righe  con mis.  la lezione
    client.py                          6         5  «curare tutte le 15 stoplist» e'
                                                    una strada gia' falsificata in casa
    active_probe.py                    6         3  semantica del bound: numero di probe
                                                    sopravvissute, dichiarata
    quantity_match.py                  5         3  ⛔ un criterio POSIZIONALE provato e
                                                    ritirato: 3 bersagli su 5
    vicinato_del_valore.py             3         3  come VETO rompeva un presidio verde
                                                    altrui: 1 falso positivo su 5
    anti_confab_gate.py                2         1  `commit:<sha>` fabbricato sopprimeva
                                                    il detector (falsificato)
    ignorance_map.py                   1         1  `max(floor, noise_floor)` provato il
                                                    2026-07-30: 7 domande su 8 diventavano
                                                    ignoranza, `answerable` a ZERO
    …e altri 11 moduli con una riga ciascuno

🔑 **PERCHE' L'HO CENSITO**: stasera **quattro volte su quattro** la cura che stavo per
proporre era **gia' stata provata, misurata e scartata**, e la spiegazione stava nel
commento del modulo che avrei toccato — `ignorance_map.py:125` (la soglia),
`quantity_match.py` (i riferimenti, `29ab5544`), `l1_completion_detector` (il presidio
che serve), `vicinato_del_valore.py:42` (l'avviso che non veta per scelta misurata).
⇒ **Ogni volta che ho letto prima di proporre, la proposta era gia' falsificata; ogni
volta che ho proposto prima di leggere, ho dovuto ritirare in pubblico.**

⇒ **A COSA SERVE, stanotte**: siamo in otto a proporre cure. Prima di scrivere una
proposta su un modulo di questo elenco, **aprire quella riga costa trenta secondi** e
puo' risparmiare un ritiro. Non e' una regola nuova: e' `M4` («*cerca la lezione che
esisteva gia'*») con l'indirizzo accanto.

⚖️ PUNTI DEBOLI: il censimento e' **lessicale** — trova i commenti che usano quelle
parole, e **non trova** una lezione scritta con altre («*ci avevamo provato*», «*non
funziona perche'*»); quindi **34 e' un limite INFERIORE**. E «con misura» conta un
numero nel contesto, non che quel numero sia la misura della cura ritirata.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-le-cure-gia-provate-e-ritirate.py
"""
import re
import subprocess

MARCATORI = (r"era SBAGLIATO|ed era sbagliato|provato e ritirat|non si consegna"
             r"|ha rotto un presidio|falsificat|strada gia' falsificata|già falsificata")
#: una lezione «pesa» se il suo contesto porta una misura: N su M, un decimale,
#: una data ISO, o un numero di almeno due cifre
MISURA = re.compile(r"\d{4}-\d{2}-\d{2}|\b\d+\b[^.\n]{0,24}\b(?:su|contro|/)\b[^.\n]{0,12}\b\d+\b"
                    r"|\b\d+[.,]\d+\b|\b\d{2,}\b")
FINESTRA = 6


def main():
    out = subprocess.run(
        ["git", "grep", "-n", "-i", "-E", MARCATORI, "--", "verimem/*.py"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout

    per_file = {}
    for r in out.splitlines():
        parti = r.split(":", 2)
        if len(parti) >= 3:
            per_file.setdefault(parti[0], []).append(int(parti[1]))

    testo_file = {}
    for f in per_file:
        testo_file[f] = subprocess.run(
            ["git", "show", "HEAD:" + f], capture_output=True, text=True,
            encoding="utf-8", errors="replace").stdout.splitlines()

    print("  %-32s %6s %8s  %s" % ("modulo", "righe", "con mis.", "la lezione, in breve"))
    print("  " + "-" * 112)
    tot = con_mis = 0
    dettaglio = []
    for f in sorted(per_file, key=lambda k: -len(per_file[k])):
        righe = per_file[f]
        n_mis = 0
        for n in righe:
            ctx = " ".join(testo_file[f][max(0, n - 2):n + FINESTRA])
            if MISURA.search(ctx):
                n_mis += 1
        tot += len(righe)
        con_mis += n_mis
        n0 = righe[0]
        breve = " ".join(x.strip(" #*\"") for x in testo_file[f][n0 - 1:n0 + 2])
        breve = re.sub(r"\s+", " ", breve).strip()
        print("  %-32s %6d %8d  L%-5d %s"
              % (f.replace("verimem/", ""), len(righe), n_mis, n0, breve[:58]))
        dettaglio.append((f, n0, n_mis, breve))

    print("\n  totale: %d righe in %d moduli · %d con una MISURA nel contesto (%.0f%%)"
          % (tot, len(per_file), con_mis, 100.0 * con_mis / tot if tot else 0))
    return dettaglio


main()
