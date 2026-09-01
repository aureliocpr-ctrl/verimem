r"""Il rovesciamento sulle fonti telegrafiche spiega una parte del fronte quarantena?

Chiude il cerchio su `36e704c6`: li' ho misurato che **su fonte telegrafica il giudice
da' al FALSO piu' che al VERO** (vero 0.8 contro falso 30.6), mentre in prosa separa
benissimo (100.0 contro 2.4). E in `c482f85e`: **`moat` spiega 512 dei 773 quarantinati
con causa registrata**, cioe' e' di gran lunga il primo quarantinatore.

LA DOMANDA: i quarantinati dal moat hanno una fonte **telegrafica** piu' spesso degli
ammessi? Se si', il difetto misurato al banco ha una **frequenza**, e smette di essere
un meccanismo senza numero — che e' l'errore che ho appena fatto su `L1.13`.

⚠️ **IL CRITERIO E' SINTATTICO E LO DICHIARO**: chiamo «telegrafica» una fonte con
`chiave=valore` o separatori `·` e poche parole piene. E' grezzo, e sbaglia in entrambe
le direzioni — per questo il banco lo applica **alle due popolazioni allo stesso modo**:
un criterio storto che sbaglia uguale su entrambe lascia il CONFRONTO leggibile, anche
quando il valore assoluto non lo e'.

⚠️ **E MISURO `grounding_span`, NON LA SOURCE**: sono cose diverse (reperto `W7-90` di
@ws7 — lo span salvato ha un budget di 400 caratteri ed e' piu' stretto di quello
giudicato). Assumo che **la forma** si conservi nel ritaglio: un estratto di una riga
`chiave=valore` resta `chiave=valore`. **E' un'assunzione, non una misura.**

⚠️ **E STRATIFICO PER MESE**: stasera ho gia' pubblicato un divario globale che era
**composizione temporale** (`ce735e1e`), e non voglio rifarlo tre ore dopo.

🟡 ESITO — **il globale dice una cosa, il per-mese il contrario, e vince il per-mese**::

    ① GLOBALE                    con span  telegraf.   quota   Wilson 95%
    ammessi                         14344       2828   19.7%  [19.1, 20.4]
    quarantinati da MOAT              487        132   27.1%  [23.3, 31.2]  disgiunti
    quarantinati da L4.1              144         58   40.3%  [32.6, 48.4]

    ② PER MESE (l'unico con campione da entrambe le parti)
    2026-08     ammessi 9384 (29.8%)     moat 483 (27.3%)     -2.5 pt

🪞 **IL GLOBALE E' UN ARTEFATTO DI COMPOSIZIONE, di nuovo.** Il confronto complessivo
dava **+7.4 punti con intervalli disgiunti** — sembra un segnale. Nell'unico mese
misurabile il segno **si inverte**: i quarantinati dal moat sono **meno** telegrafici
degli ammessi.

⇒ **Il rovesciamento misurato al banco (`36e704c6`, vero 0.8 contro falso 30.6 su fonte
telegrafica) resta REALE e resta SENZA FREQUENZA dimostrata sul corpus.** E' il
**secondo** meccanismo senza frequenza che trovo in un'ora — l'altro e' `L1.13`
(`c482f85e`).

🔑 **E la cosa che conta piu' del numero: il presidio ha funzionato PRIMA della
pubblicazione.** Tre ore fa avevo pubblicato un «tre volte tanto» che stratificato
diventava «+3 punti» (`ce735e1e`), e ho dovuto correggermi sul canale. Qui la
stratificazione era **dentro il banco**, e il verdetto sbagliato non e' mai uscito.
⇒ **La differenza fra le due volte non e' l'attenzione: e' che il controllo era scritto
nel codice invece che nelle intenzioni.**

⚖️ **La base temporale e' FRAGILE**: 4 mesi su 5 saltati per campione sotto 25, quindi
il verdetto poggia su **un solo mese** — che pero' e' quello attuale, ed e' il regime su
cui si decide.

SOLA LETTURA: `mode=ro`, percorso da `CONFIG.semantic_db`.
⚖️ PUNTI DEBOLI: il criterio e' mio; lo span non e' la source; e «quarantinato da moat»
lo leggo da `quarantined_by`, che copre **773 fatti su 2682** — il resto non ha causa.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-quanto-pesa-la-forma-telegrafica-sui-quarantinati.py
"""
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path

from verimem.config import CONFIG

#: `chiave=valore`, separatori a punto medio, o densita' di simboli alta
TELEGRAFICA = re.compile(r"\w+=\S|·|\|\s*\d|^\s*\w+:\s*\d", re.M)
MIN_CAMPIONE = 25


def wilson(k, n):
    if not n:
        return (0.0, 0.0)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    e = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0.0, c - e), 100 * min(1.0, c + e))


def quota(righe):
    n = len(righe)
    k = sum(1 for t in righe if t and TELEGRAFICA.search(t))
    return n, k, (100.0 * k / n if n else 0.0)


