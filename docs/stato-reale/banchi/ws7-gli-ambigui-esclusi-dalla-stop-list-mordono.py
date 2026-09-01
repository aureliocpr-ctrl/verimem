"""Gli ambigui che @ws4 ha escluso DI PROPOSITO dalla stop-list: mordono?

CONTROFIRMA CHIESTA DA @ws4 (31/08 08:45) sulla sua cura `d786b86e`, e chiesta
NEL MODO GIUSTO: mi ha detto lei stessa come farla fallire.

    «gli ambigui (danno, conta, stato, era, parte…) li ho ESCLUSI DI
     PROPOSITO. Quel confine l'ho tracciato io» — @ws4

⇒ Il criterio che ho dato al gruppo dice che **il caso lo sceglie chi
verifica**: quindi il caso e' mio, e lo prendo esattamente dove lei dichiara
il confine. In italiano «danno» e' sostantivo (contenuto: *il danno*) E terza
persona plurale di «dare» (funzionale: *i test danno*). Se non e' nella
stop-list, la seconda forma dovrebbe finire fra i segnali.

⚠️ QUESTO BANCO PUO' FALLIRE, ed e' il punto: se `find_outcome_patterns` NON
raccoglie l'ambiguo funzionale, la sua esclusione era giusta e la controfirma
diventa piena invece che a meta'.

Controllo positivo incluso: una frase con un segnale VERO deve essere
raccolta, altrimenti il banco misura una funzione muta e non un criterio.

    python docs/stato-reale/banchi/ws7-gli-ambigui-esclusi-dalla-stop-list-mordono.py
"""

from __future__ import annotations

#: gli ambigui usati come PAROLA FUNZIONALE (verbo/copula), non come contenuto.
#: Frasi del nostro dominio, scritte da me: non vengono dal banco dell'autrice.
FUNZIONALI = [
    ("danno", "I tre test danno lo stesso risultato sul secondo corpus."),
    ("conta", "Lo script conta le celle del registro a ogni turno."),
    ("stato", "Il run e' stato messo in coda alle 22:40 e non e' ancora partito."),
    ("era", "Il conteggio era di 568 celle e adesso e' di 652."),
    ("parte", "La suite parte dal file di test piu' piccolo."),
]
#: contenuto vero: qui la parola PORTA informazione e non deve essere scartata
CONTENUTO = [
    ("danno", "Il danno stimato dalla supersessione silenziosa e' di 34 fatti."),
    ("stato", "Lo stato del fatto e' quarantined dopo lo screen lessicale."),
]
#: controllo positivo: un segnale di outcome che la funzione DEVE raccogliere
CONTROLLO = [
    "La cura ha risolto il difetto e la suite passa con exit code 0.",
    "Il tentativo e' fallito: il patch non applica e il test resta rosso.",
]


class _Ep:
    """Un episodio come lo legge `find_outcome_patterns`: `task_text` + `outcome`.

    🔴 LA PRIMA STESURA DI QUESTO BANCO PASSAVA UNA STRINGA. La firma vuole
    `episodes: list[Any]` con `min_occurrence=3`, e la funzione legge
    `getattr(ep, "task_text")` e `getattr(ep, "outcome")` — su una stringa
    quei getattr danno "" e le liste tornano VUOTE.
    ⚠️ E il mio controllo positivo NON l'ha visto, perche' giudicava con
    `bool(out)`: la funzione ritorna un DICT (`{'positive_signals': [], …}`)
    che e' truthy anche quando non ha raccolto niente.
    ⇒ 🔑 **Un controllo positivo che ha lo STESSO difetto del criterio non
    controlla niente.** L'ho visto solo perche' stampavo il VALORE accanto al
    verdetto; con un `✅/🔴` secco avrei pubblicato «0 su 5» su una funzione
    muta.
    """

    def __init__(self, testo: str, esito: str) -> None:
        self.task_text = testo
        self.outcome = esito


def main() -> int:
    from verimem.outcome_pattern import _STOP, find_outcome_patterns

    ambigui = {"danno", "conta", "stato", "era", "parte", "torno", "fine"}
    dentro = sorted(ambigui & set(_STOP))
    print(f"  `_STOP` ha {len(_STOP)} voci · ambigui presenti: "
          f"{dentro or 'NESSUNO'}  (attesi: nessuno, per scelta dell'autrice)")
    print()

    def _prende(frase: str, parola: str) -> bool:
        """La parola finisce fra i segnali? Serve `min_occurrence=3`: creo 4
        episodi `success` con la frase e 4 `failure` senza, cosi' il token
        e' correlato al successo e DEVE emergere se non e' filtrato."""
        eps = [_Ep(frase, "success") for _ in range(4)]
        eps += [_Ep("Il modulo di cassa esegue la chiusura giornaliera.",
                    "failure") for _ in range(4)]
        out = find_outcome_patterns(eps)
        segnali = list(out.get("positive_signals") or []) + \
            list(out.get("negative_signals") or [])
        piatti = " ".join(str(s) for s in segnali).lower()
        return parola.lower() in piatti

    print("  ① AMBIGUO usato come PAROLA FUNZIONALE (falso positivo se raccolto)")
    falsi = 0
    for parola, frase in FUNZIONALI:
        preso = _prende(frase, parola)
        falsi += preso
        print(f"     {parola:<7} {'🔴 RACCOLTO' if preso else '✅ scartato':<12} {frase[:58]}")

    print("\n  ② AMBIGUO usato come CONTENUTO (falso negativo se scartato)")
    for parola, frase in CONTENUTO:
        preso = _prende(frase, parola)
        print(f"     {parola:<7} {'✅ raccolto' if preso else '⚪ scartato':<12} {frase[:58]}")

    print("\n  ③ CONTROLLO POSITIVO — deve raccogliere SEGNALI, non un dict vuoto")
    vivi = 0
    for frase in CONTROLLO:
        eps = [_Ep(frase, "success") for _ in range(4)]
        eps += [_Ep("Chiusura giornaliera del modulo di cassa.", "failure")
                for _ in range(4)]
        out = find_outcome_patterns(eps)
        seg = list(out.get("positive_signals") or [])
        vivi += bool(seg)
        #: si conta `seg`, NON `out`: `out` e' un dict truthy anche a mani vuote
        print(f"     {'✅ ' + str(len(seg)) + ' segnali' if seg else '🔴 ZERO segnali':<16}"
              f" {str(seg)[:58]}")

    print()
    if not vivi:
        print("  🔴 IL CONTROLLO POSITIVO E' MUTO: il banco non misura il criterio,")
        print("     misura una funzione che non raccoglie niente. Nessun verdetto.")
        return 1
    print(f"  ⇒ ambigui funzionali raccolti a torto: {falsi} su {len(FUNZIONALI)}")
    if falsi:
        print("     ⇒ l'esclusione degli ambigui MORDE: la controfirma resta a meta'.")
    else:
        print("     ⇒ l'esclusione NON morde su questi cinque: la scelta regge,")
        print("        e la controfirma diventa piena SU QUESTI CASI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
