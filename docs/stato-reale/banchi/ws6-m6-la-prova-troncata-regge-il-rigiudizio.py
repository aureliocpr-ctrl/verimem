# -*- coding: utf-8 -*-
"""M6 anello ②/③ — la PROVA salvata regge un secondo giudizio?

    python docs/stato-reale/banchi/ws6-m6-la-prova-troncata-regge-il-rigiudizio.py

L'IPOTESI VIENE DAL CODICE, non da fuori. `grounding_gate.py:404` dice:

    «NON si può misurare questo dal campo facts.grounding_span, che è troncato a
     400 caratteri per la persistenza: quel campo dice cosa è stato SALVATO, non
     cosa il giudice ha VISTO.»

⇒ **Due budget diversi**: il giudice legge fino a ~1500 caratteri, la persistenza
ne salva 400 (`_GROUNDING_SPAN_BUDGET`, anti_confab_gate.py:1860). Il commit che
introdusse lo span (`35dd263f`, 08/08) prometteva *«la PROVA della verifica, non
solo il voto»*: se la prova salvata è meno di un terzo di ciò che il giudice ha
visto, **la promessa vale solo finché nessuno prova a rifare il giudizio**.

E il commento di `_GROUNDING_SPAN_BUDGET` dice: *«Non è una soglia di
comportamento: alzarlo conserva più contesto, abbassarlo meno, e nessun verdetto
si muove in nessuno dei due casi»*. È vero per il verdetto **live**. Questo banco
chiede se sia vero per il verdetto **rifatto sulla prova conservata**.

L'ESPERIMENTO, una sola variabile: si passa al gate, come fonte, **lo span
salvato** invece della fonte originale, e si confronta il punteggio ottenuto con
il `grounding_score` registrato.

  braccio A  fatti con length(span) = 400  -> la prova è TRONCATA
  braccio B  fatti con length(span) < 300  -> la prova è INTERA  (controllo)

Il braccio B è il controllo che rende leggibile A: se anche lì il punteggio
cadesse, la caduta sarebbe del metodo (il gate non è deterministico, o rigiudica
diversamente) e non del troncamento.

╔═ PREDIZIONE, scritta PRIMA di eseguire (anello ②) ════════════════════════════╗
║  A (troncati)  mediana della caduta ≥ 5 punti · almeno 3 su 10 sotto 90       ║
║  B (interi)    mediana della caduta < 2 punti · al più 1 su 10 sotto 90       ║
║                                                                              ║
║  Se A ≈ B  → il troncamento NON costa riverificabilità e M6 è chiuso del      ║
║              tutto: il debito è storico e il tetto è innocuo.                 ║
║  Se A ≫ B  → la prova conservata non regge il rigiudizio, e il tetto è un     ║
║              difetto VIVO con un costo misurato.                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

⛔ Store di Aurelio in SOLA LETTURA. Il rigiudizio scrive in un tempdir.
"""
import os
import sqlite3
import statistics
import tempfile

_tmp = tempfile.mkdtemp(prefix="ws6_m6_rigiudizio_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402

CASA = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
N = 10

ro = sqlite3.connect("file:%s?mode=ro" % CASA.replace(os.sep, "/"), uri=True)


def prendi(dove):
    return ro.execute(
        "SELECT id, proposition, grounding_span, grounding_score FROM facts "
        "WHERE grounding_span IS NOT NULL AND grounding_span <> '' "
        "  AND grounding_score >= 95 AND %s "
        "ORDER BY created_at DESC LIMIT ?" % dove, (N,)).fetchall()


bracci = (("A troncati (=400)", prendi("length(grounding_span) = 400")),
          ("B interi  (<300)", prendi("length(grounding_span) < 300")))
ro.close()

m = Memory()
print("LA PROVA CONSERVATA REGGE UN SECONDO GIUDIZIO?")
print("(fonte passata al gate = lo SPAN SALVATO; confronto col punteggio registrato)\n")

esiti = {}
for nome, righe in bracci:
    print("=== %s — %d fatti ===" % (nome, len(righe)))
    print("  %-14s %8s %8s %9s  %s" % ("fatto", "prima", "dopo", "caduta", "esito"))
    cadute, sotto90 = [], 0
    for fid, prop, span, score in righe:
        r = m.add(prop, topic="ws6/rigiudizio-%s" % fid, source=span)
        nuovo = r.get("grounding_score") if isinstance(r, dict) else None
        st = (r.get("status") or "?") if isinstance(r, dict) else "?"
        # CHI ferma: il punteggio puo' reggere mentre lo STATUS cambia, e il
        # livello a cui si guarda decide il verdetto. Senza questa colonna il
        # banco misura il moat e chiama «esito» qualcosa che decidono altri.
        chi = ",".join(sorted({str(w.get("layer", "?")) for w in (r.get("warnings") or [])})) or "-"
        st = "%s [%s]" % (st, chi)
        if nuovo is None:
            print("  %-14s %8.2f %8s %9s  %s" % (fid, score, "NULL", "-", st))
            continue
        caduta = float(score) - float(nuovo)
        cadute.append(caduta)
        if float(nuovo) < 90:
            sotto90 += 1
        print("  %-14s %8.2f %8.2f %9.2f  %s" % (fid, score, nuovo, caduta, st))
    med = statistics.median(cadute) if cadute else float("nan")
    esiti[nome] = (med, sotto90, len(cadute))
    print("  -> mediana della caduta %.2f · sotto 90: %d su %d\n" % (med, sotto90, len(cadute)))

print("=" * 74)
for nome, (med, s90, n) in esiti.items():
    print("  %-20s mediana caduta %7.2f · sotto 90: %d/%d" % (nome, med, s90, n))
print("\n  la PREDIZIONE era: A mediana >= 5 e >= 3 sotto 90 · B mediana < 2 e <= 1 sotto 90")
