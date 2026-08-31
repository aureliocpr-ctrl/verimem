"""L'astensione sulla CLI: la cella che mancava alla matrice promessa x porta.

DA DOVE VIENE. @ws7 (`LANT-130`, 02:16) ha messo il Summary del pacchetto in
una **matrice promessa × porta** e ha dichiarato che se ne conoscono poche
celle. Sulla riga ④ *«abstention instead of hallucination»* ho portato le
QUATTRO celle MCP che avevo gia' misurato stanotte::

    hippo_facts_recall     NON si astiene   0.757 fuori corpus contro 0.857 dentro
    hippo_facts_search     NON si astiene   0 righe, ma e' un MISS LESSICALE
    hippo_trust_report     SI               `abstained` true/false
    hippo_recall_history   NON              nessuna astensione dichiarata

⇒ **Manca la CLI**, ed e' una porta pubblica del prodotto (`verimem recall`).

🔑 E IL REGIME DELLA CLI E' DIVERSO da quello del server, il che rende la cella
non deducibile da quelle MCP: `embedding._delegate_only` e' vero solo con
`HIPPO_ENCODE_DELEGATE_ONLY=1`, e il suo docstring dice *«The daemon + CLI
leave it unset, so they still load in-process normally»*. Questo banco la
RIMUOVE dall'ambiente per misurare la CLI nel regime in cui vive davvero — e
lo dichiara, perche' la shell di questa macchina ce l'ha impostata.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: sulla domanda COPERTA la CLI deve
trovare il fatto. Se non lo trovasse, ogni «non trova» sulla domanda estranea
sarebbe illeggibile — proverebbe che la porta non risponde, non che si astenga.
⚠️ LA POPOLAZIONE OPPOSTA: con un pavimento che nulla puo' superare, la CLI
deve dire qualcosa di DIVERSO da «non ho trovato niente» — altrimenti le due
cause (corpus povero · pavimento alto) collassano in una riga sola, che e' il
difetto che il prodotto passa la giornata a curare.
⚠️ IL CRITERIO E' IL TESTO STAMPATO, non un conteggio: una porta che non si
astiene mai restituisce comunque righe, e contarle direbbe altro.
═══════════════════════════════════════════════════════════════════════════════

REGIME: sottoprocessi veri della CLI, store TEMPORANEO,
`HIPPO_ENCODE_DELEGATE_ONLY` RIMOSSA (regime CLI), daemon condiviso come si
trova — non lo spengo, non e' mio. Lo store di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-la-riga-dell-astensione-sulla-porta-della-riga-di-comando.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

FATTO = "La penale del contratto Rossi e' 120 euro al giorno."
FONTE = "Contratto Rossi, articolo 7: penale di 120 euro al giorno di ritardo."
COPERTA = "quanto e' la penale del contratto Rossi"
ESTRANEA = "come si accorda una tromba prima di un concerto"


def _ambiente(dati: str) -> dict:
    amb = dict(os.environ)
    # ⚠️ ENTRAMBI GLI ALIAS. Con solo `HIPPO_DATA_DIR` la CLI avverte
    # «DATA_DIR aliases disagree» e non parte: l'altro nome resta puntato allo
    # store vero. E' la trappola gemella di quella in memoria («ENGRAM_DATA_DIR
    # non isola perche' HIPPO_DATA_DIR ha precedenza»), vista dall'altro lato.
    amb["HIPPO_DATA_DIR"] = dati
    amb["ENGRAM_DATA_DIR"] = dati
    amb["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
    amb.pop("ENGRAM_MIN_RELEVANCE", None)
    # 🔑 IL REGIME DELLA CLI: la variabile che vieta il caricamento locale e'
    # del processo SERVER. La shell di questa macchina ce l'ha impostata, e
    # lasciarla misurerebbe la CLI in un regime che non e' il suo.
    amb.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
    return amb


def _cli(amb: dict, *args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, "-m", "verimem.cli", *args],
                       capture_output=True, text=True, timeout=600, env=amb)
    return p.returncode, (p.stdout + p.stderr)


def main() -> int:
    dati = tempfile.mkdtemp()
    amb = _ambiente(dati)

    # I nomi dei comandi si LEGGONO da `--help`: `add` e `search` NON esistono
    # (la prima stesura li aveva indovinati, exit=2). Sono `remember` e `recall`.
    rc, out = _cli(amb, "remember", FATTO, "--source", FONTE, "--topic", "cli/pen")
    print(f"  scrittura: exit={rc}  «{' '.join(out.split())[:90]}»")
    if rc != 0:
        print("\n  PREMESSA CADUTA: la scrittura dalla CLI non riesce, quindi")
        print("  non c'e' corpus e nessuna cella qui sotto significa niente.")
        return 1

    celle = []
    for etichetta, argomenti in (
            ("domanda COPERTA (CONTROLLO)", ["recall", COPERTA]),
            ("domanda ESTRANEA", ["recall", ESTRANEA]),
            ("estranea + pavimento 0.999", ["recall", ESTRANEA,
                                            "--min-relevance", "0.999"]),
            ("coperta + pavimento 0.999", ["recall", COPERTA,
                                           "--min-relevance", "0.999"])):
        rc, out = _cli(amb, *argomenti)
        testo = " ".join(out.split())
        celle.append({"caso": etichetta, "exit": rc, "testo": testo,
                      "cita_il_fatto": "120 euro" in testo,
                      "dice_pavimento": "above the floor" in testo.lower()})

    print(f"\n  {'caso':<30} {'exit':>4}  {'cita il fatto':<14} nomina il pavimento")
    print("  " + "-" * 78)
    for c in celle:
        print(f"  {c['caso']:<30} {c['exit']:>4}  "
              f"{'SI' if c['cita_il_fatto'] else 'no':<14} "
              f"{'SI' if c['dice_pavimento'] else 'no'}")
    print("\n  ── cosa STAMPA, per esteso ──")
    for c in celle:
        print(f"  [{c['caso']}]\n      {c['testo'][:150]}")

    def _c(pref: str) -> dict:
        return next((x for x in celle if x["caso"].startswith(pref)), {})

    controllo = _c("domanda COPERTA (CONTROLLO)")
    print(f"\n  [1] CONTROLLO — sulla domanda coperta la CLI trova il fatto: "
          f"{'SI' if controllo.get('cita_il_fatto') else 'NO'}")
    if not controllo.get("cita_il_fatto"):
        print("      CONTROLLO CADUTO: la porta non risponde nemmeno su cio' che")
        print("      lo store contiene ⇒ ogni «non trova» e' illeggibile.")
        print("      NESSUN VERDETTO.")
        return 1

    estranea = _c("domanda ESTRANEA")
    pavimento = _c("estranea + pavimento")
    print("\n  ══ LA CELLA PER LA MATRICE: `verimem recall` si astiene? ══")
    if estranea.get("cita_il_fatto"):
        print("     🔴 NON SI ASTIENE: sulla domanda estranea la CLI restituisce")
        print("     il fatto piu' vicino — stesso comportamento delle porte MCP")
        print("     dei fatti. La cella della matrice e' ROSSA come le altre.")
    else:
        print("     🟢 NON restituisce il fatto sulla domanda estranea.")
        print("     ⚠️ Ma «non restituisce» non e' ancora «si astiene»: guarda")
        print("     cosa STAMPA nella riga qui sopra prima di scrivere 🟢 in una")
        print("     matrice — una lista vuota da una porta lessicale e' un MISS.")

    print("\n  ══ POPOLAZIONE OPPOSTA: le due cause restano distinte? ══")
    if pavimento.get("dice_pavimento"):
        print("     🟢 SI: col pavimento alto la CLI dice «no facts above the")
        print("     floor», che e' una frase DIVERSA da «non ho trovato niente».")
        print("     ⇒ Su questa superficie la distinzione che le ricevute MCP non")
        print("     portavano c'e' gia', ed e' in PROSA invece che in un campo.")
    else:
        print("     🔴 NO: col pavimento alto la CLI non nomina il pavimento, e")
        print("     «il corpus e' povero» e «l'hai tagliato tu» si leggono uguali.")

    print("\n  ⚠️ LIMITI: un fatto, due domande, una macchina; daemon condiviso")
    print("     VIVO (non e' mio). NON misura `verimem trust` — quello ha gia'")
    print("     quattro celle in `test_cli_trust_declares_what_ran.py` — ne' la")
    print("     qualita' del ranking: solo se la porta si astenga e se le due")
    print("     cause di una risposta vuota restino distinguibili.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
