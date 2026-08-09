# -*- coding: utf-8 -*-
"""FETTA ④ — banco 2: il TASSO di astensione, e il caso pericoloso.

Il banco 1 ha mostrato su UN caso che `trust_report` si astiene e `recall` no.
Un caso non e' un tasso. Qui: **12 domande** su un corpus di 10 fatti, tre tipi:
  A  RISPONDIBILE   — la risposta c'e'
  B  SENZA RISPOSTA — il corpus non la contiene
  C  PERICOLOSA     — chiede di un'entita' SIMILE a una presente (Trento vs
     Verona, ditta Bianchi vs Rossi): la risposta sbagliata e' **plausibile**,
     ed e' il caso in cui un utente non si accorge dell'errore.

Per ogni domanda confronto le due porte agli estremi:
  · `recall`        — la porta che tutti usano
  · `trust_report`  — la porta che dichiara `abstained`
Store ISOLATO.
"""
import os, sys, io, contextlib, tempfile, shutil

BASE = tempfile.mkdtemp(prefix="stato4b_")
os.environ["HIPPO_DATA_DIR"] = BASE
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.cli import app as cli_app
from verimem import Memory

FATTI = [
 ("Il magazzino di Verona contiene 480 unita.", "Inventario di gennaio. Il magazzino di Verona contiene 480 unita."),
 ("Il pagamento delle fatture e fissato a 60 giorni.", "Contratto quadro. Il pagamento delle fatture e fissato a 60 giorni."),
 ("La responsabile della qualita e Anna Ferri.", "Organigramma. La responsabile della qualita e Anna Ferri."),
 ("Gli interessi di mora sono del 4 per cento annuo.", "Contratto quadro. Gli interessi di mora sono del 4 per cento annuo."),
 ("Il turno di notte inizia alle 22.", "Regolamento interno. Il turno di notte inizia alle 22."),
 ("L ufficio legale ha sede a Roma.", "Organigramma. L ufficio legale ha sede a Roma."),
 ("La polizza assicurativa copre fino a 2 milioni di euro.", "Polizza 2026. La polizza copre fino a 2 milioni di euro."),
 ("Il contratto C-12 scade il 31 dicembre 2027.", "Contratto C-12. Il contratto C-12 scade il 31 dicembre 2027."),
 ("Il fornitore principale e la ditta Rossi.", "Elenco fornitori. Il fornitore principale e la ditta Rossi."),
 ("Le scorte minime sono 200 pezzi.", "Regolamento interno. Le scorte minime sono 200 pezzi."),
]
for i, (p, s) in enumerate(FATTI):
    b = io.StringIO()
    try:
        with contextlib.redirect_stdout(b), contextlib.redirect_stderr(b):
            cli_app(["save", p, "--topic", "az/%d" % i, "--source", s], standalone_mode=False)
    except SystemExit:
        pass
m = Memory(os.path.join(BASE, "semantic", "semantic.db"))

DOMANDE = [
 ("A", "Quante unita ci sono nel magazzino di Verona?"),
 ("A", "Chi e la responsabile della qualita?"),
 ("A", "A quanti giorni e fissato il pagamento?"),
 ("A", "Dove ha sede l ufficio legale?"),
 ("B", "Qual e il fatturato del 2025?"),
 ("B", "Quanti dipendenti ha l azienda?"),
 ("B", "Chi e l amministratore delegato?"),
 ("B", "Qual e l indirizzo email dell assistenza?"),
 ("C", "Quante unita contiene il magazzino di Trento?"),
 ("C", "Chi e il responsabile della sicurezza?"),
 ("C", "Il fornitore secondario e la ditta Bianchi?"),
 ("C", "Quando scade il contratto C-99?"),
]

def testo(x):
    return str(x.get("text") or x.get("proposition") or "") if isinstance(x, dict) else str(x)

print("  A = risponde il corpus · B = nessuna risposta · C = PERICOLOSA (entita' simile a una vera)\n")
print("  {:<3} {:<46} | {:<32} | {}".format("tipo", "domanda", "recall", "trust_report"))
print("  " + "-" * 118)
conta = {}
for tipo, q in DOMANDE:
    res = m.recall(q, k=3)
    lst = res if isinstance(res, list) else res.get("facts", res.get("results", []))
    lst = [x for x in (lst or []) if isinstance(x, dict)]
    r_ast = not lst
    r_txt = "(si astiene)" if r_ast else testo(lst[0])[:30]
    tr = m.trust_report(q)
    t_ast = bool(tr.get("abstained")) if isinstance(tr, dict) else None
    n_f = tr.get("n_facts") if isinstance(tr, dict) else "?"
    t_txt = "ASTIENE" if t_ast else "risponde (n_facts=%s)" % n_f
    conta.setdefault(tipo, {"n": 0, "r_ast": 0, "t_ast": 0})
    conta[tipo]["n"] += 1
    conta[tipo]["r_ast"] += 1 if r_ast else 0
    conta[tipo]["t_ast"] += 1 if t_ast else 0
    print("  {:<3}  {:<46} | {:<32} | {}".format(tipo, q[:44], r_txt, t_txt))

print("\n  === IL TASSO DI ASTENSIONE, PER TIPO DI DOMANDA ===")
print("  {:<28} {:>10} {:>16} {:>18}".format("tipo", "domande", "recall astiene", "trust_report astiene"))
print("  " + "-" * 76)
ET = {"A": "A  risponde il corpus", "B": "B  nessuna risposta", "C": "C  PERICOLOSA (simile)"}
for tipo in ("A", "B", "C"):
    c = conta.get(tipo)
    if c:
        print("  {:<28} {:>10} {:>16} {:>18}".format(
            ET[tipo], c["n"], "%d/%d" % (c["r_ast"], c["n"]), "%d/%d" % (c["t_ast"], c["n"])))
print("\n  Su A l'astensione e' un ERRORE (la risposta c'era). Su B e C e' la risposta GIUSTA.")
shutil.rmtree(BASE, ignore_errors=True)
