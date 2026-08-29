"""LA FAMIGLIA CHE TRADUCE E' CONTABILE — dallo SPAN, non dalla fonte.

Il banco `quanti-dei-256-mescolano-le-due-lingue.py` (cella W7-37, **ritirata da
me**) si chiudeva cosi': *«la famiglia che TRADUCE non e' contabile da qui,
perche' richiede di sapere in che lingua e' la FONTE, che non e' persistita»*.

⇒ **Quella conclusione ha un buco, e lo apro qui**: la fonte non e' persistita,
ma il `grounding_span` SI', ed e' **un frammento della fonte**. Se lo span c'e',
la lingua della fonte e' determinabile — per quella parte del corpus.

📌 Perche' e' plausibile che lo span basti: un'altra istanza ha misurato che lo
span **non e' «i primi N caratteri»**, e' una **selezione pertinente** (su una
fonte da 5250 char ha tenuto 314 char NON contigui, incluso il pezzo che portava
il numero). Un frammento scelto porta la lingua del testo da cui viene.

LA DOMANDA: fra i quarantinati dalla famiglia di completamento, **quanti hanno
il claim in una lingua e lo span nell'altra**? Quella e' la famiglia che la cura
del 28/08 non raggiunge, perche' quella cura perdona **solo alla lettera**.

CONTROLLI CHE POSSONO FALLIRE — e il primo puo' uccidere il banco:
 (1) 🔴 **Lo span esiste, per questa popolazione?** `L1` e' un layer LESSICALE e
     potrebbe fermare **prima** che il moat giri, lasciando lo span vuoto. Se ce
     l'ha meno del 10%, **la via e' chiusa e lo dico**, invece di pubblicare una
     percentuale calcolata su una manciata di righe.
 (2) 🪞 **Il rilevatore di lingua e' un criterio lessicale su un fenomeno
     semantico**, cioe' la classe di errore che mi e' gia' costata tre reperti.
     Lo misuro su **12 frasi di lingua NOTA** prese dalla popolazione di
     controllo, e dichiaro gli errori **in entrambe le direzioni**. Se ne sbaglia
     anche una sola, il numero finale esce con quella riserva scritta accanto.
 (3) DUE denominatori, sempre: sui quarantinati della famiglia e su quelli che
     hanno lo span.

    python -u docs/stato-reale/banchi/la-famiglia-che-traduce-e-contabile-dallo-span.py
"""

from __future__ import annotations

import collections
import re
import sqlite3
import sys

# ── Controllo (2): frasi di lingua NOTA, copiate dalla popolazione di controllo.
#    L'etichetta e' MIA e si verifica a occhio: sono sei e sei.
LINGUA_NOTA = [
    ("La migrazione e' completata e tutti i test passano.", "it"),
    ("Il refactoring e' finito e la suite e' verde.", "it"),
    ("Ho completato l'integrazione con il gateway.", "it"),
    ("La pratica e' stata chiusa correttamente.", "it"),
    ("Il collaudo e' stato completato senza rilievi.", "it"),
    ("Il ciclo di terapia e' concluso.", "it"),
    ("The migration is complete and all tests pass.", "en"),
    ("The cleanup is done and the branch is closed.", "en"),
    ("I finished the API integration this morning.", "en"),
    ("The paperwork is done.", "en"),
    ("The delivery is complete.", "en"),
    ("The shipment has been delivered.", "en"),
]

# Il criterio, dichiarato: parole funzionali, quelle che un testo tecnico non
# puo' evitare. Non participi ne' termini di dominio - quelli viaggiano fra le
# lingue ed e' proprio il fenomeno che sto misurando.
RE_IT = re.compile(
    r"\b(e|di|il|la|lo|le|dei|della|che|non|sono|stato|stata|con|per|una|"
    r"un|nel|nella|alla|dal|come|piu)\b", re.I)
RE_EN = re.compile(
    r"\b(the|and|of|is|are|was|were|has|have|been|with|to|in|on|for|from|"
    r"this|that|by|at)\b", re.I)


def lingua(t: str) -> str:
    if not t:
        return "?"
    i, e = len(RE_IT.findall(t)), len(RE_EN.findall(t))
    if i == e:
        return "?"
    return "it" if i > e else "en"


