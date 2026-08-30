"""`trust_signals` promette TRE campi; `min_status` promette una gerarchia di
QUATTRO livelli che non nomina lo stato piu' importante.

DUE PROMESSE DELLO STESSO SCHEMA (`hippo_facts_recall`), lette prima di
misurare, ed entrambe falsificabili senza ambiguita'.

① **`trust_signals`**: *«when True, each item carries `verdict`
(trusted|stale|contested|obsolete|unverified), `age_days`,
`n_contradictions`. Default False keeps the legacy 2-tuple payload format»*.
⇒ Tre campi nominati uno per uno. O ci sono o non ci sono.
📌 La descrizione porta gia' la propria cronaca: *«confirmed via agent #5 audit
that handler exposed the behaviour at runtime but clients couldn't discover it
via tools/list introspection»* — cioe' la promessa e' nata proprio da una
lacuna di dichiarazione. Verificare che oggi regga e' il minimo.

② **`min_status`**: *«Trust floor. Rows with rank lower than min_status are
dropped. Hierarchy: verified(3) > model_claim(2) > provisional(1) >
legacy_unverified(0)»*.
⇒ 🔑 **QUATTRO livelli, e `quarantined` non e' fra loro** — lo stato che
il prodotto usa per tenere un fatto FUORI dal recall di default, quello su cui
ho scritto la guida stanotte. Un agente che legge questa gerarchia impara che
gli stati sono quattro. La domanda misurabile: **un pavimento di fiducia lascia
passare uno stato che la sua gerarchia non conosce?**

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: **senza** `min_status` i fatti devono
tornare. Se lo store non rispondesse gia' cosi', nessun pavimento potrebbe
essere misurato e ogni zero sarebbe illeggibile.
⚠️ LA POPOLAZIONE OPPOSTA: `min_status` al livello PIU' BASSO
(`legacy_unverified`, rank 0) non deve scartare niente. Se scartasse, il campo
non implementa la gerarchia che dichiara.
⚠️ E LE CHIAVI SI LEGGONO: il banco stampa le chiavi di un item prima di
cercarci dentro. Quattro volte stanotte il difetto era nel misuratore.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO, porte MCP in-process, giudice locale
ASSENTE per costruzione (nessuno scaricamento). Lo store di Aurelio non e'
toccato.

    python docs/stato-reale/banchi/ws3-due-promesse-dello-schema-dei-fatti.py
"""

from __future__ import annotations

import json
import subprocess
import sys

DOMANDA = "quanto e' la penale del contratto Rossi"

