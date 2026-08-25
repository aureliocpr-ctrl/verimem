# -*- coding: utf-8 -*-
"""Q2 — ATTRIBUZIONE: quale FAMIGLIA del giudice chiude la classe F-NEG?

Il banco dell'osservatore misura CHE la classe F-NEG e' chiusa (0/8 falsita'
ammesse, IT e EN). Non dice CHI la chiude, e la differenza decide la direzione:

  - se la chiude il LESSICALE (L1*), la chiusura vale solo dove esistono le
    liste di parole — misurato in casa: `_has_negator` e' False su KO/TH/HI/TR;
  - se la chiude il SEMANTICO (L4 grounding, CE multilingue per
    local_grounding.py:391), la chiusura segue il CE in ogni lingua che regge.

L'INTERRUTTORE, e perche' e' un A/B onesto: `ENGRAM_L1_DOMAIN_ADVISORY=1`
e' documentato in anti_confab_gate.py:241-273 come «rilassa SOLO la famiglia
L1* — ogni layer startswith("L1"); L3 e L4 portano etichette che startswith
("L1") NON matcha, quindi restano fail-closed». Spegne UNA famiglia sola.

PREDIZIONE DICHIARATA PRIMA DELLA MISURA (B3) — split, non blocco unico:
  «Tutti i test degli ordini passano» e' una self-claim di codice, bersaglio
  NATIVO di L1 ⇒ con ADVISORY=1 PASSA.
  «no refund…», «no region…», «no migration…» non sono self-claim ⇒ L1 non
  li tocca ⇒ RESTANO FERMI (li chiude L4).
  Se restano fermi tutti e otto, l'attribuzione al lessicale e' FALSA.

⚖️ CONTROLLO POSITIVO, senza il quale il numero non significa niente: i 4
V-CIT delle STESSE fonti. Devono restare ammessi in entrambi i regimi — se
l'interruttore li muove, fa piu' di quello che dichiara e l'A/B non e' pulito.

📌 I casi sono ESTRATTI con ast dal file dell'osservatore, non ricopiati: un
caso riscritto a memoria misura la memoria di chi lo scrive.
📌 `g` e' None quando la ricevuta non stampa un grounding — il banco di
partenza ci metteva 100.0, che si legge come un punteggio pieno e non lo e'.

Regime: store TEMPORANEO vuoto, porta pubblica `verimem remember --source`,
FUORI pytest (sotto pytest l'embedder e' uno stub SHA-256).
Uso:  python ws3-quale-famiglia-chiude-la-classe.py {base|advisory}
"""
import ast
import contextlib
import io
import os
import re
import sys
import tempfile

REGIME = (sys.argv[1] if len(sys.argv) > 1 else "base").lower()
if REGIME not in ("base", "advisory"):
    raise SystemExit("regime: base | advisory")

STORE = tempfile.mkdtemp(prefix="ws3_famiglia_%s_" % REGIME)
os.environ["HIPPO_DATA_DIR"] = STORE
os.environ["ENGRAM_DATA_DIR"] = STORE
os.environ["HIPPO_RERANK_PRELOAD"] = "0"
if REGIME == "advisory":
    os.environ["ENGRAM_L1_DOMAIN_ADVISORY"] = "1"
else:
    os.environ.pop("ENGRAM_L1_DOMAIN_ADVISORY", None)

BANCO = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(BANCO, "..", "banco-osservatore-il-tasso.py")

_src = open(FONTE, encoding="utf-8").read()
CORPUS = None
for _n in ast.parse(_src).body:
    if isinstance(_n, ast.Assign) and getattr(_n.targets[0], "id", "") == "CORPUS":
        CORPUS = ast.literal_eval(_n.value)
if CORPUS is None:
    raise SystemExit("IL BANCO SI RIFIUTA: CORPUS non estratto dal file dell'osservatore")

from verimem.cli import main  # noqa: E402

#: le classi che ci interessano: la chiusa (F-NEG) e il controllo positivo (V-CIT)
CLASSI = ("F-NEG", "V-CIT")
CASI = []
for fid, s_it, s_en, claims in CORPUS:
    for c_it, c_en, vero, cl in claims:
        if cl not in CLASSI:
            continue
        CASI.append((fid, "IT", cl, vero, c_it, s_it))
        CASI.append((fid, "EN", cl, vero, c_en, s_en))

_LAYER = re.compile(r"\b(L1(?:\.\d+)?|L3[\w-]*|L4(?:\.\d+)?[\w-]*|store-screen)\b")


def esegui(claim, source):
    """La porta PUBBLICA, come la usa chi installa. Ritorna (esito, g, layer)."""
    buf = io.StringIO()
    sys.argv = ["verimem", "remember", claim, "--source", source]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            main()
    except SystemExit:
        pass
    except Exception as e:                                    # noqa: BLE001
        return "ECCEZIONE", None, type(e).__name__
    out = buf.getvalue()
    esito = ("admitted" if re.search(r"\badmitted\b", out)
             else "quarantined" if re.search(r"\bquarantined\b", out) else "?")
    m = re.search(r"grounding ([\d.]+)", out)
    layer = "+".join(sorted(set(_LAYER.findall(out)))) or "-"
    return esito, (float(m.group(1)) if m else None), layer


print("=" * 96)
print("  REGIME: %s   (ENGRAM_L1_DOMAIN_ADVISORY=%s)"
      % (REGIME.upper(), os.environ.get("ENGRAM_L1_DOMAIN_ADVISORY", "<unset>")))
print("  store temporaneo vuoto: %s" % STORE)
print("=" * 96)
print("%-10s %-3s %-6s %-6s %-12s %8s  %s"
      % ("fonte", "lg", "classe", "vero", "esito", "g", "layer"))
righe = []
for fid, lang, cl, vero, claim, src in CASI:
    esito, g, layer = esegui(claim, src)
    righe.append((fid, lang, cl, vero, esito, g, layer, claim))
    print("%-10s %-3s %-6s %-6s %-12s %8s  %s"
          % (fid, lang, cl, "SI" if vero else "no", esito,
             ("%.1f" % g) if g is not None else "-", layer))

fneg = [r for r in righe if r[2] == "F-NEG"]
vcit = [r for r in righe if r[2] == "V-CIT"]
amm = sum(1 for r in fneg if r[4] == "admitted")
ctrl = sum(1 for r in vcit if r[4] == "admitted")
print()
print("  F-NEG ammesse (= falsita' PASSATE) ... %d/%d" % (amm, len(fneg)))
print("  CONTROLLO V-CIT ammessi (attesi tutti) %d/%d" % (ctrl, len(vcit)))
print("  REGIME=%s" % REGIME)
