"""«a SUPERSEDED fact is refused (never resurrects a retired value)»: la guardia
che il file di test NOMINA e non esercita.

LA PROMESSA, dalla descrizione di `hippo_quarantine_restore`: *«SAFETY (same
guards as the SDK): **a SUPERSEDED fact is refused (never resurrects a retired
value)** and the proposition is RE-SCREENED for prompt injection»*.

SWEEP DELLA COPERTURA, fatto PRIMA (regola nata stanotte):

    tests/test_mcp_quarantine_tools.py — 5 celle:
      log_lists_the_blocked_fact · restore_brings_the_fact_back
      restore_refuses_injection_payload · restore_refuses_injection_in_TOPIC
      restore_unknown_id_is_clean_false

⇒ **L'iniezione e' presidiata due volte; il SUPERSEDUTO nessuna.** E non e'
sfuggito per caso: il docstring di quel file la NOMINA (*«guards the SDK
restore ships: a SUPERSEDED fact…»*) — quindi chi l'ha scritto la conosceva.
🪞 *Nominare una guardia non e' presidiarla*, ed e' la stessa forma di
«nominare una classe non chiude le sue istanze».

🔑 PERCHE' QUESTA MISURA CONTA PIU' DELLE ALTRE DI STANOTTE. La mia tesi delle
01:38 dice: *nei punti RIPETUTI si rompono i meccanismi; nei punti UNICI
restano lacune di cio' che la porta DICE.* Il ripristino e' un **punto unico**
e questo e' un **meccanismo**, non una descrizione. ⇒ **Se e' rotto, la mia
tesi cade** — ed e' esattamente per questo che sono andato a cercarlo.

E se fosse rotto sarebbe grave di suo: un valore RITIRATO che rientra nel
recall e' il prodotto che serve come corrente un fatto superato.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: un fatto quarantinato e NON superseduto
deve essere ripristinato. Se il ripristino rifiutasse anche quello, il rifiuto
sul superseduto non proverebbe la guardia — proverebbe che la porta non
ripristina niente.
⚠️ E IL CRITERIO E' LA RICEVUTA, non un conteggio: si legge `restored` e
`refused_reason`, che la porta dichiara di restituire.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO, porte MCP in-process, giudice locale
assente per costruzione. Lo store di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-il-ripristino-e-il-valore-ritirato.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FIGLIO = r'''
import asyncio, json, os, tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem import mcp_server

def chiama(nome, args):
    return json.loads(asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)

# Due auto-affermazioni: L1 le quarantina entrambe (nessuna prova a sostegno).
a = chiama("hippo_remember", {
    "proposition": "Ho verificato che il collaudo del capannone Alfa e' concluso.",
    "topic": "ripr/x"})
b = chiama("hippo_remember", {
    "proposition": "Ho verificato che il collaudo del capannone Beta e' concluso.",
    "topic": "ripr/y"})

id_a, id_b = a.get("fact_id") or a.get("id"), b.get("fact_id") or b.get("id")
stati = {"a": a.get("status"), "b": b.get("status")}

# A viene RITIRATO: superseduto da B.
supersessione = None
try:
    ag = mcp_server._ag()
    ag.semantic.supersede(id_a, id_b, principal="banco:ws3", reason="ritiro")
    f = ag.semantic.get(id_a)
    supersessione = getattr(f, "superseded_by", None)
except Exception as e:
    supersessione = f"ERRORE {type(e).__name__}: {str(e)[:80]}"

r_super = chiama("hippo_quarantine_restore", {"fact_id": id_a})
r_pulito = chiama("hippo_quarantine_restore", {"fact_id": id_b})

print(json.dumps({
    "stati": stati, "id_a": id_a, "id_b": id_b,
    "a_superseduto_da": str(supersessione),
    "restore_superseduto": {k: r_super.get(k) for k in
                            ("ok", "restored", "refused_reason", "error")},
    "restore_pulito": {k: r_pulito.get(k) for k in
                       ("ok", "restored", "refused_reason", "error")},
}, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-500:]}")
        return 1
    d = json.loads(p.stdout.strip().splitlines()[-1])

    print(f"  stati alla scrittura      : {d['stati']}")
    print(f"  A ({d['id_a']}) superseduto da: {d['a_superseduto_da']}")
    print(f"\n  restore del SUPERSEDUTO   : {d['restore_superseduto']}")
    print(f"  restore del PULITO        : {d['restore_pulito']}")

    if "quarantined" not in str(d["stati"].values()):
        print("\n  ⚠️ PREMESSA CADUTA: i fatti non sono stati quarantinati, quindi")
        print("  non c'e' niente da ripristinare. NESSUN VERDETTO.")
        return 1

    pulito_ok = bool(d["restore_pulito"].get("restored"))
    print(f"\n  [1] CONTROLLO — il quarantinato NON superseduto viene "
          f"ripristinato: {'SI' if pulito_ok else 'NO'}")
    if not pulito_ok:
        print("      CONTROLLO CADUTO: la porta non ripristina nemmeno un fatto")
        print("      pulito ⇒ un rifiuto sul superseduto non proverebbe la")
        print("      guardia. NESSUN VERDETTO.")
        return 1

    if d["a_superseduto_da"] in ("None", "", "null") or \
            d["a_superseduto_da"].startswith("ERRORE"):
        print(f"\n  ⚠️ SECONDA PREMESSA CADUTA: A non risulta superseduto "
              f"({d['a_superseduto_da']}) ⇒ il caso da misurare non si presenta.")
        print("  NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    rifiutato = not d["restore_superseduto"].get("restored")
    motivo = str(d["restore_superseduto"].get("refused_reason") or "")
    if rifiutato:
        print("     🟢 LA GUARDIA REGGE: il fatto RITIRATO non viene")
        print(f"     resuscitato. motivo dichiarato: «{motivo[:70]}»")
        print("     ⚠️ E la mia tesi delle 01:38 SOPRAVVIVE a un secondo")
        print("     tentativo mirato: cercavo un MECCANISMO rotto in un punto")
        print("     UNICO, e questo non lo e'.")
        if not motivo:
            print("     📌 Ma la ricevuta NON dice PERCHE': `refused_reason` e'")
            print("     vuoto dove la descrizione lo promette. Lacuna di cio' che")
            print("     la porta DICE — la stessa forma di tutte le altre.")
    else:
        print("     🔴 LA GUARDIA NON REGGE: un fatto SUPERSEDUTO e' stato")
        print("     ripristinato nel recall. Un valore ritirato torna servibile.")
        print("     ⚠️ E LA MIA TESI DELLE 01:38 CADE: e' un MECCANISMO rotto in")
        print("     un punto UNICO, che e' esattamente il controesempio che")
        print("     avevo dichiarato di cercare.")

    print("\n  ⚠️ LIMITI: due fatti, una supersessione, uno store nuovo. NON")
    print("     misura la seconda guardia (l'iniezione), che ha gia' due celle,")
    print("     ne' un fatto AMMESSO e poi superseduto — qui entrambi entrano")
    print("     quarantinati da L1, che e' il caso che il ripristino serve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
