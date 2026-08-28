r"""F1 - misuro il PASSO 0 che ho proposto: astenersi sulle fonti TABELLARI.

Avevo concluso (`ws5-F1-i-residui-letti-a-mano.py`) che `L4.3` su fonti
tabellari produce solo rumore e sulla prosa coglie 15 scambi su 16. Proporre una
cura non basta: qui la misuro, **col controllo che puo' bocciarla**.

ESITO IN TRE RIGHE: **la mia prima euristica e' CADUTA al controllo, la seconda
lo passa, e nemmeno la seconda risolve** — mitiga.

    v1  >=60% righe con un numero      prosa dichiarata tabellare 3/5  <== CADUTA
    v2  riga densa di numeri, povera   prosa 0/5  ·  tabelle 3/3       <== passa
    sul corpus: SEGNALA 66,1% -> 19,7%, ma il layer TACE sul 63,4% delle fonti
    sui 19 falsi positivi che avevo LETTO: ne spegne 14, **5 SOPRAVVIVONO**

⇒ **I 5 superstiti includono la forma pura del difetto**: i tre claim veri sullo
stesso span (`208 fatti` · `95 fatti` · `1322 fatti`), che il passo 0 NON
riconosce come tabellare perche' quelle righe hanno parole vere. ⇒ **Il passo 0
che avevo proposto non e' la cura: e' una mitigazione parziale**, e il caso che
mi aveva convinto a proporlo e' fra quelli che sopravvivono.

L'EURISTICA v1, dichiarata prima di misurare e poi caduta:
    una fonte e' TABELLARE se ha almeno 3 righe non vuote
    e almeno il 60% di quelle righe contiene un numero
La v2 guarda la RIGA invece del documento: una riga e' di tabella se porta
almeno due numeri, oppure un numero e al massimo sei parole. Nella prosa una
riga e' una FRASE; in una tabella e' un RECORD.

⚠️ IL CONTROLLO CHE CONTA NON E' LA POPOLAZIONE A'. Le mie fonti A'/B' stanno
su UNA riga: qualunque euristica basata sui newline le lascerebbe passare, e la
«sensibilita' invariata» sarebbe vera per costruzione, cioe' senza informazione.
⇒ Il controllo vero e' una **popolazione P di PROSA MULTILINEA con numeri** —
un contratto con gli articoli a capo. Se il passo 0 la dichiara tabellare,
l'euristica e' troppo grossolana e **spegne il layer proprio sui documenti per
cui esiste**. E' li' che questa cura puo' fallire.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-F1-il-passo-zero-sulle-fonti-tabellari.py
"""
import contextlib
import importlib.util
import io
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.config import CONFIG

_B = Path(__file__).parent / "ws5-F1-i-falsi-positivi-sul-corpus-vero.py"
_sp = importlib.util.spec_from_file_location("_cv", _B)
_cv = importlib.util.module_from_spec(_sp)
with contextlib.redirect_stdout(io.StringIO()):
    _sp.loader.exec_module(_cv)
_val = _cv._val

_NUM = re.compile(r"\d")


_PAR = __import__("re").compile(r"[^\W\d_]+", __import__("re").UNICODE)
_CIFRA = __import__("re").compile(r"(?<![\w.])\d+(?:[.,]\d+)?")


def e_tabellare_v1(fonte):
    """PRIMA euristica: >=3 righe e >=60% con un numero. CADUTA nel blocco A."""
    righe = [r for r in fonte.splitlines() if r.strip()]
    if len(righe) < 3:
        return False
    return sum(1 for r in righe if _NUM.search(r)) / len(righe) >= 0.60


