# -*- coding: utf-8 -*-
"""TRE POPOLAZIONI SULLA STESSA FONTE REALE — e i valori non li scelgo io.

Alle 19:41 il log VERO mi ha fatto ritirare un risultato che poggiava su una
fonte costruita da me. La conseguenza vale per tutti i miei risultati sullo
SCAMBIO DI ATTRIBUZIONE: sono su un contratto che ho scritto io.

Qui lo scambio viene misurato su una fonte reale — l'uscita di
`git log --shortstat` — e sulla STESSA fonte in cui la cifra inventata risulta
ben fermata (0.3-1.1, difesa doppia). Tre popolazioni, una fonte:

  VERO      il conteggio che il log attribuisce DAVVERO a quel commit
  SCAMBIO   il conteggio di un ALTRO commit, attribuito a questo
  ASSENTE   un conteggio che nel log non c'e'

I due commit e i due conteggi il banco li SCEGLIE DA SOLO, con un criterio
scritto prima: due commit il cui numero di inserzioni compare una volta sola in
tutto il log, cosi' che l'attribuzione sia univoca. Non li scelgo io guardando
quali danno il risultato che mi aspetto — che e' esattamente l'errore che mi ha
fatto ritirare la riga di venti minuti fa.

  se SCAMBIO entra dove ASSENTE e' fermato, sulla STESSA fonte reale
     -> le due popolazioni si separano anche fuori dalle mie fonti costruite
  se anche lo scambio e' fermato
     -> la separazione era un artefatto del contratto che avevo scritto io, e
        va detto forte perche' ci ho costruito sopra cinque celle del registro

CONTROLLI CHE DEVONO POTER FALLIRE: i due conteggi devono comparire una volta
sola nel log; il claim VERO dev'essere ammesso; la cifra ASSENTE non dev'essere
nel log.

    python docs/stato-reale/banchi/tre-popolazioni-sulla-stessa-fonte-reale.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

LUNGHEZZE = [2000, 4000, 8000, 16000]
CIFRA_ASSENTE = "91234"


# 🔑 ANCORA — aggiunta il 29/08 alle 20:05, ed è la cura di un difetto DEL BANCO,
# non del prodotto. `-n 400` senza ancora è una **finestra mobile** sul nostro
# repo: fra il 28 e il 29/08 abbiamo aggiunto centinaia di commit, i conteggi di
# inserzioni che allora erano univoci hanno smesso di esserlo, e chi ha
# rieseguito questo banco si è visto rispondere «trovati 1». ⇒ La cella `W7-16`
# diceva «non riproducibile» **e aveva ragione più a fondo di quanto sapessi**:
# non si riproduceva il verdetto perché non si riproduce **la fonte**.
# Con l'ancora, chiunque ottiene lo STESSO testo e l'A/B torna a un fattore.
# Per provarne un'altra si cambia questa riga e si dichiara quale nella cella.
ANCORA = "d7f4b611"  # = HEAD~800 al 29/08 20:06; 7 candidati contro 1 su HEAD


def main() -> int:
    try:
        out = subprocess.run(
            ["git", "log", "--shortstat", "--format=@@%h|%s", "-n", "400", ANCORA],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: git log non eseguibile — {type(e).__name__}: {e}")
        return 1
    if out.returncode != 0:
        print(f"NON RIUSCITO: git log returncode {out.returncode}")
        return 1

    # (subject, insertions) per i commit che dichiarano inserzioni
    commit = []
    corrente = None
    for riga in out.stdout.splitlines():
        r = riga.strip()
        if r.startswith("@@"):
            corrente = r[2:].split("|", 1)[-1]
        elif "insertion" in r and corrente:
            m = re.search(r"(\d+) insertion", r)
            if m:
                commit.append((corrente, m.group(1)))
            corrente = None
    log = " ".join(x.strip() for x in out.stdout.splitlines() if x.strip()).replace("@@", "")
    print(f"  log VERO: {len(log)} caratteri, {len(commit)} commit con inserzioni")

    # criterio scritto PRIMA: inserzioni univoche in tutto il log, e subject corto
    conteggi = [c for _s, c in commit]
    buoni = [
        (s, c) for s, c in commit
        if conteggi.count(c) == 1 and len(re.findall(rf"\b{c}\b", log)) == 1 and len(s) < 60
    ]
    if len(buoni) < 2:
        print(f"NON RIUSCITO: servono due commit con inserzioni univoche, trovati {len(buoni)}")
        return 1
    # DUE difetti trovati dal controllo, non da me:
    #  1) il primo criterio prendeva i primi due «buoni» e stavano a 23247 e
    #     25361 caratteri, oltre ogni lunghezza misurata;
    #  2) misuravo la loro posizione con `log.find(conteggio)`, che trova la
    #     prima occorrenza della STRINGA — «86» compare dentro un hash a 1035.
    # Il criterio corretto guarda la posizione del SUBJECT, che e' univoco, e
    # tiene solo i commit che stanno davvero dentro la fonte piu' corta.
    #  3) e al terzo giro il controllo ha detto che nei primi 2000 caratteri di
    #     commit buoni non ce n'e' NESSUNO: fissare le lunghezze a priori era a
    #     sua volta una scelta mia. Le derivo dai dati: la piu' corta e' quella
    #     che contiene i due commit, le altre crescono da li'.
    dentro = [(s, c) for s, c in buoni if log.find(s[:40]) >= 0]
    if len(dentro) < 2:
        print(f"NON RIUSCITO: commit con inserzioni univoche trovati: {len(dentro)}")
        return 1
    dentro.sort(key=lambda sc: log.find(sc[0][:40]))
    (sog_a, ins_a), (sog_b, ins_b) = dentro[0], dentro[1]
    base = max(log.find(sog_a[:40]), log.find(sog_b[:40])) + 300
    LUNGHEZZE = [base, base * 2, base * 4, min(base * 8, len(log))]
    print(f"  lunghezze derivate dai dati: {LUNGHEZZE}")
    print(f"  scelti dal criterio, non da me:")
    print(f"    A: {ins_a:>6} inserzioni — {sog_a[:52]}")
    print(f"    B: {ins_b:>6} inserzioni — {sog_b[:52]}")

    if CIFRA_ASSENTE in log:
        print(f"CONTROLLO CADUTO: {CIFRA_ASSENTE} e' nel log")
        return 1

    CLAIM = {
        "VERO": f"Il commit «{sog_a}» ha aggiunto {ins_a} inserzioni.",
        "SCAMBIO": f"Il commit «{sog_a}» ha aggiunto {ins_b} inserzioni.",
        "ASSENTE": f"Il commit «{sog_a}» ha aggiunto {CIFRA_ASSENTE} inserzioni.",
    }

    # la fonte deve contenere il soggetto e, per lo scambio, anche il conteggio B
    fonti = {}
    for n in LUNGHEZZE:
        f = log[:n]
        if sog_a[:40] not in f or ins_a not in f or ins_b not in f:
            continue
        fonti[n] = f
    if not fonti:
        print("NON RIUSCITO: nessuna lunghezza contiene soggetto e i due conteggi")
        return 1
    print(f"  CONTROLLO retto: {len(fonti)} lunghezze contengono soggetto e i due conteggi\n")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "trepop.db"))

    print(f"  {'lunghezza':>10}   " + "".join(f"{k:>22}" for k in CLAIM))
    print("  " + "-" * 78)
    esiti = {k: [] for k in CLAIM}
    for n, fonte in fonti.items():
        celle = []
        for nome, prop in CLAIM.items():
            ric = mem.add(prop, topic=f"tp/{nome}/{n}", source=fonte, validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            esiti[nome].append((st != "quarantined", g))
            celle.append(f"{'ENTRA' if st != 'quarantined' else 'ferma'} {g:6.1f}")
        print(f"  {n:>10}   " + "".join(f"{c:>22}" for c in celle))

    print("\nCONTROLLO il claim VERO e' ammesso:")
    veri = [e for e, _g in esiti["VERO"]]
    if not all(veri):
        gs = [g for _e, g in esiti["VERO"]]
        print(f"   CADUTO — non ammesso ovunque, ground {min(gs):.1f}-{max(gs):.1f}")
        print("   ⇒ il gate rifiuta un fatto VERO su una fonte reale: e' un dato, non un guasto")
        print("     del banco, ma questa cella non puo' misurare la separazione.")
        return 1
    print("   retto\n")

    ent = {k: sum(1 for e, _g in v if e) for k, v in esiti.items()}
    tot = len(fonti)
    print("  -- QUANTE ENTRANO, per popolazione")
    for k in CLAIM:
        gs = [g for _e, g in esiti[k]]
        print(f"     {k:<9} {ent[k]} su {tot}   ground {min(gs):5.1f}-{max(gs):5.1f}")

    print()
    if ent["SCAMBIO"] > 0 and ent["ASSENTE"] == 0:
        print("  => LE DUE POPOLAZIONI SI SEPARANO ANCHE SU FONTE REALE: lo scambio entra")
        print("     dove la cifra inventata e' fermata, sullo stesso testo. La separazione")
        print("     non era un artefatto del contratto che avevo scritto io.")
    elif ent["SCAMBIO"] == 0 and ent["ASSENTE"] == 0:
        print("  => SU FONTE REALE il gate ferma ANCHE lo scambio. La separazione misurata")
        print("     sul mio contratto costruito non si ripete qui, e cinque celle del")
        print("     registro poggiano su quella fonte: vanno ristrette.")
    else:
        print(f"  => altro caso: SCAMBIO {ent['SCAMBIO']}/{tot}, ASSENTE {ent['ASSENTE']}/{tot}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
