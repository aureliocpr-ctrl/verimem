"""Blocco 9 della mappa di client.py: LE FUNZIONI CHE SCRIVONO LA FRASE CHE
L'UTENTE LEGGE e quelle che decidono l'ETICHETTA di una scrittura.

Sono pure o quasi pure: si esercitano senza store, quindi ogni ramo si prova
davvero invece di essere dedotto. Per ognuna c'è il caso che DEVE accendersi e
quello che DEVE spegnersi — un ramo misurato solo dal lato che conferma non è
misurato.

Il caso caldo: `_pavimento_avviso` legge una variabile d'ambiente e, quando il
valore è malformato, `finite_or(grezzo, _AVVISO_FLOOR_MISURATO)` ripiega sul
default DICHIARATO (0,839), non sul pavimento calibrato del corpus. Se è così,
un errore di battitura dell'operatore non spegne l'opt-in: lo ACCENDE al valore
misurato. La virgola decimale italiana è il modo più facile di sbagliarlo.
"""
import math
import os
import pathlib
import sys
import types

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
os.environ.pop("ENGRAM_AVVISO_MIN_RELEVANCE", None)
os.environ.pop("VERIMEM_AUDIT_LOG", None)
from verimem import client as C  # noqa: E402

print("guardia verimem.__file__:", C.__file__)

print("\n=== 1. _fact_trust_line (riga 77): [quando | fonte | stato] testo")
print("  con asserted_at + source:",
      C._fact_trust_line({"asserted_at": 1756944000, "created_at": 1788000000,
                          "source": "Verbale del 3 marzo", "status": "verified",
                          "text": "Il canone e' 5900 euro."}))
print("  solo created_at, niente source, verified_by presente:",
      C._fact_trust_line({"created_at": 1756944000, "verified_by": ["doc:contratto.pdf"],
                          "text": "La consegna e' del 3 marzo."}))
print("  niente data, niente fonte, niente stato:",
      C._fact_trust_line({"text": "Nota libera."}))

print("\n=== 2. _pavimento_avviso (riga 127) — IL CASO CALDO")
CAL = 0.8805
print("  senza variabile          ->", C._pavimento_avviso(CAL), "(atteso: il calibrato)")
for grezzo in ("0.839", "0,839", "0.95abc", "auto", "-1", "nan", "inf", "0.95"):
    os.environ["ENGRAM_AVVISO_MIN_RELEVANCE"] = grezzo
    v = C._pavimento_avviso(CAL)
    marchio = "  <-- NON e' il calibrato" if abs(v - CAL) > 1e-9 else ""
    print(f"  variabile={grezzo!r:10} -> {v}{marchio}")
os.environ.pop("ENGRAM_AVVISO_MIN_RELEVANCE", None)

print("\n=== 3. _frase_origine_soglia (riga 149) — COME SI CHIAMA quel numero")
print("  soglia == calibrato      ->", C._frase_origine_soglia(CAL, CAL))
print("  soglia != calibrato      ->", C._frase_origine_soglia(0.839, CAL))
print("  IMPOSTATA a un valore UGUALE al calibrato ->",
      C._frase_origine_soglia(CAL, CAL), "(la funzione vede due numeri, non l'origine)")

print("\n=== 4. _nota_scaduti (riga 170) — dice anche COSA NON E'")
n = C._nota_scaduti(3)
print(" ", n[:120], "...")
print("  dice 'Non e' il pavimento':", "Non e' il pavimento" in n,
      "· nomina recall_as_of:", "recall_as_of" in n)

print("\n=== 5. _evidence_class (riga 4180) — i QUATTRO rami, uno per uno")
g_loc = types.SimpleNamespace(judge="local")
g_llm = types.SimpleNamespace(judge="claude")
g_no = types.SimpleNamespace(judge=None)
print("  judge='local'                       ->", C._evidence_class(g_loc, [], []))
print("  judge='claude'                      ->", C._evidence_class(g_llm, [], []))
print("  niente judge + warning L4-skipped   ->",
      C._evidence_class(g_no, [], [{"layer": "L4-skipped"}]))
