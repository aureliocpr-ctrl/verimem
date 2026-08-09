# -*- coding: utf-8 -*-
"""FETTA ④ — IL PERCORSO DI LETTURA. Banco 1: le porte sui FATTI.

Task #1 di Aurelio: «come gestiamo le informazioni? ... se un utente la installa
cosa fa?». La mia fetta e' il percorso di LETTURA: `recall`, `search`, `ask`,
`trust_report` (+ `search-docs` nel banco 2).
Regola del task: **ogni riga ESEGUITA, non letta.**

Corpus: un'aziendina italiana, 10 fatti, scritti come li scriverebbe un utente.
Domande di tre tipi:
  A  RISPONDIBILI  — la risposta e' nel corpus
  B  SENZA RISPOSTA — il corpus non la contiene (**il caso che conta**: e' qui
     che una memoria verificata dovrebbe distinguersi da un motore di ricerca)
  C  TRABOCCHETTO  — la risposta sembra esserci ma il corpus dice altro

Store ISOLATO (non tocco la memoria di casa). Il codice e' quello del branch
corrente, in sola lettura.
"""
import os, sys, io, contextlib, tempfile, shutil, json

REPO = r"C:\Users\aurel\Code\HippoAgent"
BASE = tempfile.mkdtemp(prefix="stato4_")
os.environ["HIPPO_DATA_DIR"] = BASE
sys.path.insert(0, REPO)
from verimem.cli import app as cli_app
from verimem import Memory

FATTI = [
 ("Il magazzino di Verona contiene 480 unita.", "Inventario di gennaio. Il magazzino di Verona contiene 480 unita."),
 ("Il pagamento delle fatture e fissato a 60 giorni.", "Contratto quadro. Il pagamento delle fatture e fissato a 60 giorni."),
 ("La responsabile della qualita e Anna Ferri.", "Organigramma. La responsabile della qualita e Anna Ferri."),
 ("Gli interessi di mora sono del 4 per cento annuo.", "Contratto quadro. Gli interessi di mora sono del 4 per cento annuo."),
 ("Il turno di notte inizia alle 22.", "Regolamento interno. Il turno di notte inizia alle 22."),
 ("L ufficio legale ha sede a Roma.", "Organigramma. L ufficio legale ha sede a Roma."),
 ("La polizza assicurativa copre fino a 2 milioni di euro.", "Polizza 2026. La polizza assicurativa copre fino a 2 milioni di euro."),
 ("Il contratto C-12 scade il 31 dicembre 2027.", "Contratto C-12. Il contratto C-12 scade il 31 dicembre 2027."),
 ("Il fornitore principale e la ditta Rossi.", "Elenco fornitori. Il fornitore principale e la ditta Rossi."),
 ("Le scorte minime sono 200 pezzi.", "Regolamento interno. Le scorte minime sono 200 pezzi."),
]
def salva(prop, src, topic):
    b = io.StringIO()
    try:
        with contextlib.redirect_stdout(b), contextlib.redirect_stderr(b):
            cli_app(["save", prop, "--topic", topic, "--source", src], standalone_mode=False)
    except SystemExit:
        pass
    except Exception as e:
        b.write("[EXC %s]" % e)
    return b.getvalue()

print("### PREPARAZIONE — scrivo 10 fatti come farebbe un utente\n")
for i, (p, s) in enumerate(FATTI):
    salva(p, s, "azienda/%d" % i)
m = Memory(os.path.join(BASE, "semantic", "semantic.db"))

DOMANDE = [
 ("A", "Quante unita ci sono nel magazzino di Verona?", "480"),
 ("A", "Chi e la responsabile della qualita?", "Anna Ferri"),
 ("A", "A quanti giorni e fissato il pagamento?", "60"),
 ("B", "Qual e il fatturato del 2025?", None),
 ("B", "Quanti dipendenti ha l azienda?", None),
 ("B", "Chi e l amministratore delegato?", None),
 ("C", "Il magazzino di Trento quante unita contiene?", None),
]

