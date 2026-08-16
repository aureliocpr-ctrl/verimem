"""Due filtri pensati per il CLAIM venivano applicati anche alla FONTE.

`extract_quantities` fa, a `quantity_match.py:1020`::

    claim = _senza_identificatori(claim_span(text))

Le due funzioni sono giuste **su un claim**: `claim_span` toglie la citazione
finale («… Source: `file.json`»), `_senza_identificatori` non conta i codici
prodotto (`AB-123`) come quantità. **Sulla FONTE nessuna delle due lo è**: lì
ciò che segue «Source:» è contenuto, e `file-354-` non è un codice ma il formato
di `git grep -C`.

⇒ Il risultato è che un numero **presente nella fonte** non viene visto, il
claim che lo cita sembra inventarselo, e `L4.1` quarantina un fatto vero. Due
casi misurati il 16/08 su due macchine diverse, stessa firma (`L4.1` +
`withheld_despite_judge=True` + grounding ~99,98)::

    caso A — la fonte viene TRONCATA a «Source:»
      righe 8+9 della fonte, da sole   ->  [7.0, 13.0]
      righe 7+8 (la 7 finisce con «Source:»)  ->  []

    caso B — l'identificatore viene CANCELLATO
      'verimem/cli.py:100:  …'  ->  [100.0]
      'verimem/cli.py-354-  …'  ->  []   (diventa 'verimem/cli.      -  …')

⚠️ La cura NON tocca `extract_quantities`: sei moduli del gate la leggono e su
un claim i due filtri servono davvero. Vive dove si sa quale testo è la fonte —
`valori_non_nella_fonte` — ed è nel verso sicuro: **aggiungere numeri alla fonte
TOGLIE veti, non ne mette**. Un errore qui costa un veto in meno, mai un fatto
falso ammesso.
"""
from __future__ import annotations

from verimem.valore_non_nella_fonte import valori_non_nella_fonte

# --------------------------------------------------------------- caso A -----
FONTE_CON_MARCATORE = """### 5.2 VeriBench head-to-head

Setup: 300 probes per corpus (200 answerable + 100 unanswerable). Source:
`benchmark/results/veribench_real_halueval-qa_2026-07-13.json`.
"""
CLAIM_A = ("La sezione dichiara come fonte il file "
           "benchmark/results/veribench_real_halueval-qa_2026-07-13.json.")

# --------------------------------------------------------------- caso B -----
FONTE_GIT_GREP = """verimem/cli.py:100:    console.print(intestazione)
verimem/cli.py-354-    console.print(riepilogo)
"""
CLAIM_B = "Il riepilogo viene stampato alla riga 354 di verimem/cli.py."


def _assenti(claim: str, fonte: str) -> list[float]:
    return [a.valore for a in valori_non_nella_fonte(claim, fonte)]


def test_un_numero_dopo_il_marcatore_di_provenienza_e_nella_fonte():
    """Caso A: la fonte dice «Source:» e poi nomina il file. Quel nome è
    contenuto, non una citazione da ignorare."""
    assenti = _assenti(CLAIM_A, FONTE_CON_MARCATORE)
    assert 7.0 not in assenti and 13.0 not in assenti, (
        f"i numeri della data sono nella fonte, dopo «Source:», e risultano "
        f"assenti: {assenti}. Il claim che li cita viene quarantinato contro "
        f"un giudice al 99,98")


def test_un_numero_in_un_riferimento_col_trattino_e_nella_fonte():
    """Caso B: `cli.py-354-` è il formato di `git grep -C`, non un codice
    prodotto. Il 354 c'è, e il claim che lo cita non lo sta inventando."""
    assenti = _assenti(CLAIM_B, FONTE_GIT_GREP)
    assert 354.0 not in assenti, (
        f"354 e' nella fonte dentro «cli.py-354-» e risulta assente: {assenti}")


# ----------------------------------------------------- POPOLAZIONI OPPOSTE --
def test_un_numero_che_la_fonte_NON_contiene_resta_assente():
    """⚠️⚠️ IL PRESIDIO CHE DECIDE SE LA CURA VALE. Leggere la fonte per intero
    non deve diventare un lasciapassare: un valore che lì non c'è deve restare
    un valore assente, o il layer smette di fare il suo mestiere."""
    assenti = _assenti("Il riepilogo viene stampato alla riga 999.",
                       FONTE_GIT_GREP)
    assert 999.0 in assenti, (
        f"999 non compare da nessuna parte nella fonte e deve restare assente: "
        f"{assenti}")


def test_il_claim_resta_potato_della_sua_citazione():
    """⚠️ L'altra popolazione: la cura riguarda il lato FONTE. Sul CLAIM i due
    filtri devono continuare a valere — se un claim porta in coda una citazione,
    i numeri della citazione non sono ciò che il claim AFFERMA."""
    claim_con_citazione = (
        "Il benchmark ha usato 42 sonde. Source: "
        "`benchmark/results/veribench_2026-07-13.json`.")
    assenti = _assenti(claim_con_citazione, "Il benchmark ha usato 42 sonde.")
    assert 7.0 not in assenti and 13.0 not in assenti, (
        f"i numeri della CITAZIONE del claim sono stati trattati come "
        f"affermazioni: {assenti}. Su un claim `claim_span` deve continuare "
        f"a potare la coda")
