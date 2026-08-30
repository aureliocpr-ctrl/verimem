"""Un fallimento di caricamento LOCALE spegne la delega a un daemon SANO.

LA RIGA. `local_grounding.try_local_score`, riga 693::

    if judge._scorer is None and not judge._load_failed and _delegate_only():
        punteggi = _gate_via_daemon(...)

`_load_failed` diventa vero quando il caricamento **in questo processo**
fallisce — in delegate-only avviene su un thread di sfondo
(`warm_local_judge_async`). Da quel momento il processo **smette di chiedere al
daemon**, che e' un ALTRO processo e puo' stare benissimo.

PERCHE' CONTA, e lo dice il prodotto stesso nel docstring di `_gate_via_daemon`:

    «Il reranker che non gira costa RILEVANZA; il giudice che non gira costa la
     GARANZIA — una scrittura ammessa senza essere giudicata e' precisamente
     cio' che questo prodotto esiste per non fare.»

E lo stesso docstring promette il degrado giusto: *«Se il daemon non c'e', non
sa giudicare o e' lento, si degrada ESATTAMENTE come prima»*. Nel caso
`_load_failed` **non si degrada come prima: si salta il daemon a priori**, senza
avere alcuna informazione sulla sua salute.

REGIME REALISTICO, e non e' teorico: modello sul disco ma non caricabile in
questo processo — RAM insufficiente, file corrotto, torch assente, una macchina
piccola. La memoria di casa ha un nome per quella macchina: *Atom senza AVX, il
cliente povero*. Li' il daemon condiviso e' esattamente cio' che dovrebbe
salvare la garanzia, ed e' cio' che viene spento.

LA PREDIZIONE, scritta prima di eseguire: con `_load_failed=True` imposto a
mano, `try_local_score` restituisce **None** mentre `_gate_via_daemon`, chiamata
sulla STESSA coppia nello STESSO processo, restituisce **un punteggio**.

CONDIZIONE DI FALSIFICAZIONE: se anche `_gate_via_daemon` restituisce None, la
strada non esiste e la clausola non toglie niente.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: con `_load_failed=False`,
`try_local_score` DEVE dare un punteggio. Se non lo desse, il daemon sarebbe
morto e il «None» della cella principale non direbbe niente sulla clausola —
misurerei un daemon spento.
═══════════════════════════════════════════════════════════════════════════════

⚠️ A/B NELLA STESSA ESECUZIONE, e per questo non serve toccare il sorgente: la
clausola si aggira chiamando a mano la funzione che essa impedisce di chiamare.
Un A/B nello stesso processo e' immune al movimento dell'albero, e lo dichiaro.

⚠️ COSA QUESTO BANCO NON DICE: **quanto spesso** `_load_failed` diventa vero sul
traffico reale. Non e' misurabile da qui, e senza quel numero il reperto e' un
MECCANISMO dimostrato, non una frequenza.

REGIME: `HIPPO_ENCODE_DELEGATE_ONLY=1`, daemon condiviso quale che sia il suo
stato (il banco lo dichiara leggendo `read_discovery()`), nessuna scrittura,
nessuno store — si chiama solo il giudice. Lo store di Aurelio non e' toccato.

🟡 ESITO DELLA PRIMA CORSA, 30/08 ore 20:43: **NESSUN VERDETTO**. Il
controllo ha fermato il banco perche' `read_discovery()` non annunciava alcuna
porta — il daemon era **giu'** (stessa sera in cui un altro esame misura che
undici delle ultime venti scritture vanno senza embedding). Senza un daemon
vivo non si distingue «la clausola spegne una strada» da «non c'era una strada
da spegnere», e il banco si e' rifiutato di concludere invece di leggere lo
zero come una conferma. ⇒ **Il reperto sulla clausola resta una LETTURA del
sorgente, non una misura**, e il banco e' pronto per la prima sera in cui il
daemon risponde.

    python docs/stato-reale/banchi/ws3-un-fallimento-locale-spegne-il-daemon-che-sta-bene.py
"""

from __future__ import annotations

import os

os.environ.setdefault("HIPPO_ENCODE_DELEGATE_ONLY", "1")

FONTE = "Il contratto fissa la penale in 120 euro al giorno."
CLAIM = "La penale e' di 500 euro al giorno."


