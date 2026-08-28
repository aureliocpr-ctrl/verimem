"""W2-27 · Le due porte danno verdetti DIVERSI sullo stesso claim con prove?

Reperto di @ws2, dichiarato **mai misurato**: `repo_root` è passato al gate
**SOLO da MCP** (`mcp_server.py:12887`) e **mai dall'SDK** ⇒
`EVIDENCE-EXISTENCE` (`anti_confab_gate.py:1945`) è **attivo su una porta e
spento sull'altra**.

⚠️ **Lei ha misurato l'effetto DENTRO una porta** (cella 35: con `repo_root`,
`bench:` finto 🔴 · `file:` reale 🔴 · `bench:`+`file:` reale 🟢 ·
`bench:`+`file:` inesistente 🔴). **Quello che resta aperto è un'altra cosa**:
lo **stesso identico claim, con le stesse prove**, su **due porte diverse**, dà
**due verdetti diversi**?

🔑 E la domanda è quella giusta perché stanotte ho imparato che **attivo ≠
decisivo**: `L4.1` era attivo su tutti gli scambi di attribuzione e parlava
**0 volte su 12**. Un layer acceso che non cambia nessun verdetto non è una
differenza fra porte: è rumore.

IL DISEGNO: **claim con una metrica e SENZA fonte** — così il moat non gira e
il verdetto lo decidono gli strati sulle prove, che è ciò che voglio isolare.
Cambia **solo** ciò che `verified_by` contiene:

    A  bench: finto                              (accettato da L1.19, non verificabile)
    B  file: REALE                               (verificabile, esiste davvero)
    C  bench: finto + file: REALE
    D  bench: finto + file: INESISTENTE          <- la cella che deve separare

LA PREDIZIONE, scritta prima di eseguire: **almeno un caso dà verdetti diversi
fra SDK e MCP**, e il candidato è **D** — su MCP `EVIDENCE-EXISTENCE` vede che
il file non esiste, sull'SDK no.

CONDIZIONE DI FALSIFICAZIONE: se tutti e quattro danno lo **stesso** verdetto
su entrambe le porte, allora `repo_root` è **attivo ma non decisivo**, e il
reperto W2-27 va requalificato da «differenza fra porte» a «differenza di
configurazione senza effetto misurato».

CONTROLLO CHE DEVE POTER FALLIRE: il caso **C** (prove complete e vere) deve
essere ammesso su **entrambe**. Se cadesse anche lui, starei misurando un gate
che rifiuta tutto, non una differenza.

REGIME: un processo, store TEMPORANEO (`HIPPO_DATA_DIR` in tempdir, impostato
PRIMA di importare il server), handler MCP in-process, SDK stesso processo.
Lo store di Aurelio NON è toccato.

    python docs/stato-reale/banchi/ws3-W2-27-le-due-porte-danno-verdetti-diversi-sulle-prove.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

CLAIM = "La suite di test del progetto riporta 8647 test passati."

#: un file che esiste DAVVERO nel repo, con una riga plausibile
FILE_VERO = "file:verimem/quantity_match.py:1050"
FILE_FALSO = "file:verimem/non_esiste_affatto.py:999"
BENCH_FINTO = "bench:pippo"

CASI = [
    ("A bench finto      ", [BENCH_FINTO]),
    ("B file REALE       ", [FILE_VERO]),
    ("C bench + file vero", [BENCH_FINTO, FILE_VERO]),
    ("D bench + file FALSO", [BENCH_FINTO, FILE_FALSO]),
]


def _strati(ric) -> list[str]:
    return [str(w.get("layer")) for w in (ric.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


def _sdk(mem, vb: list[str], topic: str) -> tuple[bool, list[str]]:
    r = mem.add(CLAIM, topic=topic, verified_by=vb, validate="full")
    return str(r.get("status")) == "quarantined", _strati(r)


def _mcp(vb: list[str], topic: str) -> tuple[bool, list[str]]:
    from verimem import mcp_server  # noqa: PLC0415

    out = asyncio.run(mcp_server._call_tool_impl(
        "hippo_remember",
        {"proposition": CLAIM, "topic": topic, "verified_by": vb},
    ))
    testo = "\n".join(getattr(c, "text", "") for c in out)
    try:
        d = json.loads(testo)
    except Exception:  # noqa: BLE001
        return ("quarantin" in testo.lower(), [])
    ls = [str(w.get("layer")) for w in (d.get("warnings") or [])
          if isinstance(w, dict) and w.get("layer")]
    return str(d.get("status")) == "quarantined", ls


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)     # PRIMA di importare il server
    from verimem.client import Memory  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)}")
    print(f"    HIPPO_DATA_DIR={tmp}  (lo store di Aurelio NON e' toccato)")
    print("    handler MCP in-process · SDK stesso processo · claim SENZA fonte")
    print(f"    file reale usato come prova: {FILE_VERO}")
    print(f"    esiste davvero? "
          f"{Path('verimem/quantity_match.py').exists()}")

    mem = Memory(str(tmp / "w227.db"))

    # ── CONTROLLO POSITIVO, aggiunto DOPO la prima esecuzione ───────────
    # La prima stesura non ce l'aveva e il risultato era ILLEGGIBILE: tutte e
    # otto le celle davano «ENTRA» con ZERO strati, e il mio controllo (il caso
    # C ammesso su entrambe) e' soddisfatto anche da un banco in cui NESSUNO
    # STRATO ENTRA IN GIOCO. E' il difetto che correggo agli altri: uno zero
    # non e' leggibile finche' non provi che lo strumento vede.
    ctrl = mem.add("Il fix funziona ed e' verificato.", topic="w227/ctrl",
                   validate="full")
    ctrl_l = _strati(ctrl)
    print("\n  [0] CONTROLLO POSITIVO — un autoclaim nudo deve essere preso:")
    print(f"      «Il fix funziona ed e' verificato.» -> {ctrl.get('status')}"
          f"  strati={','.join(ctrl_l) if ctrl_l else '-'}")
    if not ctrl_l:
        print("      CONTROLLO CADUTO: nemmeno un autoclaim nudo produce uno")
        print("      strato ⇒ la macchina lessicale non e' ingaggiata e il banco")
        print("      non puo' dare un verdetto. NESSUNA MISURA.")
        return 1

    senza = mem.add(CLAIM, topic="w227/senza", validate="full")
    senza_l = _strati(senza)
    print(f"      il MIO claim SENZA prove            -> {senza.get('status')}"
          f"  strati={','.join(senza_l) if senza_l else '-'}")
    if not senza_l:
        print("      ⚠️ IL CLAIM DI QUESTO BANCO NON INGAGGIA GLI STRATI SULLE")
        print("        PROVE: un claim metrico senza fonte e senza prove entra")
        print("        come `model_claim` con ZERO strati — ed e' il CONTRATTO")
        print("        DICHIARATO del prodotto («senza fonte non c'e' nulla con")
        print("        cui confrontare: model_claim non verificato»), non un")
        print("        difetto. ⇒ la matrice qui sotto e' INERTE su questa forma")
        print("        di claim, e il suo «nessuna divergenza» NON e' un")
        print("        risultato: e' un'assenza di misura.")

    print(f"\n  {'caso':<21} {'SDK':<26} {'MCP':<26} {'concordi?'}")
    print("  " + "-" * 82)
    divergenti = []
    esiti = {}
    for i, (et, vb) in enumerate(CASI):
        s_q, s_l = _sdk(mem, vb, f"w227/sdk/{i}")
        m_q, m_l = _mcp(vb, f"w227/mcp/{i}")
        esiti[et.strip()] = (s_q, m_q)
        if s_q != m_q:
            divergenti.append((et, s_q, m_q, s_l, m_l))
        def _f(q: bool, ls: list[str]) -> str:
            return f"{'ferma' if q else 'ENTRA'} {','.join(ls) if ls else '-'}"
        print(f"  {et:<21} {_f(s_q, s_l):<26} {_f(m_q, m_l):<26} "
              f"{'si' if s_q == m_q else 'NO'}")

    c = esiti.get("C bench + file vero")
    print(f"\n  CONTROLLO: il caso C (prove complete e VERE) e' ammesso su "
          f"entrambe? SDK={'no' if c[0] else 'si'} MCP={'no' if c[1] else 'si'}")
    if c[0] and c[1]:
        print("     CONTROLLO CADUTO: nemmeno le prove complete e vere passano ⇒")
        print("     misuro un gate che rifiuta tutto, non una differenza fra")
        print("     porte. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if not senza_l and not divergenti:
        print("     NESSUN VERDETTO. Le celle non divergono, ma NON HO MISURATO")
        print("     la domanda: su questa forma di claim gli strati sulle prove")
        print("     non entrano mai in gioco (zero strati ovunque, controllo [0]).")
        print("     ⇒ W2-27 resta APERTO. Serve una forma di claim che INGAGGI")
        print("       EVIDENCE-EXISTENCE — e trovarla e' il prossimo passo, non")
        print("       una conclusione. Pubblicare «nessuna divergenza» da qui")
        print("       sarebbe spacciare un'assenza di misura per un risultato.")
    elif divergenti:
        print(f"     PREDIZIONE RETTA: {len(divergenti)} caso/i con verdetto DIVERSO")
        print("     fra le due porte ⇒ W2-27 non e' solo una differenza di")
        print("     configurazione: CAMBIA IL VERDETTO. Lo stesso claim con le")
        print("     stesse prove e' accettato da una porta e rifiutato dall'altra.")
        for et, s_q, m_q, s_l, m_l in divergenti:
            print(f"        {et}  SDK={'ferma' if s_q else 'ENTRA'} [{','.join(s_l)}]"
                  f"   MCP={'ferma' if m_q else 'ENTRA'} [{','.join(m_l)}]")
    else:
        print("     PREDIZIONE FALSIFICATA: nessuna divergenza. `repo_root` e'")
        print("     ATTIVO su MCP ma NON DECISIVO su questi casi ⇒ W2-27 va")
        print("     requalificato da «differenza fra porte» a «differenza di")
        print("     configurazione senza effetto misurato».")
        print("     🔑 E' la stessa lezione di L4.1 sugli scambi: attivo != decisivo.")

    print("\n  ⚠️ LIMITI: quattro combinazioni di prove, un claim solo, nessuna")
    print("     fonte (il moat non gira: isolo gli strati sulle prove). L'handler")
    print("     MCP e' in-process: un client vero passa dallo stdio e da un altro")
    print("     env, e `repo_root` dipende da come lo store e' stato aperto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
