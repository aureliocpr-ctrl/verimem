"""`advice` non arriva a MCP sul ramo quarantena — e non e' un difetto che valga.

Dal censimento di stasera (`57726ae1`) era emerso che **`advice` esiste solo
sulla ricevuta SDK, 6 casi su 6**. Sembrava il difetto di superficie piu' netto
rimasto: *un chiamante MCP sa di essere stato fermato ma non cosa fare.* Prima
di proporlo ho fatto due cose, e **entrambe lo hanno ridimensionato**.

── ① LA LEZIONE ERA NEL FILE, e correggeva la mia stessa frase ──────────────

`"advice"` compare in `mcp_server.py` **una volta sola**, a riga **12957**, e
sta sul ramo **`reject`**::

    if _gate.action == "reject":
        return _ok({"ok": False, "rejected": True,
                    "reason": "anti_confab_gate",
                    "advice": _gate.advice,          # <- C'E'
                    "anti_confab_warnings": _gate_warnings, ...})

Il ramo **`downgrade`** (quello che produce `status="quarantined"`) espone
invece `grounding_score` · `moat` · `deferred` · `status` · `verified_by` ·
`source_signature` · `anti_confab_warnings` · `gate_knobs_denied` ·
`quarantined_by` (condizionale) · `adjudication` — **e nessun `advice`**.

⇒ **«MCP non da' mai `advice`» sarebbe FALSO.** MCP lo da' quando **rigetta**,
non quando **quarantina**. I miei sei casi producevano tutti `downgrade`, e da
li' avevo generalizzato. *Il campione non copriva il ramo dove il campo c'e'.*

── ② E POI HO LETTO COSA DICE `advice`, invece di assumere che valesse ──────

    1 nudo             model_claim   <VUOTO>
    2 autoclaim        quarantined   <VUOTO>
    3 fonte SUPPORTA   model_claim   <VUOTO>
    4 fonte NEGA       quarantined   'Source does not entail the claim
                                      (semantic grounding).'
    5 bench FABBRICATO model_claim   <VUOTO>
    6 file REALE       quarantined   <VUOTO>

**Pieno in 1 caso su 6.** E quell'unica frase e' una **diagnosi, non una cura**:
dice *cosa* e' successo, non *cosa fare* — e la stessa informazione MCP **la da'
gia'**, via `anti_confab_warnings` e via il campo `moat`.

🟢 **VERDETTO: l'asimmetria esiste ed e' quasi priva di conseguenze.** Il campo
e' popolato 1 volta su 6, il suo unico contenuto e' gia' disponibile per altra
via, e **sul ramo dove `advice` conta davvero — `reject` — MCP lo espone.** Gli
autori lo mettono dove serve. **Non e' un difetto che valga la pena proporre**,
e lo dico invece di consegnare una cura per far numero.

🔑 **E questa e' la quarta volta stasera che un mio allarme si sgonfia quando lo
misuro.** Le prime tre le ho misurate prima di postarle; **una** (il «29,1% di
quarantinati senza attribuzione») l'ho postata e ho dovuto **rettificarla**.
⇒ *La differenza fra un reperto e un allarme falso non e' la qualita'
dell'intuizione: e' se lo misuri prima o dopo averlo detto.*

⚠️ **LIMITI, e uno e' proprio quello che mi ha fregato**: **sei casi, e nessuno
raggiunge il ramo `reject`** — proprio quello dove `advice` e' esposto anche su
MCP. Quanto `advice` sia sostanzioso **li'** non l'ho misurato. Il campione
copre il ramo `downgrade`, che e' quello che produce la gran parte delle
quarantene, ma **non tutto il gate**.

📌 NOTA a margine, coerente con W2-27 (`fff6a505`): nel caso 5 (`bench:`
fabbricato) l'SDK ammette come `model_claim` e non produce advice, perche' li'
`EVIDENCE-EXISTENCE` non scatta — l'SDK non porta `repo_root`. E' la stessa
asimmetria **deliberata** gia' documentata, vista da un altro campo.

    python docs/stato-reale/banchi/ws3-advice-non-arriva-a-mcp-ma-e-quasi-sempre-vuoto.py
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

F_SUP = "Il rapporto indica che la penale e-di 500 euro al giorno."
F_NEG = "Il rapporto indica che la penale e-di 120 euro al giorno."

CASI: list[tuple[str, str, str | None, list[str] | None]] = [
    ("1 nudo            ", "Il deposito si trova a Bologna.", None, None),
    ("2 autoclaim       ", "Il fix funziona ed e' verificato.", None, None),
    ("3 fonte SUPPORTA  ", "La penale e-di 500 euro al giorno.", F_SUP, None),
    ("4 fonte NEGA      ", "La penale e-di 500 euro al giorno.", F_NEG, None),
    ("5 bench FABBRICATO", "La latenza e' 40 ms.", None,
     ["bench:non_esiste_2026"]),
    ("6 file REALE      ", "La latenza e' 40 ms.", None,
     ["file:verimem/quantity_match.py:1050"]),
]


def main() -> int:
    # ── ① il sorgente PRIMA del banco: dove sta `advice` su MCP? ─────────
    print("  [1] QUANTE VOLTE `advice` compare nella superficie MCP:")
    try:
        out = subprocess.run(
            ["git", "grep", "-n", '"advice"', "--", "verimem/mcp_server.py"],
            capture_output=True, text=True, check=False).stdout.strip()
    except Exception as e:  # noqa: BLE001
        out = f"<git grep non eseguibile: {type(e).__name__}>"
    print("      " + (out.replace("\n", "\n      ") if out else "<nessuna>"))
    n_occ = len([x for x in out.splitlines() if x.strip()])
    if n_occ != 1:
        print(f"      ⚠️ ATTESE 1 occorrenza (ramo `reject`), TROVATE {n_occ}:")
        print("      il sorgente e' cambiato ⇒ rileggi prima di fidarti del")
        print("      resto di questo banco.")

    # ── ② cosa dice davvero `advice`, esito per esito ────────────────────
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"\n  [2] IL TESTO DI `advice` NEI SEI ESITI  (store temp: {tmp})")
    mem = Memory(str(tmp / "adv.db"))
    pieni = 0
    for i, (et, prop, src, vb) in enumerate(CASI):
        kw: dict = {}
        if src:
            kw["source"] = src
        if vb:
            kw["verified_by"] = vb
        r = mem.add(prop, topic=f"adv/{i}", validate="full", **kw)
        a = (r.get("advice") or "").strip()
        if a:
            pieni += 1
        print(f"      {et} {str(r.get('status')):<12} "
              + (repr(a)[:96] if a else "<VUOTO>"))

    # CONTROLLO CHE DEVE POTER FALLIRE: se `advice` fosse pieno OVUNQUE, la
    # sua assenza su MCP sarebbe una perdita seria e il verdetto si
    # ribalterebbe. Il banco deve poter dire anche questo.
    print(f"\n  [3] CONTROLLO: `advice` pieno in {pieni}/{len(CASI)} casi")
    if pieni >= len(CASI) - 1:
        print("      ⇒ `advice` e' quasi SEMPRE pieno: la sua assenza sul ramo")
        print("        quarantena di MCP e' una perdita SERIA, e il verdetto")
        print("        qui sotto va ribaltato.")
        return 0

    print("\n  ══ VERDETTO ══")
    print("     L'asimmetria esiste ed e' quasi priva di conseguenze:")
    print(f"     `advice` e' popolato in {pieni}/{len(CASI)}, il suo unico")
    print("     contenuto e' una DIAGNOSI gia' disponibile via")
    print("     `anti_confab_warnings` e `moat`, e sul ramo dove conta davvero")
    print("     (`reject`) MCP LO ESPONE.")
    print("     ⇒ NON e' un difetto che valga la pena proporre.")
    print("\n  ⚠️ LIMITE che mi aveva gia' fregato: nessuno dei sei casi")
    print("     raggiunge il ramo `reject`, proprio quello dove `advice` e'")
    print("     esposto anche su MCP. Quanto valga LI' non l'ho misurato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
