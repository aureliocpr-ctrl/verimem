r"""`verimem trust` e `verimem save` rispondono la stessa cosa sullo stesso claim?

`trust` e' il comando che un utente usa **prima** di scrivere, e il suo help promette:
«*This runs **the same governance gate** that guards every write*», con exit **0 se
trusted, 1 se flagged**.

⚠️ Ma le due porte parlano due vocabolari::

    trust   trusted / flagged        (exit 0 / 1)
    save    admitted / quarantined   (il fatto entra o no)

⇒ **«flagged» e «quarantined» non sono la stessa cosa**: stasera **tutti** i miei fatti
sono stati **ammessi** con avvisi attivi (`L4.2` su cinque salvataggi su cinque). Se
`trust` chiamasse «flagged» cio' che `save` **ammette**, un utente che pre-verifica
leggerebbe «non fidarti» e poi vedrebbe il fatto entrare — o il contrario, che e' peggio.

LA MISURA: gli stessi claim alle due porte, **stessa source**, stesso tier (`fast`,
che e' il default di entrambe)::

    claim                          cosa mi aspetto se le due porte concordano
    vero e sostenuto               trust 0 · save admitted
    scambio di grandezza           trust ? · save admitted (misurato in `00f8a18b`)
    numero inventato               trust 1 · save quarantined
    conteggio con «completati»     trust ? · save quarantined (misurato in `4fe3e4e5`)
    auto-affermazione senza prova  trust 1 · save quarantined

⇒ Le righe con `?` sono quelle che decidono: sono i casi in cui **so gia'** cosa fa il
save, e non so cosa dice `trust`.

🟡 ESITO — **le due porte concordano 5 su 5 (buona notizia), e dentro il pannello ci
sono due cose che valgono piu' del verdetto**::

    caso                          trust (exit)     save (gate)     concordano?
    vero e sostenuto              trusted (0)      admitted        ✔
    scambio di grandezza          trusted (0)      admitted        ✔   ← ma vedi ②
    numero inventato              flagged (1)      quarantined     ✔
    conteggio con «completati»    flagged (1)      quarantined     ✔
    auto-affermazione             flagged (1)      quarantined     ✔

✅ **① LA COERENZA REGGE**: chi pre-verifica con `trust` legge cio' che `save` fara'.
E' un risultato **verde** e lo scrivo con la stessa prontezza con cui scriverei un
allarme: le due porte non si contraddicono.

🔴 **② MA IL PANNELLO SI CONTRADDICE DA SOLO.** Sullo scambio di grandezza stampa::

    Anti-confab trust check   TRUSTED ✓
      flags (why it's not trusted):
        • [L1.13] Completion claim 'conclusi' lacks closing criteria …
        • [L4.2] il claim riusa un numero della fonte riferendolo a un'altra
          grandezza: 1167 qui e' «job», nella fonte «run»
        • [L1-domain-precision-observe] …
      the moat judged the source at 98.9
    EXIT=0

⇒ **Titolo `TRUSTED ✓`, e sotto un elenco intitolato «why it's NOT trusted» con tre
voci.** Il claim e' **falso** (1167 e' il conteggio dei *run*, non dei *job*), il
comando si chiama **trust**, e l'exit code — l'unica cosa che uno script legge — dice
**0, fidati**.

🔑 **③ E QUI `L4.2` DISTINGUE DAVVERO**, il che precisa un mio reperto invece di
ripeterlo. In `W5-13` avevo misurato che l'avviso era **identico** sul vero e sul falso
(«*(nessuna parola accanto)*», sei casi su sei). Qui dice «**1167 qui e' «job», nella
fonte «run»**» — **esatto, e utile**. ⇒ La differenza e' **la posizione del numero**:
li' seguiva il sostantivo («*i job conclusi sono 1167*»), qui lo **precede** («*1167 job
conclusi*»). E' il criterio posizionale che `vicinato_del_valore.py` dichiara — «*un
identificativo SEGUE il suo sostantivo, una quantita' lo PRECEDE*».

⇒ **CONSEGUENZA PRATICA, e si salda con la riga consegnata alle 21:23**: scrivere
«*Nella coda ci sono 42 job conclusi*» invece di «*I job conclusi sono 42*» non evita
solo il falso positivo di `L1.13` — **accende un presidio che nell'altra forma e'
cieco**. La stessa riformulazione paga due volte.

REGIME: **store TEMPORANEO** per entrambe le porte · tier `fast` (default di entrambe) ·
`--source` passata a `trust` come al gate · **un solo processo** (protocollo RAM
delle 20:47) · claim `ram/giudice` preso.
⚖️ PUNTI DEBOLI: cinque claim; `trust` lo interrogo dalla CLI e il save dalla porta
`run_validation_gate` — sono i due percorsi che l'utente incontra, ma **non e' lo stesso
codepath riga per riga**, e una differenza potrebbe stare li' invece che nel verdetto.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-trust-dice-la-stessa-cosa-del-save.py <dir-temp>
"""
import contextlib
import io
import os
import re
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

