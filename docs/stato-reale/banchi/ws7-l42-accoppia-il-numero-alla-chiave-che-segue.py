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


#: ⚠️⚠️ LA FORMA CHE CONTA NON ERA QUELLA CHE AVEVO SOTTO MANO. Contati i
#: `grounding_span` reali dello store (7343 pieni, `mode=ro`):
#:
#:     chiave=numero     27,1%      <- l'unica che il banco provava
#:     chiave: numero    45,9%      <- la forma DOMINANTE, non provata
#:     almeno una        61,4%
#:
#: Avevo costruito il banco sulla forma della MIA source, non su quella che il
#: corpus usa davvero: lo stesso errore del criterio cieco scelto sulla
#: dimensione sbagliata. Se l'effetto e' della forma tabellare deve comparire
#: anche coi due punti — e se NON compare, la portata del difetto si dimezza.
def _due_punti(nome: str, k1: str, v1: int, k2: str, v2: int) -> str:
    return f"{nome}\n  {k1}: {v1}\n  {k2}: {v2}"


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
    FORME = (("k=v", _kv), ("k: v", _due_punti), ("prosa", _prosa))
    print(f"  {'campo':<24} " + " ".join(f"{nome:>8}" for nome, _ in FORME))
    colpiti = {nome: 0 for nome, _ in FORME}
    quarantene = {nome: 0 for nome, _ in FORME}
    for i, (nome, k1, v1, k2, v2) in enumerate(COPPIE):
        claim = (f"Il campo {nome} ha {v1} occorrenze in {k1} "
                 f"e {v2} occorrenze in {k2}.")
        celle = []
        for forma, rendi in FORME:
            st, w = giudica(m, claim, rendi(nome, k1, v1, k2, v2),
                            f"banco/l42-{forma}-{i}")
            colpiti[forma] += w
            quarantene[forma] += (st == "quarantined")
            celle.append("L4.2" if w else "—")
        print(f"  {nome:<24} " + " ".join(f"{c:>8}" for c in celle))
    n = len(COPPIE)
    print()
    for forma, _ in FORME:
        print(f"  L4.2 avvisa su {forma:<6} {colpiti[forma]:>3}/{n}"
              f"   (quarantene: {quarantene[forma]}/{n})")
    print(f"\n  store temporaneo: {os.environ['HIPPO_DATA_DIR']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
