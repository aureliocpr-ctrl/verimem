"""IL COSTO DI ALLARGARE L'ELENCO, SUL CORPUS VERO — il debito di `W7-66`, pagato.

`W7-66` ha misurato il costo su **dodici frasi che ho scritto io** e ha dichiarato
il limite: *«il costo sul corpus vero e' un'altra misura e non e' questa»*.
**Un limite dichiarato e' un debito** — su quattro misurati in questo registro,
uno solo reggeva. Questo lo paga.

LA POPOLAZIONE, e stavolta non la costruisco: i fatti **vivi** che hanno una
**fonte conservata** (`grounding_span`) e che il **giudice ha approvato**
(`grounding_score >= 80`). Sono fatti che il prodotto ha gia' deciso di credere,
con accanto il testo su cui li ha creduti. **Se l'elenco allargato ne ferma uno,
quello e' un falso allarme su un dato vero.**

⚠️ **DUE LIMITI, dichiarati PRIMA e uno dei due misurato lo stesso**:
 (a) misuro al **DETECTOR**, non alla porta: alla porta servirebbe rigirare il
     moat su migliaia di fatti. ⇒ **Correggo con un CAMPIONE alla porta** e
     stampo il fattore, invece di lasciare il limite in piedi (`W7-62`).
 (b) `grounding_span` e' un **frammento** della fonte, non la fonte intera: se il
     participio stava fuori dal frammento, il perdono non lo trova e io conto un
     falso allarme che forse non c'e'. ⇒ **Sovrastima**, e lo dico.

CONTROLLI CHE POSSONO FALLIRE:
 (1) **la distribuzione PRIMA di dividere**: stampo quanti fatti sono gia'
     fermati dall'elenco VECCHIO. Quelli non sono un costo dell'allargamento.
 (2) **controllo positivo**: il detector deve fermare qualcosa con l'elenco
     vecchio. Se fermasse zero su tutto il corpus sarebbe spento e il confronto
     non varrebbe niente.

    python -u docs/stato-reale/banchi/il-costo-sul-corpus-vero-di-allargare-l-elenco.py
"""

from __future__ import annotations

import re
import sqlite3
import sys

RADICI_NUOVE = [
    "ultimat[oaie]", "terminat[oaie]", "esegu[oaie]t[oaie]",
    "consegnat[oaie]", "evas[oaie]", "espletat[oaie]",
]
CAMPIONE_PORTA = 12