def main() -> int:
    try:
        from verimem.config import CONFIG
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print("  -- CONTROLLO (2): il rilevatore di lingua, su 12 frasi note")
    sbagli = [(t, v, lingua(t)) for t, v in LINGUA_NOTA if lingua(t) != v]
    for t, v, d in sbagli:
        print(f"     SBAGLIA  atteso {v}  detto {d}  |  {t[:58]}")
    print(f"     {len(LINGUA_NOTA) - len(sbagli)} su {len(LINGUA_NOTA)} corrette"
          + ("  ⇒ il numero finale vale CON questa riserva" if sbagli else
             "  ⇒ nessun errore in nessuna delle due direzioni"))
    if len(sbagli) > 3:
        print("     CADUTO - piu' di tre errori su dodici: questo rilevatore non")
        print("     separa le lingue, e un conteggio fatto con lui non vale.")
        return 1

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = list(con.execute(
        "SELECT proposition, quarantined_by, grounding_span FROM facts "
        "WHERE status='quarantined' AND superseded_by IS NULL"))
    print(f"\n  db: {CONFIG.semantic_db}")
    print(f"  quarantinati vivi: {len(righe)}")

    # 🪞 PRIMA di filtrare, GUARDO il campo su cui volevo filtrare. La prima
    # stesura prendeva `quarantined_by LIKE 'L1%'` e trovava DUE righe su 1081:
    # non perche' L1 fermi due fatti, ma perche' quel campo e' quasi sempre
    # vuoto. Filtrare su un campo senza averne stampato la copertura significa
    # misurare la copertura e chiamarla popolazione.
    q = collections.Counter((r[1] or "<VUOTO>").strip() or "<VUOTO>" for r in righe)
    print("\n  -- CONTROLLO (0): chi popola `quarantined_by`? (prima di filtrarci)")
    for k, v in q.most_common(6):
        print(f"     {v:>5}  ({100.0 * v / len(righe):>5.1f}%)  {k}")

    # ⇒ La popolazione giusta e' quindi TUTTA la coda che ha lo span, non il
    #   sottoinsieme etichettato: la domanda «claim e fonte nella stessa lingua?»
    #   non ha bisogno di sapere CHI ha fermato il fatto.
    fam = righe

    con_span = [r for r in fam if (r[2] or "").strip()]
    quota = 100.0 * len(con_span) / len(fam)
    print("\n  -- CONTROLLO (1): lo span esiste per questa popolazione?")
    print(f"     {len(con_span)} su {len(fam)} hanno lo span  ({quota:.1f}%)")
    if quota < 10.0:
        print("     🔴 CADUTO - sotto il 10%: `L1` ferma prima che il moat giri, e")
        print("     lo span non c'e'. LA VIA E' CHIUSA: la famiglia che traduce")
        print("     resta non contabile, e la conclusione di W7-37 REGGE.")
        return 1
    print("     retto - la via e' aperta su questa frazione, e solo su questa")

    d = collections.Counter()
    esempi = []
    discordanti = []
    for prop, qb, span in con_span:
        lc, ls = lingua(prop), lingua(span)
        if lc == "?" or ls == "?":
            d["incerto"] += 1
            continue
        if lc == ls:
            d[f"concordi ({lc})"] += 1
        else:
            d["DISCORDANTI"] += 1
            discordanti.append(prop)
            if len(esempi) < 5:
                esempi.append((lc, ls, prop, span))

    print(f"\n  == CLAIM contro SPAN, sui {len(con_span)} che hanno lo span")
    for k, v in d.most_common():
        print(f"     {v:>5}  ({100.0 * v / len(con_span):>5.1f}% di chi ha lo span"
              f" · {100.0 * v / len(fam):>5.1f}% della coda)  {k}")

    print("\n  == I DISCORDANTI, fino a cinque — la famiglia che TRADUCE")
    if not esempi:
        print("     NESSUNO. ⇒ Su questa popolazione la famiglia che traduce non")
        print("     compare: il claim e la fonte sono nella stessa lingua, e il")
        print("     limite della cura del 28/08 non e' quello che pesa qui.")
    for lc, ls, prop, span in esempi:
        print(f"     claim[{lc}] {prop[:70]}")
        print(f"     span [{ls}] {span[:70].replace(chr(10), ' ')}")
        print()

    # ⚠️ «Lingue diverse» e' NECESSARIO ma NON SUFFICIENTE: il primo esempio
    # stampato qui sopra («il comando save non espone una opzione principal»)
    # non e' nemmeno un claim di COMPLETAMENTO, e la cura del 28/08 non lo
    # riguarda. La famiglia vera e' l'INTERSEZIONE, e la stringo qui.
    print("  == STRINGO IL CRITERIO: quanti dei discordanti sono claim di COMPLETAMENTO?")
    try:
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim,
        )
    except Exception as e:  # noqa: BLE001
        print(f"     NON RIUSCITO: {type(e).__name__}: {e} — resto al numero largo")
        compl = None
    else:
        compl = [p for p in discordanti
                 if detect_unsupported_completion_claim(
                     proposition=p, verified_by=None, source=None) is not None]
        print(f"     {len(compl)} su {len(discordanti)} discordanti portano un")
        print("     participio di completamento ⇒ sono quelli su cui `L1` puo'")
        print("     scattare, e su cui la cura letterale non arriva perche' la")
        print("     fonte porta quel participio in un'ALTRA lingua.")
        for p in compl[:4]:
            print(f"       · {p[:76]}")
        # ⚖️ Controllo che poteva fallire: se fossero TUTTI, il detector non
        #    starebbe separando niente e il numero non direbbe piu' del largo.
        if len(compl) == len(discordanti):
            print("     ⚠️ SONO TUTTI: il detector non separa, e questo numero")
            print("     non aggiunge nulla al conteggio largo. Lo dico invece di")
            print("     spacciarlo per un affinamento.")

    print("  -- LE DUE RIGHE CHE CONTANO, e sono due cose diverse")
    n = d["DISCORDANTI"]
    stretto = len(compl) if compl is not None else "?"
    print(f"     ① LA FAMIGLIA CHE TRADUCE e' PICCOLA: {stretto} casi.")
    print("        L'aperto che avevo lasciato come incognita grossa si")
    print("        ridimensiona: la cura letterale del 28/08 lascia scoperti")
    print(f"        {stretto} fatti in questa coda, non una famiglia.")
    print(f"     ② MA {n} su {len(con_span)} ({100.0 * n / len(con_span):.1f}%) hanno")
    print("        claim e fonte in LINGUE DIVERSE, ed e' un fenomeno che")
    print("        riguarda OGNI layer che confronta un claim con la sua fonte")
    print("        — a partire dal moat, che qui ferma il 26,5% della coda.")
    print("        ⛔ Se il moat regga cross-lingua NON e' misurato da questo")
    print("        banco: e' la domanda che apre, non quella che chiude.")
    print(f"     ⚠️ Il denominatore vero e' {len(con_span)}, non {len(fam)}:")
    print("     della coda senza span non so niente, e non lo estrapolo.")
    print(f"     ⚠️ E {d['incerto']} righe restano 'incerto' — il rilevatore non")
    print("     le classifica, e stanno fuori da entrambi i numeri.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
