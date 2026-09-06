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
    for attr in ("quarantined", "blocked", "rejected"):
        v = getattr(gate_result, attr, None)
        if isinstance(v, bool):
            return v
    stato = getattr(gate_result, "status", None)
    if isinstance(stato, str):
        return stato.lower() in {"quarantined", "rejected", "blocked"}
    _non_misurato(
        "GateResult non espone uno stato booleano ne' `status` leggibile: "
        f"attributi visti = {sorted(a for a in dir(gate_result) if not a.startswith('_'))[:12]}"
    )
    return False  # irraggiungibile


def main() -> int:
    print("D-1 — le sette forme e i veri composti")
    print("=" * 68)

    # ── quale albero sto misurando (la trappola del worktree, 05/09) ──────
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
        try:
            return run_validation_gate(testo, source=FONTE)
        except TypeError:
            return run_validation_gate(testo)          # firma piu' vecchia
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
        ok = _fermato(giudica(testo))
        a_fermate += ok
        print(f"  {'FERMATA ' if ok else 'passata '} {nome}")

    # ── BRACCIO B: devono PASSARE ────────────────────────────────────────
    print()
    print("BRACCIO B — fatti composti VERI, nessuna self-claim (DEVE passare)")
    b_fermate = 0
    for nome, testo in BRACCIO_B:
        ko = _fermato(giudica(testo))
        b_fermate += ko
        print(f"  {'FERMATO ' if ko else 'passato '} {nome}"
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