print("  niente judge + verified_by          ->",
      C._evidence_class(g_no, ["source:x:sha256"], []))
print("  niente di niente                    ->", C._evidence_class(g_no, [], []))

print("\n=== 6. _blocking_layers (riga 4230) — gli advisory NON prendono il merito")
w = [{"layer": "L4.1"}, {"layer": "L1"}, {"layer": "L4.2-observe"},
     {"layer": "L4-skipped"}, {"layer": ""}]
print("  in:", [x["layer"] for x in w])
print("  out:", C._blocking_layers(w))

print("\n=== 7. _audit_log_on (riga 4239) — default OFF")
for v in (None, "1", "on", "TRUE", "yes", "y", "si", "0", " on "):
    if v is None:
        os.environ.pop("VERIMEM_AUDIT_LOG", None)
    else:
        os.environ["VERIMEM_AUDIT_LOG"] = v
    print(f"  VERIMEM_AUDIT_LOG={v!r:8} -> {C._audit_log_on()}")
os.environ.pop("VERIMEM_AUDIT_LOG", None)

print("\n=== 8. _reason_from_warnings (riga 4248) — IL CASO DEL DOCSTRING")
w2 = [{"layer": "L4.1", "advice": "il claim afferma un valore che la fonte non contiene: 7300"},
      {"layer": "L4-skipped", "advice": "nessun giudice disponibile, controllo non eseguito"}]
print("  ['L4.1','L4-skipped'] ->", C._reason_from_warnings(w2))
print("  solo L4-skipped       ->",
      C._reason_from_warnings([w2[1]]))
print("  solo un observe       ->",
      C._reason_from_warnings([{"layer": "L4.2-observe", "advice": "solo un avviso"}]))
print("  L1 contro L4.1        ->",
      C._reason_from_warnings([{"layer": "L4.1", "advice": "da L4.1"},
                               {"layer": "L1", "advice": "da L1"}]))
print("  nessun warning        ->", repr(C._reason_from_warnings([])))

print("\n=== 9. _confidence_tier (riga 4287) — la banda")
for score, judge, thr in ((95.0, "local", 40.0), (60.0, "local", 40.0),
                          (10.0, "local", 40.0), (None, "local", 40.0),
                          (float("nan"), "local", 40.0), (95.0, None, 40.0),
                          (95.0, "claude", 70.0), (60.0, "claude", 70.0)):
    s = "nan" if isinstance(score, float) and math.isnan(score) else score
    print(f"  score={s!s:6} judge={judge!s:7} thr={thr} -> {C._confidence_tier(score, judge, thr)}")

print("\n=== 10. _adjudication (riga 4293) — il verdetto SEMPRE restituito")
g1 = types.SimpleNamespace(judge="claude", grounding_score=86.0, threshold=70.0, advice="")
print("  ammesso:", C._adjudication(g1, disposition="admitted", verified_by=[], warnings=[]))
g2 = types.SimpleNamespace(judge="claude", grounding_score=12.0, threshold=70.0, advice="")
print("  quarantinato con L4.1:",
      C._adjudication(g2, disposition="quarantined", verified_by=[], warnings=w2))
g3 = types.SimpleNamespace(judge=None, grounding_score=None, threshold=None, advice="")
print("  quarantinato senza numeri ne' advice:",
      C._adjudication(g3, disposition="quarantined", verified_by=[], warnings=[]))
g4 = types.SimpleNamespace(judge="claude", grounding_score=86.0, threshold=70.0, advice="")
print("  BLOCCATO ma score SOPRA la soglia:",
      C._adjudication(g4, disposition="quarantined", verified_by=[], warnings=[])["reason"])

print("\n=== 11. _judge_of_record_dict (riga 4269) — chi ha giudicato")
print("  None     ->", C._judge_of_record_dict(None))
print("  'claude' ->", C._judge_of_record_dict("claude"))
print("  'local'  -> (carica il CE, puo' metterci qualche secondo)")
print("           ->", C._judge_of_record_dict("local"))
