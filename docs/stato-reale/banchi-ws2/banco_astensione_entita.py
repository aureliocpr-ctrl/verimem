"""BANCO: `trust_report` si astiene sugli attributi assenti e MAI sulle entita' scambiate.

⚠️⚠️ NON PUO' ESSERE UN TEST DELLA SUITE, e la ragione non e' pigrizia:
`tests/conftest.py:122` sostituisce l'embedder con uno stub SHA-256 su OGNI test
(«Real sentence-transformers is never loaded in unit tests»), e questa misura
passa TUTTA da un coseno. Sotto pytest misurerebbe lo stub. Va eseguito cosi':

    python banco_astensione_entita.py <path-del-venv-o-vuoto-per-il-repo>

📌 PERCHE' ESISTE — misurato il 2026-08-22 sulla porta MCP con il wheel 0.7.5:
    A  attributo assente   3 su 3 si astiene      (colore, stipendio, proprietario)
    B  entita' scambiata   0 su 5 si astiene      (citta', persona, codice,
                                                   matricola, anno)
e in tutte e cinque le B il dossier consegna il fatto dell'entita' ORIGINALE:
K-88 -> «Il magazzino K-77 misura 2600 metri quadrati.»

🔑 IL MECCANISMO E' NELLA DOCSTRING DEL PRODOTTO, non e' una mia ipotesi —
`trust_report.py:189`:
    «min_relevance ... Needed because the bi-encoder is ANISOTROPIC — every query
     cosine-matches *something* ~0.8»
⇒ un pavimento SCALARE puo' tagliare solo cio' che e' lontano. «Stessa domanda,
  altra entita'» e' la cosa che somiglia di piu', quindi nessun valore della
  soglia la separa: alzandola si perdono le risposte vere prima delle false.
  (E «alzare la soglia» e' gia' fra le strade falsificate: rendeva muta la mappa
  dell'ignoranza.)
⇒ LA CURA CANDIDATA E' LA STESSA del lato scrittura: il grafo delle entita' di
  `_entita_diverse`. Questo banco e' il suo secondo bersaglio.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

if len(sys.argv) > 1 and sys.argv[1]:
    sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "Lib" / "site-packages"))
else:
    sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
for _k in list(os.environ):
    if _k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_")):
        del os.environ[_k]
CASA = pathlib.Path(tempfile.mkdtemp(prefix="banco_astensione_"))
os.environ["HIPPO_DATA_DIR"] = str(CASA)

from verimem.client import Memory  # noqa: E402
from verimem.trust_report import build_trust_report  # noqa: E402

SORG = ("Verbale del collaudo del 12 marzo 2024: il ripetitore di Ancona ha "
        "inoltrato 4200 messaggi, il tecnico Rossi era di turno, il magazzino "
        "K-77 misura 2600 metri quadrati e l'apparato con matricola SN-1180 ha "
        "superato la prova.")
SCRITTI = [
    ("Il ripetitore di Ancona ha inoltrato 4200 messaggi.", "c/citta"),
    ("Il tecnico Rossi era di turno al collaudo.", "c/persona"),
    ("Il magazzino K-77 misura 2600 metri quadrati.", "c/codice"),
    ("L'apparato con matricola SN-1180 ha superato la prova.", "c/matricola"),
    ("Il collaudo si e' svolto il 12 marzo 2024.", "c/anno"),
]
#: (gruppo, etichetta, domanda). NESSUNA ha risposta nel corpus: devono astenersi
#: tutte. Le A sono il CONTROLLO — senza di loro «0 astensioni» si leggerebbe
#: come «lo strumento non si astiene mai», che e' falso e manda la cura altrove.
DOMANDE = [
    ("A", "attributo colore", "di che colore e' il ripetitore di Ancona"),
    ("A", "attributo stipendio", "che stipendio ha il tecnico Rossi"),
    ("A", "attributo proprietario", "chi e' il proprietario del magazzino K-77"),
    ("B", "citta' Bologna", "quanti messaggi ha inoltrato il ripetitore di Bologna"),
    ("B", "persona Ferrari", "il tecnico Ferrari era di turno al collaudo"),
    ("B", "codice K-88", "quanti metri quadrati misura il magazzino K-88"),
    ("B", "matricola SN-9990", "l'apparato con matricola SN-9990 ha superato la prova"),
    ("B", "anno 2019", "cosa e' successo al collaudo del 12 marzo 2019"),
]


def main() -> int:
    m = Memory(CASA / "m.db")
    for prop, topic in SCRITTI:
        m.add(prop, topic=topic, source=SORG)
    sm = getattr(m, "semantic", None) or getattr(m, "_semantic", None) or m
    conta = {"A": [0, 0], "B": [0, 0]}
    for gruppo, nome, q in DOMANDE:
        d = build_trust_report(sm, q, k=5)
        ast = bool(d.get("abstained"))
        conta[gruppo][0 if ast else 1] += 1
        reso = ""
        for f in (d.get("facts") or [])[:1]:
            reso = f"  -> «{str(f.get('proposition'))[:48]}»"
        print(f"  {'✅' if ast else '🔴'} {gruppo} {nome:<24} abstained={str(ast):<5} "
              f"n_facts={d.get('n_facts')}{reso}")
    print(f"\n  A attributo assente : {conta['A'][0]} si astiene · {conta['A'][1]} NO")
    print(f"  B entita' scambiata : {conta['B'][0]} si astiene · {conta['B'][1]} NO")
    #: il banco e' ROSSO finche' una B non si astiene. Diventa verde con la cura,
    #: e le A servono a garantire che non diventi verde spegnendo lo strumento.
    return 0 if conta["B"][1] == 0 and conta["A"][0] == 3 else 1


if __name__ == "__main__":
    esito = main()
    print(f"\n  ESITO={esito}  (0 = curato · 1 = la classe e' ancora aperta)")
    sys.exit(esito)