def e_tabellare_v2(fonte):
    """SECONDA: una RIGA e' di tabella se e' densa di numeri e povera di parole.

    Nasce dalla caduta della v1: nella prosa una riga e' una FRASE (molte
    parole, un numero); in una tabella e' un RECORD (pochi token alfabetici,
    piu' numeri). Il criterio guarda la riga, non il documento.
    """
    righe = [r for r in fonte.splitlines() if r.strip()]
    if len(righe) < 3:
        return False
    def riga_tabellare(r):
        n = len(_CIFRA.findall(r))
        w = len(_PAR.findall(r))
        if n == 0:
            return False
        return n >= 2 or w <= 6
    return sum(1 for r in righe if riga_tabellare(r)) / len(righe) >= 0.60


e_tabellare = e_tabellare_v2


# ---- P : PROSA MULTILINEA con numeri. Il passo 0 NON deve scattare qui ------
P = [
 ("contratto, articoli a capo",
  "Art. 1 - Oggetto.\nIl locatore concede in locazione l'immobile sito in via Roma.\n"
  "Art. 2 - Canone.\nIl canone mensile e' fissato in 1200 euro.\n"
  "Art. 3 - Deposito.\nIl conduttore versa un deposito di 2400 euro."),
 ("referto medico a paragrafi",
  "Anamnesi.\nIl paziente riferisce astenia da tre settimane.\n"
  "Terapia.\nSi prescrive metformina 850 mg due volte al giorno.\n"
  "Controllo.\nSi programma una visita fra 30 giorni."),
 ("verbale con elenco discorsivo",
  "Il consiglio si e' riunito in data odierna.\n"
  "Il primo punto riguarda il bilancio, che chiude con un utile di 45000 euro.\n"
  "Il secondo punto riguarda l'assunzione di 3 tecnici.\n"
  "La seduta si e' chiusa alle 18."),
 ("email in prosa con importi",
  "Buongiorno,\nconfermo l'ordine di 250 pezzi come da vostra offerta.\n"
  "Il prezzo unitario resta 12 euro.\nLa consegna e' prevista entro 30 giorni.\n"
  "Cordiali saluti."),
 ("prosa lunga, un numero solo",
  "La riunione preliminare si e' tenuta ieri.\n"
  "Sono emerse alcune criticita' sul fornitore.\n"
  "Il termine di consegna resta fissato in 30 giorni.\n"
  "Restiamo in attesa di riscontro."),
]

# ---- T : fonti dichiaratamente tabellari. Il passo 0 DEVE scattare ---------
T = [
 ("tabella a colonne", "giorno  8.2  99.3\nmese  0.6  1.1\ncolore  0.9  0.7\n"),
 ("log a righe", "write #1: 25.94s RAM 893 MB\nwrite #2: 6.27s RAM 1940 MB\n"
                 "write #3: 0.37s RAM 1978 MB\n"),
 ("referto a tre domande", "«quanti fatti ha il corpus?» 208 fatti\n"
                           "«how many facts?» 95 fatti\n"
                           "«quante volte ha parlato il gate?» 1322 fatti\n"),
]


