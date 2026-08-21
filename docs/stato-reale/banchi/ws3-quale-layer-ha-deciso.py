"""Il caso reale: un fatto che il GIUDICE APPROVA a 99.89 e viene trattenuto.

Perche' e' uno script e non un test: qui il verdetto del moat decide il ramo, e
`tests/conftest.py` sostituisce l'embedder con uno stub in una fixture
`autouse=True` — sotto pytest questo banco misurerebbe il righello, non il
prodotto. La parte deterministica sta in
`tests/test_quale_layer_ha_deciso_non_solo_gate.py`.

    python docs/stato-reale/banchi/ws3-quale-layer-ha-deciso.py

Stampa da dove importa `verimem`: senza, misura un altro albero senza dirlo.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from verimem import Memory  # noqa: E402
import verimem.client as _c  # noqa: E402

print("importa verimem da : %s" % _c.__file__)
print("VERIMEM_AUDIT_LOG  : %s" % os.environ.get("VERIMEM_AUDIT_LOG", "<non impostata>"))
print()

# Il decimale con la virgola: la fonte scrive 176.6, il claim 176,6. L4.1 legge
# «6 mb, 176» e non lo trova nella fonte. Il moat, che guarda il SENSO, approva.
CLAIM = "Con il tetto attivo il committed e 176,6 MB."
FONTE = ("Con il tetto attivo il committed e 176.6 MB e il costo per thread "
         "e 32.2 MB.")

d = tempfile.mkdtemp()
m = Memory(path=os.path.join(d, "s.db"))
r = m.add(CLAIM, topic="t", source=FONTE)

print("claim          : %s" % CLAIM)
print("status         : %s" % r.get("status"))
print("moat           : %s   grounding = %.2f" % (r.get("moat"), r.get("grounding_score") or -1))
print("warnings       : %s" % [w.get("layer") for w in (r.get("warnings") or [])])
print("quarantined_by : %r" % r.get("quarantined_by"))
print()

righe = m.quarantine_log(limit=3, explain=True)
riga = righe[0] if righe else {}
print("quarantine_log(explain=True):")
print("   layers = %r" % riga.get("layers"))
print("   why    = %s" % str(riga.get("why"))[:220])
print()

falliti = 0

atteso_by = "L4.1"
ok = r.get("quarantined_by") == atteso_by
falliti += not ok
print("[1] l'etichetta dice il layer, non 'gate'   %s  (%r)" % (
    "ok" if ok else "ROTTA", r.get("quarantined_by")))

ok = riga.get("layers") == [atteso_by]
falliti += not ok
print("[2] la porta lo espone in layers            %s  (%r)" % (
    "ok" if ok else "ROTTA", riga.get("layers")))

why = str(riga.get("why") or "")
ok = "NON e' L4" not in why and "NON è L4" not in why
falliti += not ok
print("[3] explain non asserisce piu' «NON e' L4»  %s" % ("ok" if ok else "ROTTA"))

ok = r.get("moat") == "passed"
falliti += not ok
print("[4] il caso e' quello giusto: moat=passed   %s  (%r)" % (
    "ok" if ok else "NON RIPRODOTTO", r.get("moat")))

print()
print("PORTATA sul corpus, misurata il 21/08 per FINESTRA (il totale inganna:")
print("il campo e' popolato dal 07/08 e l'ultimo senza causa e' del 07/08 17:50)")
print("    finestra        quarantinati   'gate' generico")
print("    ultime 24h            25            56%")
print("    ultimi 7 giorni      136            16%")
print()
print("FALLITI: %d" % falliti)
sys.exit(1 if falliti else 0)
