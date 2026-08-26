# -*- coding: utf-8 -*-
"""«Il paziente e' DECEDUTO» -> «e' stato DIMESSO» passa. La causa radice, e c'e' gia' la cura.

Catena delle misure che porta qui, tutte del 26/08:
  · la contraddizione IMPLICITA passa 3/10 in IT e 0/10 in EN;
  · il giudice NON e' cieco: `grounding_score=95.92 judged=True`;
  · su venti coppie, i sei casi ammessi passano TUTTI da `L3-supersession` o
    `L3-coexistence` ⇒ non e' un giudizio sbagliato, e' un ROUTING sbagliato.

Questo banco chiede PERCHE' il routing sbagli, e la risposta e' nei due
docstring del prodotto — non e' una mia congettura.

`supersession_policy.classify_write_relation` dichiara::

    «"evolution" iff new_fact is the SAME canonical source as old_fact and
     strictly NEWER in VALID-TIME (asserted_at when present, else created_at);
     otherwise "conflict" … Conservative: ANY AMBIGUITY -> CONFLICT»

Le due condizioni, misurate una per una::

    canonical_source_of(old) = 'user'    canonical_source_of(new) = 'user'
    ⇒ la PRIMA e' sempre vera per le scritture anonime. Lo dice il docstring
      stesso: «unsourced writes collapse to the "user" bucket».

    classify_write_relation, con verified_by=None su entrambi:
      SENZA asserted_at  (il caso reale)       -> **evolution**
      con asserted_at UGUALE                   -> conflict
      con asserted_at PRECEDENTE (backfill)    -> conflict

⇒ 🔑 IL CRITERIO GIUSTO ESISTE E FUNZIONA: dando ai due fatti lo stesso
istante di validita', la coppia viene classificata CONFLITTO e va al giudice.
Il difetto e' che `asserted_at` e' quasi sempre `None`, e allora `_when_true`
ricade su `created_at` — e il candidato ha `created_at = adesso` per
costruzione, quindi risulta SEMPRE «strictly newer».

⇒ 🔑 E QUI IL DOCSTRING NON DESCRIVE IL CODICE, che e' il mio perimetro:
«Conservative: any ambiguity -> conflict» promette che l'incertezza porti al
conflitto. Ma senza `asserted_at` non c'e' un'ambiguita' RISOLTA verso il
conflitto: c'e' un FALLBACK che INVENTA un ordine e produce «evolution». La
riga piu' conservativa del file e' anche quella che il codice non applica.
📌 Il file lo sa a meta': `_when_true` porta un commento sul BACKFILL («ordering
by write-time alone would call a backfill a newer evolution», opus critic
2026-07-19) — cioe' il rischio del fallback era stato visto, e la cura
individuata e' proprio `asserted_at`. Che pero' nessuna delle porte riempie.

⛔ COSA QUESTO BANCO NON DICE: non propone di rimuovere il fallback. Toglierlo
manderebbe a conflitto ogni coppia senza `asserted_at`, cioe' quasi tutte, e i
VERI ne pagherebbero il prezzo — nel banco degli antonimi due veri erano gia'
rifiutati senza alcuna cura. **Chi tocca questo punto misuri ENTRAMBE le
popolazioni**, o cura una classe e ne rompe un'altra.

Regime: funzioni pure di `supersession_policy`, nessuna scrittura, store
temporaneo per sicurezza, FUORI pytest.
"""
from __future__ import annotations

import os
import tempfile
import time
import types

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_radice_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.supersession_policy import (  # noqa: E402
    canonical_source_of,
    classify_write_relation,
)

NOW = time.time()


def _fatto(created, asserted=None, verified_by=None):
    return types.SimpleNamespace(verified_by=verified_by, created_at=created,
                                 asserted_at=asserted)


def main() -> None:
    old = _fatto(NOW - 3600)
    print("=== ① LA PRIMA CONDIZIONE: «same canonical source» ===")
    print("  canonical_source_of(old) = %r" % canonical_source_of(old))
    print("  canonical_source_of(new) = %r" % canonical_source_of(_fatto(NOW)))
    print("  ⇒ identiche per costruzione sulle scritture anonime.\n")

    print("=== ② LA SECONDA: «strictly newer in valid-time» ===")
    casi = [
        ("SENZA asserted_at  (il caso reale)", _fatto(NOW), old),
        ("asserted_at UGUALE fra i due",
         _fatto(NOW, NOW - 86400), _fatto(NOW - 3600, NOW - 86400)),
        ("asserted_at PRECEDENTE (backfill)",
         _fatto(NOW, NOW - 172800), _fatto(NOW - 3600, NOW - 86400)),
        ("asserted_at POSTERIORE (evoluzione vera)",
         _fatto(NOW, NOW - 3600), _fatto(NOW - 3600, NOW - 86400)),
    ]
    for nome, n, o in casi:
        r = classify_write_relation(n, o)
        flag = "  <<< il difetto" if (r == "evolution" and n.asserted_at is None) else ""
        print("  %-42s -> %s%s" % (nome, r, flag))
    print()
    print("=== ③ COSA NE SEGUE ===")
    print("  Il criterio giusto ESISTE: con un istante di validita' esplicito la")
    print("  coppia va a CONFLITTO, cioe' al giudice. Il difetto e' il FALLBACK")
    print("  su created_at, che per il candidato vale sempre «adesso».")
    print("  Il docstring promette «any ambiguity -> conflict»; il codice, in")
    print("  assenza di asserted_at, non risolve l'ambiguita': inventa un ordine.")


if __name__ == "__main__":
    main()