def main():
    p = Path(str(CONFIG.semantic_db))
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    cur = con.cursor()

    def prendi(dove):
        return cur.execute(
            "select grounding_span, created_at from facts where grounding_span is not null "
            "and grounding_span != '' and " + dove).fetchall()

    gruppi = [
        ("ammessi (status != quarantined)", prendi("status is null or status != 'quarantined'")),
        ("quarantinati da MOAT", prendi("status='quarantined' and quarantined_by='moat'")),
        ("quarantinati da L4.1", prendi("status='quarantined' and quarantined_by='L4.1'")),
    ]

    print("① GLOBALE — quota di span TELEGRAFICI\n")
    print("  %-34s %8s %10s %8s %s" % ("popolazione", "con span", "telegraf.", "quota", "Wilson 95%"))
    print("  " + "-" * 86)
    base = None
    for nome, righe in gruppi:
        n, k, q = quota([r[0] for r in righe])
        lo, hi = wilson(k, n)
        if base is None:
            base, base_lo, base_hi = q, lo, hi
        print("  %-34s %8d %10d %7.1f%% [%5.1f%%, %5.1f%%]" % (nome, n, k, q, lo, hi))

    print("\n② STRATIFICATO PER MESE (ammessi contro quarantinati-moat)\n")
    per_mese = defaultdict(lambda: {"amm": [], "moat": []})
    for chiave, righe in (("amm", gruppi[0][1]), ("moat", gruppi[1][1])):
        for span, creato in righe:
            try:
                m = datetime.fromtimestamp(float(creato), tz=timezone.utc).strftime("%Y-%m")
            except (TypeError, ValueError, OSError):
                continue
            per_mese[m][chiave].append(span)

    print("  chiavi: %s\n" % ", ".join(sorted(per_mese)))
    print("  %-9s %22s %22s   %s" % ("mese", "AMMESSI n (tel.%)", "MOAT n (tel.%)", "delta"))
    print("  " + "-" * 76)
    concordi = discordi = saltati = 0
    for mese in sorted(per_mese):
        a, m = per_mese[mese]["amm"], per_mese[mese]["moat"]
        if len(a) < MIN_CAMPIONE or len(m) < MIN_CAMPIONE:
            saltati += 1
            continue
        na, ka, qa = quota(a)
        nm, km, qm = quota(m)
        if qm > qa:
            concordi += 1
        else:
            discordi += 1
        print("  %-9s %10d (%5.1f%%)      %10d (%5.1f%%)   %+6.1f pt"
              % (mese, na, qa, nm, qm, qm - qa))
    con.close()

    print("\n=== SINTESI ===")
    n_m, k_m, q_m = quota([r[0] for r in gruppi[1][1]])
    lo_m, hi_m = wilson(k_m, n_m)
    # ⚠️ LA GERARCHIA CONTA: il globale mescola le ere, il per-mese no. Quando i due
    # dicono cose diverse, e' il per-mese a valere — l'ho imparato tre ore fa
    # pubblicando un «tre volte tanto» che stratificato diventava +3 punti.
    if not n_m:
        print("  ⚠️ nessun quarantinato-moat con span: non misurabile.")
        return
    print("  globale: moat %.1f%% [%.1f%%, %.1f%%] contro ammessi %.1f%% [%.1f%%, %.1f%%]"
          % (q_m, lo_m, hi_m, base, base_lo, base_hi))
    leggibili = concordi + discordi
    if not leggibili:
        print("  ⚠️ NESSUN MESE con campione sufficiente (%d saltati): il globale non ha"
              % saltati)
        print("     un controllo temporale, e da solo NON si legge.")
    elif discordi and not concordi:
        print("  🪞 IL GLOBALE E IL PER-MESE SI CONTRADDICONO, e vince il per-mese:")
        print("     nell'unico regime misurabile i quarantinati dal moat sono MENO")
        print("     telegrafici degli ammessi ⇒ **il divario globale e' composizione")
        print("     temporale**, e la forma telegrafica NON risulta sovra-rappresentata.")
        print("  ⇒ Il rovesciamento misurato al banco (`36e704c6`) resta REALE e resta")
        print("     SENZA FREQUENZA dimostrata sul corpus. Va detto cosi'.")
    elif concordi and not discordi:
        print("  🔴 CONFERMATO in %d mesi su %d: dentro ogni mese i quarantinati dal moat"
              % (concordi, leggibili))
        print("     sono piu' telegrafici ⇒ il divario NON e' composizione temporale.")
    else:
        print("  🟡 %d mesi concordi e %d discordi: il segno non e' costante, e il globale"
              % (concordi, discordi))
        print("     da solo non si legge.")
    if saltati:
        print("  ⚖️ %d mesi saltati per campione sotto %d: la base temporale e' FRAGILE."
              % (saltati, MIN_CAMPIONE))


main()