def testo(x):
    if not isinstance(x, dict):
        return str(x)
    return str(x.get("text") or x.get("proposition") or "")

print("\n" + "=" * 104)
print("  PORTA 1 — `recall(domanda)`  : cosa restituisce, in che ordine, con che punteggio")
print("=" * 104)
print("  {:<3} {:<44} {:>8}  {}".format("tipo", "domanda", "punteggio", "primo risultato"))
print("  " + "-" * 100)
astensioni_recall = 0
tot_b = 0
for tipo, q, atteso in DOMANDE:
    res = m.recall(q, k=3)
    lst = res if isinstance(res, list) else res.get("facts", res.get("results", []))
    lst = [x for x in (lst or []) if isinstance(x, dict)]
    if tipo == "B":
        tot_b += 1
        if not lst:
            astensioni_recall += 1
    p = round(lst[0].get("score") or 0, 4) if lst else None
    print("  {:<3}  {:<44} {:>8}  {}".format(
        tipo, q[:42], p if p is not None else "-",
        testo(lst[0])[:46] if lst else "(NESSUN RISULTATO = si astiene)"))
print("\n  >> astensioni sulle domande SENZA RISPOSTA: {}/{}".format(astensioni_recall, tot_b))

print("\n" + "=" * 104)
print("  PORTA 2 — `search(termine)` : quanti ne torna e quale per primo")
print("=" * 104)
print("  {:<3} {:<44} {:>8}  {}".format("tipo", "termine cercato", "quanti", "primo risultato"))
print("  " + "-" * 100)
for tipo, q, atteso in DOMANDE:
    r = m.search(q)
    items = (r.get("facts") or r.get("results") or r.get("items") or []) if isinstance(r, dict) else (r or [])
    print("  {:<3}  {:<44} {:>8}  {}".format(
        tipo, q[:42], len(items), testo(items[0])[:46] if items else "(nessuno)"))

print("\n" + "=" * 104)
print("  PORTA 3 — `ask(domanda)`   : che forma ha la risposta")
print("=" * 104)
for tipo, q, atteso in DOMANDE:
    out = m.ask(q)
    if isinstance(out, dict):
        chiavi = ", ".join(sorted(out.keys()))
        intent = out.get("intent")
        n = len(out.get("results") or []) if "results" in out else out.get("count")
        estratto = ""
        if out.get("results"):
            estratto = testo(out["results"][0])[:40]
        elif "count" in out:
            estratto = "count=%s" % out["count"]
        print("  [{}] {:<42} intent={:<7} n={:<4} {}".format(tipo, q[:40], str(intent), str(n), estratto))
    else:
        print("  [{}] {:<42} -> {}".format(tipo, q[:40], str(out)[:50]))

print("\n" + "=" * 104)
print("  PORTA 4 — `trust_report(domanda)` : ASTIENE quando non sa?")
print("=" * 104)
astensioni_trust = 0
tot_b2 = 0
for tipo, q, atteso in DOMANDE:
    try:
        tr = m.trust_report(q)
    except Exception as e:
        print("  [{}] {:<42} EXC {}".format(tipo, q[:40], type(e).__name__))
        continue
    if isinstance(tr, dict):
        risp = tr.get("answer") or tr.get("verdict") or tr.get("summary") or ""
        ast = bool(tr.get("abstained")) or ("non lo so" in str(risp).lower()) or \
              ("i don't know" in str(risp).lower()) or (not risp)
        if tipo == "B":
            tot_b2 += 1
            if ast:
                astensioni_trust += 1
        print("  [{}] {:<40} astiene={:<6} chiavi={}".format(
            tipo, q[:38], "SI" if ast else "no", ", ".join(sorted(tr.keys()))[:52]))
    else:
        print("  [{}] {:<40} -> {}".format(tipo, q[:38], str(tr)[:50]))
print("\n  >> astensioni di trust_report sulle domande SENZA RISPOSTA: {}/{}".format(
    astensioni_trust, tot_b2))
shutil.rmtree(BASE, ignore_errors=True)
