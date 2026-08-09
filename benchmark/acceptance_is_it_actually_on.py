"""È davvero acceso? Una prova di accettazione, non una dichiarazione.

Ogni cosa cablata il 2026-07-29 viene esercitata su uno store VUOTO, dal di
fuori, come farebbe un utente appena installato. Non "i test passano" — i test
li ho scritti io e passano per costruzione. Qui si guarda il COMPORTAMENTO:
scrivo, leggo, chiedo, e confronto con quello che il prodotto promette.

Nasce da una domanda di Aurelio a cui la risposta onesta era "non lo so": ogni
volta che dico «fatto», fatto non è. Oggi stesso: «l'astensione è accesa» e la
suite intera ha poi trovato tre rossi. Una dichiarazione non è una verifica, e
questo file esiste per rendere la differenza eseguibile.

    python -m benchmark.acceptance_is_it_actually_on

Esce 0 se ogni promessa regge, 1 al primo scarto — con la riga che lo mostra.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

ESITI: list[tuple[str, bool, str]] = []


def _check(nome: str, ok: bool, dettaglio: str = "") -> None:
    ESITI.append((nome, bool(ok), dettaglio))


def main() -> int:
    d = Path(tempfile.mkdtemp(prefix="acceptance_"))
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        os.environ[k] = str(d)
    os.environ.pop("ENGRAM_MIN_RELEVANCE", None)
    os.environ.pop("ENGRAM_GROUNDING_WRITE", None)

    from verimem.client import Memory
    m = Memory(path=d / "semantic" / "semantic.db")

    # 1 — una scrittura CON source viene giudicata, senza toccare env
    r1 = m.add("Il servizio di fatturazione ascolta sulla porta 8443.",
               topic="acc/scrittura",
               source="Runbook: il servizio di fatturazione ascolta sulla "
                      "porta 8443 dietro nginx.")
    _check("scrittura con source → giudicata",
           isinstance(r1.get("grounding_score"), (int, float)),
           f"grounding_score={r1.get('grounding_score')}")

    # 2 — il verdetto è PERSISTITO, non solo restituito
    con = sqlite3.connect(str(m.semantic.db_path))
    row = con.execute("SELECT grounding_score FROM facts WHERE id = ?",
                      (r1.get("id"),)).fetchone()
    con.close()
    _check("il verdetto è persistito sulla riga", bool(row and row[0] is not None),
           f"riga={row}")

    # 3 — una scrittura SENZA source non viene giudicata, e non finge
    r2 = m.add("Il totale della fattura è 1240 euro.", topic="acc/senza-source")
    _check("scrittura senza source → non giudicata (None, non 0)",
           r2.get("grounding_score") is None,
           f"grounding_score={r2.get('grounding_score')}")

    # 4 — una fonte che NON sostiene la proposizione viene fermata
    r3 = m.add("La fattura 88 è già stata pagata.", topic="acc/moat",
               source="Fattura 88: importo 1240 euro, scadenza 30 giorni.")
    _check("fonte che non sostiene → trattenuta o punteggio basso",
           r3.get("status") == "quarantined"
           or (r3.get("grounding_score") or 100) < 60,
           f"status={r3.get('status')} score={r3.get('grounding_score')}")

    # 5 — l'astensione è accesa SENZA configurare niente
    dossier = m.explain("quale compagnia aerea usa il reparto vendite?")
    _check("domanda che lo store non regge → si astiene",
           bool(dossier.get("abstained")) and not dossier.get("facts"),
           f"abstained={dossier.get('abstained')} n={len(dossier.get('facts') or [])}")

    # 6 — e NON si astiene su una domanda che regge
    dossier2 = m.explain("su quale porta ascolta il servizio di fatturazione?")
    _check("domanda sostenuta → risponde",
           not dossier2.get("abstained") and bool(dossier2.get("facts")),
           f"abstained={dossier2.get('abstained')} n={len(dossier2.get('facts') or [])}")

    # 7 — la lettura restituisce il verdetto del moat
    facts = dossier2.get("facts") or []
    _check("la lettura porta il grounding_score",
           any("grounding_score" in f for f in facts),
           f"chiavi={sorted(facts[0].keys()) if facts else '(nessun fatto)'}")

    # 8 — un fatto che diventa falso viene superseduto e il recall serve il nuovo
    m.add("Il servizio di fatturazione ascolta sulla porta 9443.",
          topic="acc/scrittura",
          source="Runbook aggiornato: la porta è ora 9443.")
    vivi = [f.proposition for f in m.semantic.all()
            if "fatturazione ascolta" in f.proposition and not f.superseded_by]
    _check("il valore vecchio non resta vivo accanto al nuovo",
           len(vivi) <= 1, f"vivi={vivi}")

    print(f"{'':2s}{'controllo':52s} esito")
    print("-" * 78)
    for nome, ok, det in ESITI:
        print(f"  {nome:52s} {'OK ' if ok else 'NO '} {det[:60]}")
    falliti = [e for e in ESITI if not e[1]]
    print()
    if falliti:
        print(f"=== {len(falliti)} PROMESSE NON MANTENUTE su {len(ESITI)} ===")
        for nome, _ok, det in falliti:
            print(f"  {nome}: {det}")
        return 1
    print(f"tutte e {len(ESITI)} le promesse reggono su uno store vuoto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
