"""La terza via sul ramo proper è giusta come idea e NON si scrive oggi.

Questo banco esiste perché il 24/08 ho **annunciato** una cura sul canale e poi
l'ho ritirata. Senza righello, quel ritiro è un'opinione: chiunque riprovi
rifà la stessa strada e perde le stesse due ore.

═══ IL NODO ═══
`_entita_diverse` (anti_confab_gate.py) contiene::

    ea, eb = _proper(pa), _proper(pb)
    if ea and eb:
        return not (ea & eb)
    if ea or eb:          # <- il ramo conteso (59fb0862, mio)
        return True
    return False

@ws4 lo toglierebbe, @ws6 lo tiene. Misurato: su 57 coppie orientate come in
produzione il ramo decide da solo 7 volte (12,3%) — 5 ritiri sbagliati
evitati, 1 danno, 1 ambiguo. Positivo ma **non schiacciante**: né togliere né
lasciare com'è.

⇒ LA TERZA VIA: il ramo non guarda **DOVE** sta il nome proprio. In
`SIB_SAME` («The payments team migrated to Stripe» contro «The payments team
still runs on the legacy processor») il soggetto è IDENTICO e il proper sta
nel complemento: non rende diverse le entità, rende una frase più specifica.

═══ PERCHÉ NON SI SCRIVE — due tentativi, entrambi caduti ═══

① `same_subject(pa, pb)` — SBAGLIATO, e per un motivo che vale a chiunque la
   usi. Il suo docstring dice: «An empty/pronoun/uncertain subject is a
   WILDCARD -> True (**fail-open**: a conflict we cannot attribute must still
   reach the judge)». ⇒ Non significa «hanno lo stesso soggetto»: significa
   «vanno CONFRONTATI». Su «payments team» contro «checkout squad» risponde
   True. Usarla come il nome suggerisce è un difetto di giunzione.

② `subject_head(pa) != subject_head(pb)` — sblocca i due casi giusti ma
   **perde uno dei 5 salvati**, e la colonna delle teste dice perché: vuote
   da entrambi i lati. `"" != ""` è falso, quindi il ramo si spegne.

═══ E LA RAGIONE VERA, misurata su entrambe le popolazioni ═══

    subject_head VUOTA ......... 480 su 500   (96,0%)
       fra le ITALIANE ......... 97,5%
       fra le NON italiane ..... 94,0%        <- 3,5 punti: NON è la lingua

Avevo diagnosticato «non regge l'italiano»: falso. Il nostro corpus **non è
prosa** — sono referti, etichette, log (`[project/x — VISIBILITY] Repo a 0
star…`, `Lesson cycle #70: …`) — e `subject_of` è fatto per frasi con un
soggetto grammaticale.

⇒ 🔑 IL COROLLARIO CHE VALE PIÙ DELLA CURA MANCATA: `same_subject` è
fail-open E il soggetto non si estrae sul 96% del corpus ⇒ ritorna True quasi
sempre ⇒ **il pre-filtro L3 semantico è INERTE sul corpus reale**. Non fa
danno, non fa nulla. Spiega il «15 su 15 arrivano al giudice» misurato da
ws1: non è che il pre-filtro sia buono, è che non decide mai.

⇒ Per scrivere la terza via serve un estrattore di soggetto che regga i
referti. È un fronte, non una riga.
"""
from __future__ import annotations

import inspect
import os
import sqlite3

os.environ.setdefault("HIPPO_RERANK_PRELOAD", "0")

import verimem.anti_confab_gate as G                      # noqa: E402
from verimem.subject_extract import same_subject, subject_head   # noqa: E402

RAMO = "    if ea or eb:\n        return True\n"
CAND = "The payments team migrated to Stripe in 2025."

#: (nome, A, B, atteso per la variante RISTRETTA — None = solo osservare)
CASI = [
    ("SIB_SAME  deve sbloccarsi", CAND,
     "The payments team still runs on the legacy processor.", False),
    ("SIB_RENAME teste diverse", CAND,
     "The checkout squad reverted to the legacy processor.", None),
    ("SIB_FP    altro tema", CAND,
     "The design team runs a weekly critique on Fridays.", None),
    ("DANNO 1894/1805 deve sbloccarsi",
     "Il motivo autohook-snapshot daily collapse compare in 1463 fatti superseduti su 1894.",
     "Dei 1805 fatti superseduti nel corpus, 1463 hanno superseded_reason "
     "autohook-snapshot daily collapse e 202 hanno exact-text dedup.", False),
    ("SALVATO suite vs merge  deve RESTARE",
     "La suite di non-regressione sull'asse entita' da' 38 passed e 11 xfailed.",
     "MERGIATO SU MAIN IL 25/7 (commit di merge 0a609273, PR#2), su mandato "
     "esplicito di Aurelio.", True),
    ("SALVATO run-ci vs quarant. deve RESTARE",
     "Nelle ultime 6 ore sono nati 14 run di ci su main e nessuno ha prodotto "
     "un verdetto success o failure.",
     "Nelle ultime 24 ore i quarantinati sono 25 e la quota con quarantined_by "
     "uguale a gate e' 56 per cento.", True),
]


