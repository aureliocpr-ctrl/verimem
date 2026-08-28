"""W2-27 bis · Con la forma GIUSTA di claim, le due porte divergono?

Il mio primo banco (`1ac18284`) era **INERTE** e l'ho dichiarato: otto celle,
tutte «ENTRA», **zero strati** ⇒ nessuno strato ingaggiato. Il verdetto era
«NESSUN VERDETTO».

**La ragione ora è nel sorgente**, e l'ho letta invece di indovinarla —
`anti_confab_gate.py:1960`::

    if (repo_root is not None and not warnings and verified_by is not None …

EVIDENCE-EXISTENCE scatta **solo quando la prova ha «ripulito» un claim**: `L1`
**non** fira **con** la prova ma **firerebbe senza**. Il mio claim metrico
(«*la suite riporta 8647 test passati*») **non fa scattare `L1` nemmeno senza
prove** — misurato: `model_claim`, zero strati — quindi quella condizione era
**falsa** e il layer non poteva entrare. **La forma del claim era sbagliata,
e adesso so perché.**

🤝 E @ws2 ha appena **ritirato** il proprio finding sullo stesso fronte: il suo
stub `_Ag` **non portava `repo_root`**, cioè **spegneva la cosa che cercava di
innescare**. Col suo agente vero: `bench:non_esiste_2026` **da solo** →
`quarantined ['L1.19']` con `evidence_existence=True`; lo stesso `bench:` finto
**+ un `file:` che esiste** → `model_claim []`. **La cura è viva e discrimina.**

LA FORMA GIUSTA, che ne segue: un claim che **`L1` prende SENZA prove** (un
autoclaim di successo), accompagnato da una prova **fabbricata** che sopprime
`L1` — a quel punto `EVIDENCE-EXISTENCE` deve accorgersi che non esiste.

    ctrl  nessuna prova              -> L1 deve FERMARE (prova che la macchina c'e')
    A     bench: FABBRICATO          -> la prova sopprime L1; esiste? NO
    B     bench: fabbricato + file: REALE -> un ref esiste davvero
    C     file: REALE da solo        -> prova vera

LA PREDIZIONE, scritta prima di eseguire: **A diverge fra le porte** — su MCP
`repo_root` c'è e la cura scatta (**ferma**), sull'SDK `repo_root` è `None` e il
comportamento resta *format-only* (**entra**). B e C non divergono.

CONDIZIONE DI FALSIFICAZIONE: se **A non diverge**, allora o `repo_root` non
arriva nemmeno dalla mia chiamata MCP in-process — **e allora sto rifacendo
l'errore di @ws2 con un altro strumento** — oppure W2-27 non ha effetto sul
verdetto. **Il banco stampa `repo_root` per distinguere i due casi**: senza
quella stampa non saprei quale dei due.

CONTROLLO CHE DEVE POTER FALLIRE: `ctrl` (nessuna prova) deve essere **fermato
su entrambe**. Se entrasse, `L1` non è ingaggiato e il banco è inerte come il
primo.

REGIME: un processo, store TEMPORANEO, handler MCP in-process, SDK stesso
processo. Lo store di Aurelio NON è toccato.

    python docs/stato-reale/banchi/ws3-W2-27-bis-la-forma-giusta-e-le-due-porte.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

#: un autoclaim di successo: `L1` lo prende SENZA prove (misurato: L1.10/15/20)
CLAIM = "Il fix funziona ed e' verificato."

BENCH_FABBRICATO = "bench:non_esiste_2026"
FILE_VERO = "file:verimem/quantity_match.py:1050"

CASI = [
    ("ctrl nessuna prova ", None),
    ("A bench FABBRICATO ", [BENCH_FABBRICATO]),
    ("B fabbricato + reale", [BENCH_FABBRICATO, FILE_VERO]),
    ("C file REALE       ", [FILE_VERO]),
]


def _strati(ric) -> list[str]:
    return [str(w.get("layer")) for w in (ric.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


def _ev_ex(ric) -> bool:
    """`evidence_existence` sul warning: la firma della cura di @ws2."""
    return any(bool(w.get("evidence_existence"))
               for w in (ric.get("warnings") or []) if isinstance(w, dict))


def _sdk(mem, vb, topic: str):
    kw = {"verified_by": vb} if vb else {}
    r = mem.add(CLAIM, topic=topic, validate="full", **kw)
    return str(r.get("status")) == "quarantined", _strati(r), _ev_ex(r)


def _mcp(vb, topic: str):
    from verimem import mcp_server  # noqa: PLC0415

    args = {"proposition": CLAIM, "topic": topic}
    if vb:
        args["verified_by"] = vb
    out = asyncio.run(mcp_server._call_tool_impl("hippo_remember", args))
    testo = "\n".join(getattr(c, "text", "") for c in out)
    try:
        d = json.loads(testo)
    except Exception:  # noqa: BLE001
        return ("quarantin" in testo.lower(), [], False)
    ls = [str(w.get("layer")) for w in (d.get("warnings") or [])
          if isinstance(w, dict) and w.get("layer")]
    return str(d.get("status")) == "quarantined", ls, _ev_ex(d)


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)}")
    print(f"    HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print(f"    claim: «{CLAIM}»  (autoclaim: L1 lo prende SENZA prove)")
    print(f"    file reale esiste? {Path('verimem/quantity_match.py').exists()}")

    # ⚠️ LA STAMPA CHE DISTINGUE I DUE FALLIMENTI POSSIBILI: se `repo_root` e'
    # None anche su MCP, sto rifacendo l'errore di @ws2 con un altro strumento
    # (il suo stub non lo portava e lei spegneva cio' che voleva innescare).
    mem = Memory(str(tmp / "w227b.db"))
    rr_sdk = getattr(getattr(mem, "semantic", None), "repo_root", None)
    print(f"\n  [0] repo_root visto dall'SDK ....... {rr_sdk!r}")
    try:
        from verimem import mcp_server  # noqa: PLC0415
        rr_mcp = getattr(getattr(getattr(mcp_server, "_ag", None),
                                 "semantic", None), "repo_root", None)
    except Exception as e:  # noqa: BLE001
        rr_mcp = f"<non leggibile: {type(e).__name__}>"
    print(f"      repo_root visto da MCP ......... {rr_mcp!r}")
    if not rr_mcp:
        print("      ⚠️ repo_root ASSENTE anche su MCP: se A non diverge, la causa")
        print("        e' QUESTA e non W2-27 — sarebbe l'errore di @ws2 rifatto")
        print("        con un altro strumento, e il banco non puo' concludere.")

    print(f"\n  {'caso':<21} {'SDK':<30} {'MCP':<30} {'div?'}")
    print("  " + "-" * 88)
    div = []
    esiti = {}
    for i, (et, vb) in enumerate(CASI):
        s_q, s_l, s_e = _sdk(mem, vb, f"bis/sdk/{i}")
        m_q, m_l, m_e = _mcp(vb, f"bis/mcp/{i}")
        esiti[et.strip()] = (s_q, m_q)
        if s_q != m_q:
            div.append((et, s_q, m_q, s_l, m_l, s_e, m_e))
        def _f(q, ls, e):
            return (f"{'ferma' if q else 'ENTRA'} "
                    f"{','.join(ls) if ls else '-'}{' +evEx' if e else ''}")
        print(f"  {et:<21} {_f(s_q, s_l, s_e):<30} {_f(m_q, m_l, m_e):<30} "
              f"{'NO' if s_q == m_q else 'SI'}")

    c = esiti.get("ctrl nessuna prova")
    print(f"\n  CONTROLLO: `ctrl` (nessuna prova) fermato su entrambe? "
          f"SDK={'si' if c[0] else 'NO'} MCP={'si' if c[1] else 'NO'}")
    if not (c[0] and c[1]):
        print("     CONTROLLO CADUTO: L1 non ferma nemmeno il claim nudo ⇒ il")
        print("     banco e' inerte come il primo. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if div:
        print(f"     PREDIZIONE RETTA: {len(div)} caso/i DIVERGONO fra le porte ⇒")
        print("     W2-27 non e' una differenza di configurazione: CAMBIA IL")
        print("     VERDETTO. Lo stesso claim con la stessa prova FABBRICATA e'")
        print("     fermato da una porta e ammesso dall'altra.")
        for et, s_q, m_q, s_l, m_l, _se, _me in div:
            print(f"        {et}  SDK={'ferma' if s_q else 'ENTRA'} [{','.join(s_l)}]"
                  f"   MCP={'ferma' if m_q else 'ENTRA'} [{','.join(m_l)}]")
    else:
        print("     PREDIZIONE FALSIFICATA: nessuna divergenza.")
        print(f"     ⚠️ Leggere il [0]: repo_root SDK={rr_sdk!r} MCP={rr_mcp!r}.")
        print("     Se sono UGUALI, non ho messo le due porte in due regimi")
        print("     diversi e il banco NON risponde a W2-27 — sarebbe l'errore di")
        print("     @ws2 rifatto con un altro strumento.")

    print("\n  ⚠️ LIMITI: quattro combinazioni, un claim solo, nessuna fonte.")
    print("     L'handler MCP e' in-process: un client vero passa dallo stdio.")
    print("     E `repo_root` dipende da come lo store e' stato aperto, che e'")
    print("     precisamente la variabile che ha ingannato @ws2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
