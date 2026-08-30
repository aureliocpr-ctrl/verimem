"""Il banco che il doc 52 dichiarava mancante.

Domanda: quando si spezza una misura in due fatti con la STESSA source, cosa
impedisce al secondo di ritirare il primo (`same-source evolution`)?

Disegno: N misure, ciascuna spezzata in DUE fatti con la stessa source.
  braccio A (controllo)       : i due pezzi dicono solo il numero
  braccio B (prima ipotesi)   : i due pezzi nominano lo STESSO soggetto
  braccio C (seconda ipotesi) : i due pezzi nominano ENTITA' DIVERSE
Poi si conta quanti restano con `superseded_by IS NULL`.

ESITO MISURATO (6 misure per braccio, 31/08):
  A  6 vivi su 12      B  6 vivi su 12      C  12 vivi su 12
La prima ipotesi e' FALSIFICATA (B non fa meglio del controllo), la seconda
regge — coerente con `is_same_source` sempre vera e `_entita_diverse` come
unica difesa. In A e in B il ritirato e' SEMPRE il primo pezzo scritto, 12 su 12.

STORE TEMPORANEO: quello di Aurelio non viene toccato.
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="ws6-banco-pezzi-"))
os.environ["HIPPO_DATA_DIR"] = str(TMP)          # PRIMA degli import
os.environ.pop("ENGRAM_DATA_DIR", None)
os.environ.pop("VERIMEM_DATA_DIR", None)
print("store temporaneo: %s" % TMP)

from verimem.cli import main   # noqa: E402

N = 6   # misure per braccio

def salva(prop, topic, src):
    # Niente `--lineage-to auto`: su uno store VUOTO non esiste un fatto
    # precedente sotto il segmento, e il prodotto rifiuta la scrittura dicendo
    # «omit --lineage-to for a root checkpoint». Qui ogni fatto e' una radice.
    sys.argv = ["verimem", "save", prop, "--topic", topic, "--source", src]
    try:
        main()
    except SystemExit:
        pass


# --------------------------------------------------------------- il materiale
# Ogni misura ha DUE valori e una source che li contiene entrambi: e' la forma
# esatta dei fatti che si sono mangiati fra loro nella notte del 30/08.
MISURE = [
    ("banco/braccio/uno",     "topic", 12401, 16601),
    ("banco/braccio/due",     "righe", 12643,  2708),
    ("banco/braccio/tre",     "fatti",  2614,   118),
    ("banco/braccio/quattro", "coppie", 93263, 74646),
    ("banco/braccio/cinque",  "sonde",     32,   470),
    ("banco/braccio/sei",     "query",    120,    36),
]

for i, (topic_base, nome, v1, v2) in enumerate(MISURE):
    src = ("Il banco stampa per la misura %s due valori: il primo vale %d e il "
           "secondo vale %d." % (nome, v1, v2))
    # --- braccio A: SOLO IL NUMERO
    ta = topic_base + "/a"
    salva("Il primo valore e %d." % v1, ta, src)
    salva("Il secondo valore e %d." % v2, ta, src)
    # --- braccio B: NUMERO + SOGGETTO (ma lo STESSO soggetto in entrambi)
    tb = topic_base + "/b"
    salva("Nella misura %s il primo valore e %d." % (nome, v1), tb, src)
    salva("Nel conteggio successivo della misura %s il secondo valore e %d."
          % (nome, v2), tb, src)
    # --- braccio C: ENTITA' DIVERSE nei due pezzi
    # E' la correzione del disegno: in B avevo ripetuto lo STESSO soggetto,
    # quindi `_entita_diverse` non aveva nulla da distinguere. Qui ogni pezzo
    # nomina un oggetto suo.
    tc = topic_base + "/c"
    salva("Il file di ingresso della misura %s contiene %d elementi."
          % (nome, v1), tc, src)
    salva("La tabella di uscita della misura %s contiene %d righe."
          % (nome, v2), tc, src)

# ------------------------------------------------------------------ il conteggio
DB = TMP / "semantic" / "semantic.db"
con = sqlite3.connect("file:%s?mode=ro" % str(DB).replace(os.sep, "/"), uri=True)
c = con.cursor()
print("\n%-10s %7s %9s %9s %9s" % ("braccio", "fatti", "vivi", "ritirati", "giudicati"))
esiti = {}
for braccio in ("a", "b", "c"):
    righe = c.execute(
        "SELECT superseded_by, grounding_score FROM facts "
        "WHERE topic LIKE 'banco/braccio/%/" + braccio + "'").fetchall()
    vivi = sum(1 for s, _ in righe if s is None)
    giud = sum(1 for _, g in righe if g is not None)
    esiti[braccio] = (len(righe), vivi)
    print("%-10s %7d %9d %9d %9d"
          % (braccio, len(righe), vivi, len(righe) - vivi, giud))
con.close()

na, va = esiti.get("a", (0, 0))
nb, vb = esiti.get("b", (0, 0))
nc, vc = esiti.get("c", (0, 0))
print("\n   A (solo numero)      : %d vivi su %d" % (va, na))
print("   B (stesso soggetto)   : %d vivi su %d" % (vb, nb))
print("   C (entita' diverse)   : %d vivi su %d" % (vc, nc))
print()
print("=> B contro A (nominare lo STESSO soggetto) : %s"
      % ("aiuta" if vb > va else "NON aiuta, stesso esito"))
print("=> C contro A (nominare ENTITA' DIVERSE)    : %s"
      % ("AIUTA" if vc > va else "non aiuta"))
print("\n⚠️ store VUOTO all'inizio: giudice e pavimento possono comportarsi")
print("   diversamente che su un corpus reale. Dichiarato.")
print("copia in %s" % TMP)