FIGLIO = r'''
import asyncio, json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem import mcp_server

domanda = sys.argv[1]

def chiama(nome, args):
    return json.loads(asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)

# Un fatto SOSTENUTO dalla fonte e uno che si auto-afferma senza prove.
scritti = []
for prop, fonte in (
        ("La penale del contratto Rossi e' 120 euro al giorno.",
         "Contratto Rossi, articolo 7: penale di 120 euro al giorno di ritardo."),
        ("Ho verificato che la penale del contratto Rossi e' corretta.", None)):
    a = {"proposition": prop, "topic": "sch/x"}
    if fonte:
        a["source"] = fonte
    r = chiama("hippo_remember", a)
    scritti.append({"status": r.get("status"), "qb": r.get("quarantined_by")})

def items(args):
    d = chiama("hippo_facts_recall", {"query": domanda, "k": 10, **args})
    return d.get("items") or []

base = items({})
CHIAVI = sorted(base[0].keys()) if base else []

righe = []
for etichetta, args in (
        ("nessun min_status (CONTROLLO)", {}),
        ("min_status=legacy_unverified", {"min_status": "legacy_unverified"}),
        ("min_status=model_claim",       {"min_status": "model_claim"}),
        ("min_status=verified",          {"min_status": "verified"}),
        ("include_legacy=True",          {"include_legacy": True})):
    it = items(args)
    righe.append({"caso": etichetta, "n": len(it),
                  "stati": sorted({str(i.get("status")) for i in it})})

# ① trust_signals: i tre campi nominati dalla descrizione
senza = items({})
con = items({"trust_signals": True})
CAMPI = ("verdict", "age_days", "n_contradictions")
segnali = {
    "n_senza": len(senza), "n_con": len(con),
    "presenti_senza": [c for c in CAMPI if senza and c in senza[0]],
    "presenti_con": [c for c in CAMPI if con and c in con[0]],
    "chiavi_con": sorted(con[0].keys()) if con else [],
}

print(json.dumps({"scritti": scritti, "chiavi": CHIAVI, "righe": righe,
                  "segnali": segnali}, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO, DOMANDA],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-500:]}")
        return 1
    d = json.loads(p.stdout.strip().splitlines()[-1])

    print("  SCRITTI:", ", ".join(
        f"{s['status']}" + (f" (da {s['qb']})" if s["qb"] else "")
        for s in d["scritti"]))
    print(f"  CHIAVI DI UN ITEM (lette, non indovinate): {d['chiavi']}")

    print(f"\n  ② min_status — {'caso':<32} {'n':>3}  stati serviti")
    print("  " + "-" * 74)
    for r in d["righe"]:
        print(f"     {r['caso']:<32} {r['n']:>3}  {', '.join(r['stati']) or '-'}")

    base = next((r for r in d["righe"] if "CONTROLLO" in r["caso"]), {"n": -1})
    print(f"\n  [1] CONTROLLO — senza `min_status` lo store risponde: n={base['n']}")
    if base["n"] <= 0:
        print("      CONTROLLO CADUTO: nessun fatto torna nemmeno senza pavimento")
        print("      di fiducia ⇒ ogni zero qui sotto sarebbe illeggibile.")
        print("      NESSUN VERDETTO.")
        return 1

    basso = next((r for r in d["righe"] if "legacy_unverified" in r["caso"]),
                 {"n": -1})
    print(f"  [2] POPOLAZIONE OPPOSTA — il livello PIU' BASSO non deve "
          f"scartare: n={basso['n']} contro {base['n']}")
    if basso["n"] != base["n"]:
        print("      ⚠️ il rank 0 scarta comunque ⇒ il campo non implementa la")
        print("      gerarchia che dichiara. E' un REPERTO, ma rende non")
        print("      interpretabili le righe intermedie: nessun verdetto su di esse.")

    alto = next((r for r in d["righe"] if "verified" == r["caso"].split("=")[-1]),
                {"n": -1, "stati": []})
    print("\n  ══ VERDETTO ② ══")
    if alto["n"] == 0:
        print(f"     🟢 `min_status=verified` scarta tutto ({alto['n']}): la")
        print("     gerarchia e' applicata — nessun `model_claim` la supera.")
    elif alto["n"] > 0:
        print(f"     🔴 `min_status=verified` lascia passare {alto['n']} riga/e "
              f"di stato {alto['stati']}:")
        print("     la promessa «rows with rank lower than min_status are")
        print("     dropped» non regge sul livello piu' alto.")

    s = d["segnali"]
    print("\n  ══ VERDETTO ① — trust_signals ══")
    print(f"     senza: n={s['n_senza']} campi presenti fra i tre promessi: "
          f"{s['presenti_senza'] or 'nessuno'}")
    print(f"     con:   n={s['n_con']} campi presenti fra i tre promessi: "
          f"{s['presenti_con'] or 'nessuno'}")
    if len(s["presenti_con"]) == 3 and not s["presenti_senza"]:
        print("     🟢 LA PROMESSA REGGE ED E' SIMMETRICA: i tre campi ci sono")
        print("     con `True` e nessuno con `False`.")
    elif len(s["presenti_con"]) == 3:
        print("     🟡 i tre campi ci sono con `True`, ma ALCUNI ci sono anche")
        print(f"     senza ({s['presenti_senza']}): il default non e' quello")
        print("     che la descrizione chiama «legacy payload».")
    else:
        mancanti = [c for c in ("verdict", "age_days", "n_contradictions")
                    if c not in s["presenti_con"]]
        print(f"     🔴 CON `trust_signals=True` MANCANO: {mancanti}")
        print(f"     chiavi effettive dell'item: {s['chiavi_con']}")
        print("     ⇒ lo schema nomina campi che la porta non consegna.")

    print("\n  ⚠️ LIMITI: due fatti, una domanda, uno store nuovo. NON misura")
    print("     `provisional` (non ottenibile da questa porta), ne' i valori")
    print("     dei `verdict`: solo la PRESENZA dei campi promessi e il")
    print("     comportamento del pavimento di fiducia sugli stati ottenibili.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
