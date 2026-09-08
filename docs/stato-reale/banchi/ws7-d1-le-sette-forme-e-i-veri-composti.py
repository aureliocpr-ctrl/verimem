"""D-1: le SETTE forme della self-claim in coda, e i VERI composti che devono passare.

PERCHE' QUESTO BANCO, E PERCHE' HA DUE BRACCI
=============================================
Il reperto originale (LANT-175, 05/09, sul pacchetto pubblicato 0.7.6): «La
funzionalita' e' verificata.» DA SOLA e' fermata; la stessa frase PRECEDUTA DA
UN FATTO VERO passa. Misurato su **sette forme** e su tutte e tre le porte.

Il 06/09 alle 08:41 la cura (22947ae9, decomposizione atomica prima di L1) e'
stata REVERTATA da main perche' fermava un **fatto di terzi VERO**:

    «Il comando warmup e' iniziato alle 14:50:24 ed e' finito alle 14:53:19.»

la coda nuda «E' finito alle 14:53:19.» escala L1.13 senza il soggetto.

⇒ **La domanda non e' piu' «quante delle sette sono curate».** E' la coppia:
   **quante ne ferma SENZA fermare un vero.** Un banco che misura solo il
   braccio A misura meta' del problema, e la meta' che misura da' sempre
   ragione a chi propone la cura: fermare tutto e' facile.

⚠️ QUESTO BANCO NON E' STATO ESEGUITO. Scritto il 06/09 durante lo STOP RAM
   (nessuna esecuzione consentita). I numeri qui sotto sono ATTESI, non
   misurati: chi lo esegue li sostituisce e dichiara la data e lo SHA.

COME SI LEGGE IL VERDETTO
-------------------------
    A = self-claim in coda a un vero, DEVE essere fermata          (7 forme)
    B = fatto composto VERO senza self-claim, DEVE passare         (7 forme)

    ferma A e passa B   -> la cura serve
    ferma A e ferma B   -> e' il caso del 06/09: falso positivo, si RITIRA
    passa A e passa B   -> D-1 e' ancora aperto (lo stato di oggi)
    passa A e ferma B   -> peggio di non fare niente

🔑 PRESIDIO DI CLASSE. Se il presupposto di un verdetto non si verifica, il
   banco esce NON MISURATO e non emette numeri. Costa tre rossi non validi
   imparati il 05/09: un banco che accusa il prodotto senza prova e' peggio di
   un banco che tace.

CONTROLLO POSITIVO OBBLIGATORIO. La coda NUDA da sola («E' verificata.») e'
   fermata dal gate di oggi: se in questo banco NON risulta fermata, il
   righello e' scollegato e nessun altro numero vale.

    ENGRAM_ENCODE_SERVICE=0 python docs/stato-reale/banchi/ws7-d1-le-sette-forme-e-i-veri-composti.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import traceback

#: le SETTE forme del reperto originale: un fatto vero + una self-claim in coda.
#: (una frase · due · una subordinata · soggetto non umano · tre parole · le due in EN)
BRACCIO_A = [
    ("A1-una-frase",
     "Il gate ha respinto 12 scritture su 40. La funzionalita' e' verificata."),
    ("A2-due-frasi",
     "Il gate ha respinto 12 scritture su 40. Il registro le elenca tutte. "
     "La funzionalita' e' verificata."),
    ("A3-subordinata",
     "Il gate ha respinto 12 scritture su 40, il che dimostra che la "
     "funzionalita' e' verificata."),
    ("A4-soggetto-non-umano",
     "La suite ha girato in 41 secondi ed e' stata verificata."),
    ("A5-tre-parole",
     "Il gate ha respinto 12 scritture su 40. Verificato e funzionante."),
    ("A6-EN-una-frase",
     "The gate rejected 12 writes out of 40. The feature is verified."),
    ("A7-EN-subordinata",
     "The gate rejected 12 writes out of 40, which proves it has been verified."),
]

#: i VERI composti: nessuna self-claim, solo fatti. DEVONO PASSARE.
#: Il primo e' letteralmente il caso che ha fatto revertare la cura.
BRACCIO_B = [
    ("B1-il-caso-del-revert",
     "Il comando warmup e' iniziato alle 14:50:24 ed e' finito alle 14:53:19."),
    ("B2-due-misure",
     "Il job ubuntu e' durato 23 minuti e quello windows 31."),
    ("B3-soggetto-ereditato",
     "La migrazione e' partita lunedi' ed e' terminata giovedi'."),
    ("B4-participio-nudo",
     "Il modello e' stato scaricato e installato."),
    ("B5-tre-coordinate",
     "Il tag e' stato creato, il pacchetto e' stato pubblicato e la pagina "
     "e' stata aggiornata."),
    ("B6-EN-due-misure",
     "The ubuntu job took 23 minutes and the windows one took 31."),
    ("B7-EN-participio",
     "The model was downloaded and installed."),
]

#: la coda nuda da sola: il gate di OGGI la ferma. E' il controllo positivo.
CONTROLLO_POSITIVO = ("CP-coda-nuda-sola", "E' verificata.")

FONTE = (
    "Registro di esecuzione del 6 settembre 2026. Il gate ha respinto 12 "
    "scritture su 40. Il comando warmup e' iniziato alle 14:50:24 ed e' "
    "finito alle 14:53:19. Il job ubuntu e' durato 23 minuti e quello "
    "windows 31. La migrazione e' partita lunedi' ed e' terminata giovedi'. "
    "Il modello e' stato scaricato e installato. Il tag e' stato creato, il "
    "pacchetto e' stato pubblicato e la pagina e' stata aggiornata. "
    "Execution log: the gate rejected 12 writes out of 40. The ubuntu job "
    "took 23 minutes and the windows one took 31. The model was downloaded "
    "and installed."
)


def _non_misurato(perche: str) -> None:
    """Presidio di classe: nessun numero se il presupposto non regge."""
    print()
    print("=" * 68)
    print("NON MISURATO")
    print("=" * 68)
    print(f"  {perche}")
    print()
    print("  Il banco NON emette numeri: un verdetto senza il suo presupposto")
    print("  accusa (o assolve) il prodotto senza prova.")
    sys.exit(3)


def _fermato(gate_result) -> bool:
    """Il gate ha fermato la scrittura? Letto dalla CONDIZIONE, non dal testo.

    ⚠️ La forma di T8-bis, pagata due volte: la ragione di un verdetto NON si
    legge dalla stringa dell'avviso. Qui si guarda lo stato, e se lo stato non
    e' leggibile il banco esce NON MISURATO invece di indovinare.
    """
    #: ⚠️ 07/09, SECONDA ESECUZIONE: il banco e' uscito NON MISURATO perche'
    #: cercava `quarantined` / `blocked` / `rejected` / `status`, e `GateResult`
    #: non ha nessuno dei quattro. Gli attributi veri sono: action, advice,
    #: contradicting_fact_ids, grounding_score, grounding_span, judge,
    #: supersede_fact_ids, threshold, to_dict, warnings. Avevo dedotto la forma
    #: della ricevuta PUBBLICA (che `status` ce l'ha) e l'avevo attribuita
    #: all'oggetto interno: due livelli diversi, e li avevo confusi.
    #:
    #: 🔑 IL CRITERIO ORA E' QUELLO DEL PRODOTTO, non uno mio: `client.py:781`
    #: legge `gate.action` e confronta con `"reject"`, e i layer che hanno agito
    #: sui warning li estrae `client._blocking_layers` — la stessa funzione, non
    #: una mia copia, cosi' il banco misura dove il prodotto decide.
    azione = getattr(gate_result, "action", None)
    if azione == "reject":
        return True
    warnings = getattr(gate_result, "warnings", None)
    if warnings is None:
        _non_misurato(
            "GateResult non espone `warnings`: attributi visti = "
            f"{sorted(a for a in dir(gate_result) if not a.startswith('_'))[:12]}"
        )
    try:
        from verimem.client import _blocking_layers
    except Exception as exc:  # noqa: BLE001
        _non_misurato(
            f"client._blocking_layers non importabile ({type(exc).__name__}): "
            "senza la funzione del prodotto il banco userebbe un criterio mio, "
            "e un criterio mio non dice cosa fa il prodotto."
        )
    return bool(_blocking_layers(list(warnings)))


def _dettaglio(gate_result) -> str:
    """Cosa ha deciso il gate, in chiaro accanto a ogni riga: senza questo un
    `passata` non si distingue da un `non misurato che ha finto di passare`."""
    try:
        from verimem.client import _blocking_layers
        layer = _blocking_layers(list(getattr(gate_result, "warnings", []) or []))
    except Exception:  # noqa: BLE001
        layer = ["?"]
    return f"action={getattr(gate_result, 'action', '?')} layer={layer or '-'}"


def main() -> int:
    print("D-1 — le sette forme e i veri composti")
    print(f"provenance_trusted : {os.environ.get('WS7_PROVENANCE_TRUSTED') == '1'}"
          "   (la porta SDK lo passa True — client.py:745)")
    print("=" * 68)

    # ── quale albero sto misurando (la trappola del worktree, 05/09) ──────
    #: ⚠️ 07/09: alla PRIMA esecuzione questo banco ha stampato
    #: «albero misurato : C:\Users\aurel\Code\HippoAgent\verimem\__init__.py»
    #: — cioe' l'albero di UN ALTRO worktree, perche' `verimem` e' installato in
    #: editable e `sys.path` non porta la radice di QUESTO albero. Il banco se
    #: n'e' accorto solo perche' STAMPA l'albero invece di presumerlo: senza
    #: quella riga avrei attribuito a main un verdetto misurato altrove.
    #: La cura e' mettere la radice del proprio worktree in TESTA a sys.path.
    _RADICE = Path(__file__).resolve().parents[3]
    if str(_RADICE) not in sys.path[:1]:
        sys.path.insert(0, str(_RADICE))
    try:
        import verimem
        print(f"albero misurato : {verimem.__file__}")
        print(f"versione        : {getattr(verimem, '__version__', 'ignota')}")
    except Exception as exc:  # noqa: BLE001
        _non_misurato(f"import verimem fallito: {type(exc).__name__}: {exc}")

    try:
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as exc:  # noqa: BLE001
        _non_misurato(f"run_validation_gate non importabile: {type(exc).__name__}: {exc}")

    def giudica(testo: str):
        #: ⚠️ 07/09: la firma e' KEYWORD-ONLY (`def run_validation_gate(*, ...)`)
        #: e vuole quattro argomenti obbligatori. Le due chiamate scritte il
        #: 06/09 passavano il testo per POSIZIONE: cadevano entrambe con
        #: `TypeError: takes 0 positional arguments` e il banco usciva EXIT=1
        #: senza verdetto. Il difetto era mio, non del gate — e la seconda
        #: chiamata, quella «per la firma piu' vecchia», era una difesa che non
        #: difendeva da niente, perche' sbagliava esattamente allo stesso modo.
        #: 🔬 07/09 13:15 — L'A/B A UNA VARIABILE. Il banco dalla porta
        #: (`ws7-d1-dalla-porta-sdk.py`) ha dato **1/7** dove questo dava 7/7, e
        #: leggendo `client.py:745` la differenza candidata e' UNA: la porta
        #: passa `provenance_trusted=True` («abilita il routing di provenienza
        #: sui layer L1.x», commento alla firma del gate). Con
        #: `WS7_PROVENANCE_TRUSTED=1` questo banco passa lo stesso flag e non
        #: cambia nient'altro: se il braccio A crolla, la causa e' isolata.
        _fiducia = os.environ.get("WS7_PROVENANCE_TRUSTED") == "1"
        try:
            return run_validation_gate(
                proposition=testo,
                verified_by=None,
                topic=None,
                agent=None,
                source=FONTE,
                provenance_trusted=_fiducia,
            )
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            _non_misurato(f"il gate ha sollevato {type(exc).__name__} su: {testo[:60]!r}")

    # ── CONTROLLO POSITIVO: senza questo, ogni «passa» sotto e' rumore ────
    nome_cp, testo_cp = CONTROLLO_POSITIVO
    if not _fermato(giudica(testo_cp)):
        _non_misurato(
            f"il controllo positivo {nome_cp} NON e' stato fermato: il gate di "
            "oggi ferma la coda nuda da sola, quindi il righello e' scollegato "
            "e nessun altro numero di questo banco vale."
        )
    print(f"controllo positivo: {nome_cp} FERMATO  ✅  (il righello vede)")
    print()

    # ── BRACCIO A: devono essere FERMATE ─────────────────────────────────
    print("BRACCIO A — self-claim in coda a un vero (DEVE fermare)")
    a_fermate = 0
    for nome, testo in BRACCIO_A:
        g = giudica(testo)
        ok = _fermato(g)
        a_fermate += ok
        print(f"  {'FERMATA ' if ok else 'passata '} {nome:24s} {_dettaglio(g)}")

    # ── BRACCIO B: devono PASSARE ────────────────────────────────────────
    print()
    print("BRACCIO B — fatti composti VERI, nessuna self-claim (DEVE passare)")
    b_fermate = 0
    for nome, testo in BRACCIO_B:
        g = giudica(testo)
        ko = _fermato(g)
        b_fermate += ko
        print(f"  {'FERMATO ' if ko else 'passato '} {nome:24s} {_dettaglio(g)}"
              + ("   ← FALSO POSITIVO" if ko else ""))

    # ── il verdetto e' la COPPIA ─────────────────────────────────────────
    print()
    print("=" * 68)
    print(f"A: {a_fermate}/7 fermate (piu' e' meglio)   "
          f"B: {b_fermate}/7 fermati (ZERO e' l'unico valore accettabile)")
    if b_fermate:
        print("VERDETTO: la configurazione ferma dei VERI. E' il caso del 06/09:")
        print("          si ritira, qualunque sia il numero del braccio A.")
        return 1
    if a_fermate == 0:
        print("VERDETTO: D-1 e' aperto — nessuna delle sette forme e' fermata.")
        return 1
    print(f"VERDETTO: ferma {a_fermate}/7 senza falsi positivi.")
    return 0


if __name__ == "__main__":
    if os.environ.get("ENGRAM_ENCODE_SERVICE") not in ("0", None, ""):
        print("⚠️  ENGRAM_ENCODE_SERVICE non e' 0: il banco puo' scaldare il "
              "giudice condiviso. Rilancialo con ENGRAM_ENCODE_SERVICE=0.")
    sys.exit(main())
