"""Quanti commit separano HEAD dall'ultima versione PUBBLICATA.

⚠️ PERCHE' ESISTE, ed e' una capacita' NUOVA e non un ripristino.
`test_la_versione_dichiarata_non_e_troppo_lontana_dal_codice` dichiara nel suo
docstring di accorgersi che «il pacchetto PUBBLICATO e' vecchio». Il suo codice
non puo': invoca solo ``git log`` e ``git rev-parse``, non nomina mai i tag e
non interroga nessuna fonte esterna — «PyPI» compare nella prosa e mai
nell'implementazione. Misura ``HEAD - commit_che_ha_scritto_il_numero``.

L'08/08 quel proxy funziono' per COINCIDENZA: dichiarato e pubblicato erano
entrambi ``0.7.0``, quindi le due distanze erano la stessa quantita'. Il bump a
0.7.6 senza pubblicare le ha separate, e si e' scoperto cosa misurava davvero::

    distanza dal BUMP     4 commit    -> il presidio tace
    distanza dal TAG    867 commit    -> cio' che paga chi installa

⚖️ QUESTO E' UN MISURATORE, NON UN PRESIDIO: stampa e non blocca niente. La
distinzione e' deliberata — il docstring di quel test dice «e' un avviso, non un
veto», ma essendo un test in una suite un suo FAILED chiude il cancello di
`publish.yml` (che pretende ``conclusion == "success"``). Un avviso che impedisce
la pubblicazione impedisce l'unica cosa che spegnerebbe l'avviso. Dove agganciare
questo numero — un job non bloccante, una riga di referto, un test vero — e' una
decisione di rilascio, e chi la prende deve poterla prendere separatamente dal
sapere il numero.

⚠️ SI ASTIENE INVECE DI INVENTARE. Su un clone ``--depth 1`` i tag non ci sono:
in quel caso questo script dice «non lo so» ed esce con 2. E' la stessa trappola
che il 20/08 ha fatto passare per PASSED un presidio che avrebbe dovuto essere
rosso — li' un bump introvabile diventava distanza 0, cioe' la risposta migliore
possibile a partire da una storia troncata.

⚠️⚠️ E CHI LO AGGANCIA A UN TEST DEVE ROVESCIARE QUELLA RIGA. L'astensione e'
giusta per un misuratore che chiami a mano — «non lo so» batte un numero
inventato — ed e' PERICOLOSA dentro una suite: in CI uno skip si conta fra i
verdi e apre il cancello della pubblicazione (@ws6, 21/08). Un presidio costruito
su questo deve trattare ``stato != "misurato"`` come un FALLIMENTO, non come uno
skip.

📌 CORREZIONE al messaggio del commit che ha introdotto questo file (`074198c1`):
li' ho scritto che la storia troncata «e' la norma in CI». E' FALSO per il job
``test``, che ha ``fetch-depth: 0`` (ci.yml:231) e quindi riceve i tag — l'anello
l'ha chiuso @ws6 leggendo il refspec dal log di un run. Resta profondo 1 il job
``build`` (ci.yml:988), che pero' non legge la storia: li' e' una trappola
armata, non un difetto attivo.

Uso::

    python scripts/distanza_dal_pubblicato.py          # riga leggibile
    python scripts/distanza_dal_pubblicato.py --json   # per un referto

Uscita: 0 misurato · 2 non misurabile (nessun tag: storia troncata o repo nuovo).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]


def _git(*a: str) -> str:
    r = subprocess.run(["git", *a], cwd=RADICE, capture_output=True,
                       text=True, timeout=60)
    return r.stdout.strip() if r.returncode == 0 else ""


def _versione_dichiarata() -> str | None:
    m = re.search(r'^version\s*=\s*"([^"]+)"',
                  (RADICE / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def _chiave(tag: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", tag))


def misura() -> dict[str, object]:
    if not _git("rev-parse", "--git-dir"):
        return {"stato": "non-misurabile", "perche": "non e' un checkout git"}
    tag = [t for t in _git("tag", "--list", "v*").splitlines() if t.strip()]
    if not tag:
        # Nessun tag: o la storia e' troncata (clone --depth 1, che in CI e' la
        # norma) o il progetto non ha mai pubblicato. In entrambi i casi un
        # numero sarebbe inventato.
        return {"stato": "non-misurabile",
                "perche": "nessun tag v* raggiungibile (storia troncata?)"}
    ultimo = max(tag, key=_chiave)
    distanza = _git("rev-list", "--count", f"{ultimo}..HEAD")
    return {
        "stato": "misurato",
        "tag_pubblicato": ultimo,
        "data_tag": _git("log", "-1", "--format=%ci", ultimo),
        "versione_dichiarata": _versione_dichiarata(),
        "distanza_commit": int(distanza) if distanza.isdigit() else None,
        "head": _git("rev-parse", "--short", "HEAD"),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    d = misura()
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    elif d["stato"] != "misurato":
        print(f"non misurabile: {d['perche']}")
    else:
        print(f"HEAD {d['head']} dichiara {d['versione_dichiarata']} ed e' a "
              f"{d['distanza_commit']} commit dall'ultimo tag {d['tag_pubblicato']} "
              f"({str(d['data_tag'])[:10]})")
    return 0 if d["stato"] == "misurato" else 2


if __name__ == "__main__":
    sys.exit(main())