FONTE = ("La coda contiene in questo momento 1167 run completati, 895 run in "
         "attesa, 42 job conclusi e 812 test finiti.")

CASI = [
    ("vero e sostenuto", "Nella coda ci sono 42 job conclusi."),
    ("scambio di grandezza", "Nella coda ci sono 1167 job conclusi."),
    ("numero inventato", "Nella coda ci sono 7777 job conclusi."),
    ("conteggio con «completati»", "I run completati sono 1167."),
    ("auto-affermazione", "Ho completato la migrazione della coda."),
]


def chiedi_trust(claim, fonte):
    """`verimem trust` nello STESSO processo: il modello si carica una volta sola."""
    from verimem.cli import app
    buf = io.StringIO()
    argv, uscita = sys.argv, None
    sys.argv = ["verimem", "trust", claim, "--source", fonte]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                app()
                uscita = 0
            except SystemExit as e:
                uscita = e.code if isinstance(e.code, int) else 0
    finally:
        sys.argv = argv
    return uscita, buf.getvalue()


def main():
    print("  %-28s %-22s %-22s %s"
          % ("caso", "trust (exit)", "save (gate)", "concordano?"))
    print("  " + "-" * 88)
    divergenze = []
    for nome, claim in CASI:
        uscita, testo = chiedi_trust(claim, FONTE)
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=FONTE, grounding_llm=None,
                                ground_write=True)
        az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
        entra = az == "persist"
        fidato = uscita == 0
        # ⚠️ il confronto e' fra «l'utente legge di fidarsi» e «il fatto entra»:
        # e' la domanda che si pone chi usa `trust` prima di `save`.
        ok = fidato == entra
        if not ok:
            divergenze.append((nome, fidato, entra, " ".join(testo.split())[:150]))
        print("  %-28s %-22s %-22s %s"
              % (nome, "trusted (0)" if fidato else "flagged (%s)" % uscita,
                 "admitted" if entra else "quarantined", "✔" if ok else "🔴 DIVERGE"))

    print("\n=== SINTESI ===")
    if not divergenze:
        print("  🟢 le due porte concordano su tutti e %d i casi: chi pre-verifica con"
              % len(CASI))
        print("     `trust` legge cio' che `save` fara'.")
    else:
        print("  🔴 %d casi su %d DIVERGONO: chi pre-verifica legge una cosa e ne ottiene"
              % (len(divergenze), len(CASI)))
        print("     un'altra.")
        for nome, fidato, entra, testo in divergenze:
            verso = ("dice di FIDARSI e il fatto NON entra" if fidato
                     else "dice FLAGGED e il fatto ENTRA")
            print("    · %-26s %s" % (nome, verso))
            if testo:
                print("      trust: %s" % testo)


main()
