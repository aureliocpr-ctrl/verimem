"""`adjudication` sulle due porte: stesso claim, stessa fonte, campi a confronto.

DA DOVE VIENE. Il commento a `mcp_server.py:13234` racconta una cura del 28/08 e
la sua ragione, ed e' la stessa frase che questo banco esiste per verificare:

    «Il docstring di `_adjudication` dice "the write verdict, ALWAYS returned to
     the caller"; quello di `tests/test_adjudication_receipt.py` dice "EVERY
     write returns a VISIBLE verdict". Entrambe presidiate — e gli otto test di
     quel file passano tutti da `Memory(...)`, cioe' dall'SDK. Misurato il 28/08
     …: SDK restituiva `adjudication` con 8 campi, MCP restituiva 14 chiavi di
     primo livello e non quella. **Una promessa presidiata su una porta sola non
     e' presidiata: e' vera dove il test guarda.**»

⇒ La cura ha aggiunto il campo su MCP. **La domanda che resta e' un'altra**, ed e'
quella che @ws2 ha dovuto RITIRARE il 30/08 perche' non misurata (`F3-③`,
`adjudication.disposition`): **i campi sono gli STESSI sulle due porte?** Un
campo presente ma piu' povero e' la stessa classe di difetto un giro dopo.

LA PREDIZIONE, scritta prima di eseguire: **le due porte danno le stesse
CHIAVI**, perche' entrambe chiamano la stessa `client._adjudication`. Il rischio
sta negli ARGOMENTI: MCP la chiama con `disposition=` dedotta da
`fact.status`, l'SDK dal proprio percorso — **due derivazioni della stessa
grandezza sono due occasioni di divergere**, ed e' cio' che questo banco guarda
piu' da vicino.

CONDIZIONE DI FALSIFICAZIONE: chiavi diverse, o `disposition` diversa a parita'
di esito, e la promessa «ALWAYS returned to the caller» vale meno di quanto dice.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: il caso deve produrre **una quarantena**
su entrambe le porte. Se il claim passasse, confronterei due verdetti «admitted»
— cioe' il caso in cui `disposition` ha meno da dire, e un'uguaglianza li'
non direbbe nulla sul caso che conta.
═══════════════════════════════════════════════════════════════════════════════

REGIME: due processi separati, store TEMPORANEO ciascuno, stesso claim e stessa
fonte (che NEGA), `validate='full'`. Lo store di Aurelio non e' toccato. Il
primo write di ogni processo paga il caricamento del giudice (~33 s misurati il
30/08): il banco impiega circa un minuto ed e' normale.

    python docs/stato-reale/banchi/ws3-adjudication-le-due-porte-dicono-la-stessa-cosa.py
"""

from __future__ import annotations

import json
import subprocess
import sys

CLAIM = "La penale e' di 500 euro al giorno."
FONTE = "Il contratto fissa la penale in 120 euro al giorno."

FIGLIO = r'''
import asyncio, json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
porta, claim, fonte = sys.argv[1:4]
if porta == "sdk":
    from verimem.client import Memory
    r = Memory().add(claim, topic="adj/x", source=fonte, validate="full")
else:
    from verimem import mcp_server
    r = json.loads(asyncio.run(mcp_server._call_tool_impl(
        "hippo_remember",
        {"proposition": claim, "topic": "adj/x", "source": fonte,
         "validate": "full"}))[0].text)
adj = r.get("adjudication")
print(json.dumps({"status": r.get("status"),
                  "adj_presente": adj is not None,
                  "adj": adj if isinstance(adj, dict) else None},
                 default=str, ensure_ascii=False))
'''


def _porta(nome: str) -> dict:
    p = subprocess.run([sys.executable, "-c", FIGLIO, nome, CLAIM, FONTE],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        raise RuntimeError(f"exit={p.returncode}: {p.stderr.strip()[-200:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def main() -> int:
    print("  PROMESSA (`client._adjudication`): «the write verdict, ALWAYS")
    print("  returned to the caller». Curata su MCP il 28/08; qui si guarda se")
    print("  le due porte dicono la STESSA cosa, non solo se il campo c'e'.\n")

    letto = {}
    for nome in ("sdk", "mcp"):
        try:
            letto[nome] = _porta(nome)
        except RuntimeError as exc:
            print(f"  {nome.upper()}: PROCESSO MORTO {exc}")
            return 1
        d = letto[nome]
        print(f"  {nome.upper():<4} status={str(d['status']):<13} "
              f"adjudication presente: {d['adj_presente']}")

    a, m = letto["sdk"], letto["mcp"]

    print("\n  [1] CONTROLLO — entrambe le porte devono QUARANTINARE: "
          f"{'SI' if a['status'] == m['status'] == 'quarantined' else 'NO'}")
    if not (a["status"] == m["status"] == "quarantined"):
        print("      CONTROLLO CADUTO: senza una quarantena confronterei due")
        print("      verdetti «admitted», dove `disposition` ha meno da dire.")
        print("      NESSUN VERDETTO.")
        return 1

    if not (a["adj"] and m["adj"]):
        print("\n  ══ VERDETTO ══")
        print("     🔴 IL CAMPO MANCA SU UNA DELLE DUE PORTE: "
              f"sdk={a['adj_presente']} · mcp={m['adj_presente']}")
        return 0

    ka, km = set(a["adj"]), set(m["adj"])
    print(f"\n  [2] CHIAVI  sdk={len(ka)}  mcp={len(km)}")
    print(f"      solo SDK: {sorted(ka - km) or '-'}")
    print(f"      solo MCP: {sorted(km - ka) or '-'}")

    print("\n  [3] I VALORI SUI CAMPI COMUNI")
    diverse = []
    for k in sorted(ka & km):
        va, vm = a["adj"].get(k), m["adj"].get(k)
        segno = "=" if va == vm else "≠"
        if va != vm:
            diverse.append(k)
        print(f"      {k:<18} {segno}  sdk={str(va)[:34]:<34} mcp={str(vm)[:34]}")

    print("\n  ══ VERDETTO ══")
    if ka == km and not diverse:
        print("     🟢 LE DUE PORTE DICONO LA STESSA COSA: stesse chiavi, stessi")
        print("     valori. La promessa «ALWAYS returned to the caller» vale su")
        print("     entrambe, e `adjudication.disposition` si puo' usare senza")
        print("     chiedersi da quale porta arrivi il fatto.")
    elif ka == km:
        print(f"     🟡 STESSE CHIAVI, VALORI DIVERSI su: {diverse}")
        print("     ⇒ il campo c'e' su entrambe e non dice lo stesso: chi lo")
        print("     legge deve sapere da quale porta viene il fatto.")
    else:
        print("     🔴 CHIAVI DIVERSE ⇒ la cura del 28/08 ha portato il campo,")
        print("     non tutto il suo contenuto: e' la stessa classe di difetto")
        print("     un giro dopo — «vera dove il test guarda».")

    print("\n  ⚠️ LIMITI: un claim, una fonte, italiano, una sola disposition")
    print("     (`quarantined`). Non dice nulla sul caso `admitted`, ne' sui")
    print("     valori che dipendono dal giudice (punteggio, soglia) quando il")
    print("     giudice non e' lo stesso fra le due corse.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
