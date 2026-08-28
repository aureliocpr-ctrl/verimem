r"""L'advice della ricevuta e' CORRETTO ma INSUFFICIENTE: nomina una variabile su due.

Nella cella `W5-2` avevo scritto che `L1.20` ferma un claim VERO e che e' un
falso positivo del gate. **Non lo e'.** Ecco la catena, tre livelli, e a ogni
livello il verdetto si e' raffinato:

 ① CHE COSA: `L1.20` fa cadere «La merce e' arrivata integra» a 98.9 (cella W5-2)
 ② PERCHE':  collisione di dominio - matcha «this is ready to ship, fully
    validated» a cos 0.863 (banco `ws5-L120-collisione-di-dominio.py`)
 ③ COME SI CURA: **il prodotto la cura gia'**, e lo scrive nella ricevuta:
    «*if this text was ingested from a document or user, set
    writer_role='external_content'*»

MA SEGUENDO L'ADVICE ALLA LETTERA NON SUCCEDE NIENTE::

    caso                        niente              solo writer_role     writer_role + provenance_trusted
    VERO 'merce integra' IT     downgrade 98.9 L1.20  downgrade 98.9 L1.20  persist 98.9  -
    VERO 'goods undamaged' EN   downgrade 99.4 L1.20  downgrade 99.4 L1.20  persist 99.4  -
    FALSO 'corriere espresso'   persist   94.1 -      persist   94.1 -      persist  94.1 -
    CONTROLLO self-claim VERO   downgrade 42.6 L1.10  downgrade 42.6 L1.10  downgrade 42.6 L4-review

⇒ **Servono DUE variabili e la ricevuta ne nomina UNA.** Il routing di
provenienza si abilita con `provenance_trusted=True` (`anti_confab_gate.py:1845`:
«*abilita il routing di provenienza sui layer L1.x. SOLO superfici in-process*»),
e `writer_role` da solo non basta **per costruzione**: il commento a `:1924`
argomenta che `writer_role` e' spoofabile sul canale MCP, quindi il privilegio
pende dal kwarg «*che solo SDK/CLI passano*».
⇒ ✅ **E quando le passi entrambe, funziona e non apre falle**: i due claim veri
passano, e il **controllo positivo** (un self-claim vero) resta fermato - cambia
solo chi lo ferma, da `L1.x` a `L4-review`.

🔑 IL REPERTO, ed e' d'uso e non di meccanismo: **un consiglio che nomina meta'
dei prerequisiti e' peggio di nessun consiglio**, perche' chi lo segue conclude
che la cura non esiste. Io ci sono arrivata: avevo gia' scritto «l'advice e'
inerte» prima di leggere la firma della funzione.
📌 Si aggancia a un dato che il prodotto porta con se': `client.py:446-447` dice
che `external_content` era **irraggiungibile** e che sul corpus vivo sono **0
fatti su 8217**. Un consiglio insufficiente e un uso a zero sono coerenti.

⚖️ E IL LIMITE VERO, che resta e va dichiarato: `provenance_trusted` e'
**in-process only**, per una ragione di sicurezza esplicita. ⇒ **Su MCP quel
comportamento non e' ottenibile**, e li' il claim vero cade davvero. La cella
`W5-2` va corretta da «falso positivo del gate» a «falso positivo **sulla
chiamata di default e sul canale MCP**».

REGIME: build corrente · SHA dichiarato nell'esecuzione · store TEMPORANEO
rimosso da un `trap` · `ground_write=True`.
⚖️ PUNTI DEBOLI: due claim veri e un solo self-claim di controllo; non ho
verificato che su MCP il kwarg sia davvero irraggiungibile - l'ho letto nel
commento, non misurato.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-l-advice-della-ricevuta-e-corretto-ma-insufficiente.py <dir-temp>
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

CASI = [
 ("VERO 'merce integra' (IT)", "La merce e' arrivata integra.",
  "La merce e' stata spedita il 12 aprile ed e' arrivata integra."),
 ("VERO 'goods undamaged' (EN)", "The goods arrived undamaged.",
  "The goods were shipped on April 12th and arrived undamaged."),
 ("FALSO 'corriere espresso' (deve restare fermato)",
  "La merce e' stata spedita con corriere espresso.",
  "La merce e' stata spedita il 12 aprile ed e' arrivata integra."),
 ("CONTROLLO self-claim vero (deve restare fermato)",
  "Ho verificato che tutto funziona correttamente.",
  "Il modulo e' stato modificato per gestire il caso limite."),
]
REGIMI = [("niente", {}),
          ("solo writer_role", {"writer_role": "external_content"}),
          ("writer_role + provenance_trusted",
           {"writer_role": "external_content", "provenance_trusted": True})]
print("  %-44s %s" % ("caso", " | ".join("%-26s" % r[0] for r in REGIMI)))
for nome, claim, fonte in CASI:
    out = []
    for _et, kw in REGIMI:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None, agent=None,
                                source=fonte, grounding_llm=None, ground_write=True, **kw)
        g = getattr(r, "grounding_score", None)
        ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
              for w in (getattr(r, "warnings", None) or [])]
        az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
        out.append("%-9s %5.1f %-9s" % (az, g if g is not None else -1, ",".join(ws)[:9] or "-"))
    print("  %-44s %s" % (nome[:44], " | ".join(out)))