def main():
    print("=== A: le DUE euristiche sulle popolazioni di controllo ===")
    for et, fn in (("v1  >=60% righe con un numero", e_tabellare_v1),
                   ("v2  riga densa di numeri e povera di parole", e_tabellare_v2)):
        fp1 = [n for n, f in P if fn(f)]
        t1 = [n for n, f in T if fn(f)]
        print("  %-44s prosa dichiarata tabellare %d/%d  ·  tabelle riconosciute %d/%d %s"
              % (et, len(fp1), len(P), len(t1), len(T),
                 "" if not fp1 else "<== SPEGNE LA PROSA: " + ", ".join(fp1)))
    print()
    fp_p = [n for n, f in P if e_tabellare(f)]
    ok_t = [n for n, f in T if e_tabellare(f)]
    print("  PROSA multilinea  : dichiarate tabellari %d su %d   %s"
          % (len(fp_p), len(P), "<== il passo 0 SPEGNE la prosa" if fp_p else "(nessuna: bene)"))
    for n in fp_p:
        print("      FALSO TABELLARE: %s" % n)
    print("  TABELLE vere      : dichiarate tabellari %d su %d   %s"
          % (len(ok_t), len(T), "" if len(ok_t) == len(T) else "<== ne manca"))
    if len(ok_t) < len(T):
        for n, f in T:
            if not e_tabellare(f):
                print("      MANCATA: %s" % n)
    if not ok_t:
        print("  !! il passo 0 non riconosce NESSUNA tabella: il banco non separa.")
        return

    print("\n=== B: quanto rumore toglie sul CORPUS VERO, e quanto layer spegne ===")
    p = Path(str(CONFIG.semantic_db))
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    righe = con.execute(
        "select proposition, grounding_span from facts where grounding_score >= 90 "
        "and grounding_span is not null and length(grounding_span) > 20 "
        "and superseded_by is null order by created_at desc limit 4000").fetchall()
    con.close()
    giud = seg = seg_dopo = tab = 0
    for prop, span in righe:
        if not ({v for _, v in _val.extract_quantities(prop)}
                & {v for _, v in _val.qty(span)}):
            continue
        giud += 1
        e, _d = _val.L43_finale(prop, span, "S")
        if e == "SEGNALA":
            seg += 1
            if not e_tabellare(span):
                seg_dopo += 1
        if e_tabellare(span):
            tab += 1
    print("  giudicabili                       %4d" % giud)
    print("  di cui su fonte TABELLARE         %4d  (%.1f%%)  <- il layer tacerebbe qui"
          % (tab, 100.0 * tab / max(giud, 1)))
    print("  SEGNALA senza passo 0             %4d  (%.1f%%)" % (seg, 100.0 * seg / max(giud, 1)))
    print("  SEGNALA con    passo 0            %4d  (%.1f%%)"
          % (seg_dopo, 100.0 * seg_dopo / max(giud, 1)))

    print("\n=== C: CONTROLLO - la sensibilita' sulla PROSA regge? ===")
    colti = sum(1 for _n, c, f in _val.A1
                if not e_tabellare(f) and _val.L43_finale(c, f, "S")[0] == "SEGNALA")
    fp = sum(1 for _n, c, f in _val.B1
             if not e_tabellare(f) and _val.L43_finale(c, f, "S")[0] == "SEGNALA")
    print("  scambi costruiti colti  %d su %d" % (colti, len(_val.A1)))
    print("  falsi positivi          %d su %d" % (fp, len(_val.B1)))
    print("  ⚠️ questo controllo e' DEBOLE e lo dichiaro: le fonti A'/B' stanno su una")
    print("     riga sola, quindi il passo 0 non poteva toccarle. Il controllo che")
    print("     conta e' il blocco A, sulla prosa MULTILINEA.")


if __name__ == "__main__":
    main()


# ---- D: i 18 residui che ho LETTO sopravvivono al passo 0? ------------------
def d_sui_letti():
    _L = Path(__file__).parent / "ws5-F1-i-residui-letti-a-mano.py"
    _s = importlib.util.spec_from_file_location("_lt", _L)
    _m = importlib.util.module_from_spec(_s)
    with contextlib.redirect_stdout(io.StringIO()):
        _s.loader.exec_module(_m)
    ids = set(_m.LETTURA)
    p = Path(str(CONFIG.semantic_db))
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    q = ",".join("?" * len(ids))
    righe = con.execute(
        "select id, grounding_span from facts where id in (%s)" % q, tuple(ids)).fetchall()
    con.close()
    print("\n=== D: i residui che ho LETTO (tutti giudicati FALSI POSITIVI) ===")
    vivi = [i for i, sp in righe if not e_tabellare(sp)]
    print("  ritrovati nel corpus            %d su %d" % (len(righe), len(ids)))
    print("  dichiarati TABELLARI dal passo 0 %d  -> il passo 0 li spegne"
          % (len(righe) - len(vivi)))
    print("  SOPRAVVIVONO al passo 0          %d  %s"
          % (len(vivi), "<== questi restano falsi positivi" if vivi else "(nessuno)"))
    for i in vivi:
        print("      %s" % i)


d_sui_letti()
