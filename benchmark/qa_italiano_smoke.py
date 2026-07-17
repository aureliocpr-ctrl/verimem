"""QA ITALIANO — il claim multilingue MISURATO, non dichiarato. Store di fatti in
italiano (accenti inclusi: à/è/ì/ò/ù) + domande italiane: fattuali (con risposta),
trappole di astensione (gold=sconosciuto), transizioni datate. Misura
recall-corretto + astensione. Usa l'harness gem (recall_with_history + score_qa)
e il fix unicode 0aa4b72 (senza il quale un accento crasherebbe il run)."""
import json
import os
import tempfile
from pathlib import Path

os.environ["ENGRAM_RECONCILE_ON_WRITE"] = "1"
os.environ["ENGRAM_RECONCILE_AUTO_SUPERSEDE"] = "1"
os.environ["ENGRAM_RECONCILE_NLI"] = "local"
os.environ["ENGRAM_RECONCILE_MIN_OVERLAP"] = "0.35"
os.environ["ENGRAM_ANSWER_VERIFY"] = "1"

from benchmark.qa_eval import score_qa
from benchmark.qa_runner import LeanClaudeCLILLM
from verimem.agent import wire_reconcile_judge
from verimem.semantic import Fact, SemanticMemory
from verimem.temporal_context import recall_with_history

_DAY = 86400.0
_BASE = 1_577_836_800.0  # 2020-01-01, per date event-time deterministiche

# Fatti in italiano, con accenti — due persone, timeline datate.
FATTI = [
    ("Marco Rossi vive a Milano.", _BASE + 100 * _DAY),
    ("Marco Rossi lavora come ingegnere civile.", _BASE + 100 * _DAY),
    ("Marco Rossi ha una figlia di nome Sofia.", _BASE + 120 * _DAY),
    ("Marco Rossi preferisce il caffè macchiato senza zucchero.", _BASE + 130 * _DAY),
    ("Marco Rossi è appassionato di fotografia analogica.", _BASE + 140 * _DAY),
    ("Marco Rossi si è trasferito a Torino per un nuovo incarico.", _BASE + 500 * _DAY),
    ("Giulia Bianchi è una biologa marina di Napoli.", _BASE + 90 * _DAY),
    ("Giulia Bianchi ha adottato un gatto chiamato Nuvola.", _BASE + 110 * _DAY),
    ("Giulia Bianchi soffre di allergia ai pollini in primavera.", _BASE + 115 * _DAY),
    ("Giulia Bianchi ha pubblicato uno studio sulle barriere coralline nel 2023.", _BASE + 200 * _DAY),
    ("Giulia Bianchi parla correntemente inglese e spagnolo.", _BASE + 210 * _DAY),
    ("Il budget del progetto Delta è di 500.000 euro.", _BASE + 150 * _DAY),
]

# Domande: (domanda, gold, is_trappola). Trappola => gold blanco, astensione attesa.
DOMANDE = [
    # fattuali dirette
    ("Dove vive attualmente Marco Rossi?", "Torino", False),
    ("Che lavoro fa Marco Rossi?", "ingegnere civile", False),
    ("Come si chiama la figlia di Marco Rossi?", "Sofia", False),
    ("Come preferisce il caffè Marco Rossi?", "macchiato senza zucchero", False),
    ("Di cosa è appassionato Marco Rossi?", "fotografia analogica", False),
    ("Di che città è Giulia Bianchi?", "Napoli", False),
    ("Che animale ha adottato Giulia Bianchi?", "un gatto", False),
    ("Come si chiama il gatto di Giulia Bianchi?", "Nuvola", False),
    ("Quali lingue parla Giulia Bianchi?", "inglese e spagnolo", False),
    ("Qual è il budget del progetto Delta?", "500.000 euro", False),
    ("Che professione ha Giulia Bianchi?", "biologa marina", False),
    ("Di cosa soffre Giulia Bianchi in primavera?", "allergia ai pollini", False),
    # trappole di astensione (dato mai fornito) -> gold sconosciuto
    ("Qual è il gruppo sanguigno di Marco Rossi?", "sconosciuto", True),
    ("Quanti anni ha Sofia?", "non fornito", True),
    ("Qual è il secondo nome di Giulia Bianchi?", "non indicato", True),
    ("Che macchina guida Marco Rossi?", "sconosciuto", True),
    ("Dove è andata in vacanza Giulia Bianchi nel 2024?", "non fornito", True),
    ("Qual è il numero di telefono di Marco Rossi?", "non fornito", True),
    # transizione datata
    ("Dove viveva Marco Rossi prima di trasferirsi?", "Milano", False),
]


def main() -> None:
    llm = LeanClaudeCLILLM(timeout_s=120, model="claude-sonnet-4-6")
    sm = SemanticMemory(db_path=Path(tempfile.mkdtemp(prefix="qait_")) / "d.db")
    wire_reconcile_judge(sm, None)
    for i, (prop, ts) in enumerate(FATTI):
        sm.store(Fact(proposition=prop, topic=f"it/{i}", asserted_at=ts),
                 embed="sync")
    print(f"store IT: {len(FATTI)} fatti", flush=True)

    recs = []
    for j, (q, gold, trap) in enumerate(DOMANDE):
        recs.append({"id": f"it:{j}", "question": q,
                     "gold": "" if trap else gold,
                     "context": recall_with_history(sm, q, k=8),
                     "category": "Astensione IT" if trap else "Fattuale IT",
                     "adversarial": trap, "gold_full": gold})
    print(f"{len(recs)} domande IT ({sum(d[2] for d in DOMANDE)} trappole)", flush=True)

    res = score_qa(recs, answer_llm=llm, judge_llm=llm)
    gmap = {r["id"]: r["gold_full"] for r in recs}
    for d in res.get("details", []):
        d["gold"] = gmap.get(d.get("id"), "")
    res["lang"] = "it"
    print(f"QA-IT: acc={res['accuracy']} per_cat={json.dumps(res['per_category'], ensure_ascii=False)}",
          flush=True)
    Path("benchmark/results/qa_italiano.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
