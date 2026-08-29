"""LA BAND ESCALATION CONSEGNA? — l'aperto che ho dichiarato TRE volte e mai eseguito.

`W7-47` ha misurato **per lettura** che l'escalation della banda ha due fragilita'
in serie: il **modello non e' fissato** (`claude -p` senza `--model`) e il
**parser accetta due sole forme** (`SCORE: N` o un numero iniziale). E si
chiudeva con una riga che ho ripetuto in tre pubblicazioni diverse:

    «NON ho eseguito il giudice, quindi NON so se i 79 in banda siano fermi per
     questo. E' plausibile e non misurato.»

⇒ **Qui lo eseguo.** E' l'unico modo di trasformare quella plausibilita' in un
fatto — o di falsificarla.

⚠️ **COSTO E REGIME, dichiarati prima**: `_timeout_s()` vale **90 secondi per
caso**, quindi il banco puo' fermarsi a lungo senza stampare. Chiamo il giudice
**due volte al massimo**, un processo, niente in parallelo.

LE TRE DOMANDE, in ordine di quanto costano:
 (1) **Il caso in banda si costruisce?** Uso la ricetta gia' misurata in `W7-42`:
     la stessa fonte con **due caratteri di coda** da' `78.6`, cioe' DENTRO la
     banda [40, 80]. Se oggi non ci cade piu', il banco muore qui e lo dico.
 (2) **L'escalation viene CHIAMATA?** Il gate la invoca solo se
     `grounding_llm is None` (`anti_confab_gate.py:2691`). Se nel percorso vero
     non e' None, allora i 79 in banda **non passano nemmeno di li'**, e la mia
     ipotesi cade per una ragione che non avevo considerato.
 (3) **CONSEGNA un numero?** Chiamata diretta, con il tempo cronometrato:
     · un `float` in pochi secondi -> la mia ipotesi e' FALSIFICATA, il giudice
       funziona e i 79 sono fermi per altro;
     · `None` dopo ~90 s -> timeout, ed e' la fragilita' ① (modello non fissato,
       nessuna risposta in tempo);
     · `None` subito -> il giudice ha risposto ma il **parser** non ha capito,
       ed e' la fragilita' ②. **Le tre uscite si distinguono dal TEMPO**, ed e'
       per questo che lo misuro invece di guardare solo il valore.

    python -u docs/stato-reale/banchi/la-band-escalation-consegna-o-no.py
"""

from __future__ import annotations

import sys
import time

# Ricetta di W7-42: NUDA + 2 caratteri di CODA -> 78.6, dentro la banda.
NUDA = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
CODA = " Le parti dichiarano di aver letto e compreso ogni clausola del"
CLAIM = "La cauzione definitiva e' pari a 148000 euro."


