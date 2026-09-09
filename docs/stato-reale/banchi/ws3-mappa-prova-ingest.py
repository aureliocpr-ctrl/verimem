"""`conversation_ingest.py` (12): da una CONVERSAZIONE ai fatti, uno per uno,
ognuno attraverso il gate.

Le domande che decidono:
  · `render_conversation(with_flag=True)` esiste perché «il taglio era
    SILENZIOSO» (audit mod.9): il controllo è **superare il cap** e vedere
    `truncated=True`, non stare sotto;
  · `parse_extracted_lines` toglie **UN SOLO** marcatore iniziale: si prova con
    due marcatori di fila;
  · `_grounds` è il moat sulla via dell'ingest: si prova con un dialogo che
    sostiene il fatto **e** con uno che non lo sostiene.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-ing-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import conversation_ingest as CI  # noqa: E402

print("=== split_entities_line")
for t in ("Il canone e' 5900 euro.\nENTITIES: person:Mario; org:Acme",
          "Il canone e' 5900 euro.",
          "Il canone e' 5900 euro.\nENTITIES: alieno:Zorg; person:Mario"):
    testo, ent = CI.split_entities_line(t)
    print(f"  in: {t[:46]!r:50} -> testo {testo[:28]!r} · entita' {ent}")

print("\n=== parse_extracted_lines: UN SOLO marcatore tolto")
grezzo = ("- Il canone e' 5900 euro.\n"
          "1. La consegna e' il 3 marzo.\n"
          "-- Due marcatori di fila.\n"
          "\n"
          "   Riga con spazi davanti.\n")
for r in CI.parse_extracted_lines(grezzo):
    print(f"  {r!r}")

print("\n=== strip_belief_marker")
for r in ("BELIEF: il canone dovrebbe salire.", "Il canone e' 5900 euro.",
          "belief: minuscolo"):
    print(f"  {r!r:44} -> {CI.strip_belief_marker(r)}")

print("\n=== render_conversation: il taglio non deve essere SILENZIOSO")
msgs = [{"role": "user", "content": "Quanto costa il capannone 12?"},
        {"role": "assistant", "content": "Il canone e' 5900 euro al mese."},
        {"role": "user", "content": "x" * 500}]
testo = CI.render_conversation(msgs, cap_chars=10_000)
print("  senza cap stretto: lunghezza", len(testo), "· prime righe:",
      repr(testo[:60]))
corto, tagliato = CI.render_conversation(msgs, cap_chars=80, with_flag=True)
print("  con cap 80 e with_flag=True -> lunghezza", len(corto), "· truncated:", tagliato)
lungo, tagliato2 = CI.render_conversation(msgs, cap_chars=10_000, with_flag=True)
print("  con cap largo            -> truncated:", tagliato2,
      "(il flag distingue i due casi)")

print("\n=== conversation_provenance_ref")
print("  ref('conv-1'):", CI.conversation_provenance_ref("conv-1"))
print("  stabile:", CI.conversation_provenance_ref("conv-1")
      == CI.conversation_provenance_ref("conv-1"),
      "· diverso per conversazioni diverse:",
      CI.conversation_provenance_ref("conv-1") != CI.conversation_provenance_ref("conv-2"))

print("\n=== extraction_system_for: il prompt di estrazione")
p1 = CI.extraction_system_for("Aurelio")
p2 = CI.extraction_system_for(None)
print("  col nome utente: lunghezza", len(p1), "· contiene 'Aurelio':", "Aurelio" in p1)
print("  senza nome     : lunghezza", len(p2), "· contiene 'Aurelio':", "Aurelio" in p2)
p3 = CI.extraction_system_for("Aurelio", typed_entities=True, tag_beliefs=True)
print("  con entita' tipizzate e BELIEF: piu' lungo:", len(p3) > len(p1),
      "· nomina ENTITIES:", "ENTITIES" in p3, "· nomina BELIEF:", "BELIEF" in p3)

print("\n=== _ingest_ground_threshold / _grounds (il moat sulla via dell'ingest)")
print("  soglia:", CI._ingest_ground_threshold())
dialogo = ("user: Quanto costa il capannone 12?\n"
           "assistant: Il canone del capannone 12 e' 5900 euro al mese.")
for prop in ("Il canone del capannone 12 e' 5900 euro.",
             "Il canone del capannone 12 e' 9999 euro.",
             "Il capannone 12 e' stato venduto nel 2019."):
    ammesso, punteggio = CI._grounds(dialogo, prop)
    print(f"  {prop[:46]!r:50} -> ammesso={ammesso} punteggio={round(float(punteggio), 2)}")

print("\n=== ingest_conversation con un LLM finto (nessuna chiamata esterna)")
from verimem import Memory  # noqa: E402


class _Risposta:
    def __init__(self, text):
        self.text = text


class _LLM:
    def __init__(self, righe):
        self.righe = righe
        self.chiamate = 0

    def complete(self, **kw):
        self.chiamate += 1
        return _Risposta(self.righe)


m = Memory(str(tmp / "i.db"))
llm = _LLM("- Il canone del capannone 12 e' 5900 euro.\n"
           "- Il capannone 12 e' in via Roma.\n")
res = CI.ingest_conversation(m.semantic, [{"role": "user", "content": "Quanto costa?"},
                                          {"role": "assistant",
                                           "content": "Il canone del capannone 12 e' 5900 "
                                                      "euro. Il capannone 12 e' in via Roma."}],
                             llm=llm, conversation_id="conv-1", topic="ing/x")
print("  ->", {k: str(v)[:80] for k, v in list(res.items())[:8]})
print("  chiamate all'llm finto:", llm.chiamate)

print("\n=== gapfill_facts / consolidate_facts (le due passate opzionali)")
llm2 = _LLM("- Il contratto scade nel 2027.\n")
print("  gapfill_facts (llm che aggiunge una riga):",
      CI.gapfill_facts("user: il contratto scade nel 2027", ["Il canone e' 5900 euro."],
                       llm=llm2))
llm3 = _LLM("non e' una lista valida")
print("  gapfill_facts (llm che risponde spazzatura, fail-safe):",
      CI.gapfill_facts("dialogo", ["Il canone e' 5900 euro."], llm=llm3))
llm4 = _LLM("- Il canone e' 5900 euro.\n")
print("  consolidate_facts (due quasi-duplicati):",
      CI.consolidate_facts(["Il canone e' 5900 euro.", "Il canone e' di 5900 euro."],
                           llm=llm4))
llm5 = _LLM("")
print("  consolidate_facts (llm che risponde vuoto, fail-safe):",
      CI.consolidate_facts(["Il canone e' 5900 euro."], llm=llm5))
