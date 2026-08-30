"""L4.2 sbaglia l'accoppiamento numero-grandezza su una source in forma `k=v`?

NASCE DA UNA RICEVUTA VERA (31/08 01:45). Salvando un fatto con source
`quarantined_by v0.7.0=0 main=20`, il layer ha avvisato:

    L4.2 — il claim riusa un numero della fonte riferendolo a un'altra
    grandezza: 0 qui e' «occorrenze», nella fonte «main»

Ma nella fonte lo **0** appartiene a `v0.7.0`: `main` e' la chiave del **20**.
L'ipotesi e' che su `chiave=valore` il layer prenda la parola che SEGUE il
numero invece della chiave che lo precede.

⚠️ UN CASO NON E' UNA FREQUENZA (lezione pagata due volte il 30/08: un A/B
pulito dimostra che un meccanismo esiste, non quanto pesa). Percio' il banco
NON si ferma alla riproduzione: gira la STESSA affermazione su due forme di
source — `k=v` e prosa — e su piu' coppie, e conta.

Fuori da pytest, store temporaneo, zero rete.

    python docs/stato-reale/banchi/ws7-l42-accoppia-il-numero-alla-chiave-che-segue.py
"""

from __future__ import annotations

import os
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_l42_")

from verimem import Memory  # noqa: E402  (dopo l'isolamento dello store)

#: la stessa coppia di misure, detta in due forme. Il claim e' IDENTICO.
#: ⚠️ Le prime quattro erano tutte `<campo> v0.7.0=N main=M`: **quattro varianti
#: della stessa frase**, cioe' un banco omogeneo che dice 4/4 senza aver provato
#: niente di diverso (e' la forma «un banco senza riferimento» che ho appena
#: messo in memoria). Le sei sotto cambiano dominio, unita', ordine di grandezza
#: e nomi delle chiavi: se l'effetto e' della FORMA `k=v` deve reggere anche li'.
COPPIE = [
    ("quarantined_by", "v0.7.0", 0, "main", 20),
    ("withheld_despite_judge", "v0.7.0", 0, "main", 6),
    ("floor_applied_by", "v0.7.0", 0, "main", 3),
    ("confidence_tier", "v0.7.0", 23, "main", 41),
    ("la latenza", "p50", 40, "p95", 1200),
    ("la suite", "passati", 17, "falliti", 3),
    ("il corpus", "italiano", 512, "inglese", 7431),
    ("il disco", "usato_gb", 44, "libero_gb", 211),
    ("la coda", "entrati", 48, "usciti", 26),
    ("il gate", "ammessi", 260, "quarantinati", 40),
]


def _kv(nome: str, k1: str, v1: int, k2: str, v2: int) -> str:
    return f"{nome} {k1}={v1} {k2}={v2}"


def _prosa(nome: str, k1: str, v1: int, k2: str, v2: int) -> str:
    return (f"Il campo {nome} ha {v1} occorrenze in {k1}. "
            f"Il campo {nome} ha {v2} occorrenze in {k2}.")


def giudica(m: Memory, claim: str, source: str, topic: str) -> tuple[str, bool]:
    """Ritorna (status, l42_ha_avvisato)."""
    r = m.add(claim, source=source, topic=topic)
    testo = " ".join(str(w) for w in (r.get("warnings") or []))
    return str(r.get("status")), "L4.2" in testo


def main() -> int:
    m = Memory()
    print(f"  {'campo':<24} {'forma k=v':>12} {'prosa':>12}")
    colpiti = {"kv": 0, "prosa": 0}
    for i, (nome, k1, v1, k2, v2) in enumerate(COPPIE):
        claim = (f"Il campo {nome} ha {v1} occorrenze in {k1} "
                 f"e {v2} occorrenze in {k2}.")
        s_kv, w_kv = giudica(m, claim, _kv(nome, k1, v1, k2, v2), f"banco/l42-kv-{i}")
        s_pr, w_pr = giudica(m, claim, _prosa(nome, k1, v1, k2, v2), f"banco/l42-pr-{i}")
        colpiti["kv"] += w_kv
        colpiti["prosa"] += w_pr
        print(f"  {nome:<24} {('L4.2 ' + s_kv) if w_kv else ('— ' + s_kv):>12}"
              f" {('L4.2 ' + s_pr) if w_pr else ('— ' + s_pr):>12}")
    n = len(COPPIE)
    print(f"\n  L4.2 avvisa su k=v:   {colpiti['kv']}/{n}")
    print(f"  L4.2 avvisa su prosa: {colpiti['prosa']}/{n}")
    print(f"\n  store temporaneo: {os.environ['HIPPO_DATA_DIR']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