def main() -> int:
    try:
        from verimem import band_escalation as be
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.grounding_gate import (
            _ce_band_tau_hi,
            resolve_write_threshold_for,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    CUT, TAU = resolve_write_threshold_for("local"), _ce_band_tau_hi()
    print(f"  banda letta dal gate: [{CUT}, {TAU}]")
    print(f"  modo escalation: {be._mode()!r}   timeout: {be._timeout_s()}s")
    print(f"  via locale (ollama): {be._local_ollama_available()}")
    print(f"  cli risolta: {be._resolve_cli()}")

    fonte = NUDA + CODA[:2]
    print("\n  -- DOMANDA (1): il caso cade IN BANDA?")
    g = run_validation_gate(proposition=CLAIM, verified_by=[], topic=None,
                            agent=None, source=fonte, ground_write=True)
    score = getattr(g, "grounding_score", None)
    azione = getattr(g, "action", None)
    print(f"     score {score}   azione {azione}")
    if score is None or not (CUT <= float(score) < TAU):
        print("     CADUTO - il caso non e' in banda oggi: la ricetta di W7-42")
        print("     non si riproduce, e senza un caso in banda non ho oggetto.")
        return 1
    print(f"     retto - {float(score):.1f} e' dentro [{CUT}, {TAU}]")

    print("\n  -- DOMANDA (3): l'escalation CONSEGNA? (chiamata diretta, cronometrata)")
    print("     ⏳ fino a 90 secondi senza stampare nulla e' un esito, non un blocco")
    t0 = time.monotonic()
    try:
        esito = be.escalate_band(fonte, CLAIM)
        errore = None
    except Exception as e:  # noqa: BLE001
        esito, errore = None, f"{type(e).__name__}: {e}"
    dt = time.monotonic() - t0
    print(f"     tornato dopo {dt:.1f}s -> {esito!r}"
          + (f"   ECCEZIONE {errore}" if errore else ""))

    print("\n  == LA LETTURA, e la distinguo con il TEMPO come dichiarato prima")
    if esito is not None:
        print(f"     🟢 CONSEGNA: {esito!r} in {dt:.1f}s.")
        print("     ⇒ LA MIA IPOTESI DI W7-47 E' FALSIFICATA: il giudice risponde")
        print("     e viene capito. I 79 fatti in banda sono fermi per ALTRO, e")
        print("     quel «altro» non lo so.")
    elif dt >= 0.8 * be._timeout_s():
        print(f"     🔴 None dopo {dt:.1f}s, cioe' al TIMEOUT ({be._timeout_s()}s).")
        print("     ⇒ E' la fragilita' ① di W7-47: la via che resta su questa")
        print("     macchina non consegna in tempo, e il fatto resta trattenuto.")
    else:
        print(f"     🔴 None dopo appena {dt:.1f}s: NON e' un timeout.")
        print("     ⇒ Il giudice ha risposto e il PARSER non ha capito, oppure la")
        print("     via non e' nemmeno partita — e' la fragilita' ②, o una terza")
        print("     causa che questo banco non separa. **Non la invento.**")

    # ── DOMANDA (4): `_score_via_claude` ha DUE uscite a None oltre al timeout —
    #    `r.returncode != 0` e `_parse_score(stdout) is None`. Il banco sopra non
    #    le separa; qui le separo replicando **l'invocazione esatta del
    #    prodotto**, presa da `band_escalation.py:152-158`.
    #    ⚠️ Questo significa lanciare `claude -p` **senza `--model`**, che e'
    #    proprio la fragilita' ①: lo faccio di proposito, perche' fissare il
    #    modello misurerebbe una cosa diversa da quella che il prodotto fa.
    if esito is None:
        import subprocess

        from verimem.grounding_gate import _FACT_SYSTEM
        print("\n  -- DOMANDA (4): e' il RETURNCODE o il PARSER?")
        cli = be._resolve_cli()
        user = f"Source: {fonte}\n\nCandidate fact: {CLAIM}\n\nScore:"
        t1 = time.monotonic()
        try:
            r = subprocess.run(
                [cli, "-p", "--output-format", "text",
                 "--append-system-prompt", _FACT_SYSTEM],
                input=user, capture_output=True, text=True,
                timeout=be._timeout_s(), encoding="utf-8", errors="replace")
            dt1 = time.monotonic() - t1
            print(f"     returncode {r.returncode}   dopo {dt1:.1f}s")
            print(f"     stdout: {r.stdout[:300]!r}")
            print(f"     stderr: {r.stderr[:300]!r}")
            letto = be._parse_score(r.stdout)
            print(f"     _parse_score(stdout) -> {letto!r}")
            if r.returncode != 0:
                print("     🔴 E' IL RETURNCODE: la CLI esce con errore, e il")
                print("     prodotto degrada a None senza guardare l'uscita.")
                print("     ⇒ NON e' il parser: e' che la via non porta a casa")
                print("     nemmeno una risposta da leggere.")
            elif letto is None:
                print("     🔴 E' IL PARSER: la CLI risponde (returncode 0) e il")
                print("     punteggio NON viene letto. La forma della risposta e'")
                print("     stampata qui sopra ed e' l'evidenza.")
            else:
                print("     🪞 CONTRADDIZIONE: qui il punteggio SI legge, mentre")
                print("     `escalate_band` ha dato None. Le due chiamate non sono")
                print("     equivalenti e la mia replica NON e' fedele: lo dico")
                print("     invece di dedurne qualcosa.")
        except Exception as e:  # noqa: BLE001
            print(f"     ECCEZIONE dopo {time.monotonic() - t1:.1f}s: "
                  f"{type(e).__name__}: {e}")
            print("     ⇒ La via non parte affatto, ed e' la terza causa.")

    print("\n  ⚠️ COSA NON DICE, comunque vada: e' UN caso, su UNA macchina, con")
    print("  la CLI di questa installazione. Non e' un tasso, e i 79 in banda del")
    print("  corpus restano una popolazione che questo banco NON ha toccato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
