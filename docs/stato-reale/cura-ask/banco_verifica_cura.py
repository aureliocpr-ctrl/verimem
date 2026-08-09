# -*- coding: utf-8 -*-
"""VERIFICA DELLA CURA sulla copia curata. Due popolazioni, come si deve:
non basta che `ask` avvisi — NON deve avvisare quando la risposta c'e'."""
import os, sys, io, contextlib, tempfile, shutil
ALBERO = sys.argv[1]
BASE = tempfile.mkdtemp(prefix="cura_")
os.environ["HIPPO_DATA_DIR"] = BASE
sys.path.insert(0, ALBERO)
b = io.StringIO()
with contextlib.redirect_stdout(b), contextlib.redirect_stderr(b):
    from verimem.cli import app as cli_app
FATTI = [
 ("Il magazzino di Verona contiene 480 unita.", "Inventario. Il magazzino di Verona contiene 480 unita."),
 ("Il pagamento delle fatture e fissato a 60 giorni.", "Contratto. Il pagamento delle fatture e fissato a 60 giorni."),
 ("La responsabile della qualita e Anna Ferri.", "Organigramma. La responsabile della qualita e Anna Ferri."),
 ("Il fornitore principale e la ditta Rossi.", "Fornitori. Il fornitore principale e la ditta Rossi."),
 ("Gli interessi di mora sono del 4 per cento annuo.", "Contratto. Gli interessi di mora sono del 4 per cento annuo."),
 ("Il turno di notte inizia alle 22.", "Regolamento. Il turno di notte inizia alle 22."),
 ("L ufficio legale ha sede a Roma.", "Organigramma. L ufficio legale ha sede a Roma."),
 ("La polizza copre fino a 2 milioni di euro.", "Polizza. La polizza copre fino a 2 milioni di euro."),
]
def cli(argv):
    o = io.StringIO()
    try:
        with contextlib.redirect_stdout(o), contextlib.redirect_stderr(o):
            cli_app(argv, standalone_mode=False)
    except SystemExit:
        pass
    except Exception as e:
        o.write("[EXC %s]" % e)
    return o.getvalue()
for i, (p, s) in enumerate(FATTI):
    cli(["save", p, "--topic", "az/%d" % i, "--source", s])
SENZA = "Qual e il fatturato del 2025?"
CON   = "Chi e la responsabile della qualita?"
print("  albero: {}\n".format(os.path.basename(ALBERO)))
print("  {:<22} {:<30} {:<30} {}".format("comando", "domanda SENZA risposta", "domanda CON risposta", "verdetto"))
print("  " + "-" * 100)
esiti = {}
for cmd in ("recall", "ask"):
    a = "sotto il pavimento" in cli([cmd, SENZA])
    c = "sotto il pavimento" in cli([cmd, CON])
    esiti[cmd] = (a, c)
    if a and not c:
        v = "CORRETTO: avvisa solo quando serve"
    elif a and c:
        v = "RUMORE: avvisa sempre"
    elif not a:
        v = "MUTO: non avvisa quando dovrebbe"
    print("  {:<22} {:<30} {:<30} {}".format(
        "verimem " + cmd, "AVVISA" if a else "muto", "AVVISA" if c else "muto", v))
# il conteggio non deve essere toccato
o = cli(["ask", "quante volte ho parlato del magazzino?"])
print("\n  ramo count (non deve cambiare): {}".format(
    " ".join(o.split())[:70] or "(muto)"))
shutil.rmtree(BASE, ignore_errors=True)