def main() -> int:
    try:
        from verimem import l1_completion_detector as L1
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.config import CONFIG
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    VECCHIO = L1._COMPLETION_PATTERN
    coda = "conclus[oaie])"
    if coda not in VECCHIO.pattern:
        print("NON RIUSCITO: non riconosco la coda del pattern.")
        return 1
    NUOVO = re.compile(
        VECCHIO.pattern.replace(
            coda, "conclus[oaie]|" + "|".join(RADICI_NUOVE) + ")"),
        re.IGNORECASE)

    db = CONFIG.semantic_db
    print(f"  DB: {db}")
    c = sqlite3.connect(str(db))
    righe = c.execute(
        "select id, proposition, grounding_span, grounding_score from facts "
        "where superseded_by is null and grounding_span is not null "
        "and grounding_span <> '' and grounding_score >= 80").fetchall()
    print(f"  popolazione: {len(righe)} fatti vivi con fonte conservata e"
          " giudizio >= 80")
    if not righe:
        print("NON RIUSCITO: popolazione vuota.")
        return 1

    def ferma(pat, prop, src):
        L1._COMPLETION_PATTERN = pat
        try:
            return L1.detect_unsupported_completion_claim(
                proposition=prop, verified_by=None, source=src) is not None
        finally:
            L1._COMPLETION_PATTERN = VECCHIO

    gia, nuovi, invariati = [], [], 0
    for fid, prop, span, sc in righe:
        a = ferma(VECCHIO, prop or "", span or "")
        b = ferma(NUOVO, prop or "", span or "")
        if a:
            gia.append(fid)
        elif b:
            nuovi.append((fid, prop, span, sc))
        else:
            invariati += 1

    print("\n  -- CONTROLLO (1) e (2): LA DISTRIBUZIONE, prima di dividere")
    print(f"     gia' fermati dall'elenco VECCHIO : {len(gia)}")
    print(f"     fermati SOLO dall'allargato      : {len(nuovi)}")
    print(f"     non fermati da nessuno dei due   : {invariati}")
    if not gia:
        print("     ⚠️ zero fermati dall'elenco vecchio: il detector e' spento su")
        print("     questa popolazione e il confronto non significa nulla.")
        return 1
    base = len(righe) - len(gia)
    print(f"\n  == IL COSTO: {len(nuovi)} su {base} fatti utili"
          f"  ({100.0 * len(nuovi) / base:.2f}%)")

    # ── quale radice paga, e quanto pesa la spiegazione morfologica di `W7-66`
    print("\n  == QUALE RADICE PAGA (e la spiegazione di W7-66 tiene sul vero?)")
    per_radice: dict[str, int] = {}
    fless = 0
    for _fid, prop, span, _sc in nuovi:
        m = NUOVO.search(prop or "")
        parola = (m.group(0) if m else "?").casefold()
        radice = parola[:6]
        per_radice[radice] = per_radice.get(radice, 0) + 1
        # `W7-66`: il perdono e' testuale ⇒ se la RADICE e' nella fonte ma la
        # PAROLA no, il falso allarme e' morfologico, non semantico.
        if parola[:-1] and parola[:-1] in (span or "").casefold() \
                and parola not in (span or "").casefold():
            fless += 1
    for r, n in sorted(per_radice.items(), key=lambda kv: -kv[1]):
        print(f"     {r:<10}{n}")
    if nuovi:
        print(f"\n     di cui MORFOLOGICI (radice nella fonte, parola no):"
              f" {fless} su {len(nuovi)}"
              f"  ({100.0 * fless / len(nuovi):.0f}%)")
        if fless >= len(nuovi) / 2:
            print("     ⇒ la spiegazione di `W7-66` TIENE anche sul vero: una")
            print("     cura morfologica del perdono toglierebbe questi falsi")
            print("     allarmi SENZA toccare l'elenco.")
        else:
            print("     🪞 **LA SPIEGAZIONE DI `W7-66` NON TIENE SUL CORPUS**: in")
            print("     laboratorio i falsi allarmi erano 3 su 3 morfologici,")
            print("     qui quasi nessuno. ⇒ Sul vero la causa e' un'ALTRA, e")
            print("     una cura morfologica non comprerebbe quasi niente.")

            # 🔬 ALLORA QUAL E'? Il perdono e' testuale: se la parola non e'
            #    nella fonte NEMMENO come radice, non puo' scattare mai. La
            #    domanda diventa **che cosa sono quelle fonti**. Ipotesi:
            #    sono EVIDENZA GREZZA (output di pytest, EXIT=, SHA) — il
            #    regime che la regola O3 impone — e un output di comando
            #    sostiene un claim **senza usarne le parole**.
            #    Falsificabile: se fosse falsa, le fonti sarebbero prosa che
            #    contiene la parola, e allora il perdono avrebbe dovuto
            #    scattare.
            print("\n  == 🔬 ALLORA COSA SONO QUELLE FONTI? (ipotesi: evidenza"
                  " grezza)")
            SEGNI = ("passed", "failed", "EXIT=", "====", "PASS", "FAIL",
                     "warning", "error", "$ ", "commit ", "python ")
            grezze = parola_assente = 0
            for _fid, prop, span, _sc in nuovi:
                s = span or ""
                if any(g in s for g in SEGNI) or sum(ch.isdigit() for ch in s) > len(s) / 12:
                    grezze += 1
                m = NUOVO.search(prop or "")
                if m and m.group(0).casefold()[:5] not in s.casefold():
                    parola_assente += 1
            print(f"     fonti che sembrano OUTPUT/evidenza grezza:"
                  f" {grezze} su {len(nuovi)}")
            print(f"     fonti che NON contengono la radice del claim :"
                  f" {parola_assente} su {len(nuovi)}")
            if parola_assente >= len(nuovi) * 0.8:
                print("     🔑 **Il perdono testuale non puo' scattare per")
                print("     COSTRUZIONE**: la fonte sostiene il claim senza")
                print("     usarne le parole. ⇒ E' il verso ALLARME di `W7-62`")
                print("     su dati veri — e cade proprio nel regime che la")
                print("     regola O3 IMPONE (source = evidenza grezza).")
            else:
                print("     ⇒ la radice c'e' in parte dei casi: l'ipotesi non")
                print("     spiega tutto e non la forzo.")

    # ── (a) il limite del DETECTOR, corretto con un campione ALLA PORTA
    print(f"\n  == LIMITE (a) CORRETTO: {CAMPIONE_PORTA} dei nuovi, ALLA PORTA")
    print(f"     {'porta':<12}{'grounding':<11}claim")
    sopravvivono = 0
    visti = 0
    for _fid, prop, span, _sc in nuovi[:CAMPIONE_PORTA]:
        L1._COMPLETION_PATTERN = NUOVO
        try:
            g = run_validation_gate(proposition=prop, verified_by=[],
                                    topic=None, agent=None, source=span,
                                    ground_write=True)
        except Exception as e:  # noqa: BLE001
            print(f"     [porta non raggiunta: {type(e).__name__}]")
            break
        finally:
            L1._COMPLETION_PATTERN = VECCHIO
        visti += 1
        az = str(getattr(g, "action", None))
        gs = getattr(g, "grounding_score", None)
        if az != "persist":
            sopravvivono += 1
        print(f"     {az:<12}{('-' if gs is None else f'{gs:.1f}'):<11}"
              f"{(prop or '')[:46]}")
    if visti:
        print(f"\n     alla porta ne ferma {sopravvivono} su {visti}"
              f"  ⇒ fattore {sopravvivono / visti:.2f}")
        print(f"     stima del costo ALLA PORTA:"
              f" {len(nuovi) * sopravvivono / visti:.0f} su {base}"
              f"  ({100.0 * len(nuovi) * sopravvivono / visti / base:.2f}%)")
        if sopravvivono < visti:
            print("     🪞 La differenza e' la lezione di `W7-62`: il layer parla")
            print("     e il sistema decide altro. Il numero del detector"
                  " SOVRASTIMA.")

    print("\n  ⚠️ COSA NON DICE: limite (b) in piedi — `grounding_span` e' un")
    print("  FRAMMENTO, e un participio fuori dal frammento fa contare un falso")
    print("  allarme che forse non c'e'. ⇒ questi numeri sono un LIMITE")
    print("  SUPERIORE. E le sei radici restano scelte da me.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