def main() -> int:
    from verimem import encode_service as _svc
    from verimem.local_grounding import (
        _delegate_only,
        _gate_via_daemon,
        get_local_judge,
        judge_state,
        try_local_score,
    )

    info = _svc.read_discovery()
    porta = (info or {}).get("port")
    # ⚠️ IL REGIME COMPRENDE LA RIGA STESSA. Un banco che non sa se la cura e'
    # applicata scrive un verdetto che dice il contrario di cio' che e'
    # successo: PRIMA della cura il ramo verde significava «la clausola non
    # spegne niente», DOPO significa «la cura funziona». Preso alle 22:18 del
    # 30/08, rileggendo il proprio output subito dopo aver curato.
    import inspect  # noqa: PLC0415 — serve solo qui, per leggere il regime
    riga = next((r.strip() for r in inspect.getsource(try_local_score).splitlines()
                 if "_delegate_only()" in r and r.strip().startswith("if")),
                "(riga non trovata)")
    curata = "_load_failed" not in riga
    stato = "GIA' TOLTA (cura applicata)" if curata else "ANCORA PRESENTE"
    print(f"  REGIME  delegate_only={_delegate_only()}  ·  daemon porta={porta}"
          f"  ·  judge_state={judge_state()!r}")
    print(f"  RIGA    {riga}")
    print(f"  stato   la clausola `_load_failed` e' {stato}")
    if not porta:
        print("\n  DAEMON NON ANNUNCIATO (nessuna porta in read_discovery).")
        print("  Il banco misura la clausola CONTRO un daemon vivo: senza, non")
        print("  distinguerei «la clausola spegne» da «non c'era niente da")
        print("  spegnere». NESSUN VERDETTO.")
        return 1

    judge = get_local_judge()
    coppia = judge.coppia(FONTE, CLAIM)

    # [1] IL CONTROLLO — stato di partenza, `_load_failed` com'e'
    _prima = bool(getattr(judge, "_load_failed", False))
    judge._load_failed = False
    sano = try_local_score(FONTE, CLAIM)
    print(f"\n  [1] CONTROLLO  _load_failed=False  ->  try_local_score = {sano}")
    if not sano:
        print("      CONTROLLO CADUTO: con la clausola SODDISFATTA il giudizio")
        print("      non arriva comunque ⇒ il daemon non sta giudicando e il")
        print("      None della cella sotto non dice niente sulla clausola.")
        print("      NESSUN VERDETTO.")
        judge._load_failed = _prima
        return 1

    # [2] LA CELLA — lo stesso processo, la stessa coppia, `_load_failed=True`
    judge._load_failed = True
    spento = try_local_score(FONTE, CLAIM)
    diretto = _gate_via_daemon([coppia])
    judge._load_failed = _prima

    print(f"  [2] CELLA      _load_failed=True   ->  try_local_score = {spento}")
    print(f"      la STESSA strada, chiamata a mano  ->  _gate_via_daemon = "
          f"{diretto}")

    print("\n  ══ VERDETTO ══")
    if spento is None and diretto:
        print("     🔴 LA CLAUSOLA SPEGNE UNA STRADA CHE FUNZIONA: un fallimento")
        print("     di caricamento LOCALE fa smettere di chiedere a un daemon che")
        print("     nello stesso istante risponde. La garanzia si perde per una")
        print("     ragione che non riguarda chi la fornisce.")
        print("     ⇒ Candidato di cura, UNA riga: togliere `and not")
        print("     judge._load_failed` dalla condizione di riga 693. Il degrado")
        print("     e' gia' gestito — `_gate_via_daemon` torna None e il")
        print("     chiamante fa esattamente cio' che faceva prima.")
    elif spento is not None and curata:
        print("     🟢 LA CURA FUNZIONA: con la clausola TOLTA, un giudice")
        print("     locale fallito non impedisce piu' di chiedere al daemon e il")
        print("     punteggio arriva. ⇒ RED->GREEN falsificato dal banco stesso:")
        print("     la STESSA cella dava None finche' la clausola c'era.")
    elif spento is not None:
        print("     🟢 LA CLAUSOLA NON SPEGNE NIENTE: il punteggio arriva lo")
        print("     stesso e la clausola c'e' ANCORA ⇒ la mia lettura della riga")
        print("     era incompleta e lo dico.")
    else:
        print("     ⚪ NESSUNA STRADA: nemmeno la chiamata diretta ottiene un")
        print("     punteggio ⇒ la clausola non toglie nulla, in questo regime.")

    print("\n  ⚠️ COSA NON MISURA: quanto spesso `_load_failed` diventa vero sul")
    print("     traffico reale. Meccanismo dimostrato, frequenza NON misurata.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
