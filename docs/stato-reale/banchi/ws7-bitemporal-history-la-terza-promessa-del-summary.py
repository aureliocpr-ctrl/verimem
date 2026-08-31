"""«bi-temporal history» — la TERZA delle quattro promesse del Summary pubblicato.

Il Summary di `v0.7.0:pyproject.toml` — la riga che `pip show verimem` stampa e
che apre la pagina PyPI — promette quattro cose. Stato prima di questo banco:

    ① gated writes                      LANT-33   regge su 3 porte
    ② provenance on every read          banco ws7 4/4 porte pubbliche
    ③ bi-temporal history               ← QUESTO
    ④ abstention instead of hallucination  @ws1   NON regge su `search`

Il README (v0.7.0:120) la esplicita: *«facts carry both when it happened and
when we learned it. Query the past (`as_of`), see transitions ("changed from X
to Y on date Z"), and audit every revision.»* ⇒ **tre affermazioni distinte**,
e si provano separatamente:

    (a) i due tempi ESISTONO e sono distinti
    (b) `as_of` interroga il passato
    (c) la transizione e' visibile (la vecchia versione resta, non sovrascritta)

⚠️ Questa e' una promessa CONGIUNTIVA: cade se cade uno dei tre pezzi. Provarne
uno solo e dichiararla verde sarebbe la stessa cosa che chiamare «provenienza»
la presenza di un `id`.

Fuori da pytest, store temporaneo, zero rete.

    python docs/stato-reale/banchi/ws7-bitemporal-history-la-terza-promessa-del-summary.py
"""

from __future__ import annotations

import os
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_bitemp_")

from verimem import Memory  # noqa: E402

FONTE = ("Il listino 2025 di Acme fissa il prezzo della licenza Pro a 100 euro. "
         "Dal primo luglio 2025 il prezzo della licenza Pro passa a 150 euro.")
PRIMO = "Il prezzo della licenza Pro di Acme e' di 100 euro."
SECONDO = "Il prezzo della licenza Pro di Acme e' di 150 euro."
DOMANDA = "Quanto costa la licenza Pro di Acme?"


def main() -> int:
    m = Memory()
    a = m.add(PRIMO, source=FONTE, topic="banco/bitemporale")
    b = m.add(SECONDO, source=FONTE, topic="banco/bitemporale")
    print(f"  scrittura 1: {a.get('status')}   scrittura 2: {b.get('status')}\n")

    esiti: dict[str, bool] = {}

    # (a) i DUE tempi esistono e sono distinti come campi
    righe = m.search(DOMANDA, k=5)
    campi = set()
    for r in righe:
        campi |= set(r.keys()) if isinstance(r, dict) else set(vars(r))
    quando_successo = {c for c in campi if c in ("asserted_at", "valid_from",
                                                 "valid_until", "happened_at")}
    quando_saputo = {c for c in campi if c in ("created_at", "learned_at",
                                               "recorded_at")}
    esiti["(a) due tempi distinti"] = bool(quando_successo and quando_saputo)
    print(f"  (a) quando E' SUCCESSO : {sorted(quando_successo) or 'NESSUNO'}")
    print(f"      quando l'ABBIAMO SAPUTO: {sorted(quando_saputo) or 'NESSUNO'}")

    # (b) `as_of` interroga il passato: la porta lo accetta e cambia la risposta?
    #: ⚠️ DUE FORME, e la differenza e' il reperto. La firma dichiara
    #: `as_of: float | str | None`, quindi una STRINGA e' un input legittimo —
    #: e la forma piu' ovvia per un umano che vuole «interrogare il passato» e'
    #: una data ISO. Provate entrambe: se il float funziona e la data no, il
    #: pezzo non e' rotto ma la porta chiede un formato che il README non dice.
    #: (La prima stesura provava SOLO la data ISO e avrei contato «(b) 🔴»
    #: attribuendo al prodotto un mio errore di chiamata.)
    import time
    passato_ts = time.time() - 86400 * 365      # un anno fa, in secondi
    ora = m.explain(DOMANDA)
    n_ora = ora.get("n_facts") if isinstance(ora, dict) else None
    n_pas = None
    for etichetta, valore in (("float (timestamp)", passato_ts),
                              ("stringa ISO '2024-01-01'", "2024-01-01")):
        try:
            r_p = m.explain(DOMANDA, as_of=valore)
            n = r_p.get("n_facts") if isinstance(r_p, dict) else None
            if "float" in etichetta:
                n_pas = n
            print(f"\n  (b) as_of {etichetta:<26} → n_facts={n}   (oggi {n_ora})")
        except Exception as e:  # noqa: BLE001
            print(f"\n  (b) as_of {etichetta:<26} → {type(e).__name__}: "
                  f"{str(e)[:70]}")
    esiti["(b) as_of interroga il passato"] = (n_pas is not None
                                               and n_pas < (n_ora or 0))

    # (c) la transizione e' visibile: la vecchia versione resta e si sa da cosa
    #     e' stata rimpiazzata. Il parametro giusto e' `with_history`, letto
    #     dalla FIRMA — la prima stesura ne aveva inventato uno inesistente.
    ritirate = [r for r in righe if (r.get("superseded_by")
                                     if isinstance(r, dict) else None)]
    try:
        tutte = list(m.search(DOMANDA, k=5, with_history=True))
    except Exception as e:  # noqa: BLE001
        tutte = []
        print(f"  (c) with_history ERRORE {type(e).__name__}: {str(e)[:70]}")
    storie = [h for r in tutte
              for h in (m.history(r["id"]) if isinstance(r, dict) and r.get("id") else [])]
    esiti["(c) transizione visibile"] = bool(ritirate) or len(tutte) > len(righe) \
        or len(storie) > len(tutte)
    print(f"\n  (c) default: {len(righe)} righe · {len(ritirate)} con superseded_by"
          f" · with_history: {len(tutte)} · revisioni da history(): {len(storie)}")

    print()
    for k, v in esiti.items():
        print(f"  {'✅' if v else '🔴'} {k}")
    ok = sum(esiti.values())
    print(f"\n  «bi-temporal history»: {ok}/{len(esiti)} pezzi su tre "
          f"— la promessa e' CONGIUNTIVA, serve 3/3")
    print(f"\n  store temporaneo: {os.environ['HIPPO_DATA_DIR']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
