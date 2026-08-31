"""«abstention instead of hallucination» — la QUARTA promessa del Summary, verificata DA ME.

PERCHE' RIFARE UNA MISURA GIA' FATTA. @ws1 (31/08 01:45) ha misurato che
`search` non astiene mai — 18 sonde su 18 servite — contro 1 su 18 di
`explain`, e che la differenza e' di CONTRATTO, documentata nel docstring.
In `LANT-130` io **cito** quel numero dentro una mia tabella: e la regola del
registro dice che un difetto misurato una volta va **rimisurato** prima di
ripeterlo. Chi mette un numero in una tabella lo firma.

⚠️ QUESTO NON E' UNA REPLICA. @ws1 ha 18 sonde su un corpus di 401 frasi di
terzi; io ho 5 sonde su uno store da 3 fatti. **Con n=5 l'intervallo e'
enorme** (5/5 → IC95 ~[57–100]): il risultato utile qui non e' una
proporzione, e' **BINARIO — l'asimmetria fra le due porte c'e' o non c'e'**.
Se c'e', e' una conferma indipendente qualitativa; se non c'e', c'e' qualcosa
da capire e il numero in tabella va sospeso.

Fuori da pytest, store temporaneo, zero rete.

    python docs/stato-reale/banchi/ws7-la-quarta-promessa-verificata-da-me.py
"""

from __future__ import annotations

import os
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_astens_")

from verimem import Memory  # noqa: E402

#: lo store sa SOLO queste tre cose.
FONTE = ("Il bilancio 2025 del comune di Ozzano riporta una spesa corrente di "
         "4,2 milioni di euro, investimenti per 1,8 milioni e un avanzo di "
         "0,3 milioni.")
FATTI = [
    "La spesa corrente del comune di Ozzano nel 2025 e' di 4,2 milioni di euro.",
    "Gli investimenti del comune di Ozzano nel 2025 sono di 1,8 milioni di euro.",
    "L'avanzo del comune di Ozzano nel 2025 e' di 0,3 milioni di euro.",
]

#: SONDE: domande la cui risposta NON e' nello store. Devono essere
#: PLAUSIBILI e dello stesso dominio — una domanda su un altro pianeta la
#: respinge anche un retriever cieco, e il banco sarebbe troppo facile.
SONDE = [
    "Quanti dipendenti ha il comune di Ozzano?",
    "Qual e' il debito residuo del comune di Ozzano?",
    "Quanto ha speso il comune di Ozzano per la scuola nel 2025?",
    "Chi e' il sindaco del comune di Ozzano?",
    "Qual e' la spesa corrente del comune di Ozzano nel 2024?",
]
#: CONTROLLO POSITIVO: se anche queste non tornano, il banco misura il
#: retriever rotto, non l'astensione.
CONTROLLI = [
    "Quanto e' la spesa corrente del comune di Ozzano?",
    "Quanto sono gli investimenti del comune di Ozzano?",
]

#: SONDE TEMPORALI — l'ENTITA' c'e' in memoria, l'ANNO no. Nate da un caso
#: singolo visto nel primo giro: alla domanda sul 2024 `explain` ha servito il
#: fatto del 2025 con `abstained=False` e nessun caveat. ⚠️ **Un caso non e'
#: una frequenza** (lezione pagata due volte il 30/08): cinque sonde per
#: vedere se il pattern regge.
#: 📌 E NON E' UN'ALLUCINAZIONE: il testo servito dice «nel 2025», quindi si
#: autoqualifica e il lettore puo' accorgersene. E' un'ASTENSIONE MANCATA su
#: una dimensione — il tempo — che il prodotto MISURA (`asserted_at` e' fra le
#: chiavi che serve) e che qui non usa per astenersi.
TEMPORALI = [
    "Qual e' la spesa corrente del comune di Ozzano nel 2024?",
    "Qual e' la spesa corrente del comune di Ozzano nel 2019?",
    "Quanto erano gli investimenti del comune di Ozzano nel 2023?",
    "Qual era l'avanzo del comune di Ozzano nel 2020?",
    "Qual e' la spesa corrente prevista del comune di Ozzano nel 2030?",
]


def serve(out) -> bool:
    """La porta ha restituito qualcosa, o si e' astenuta?"""
    if isinstance(out, dict):
        if "n_facts" in out:
            return bool(out.get("n_facts"))
        if "results" in out:
            return bool(out.get("results"))
    return bool(out)


def main() -> int:
    m = Memory()
    for f in FATTI:
        m.add(f, source=FONTE, topic="banco/astensione")
    print(f"  store: {len(FATTI)} fatti\n")

    PORTE = [("search", lambda q: m.search(q, k=3)),
             ("explain", lambda q: m.explain(q))]

    for nome, gruppo in (("SONDE (risposta NON in memoria)", SONDE),
                         ("TEMPORALI (entita' SI', anno NO)", TEMPORALI),
                         ("CONTROLLI (risposta IN memoria)", CONTROLLI)):
        print(f"  {nome}")
        conta = {p: 0 for p, _ in PORTE}
        for q in gruppo:
            riga = []
            for porta, chiama in PORTE:
                try:
                    s = serve(chiama(q))
                except Exception as e:  # noqa: BLE001
                    s = None
                    riga.append(f"{porta}=ERR({type(e).__name__})")
                    continue
                conta[porta] += bool(s)
                riga.append(f"{porta}={'SERVE' if s else 'astiene'}")
            print(f"     {q[:52]:<54} {' · '.join(riga)}")
        print(f"     → servite: " + " · ".join(
            f"{p} {conta[p]}/{len(gruppo)}" for p, _ in PORTE) + "\n")

    print(f"  store temporaneo: {os.environ['HIPPO_DATA_DIR']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