def _variante(sostituzione: str, extra: dict | None = None):
    """La funzione di PRODUZIONE con il ramo sostituito — mai riscritta a mano.

    Ricostruire `_entita_diverse` nel banco è la trappola che il 21/08 mi è
    costata una divergenza su 1515 coppie su 1933.
    """
    src = inspect.getsource(G._entita_diverse)
    if src.count(RAMO) != 1:
        raise SystemExit("IL BANCO SI RIFIUTA: il ramo non è isolabile")
    ns = dict(G.__dict__)
    ns.update(extra or {})
    exec(compile(src.replace(RAMO, sostituzione), "<variante>", "exec"), ns)
    return ns["_entita_diverse"]


def main() -> None:
    senza = _variante("")
    ristretto = _variante(
        "    if (ea or eb) and _head_(pa) != _head_(pb):\n        return True\n",
        {"_head_": subject_head})

    print("=== ① same_subject NON significa «stesso soggetto» ===")
    print("   same_subject(payments team…, checkout squad…) =",
          same_subject(CAND, CASI[1][2]))
    print("   (docstring: wildcard -> True, FAIL-OPEN = «vanno confrontati»)\n")

    print("=== ② A/B a TRE vie ===")
    print("%-40s %-5s %-5s %-9s %-13s %s"
          % ("caso", "orig", "senza", "RISTRETTO", "teste", "atteso"))
    passa = True
    for nome, a, b, atteso in CASI:
        r = ristretto(a, b)
        esito = ""
        if atteso is not None:
            ok = (r == atteso)
            passa = passa and ok
            esito = "OK" if ok else "<<< FALLITO"
        print("%-40s %-5s %-5s %-9s %-13s %s"
              % (nome, G._entita_diverse(a, b), senza(a, b), r,
                 "%s|%s" % (subject_head(a)[:5], subject_head(b)[:5]), esito))
    print("\nLA CURA PASSA LA FALSIFICAZIONE:", passa)

    print("\n=== ③ PERCHÉ: subject_head è vuota quasi ovunque ===")
    from verimem.config import CONFIG                      # noqa: PLC0415
    db = os.environ.get("VERIMEM_BANCO_DB") or str(CONFIG.semantic_db)
    c = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    ancora = c.execute("SELECT MAX(rowid) FROM facts").fetchone()[0]
    tutti = [r[0] for r in c.execute(
        "SELECT proposition FROM facts WHERE rowid <= ? AND superseded_by IS NULL "
        "AND length(proposition) BETWEEN 40 AND 300 ORDER BY rowid", (ancora,))]
    passo = max(1, len(tutti) // 500)
    campione = tutti[::passo][:500]
    IT = (" che ", " sono ", " della ", " nel ", " con ", " per ", " non ", " il ", " di ")
    vuote = vuote_it = tot_it = 0
    for p in campione:
        it = sum(1 for m in IT if m in " %s " % p.lower()) >= 2
        tot_it += it
        if not subject_head(p):
            vuote += 1
            vuote_it += it
    non_it = len(campione) - tot_it
    print("   ancora rowid <= %d   campione %d" % (ancora, len(campione)))
    print("   subject_head VUOTA ........ %d  (%.1f%%)"
          % (vuote, 100.0 * vuote / max(len(campione), 1)))
    print("   fra le ITALIANE ........... %.1f%%" % (100.0 * vuote_it / max(tot_it, 1)))
    print("   fra le NON italiane ....... %.1f%%   <- l'altra popolazione"
          % (100.0 * (vuote - vuote_it) / max(non_it, 1)))
    print("\n⇒ Non è la lingua: il corpus non è PROSA. Con `same_subject`")
    print("  fail-open, il pre-filtro L3 semantico è INERTE sul corpus reale.")


if __name__ == "__main__":
    main()
