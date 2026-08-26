# -*- coding: utf-8 -*-
r"""Il traino preso dalla fonte RADDOPPIA la contraddizione implicita: 3/10 -> 6/10.
E non scalfisce l'esplicita: 0/10 -> 0/10.

Incrocia due variabili misurate separatamente da due istanze diverse:
  · @ws3 (`ws3-la-contraddizione-implicita.py`): contraddizione IMPLICITA vs
    ESPLICITA. Suo numero, in italiano: implicita 3/10, esplicita 0/10.
  · @ws5 (`tests/test_una_falsita_in_compagnia_non_deve_passare.py`): una falsita'
    accompagnata da una verita' PRESA DALLA FONTE entra a 100.0, la stessa falsita'
    con una verita' qualunque e' bloccata a 0.7.

Nessuna delle due aveva misurato le due celle incrociate. Il traino qui e' il
`vero_IT` del banco di ws3, che e' per costruzione preso dalla fonte::

    implicita  SOLA      ammesse  3/10   g piu' alti: 99.9, 95.9, 87.7
    esplicita  SOLA      ammesse  0/10   g piu' alti: 6.1, 4.7, 3.7
    implicita +TRAINO    ammesse  6/10   g piu' alti: 99.9, 99.7, 99.6
    esplicita +TRAINO    ammesse  0/10   g piu' alti: 11.7, 4.7, 4.6

    implicita +TRAINO    passano: deceduto, dimissioni, scaduto, vuoto, annullata, sospeso

🔑 IL CONTROLLO E' DENTRO LA MISURA, ed e' la ragione per cui le due celle «SOLA»
sono qui: riproducono il 3/10 e lo 0/10 di ws3. Se non fossero tornate, starei
misurando a un livello diverso dal suo e l'incrocio non direbbe niente — la
lezione «il livello a cui misuri decide il verdetto», che in questo repo ha gia'
prodotto cinque ritiri in un giorno.

⇒ ① I DUE DIFETTI SI COMPONGONO. Il traino non apre una strada nuova: RADDOPPIA
quella che c'era. Sei casi su dieci contro tre, e i tre nuovi (dimissioni, vuoto,
annullata... vedi la riga) passano solo in compagnia.

⇒ ② E LA NEGAZIONE ESPLICITA E' IMMUNE. Zero su dieci con traino esattamente come
senza, e i punteggi restano a una cifra (11.7 il massimo) mentre l'implicita col
traino sta a 99.9. Il traino gonfia il punteggio dell'implicita di ~90 punti e
quello dell'esplicita di ~5.

⇒ ③ TESI, ed e' quello che le due misure separate non potevano dire: NON C'E' UN
SOLO MECCANISMO. C'e' un veto lessicale sulla negazione visibile, che il traino
non scavalca, e un punteggio semantico che il traino gonfia. Chi legge solo il
numero del giudice vede una scala continua e conclude «il CE e' impreciso»; qui
si vede che sotto ci sono due cose diverse, e solo una delle due e' comprabile
con la sovrapposizione.

⚠️ QUELLO CHE QUESTO BANCO NON DICE, e lo dichiaro perche' e' il salto che mi
verrebbe voglia di fare: NON spiega l'asimmetria che avevo lasciato aperta nel mio
docstring (nel dominio dei test una falsita' passa anche con un valore assente
dalla fonte, nei magazzini no). Che sia lo stesso veto e' un'IPOTESI, non un
risultato: qui il veto e' stato osservato solo sui negatori espliciti.

⛔ SOLO ITALIANO. ws3 misura EN implicita 0/10: la cella EN col traino non l'ho
fatta, e finche' non c'e' questo banco non dice niente sull'inglese.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-traino-raddoppia-l-implicita.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA: scrive in HIPPO_DATA_DIR, mai lo store principale.
"""
import importlib.util
import os
import sys

if len(sys.argv) < 2:
    raise SystemExit("uso: %s <dir-temporanea>" % sys.argv[0])
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

_BANCO_WS3 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "ws3-la-contraddizione-implicita.py")
_spec = importlib.util.spec_from_file_location("_banco_ws3", _BANCO_WS3)
_wb = importlib.util.module_from_spec(_spec)
sys.modules["_banco_ws3"] = _wb
try:
    _spec.loader.exec_module(_wb)
except SystemExit:
    #: il banco di ws3 esce da solo se invocato senza argomenti: a noi serve
    #: solo la sua tabella CASI, che a quel punto e' gia' stata definita.
    pass

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402


def _ammesso(claim: str, source: str):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=source, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    return (getattr(r, "action", "?") == "persist",
            g if isinstance(g, (int, float)) else -1.0)


def main() -> None:
    celle: dict[str, list] = {}
    for nome, src, vero, impl, espl, *_ in _wb.CASI:
        for eti, claim in (("implicita  SOLA", impl),
                           ("esplicita  SOLA", espl),
                           ("implicita +TRAINO", vero + " " + impl),
                           ("esplicita +TRAINO", vero + " " + espl)):
            ok, g = _ammesso(claim, src)
            celle.setdefault(eti, []).append((nome, ok, g))

    print("")
    for eti in ("implicita  SOLA", "esplicita  SOLA",
                "implicita +TRAINO", "esplicita +TRAINO"):
        righe = celle[eti]
        n = sum(1 for _, ok, _ in righe if ok)
        alti = sorted((g for _, _, g in righe), reverse=True)[:3]
        print("%-20s ammesse %2d/10   g piu' alti: %s"
              % (eti, n, ", ".join("%.1f" % x for x in alti)))
    print("")
    for eti in ("implicita +TRAINO", "esplicita +TRAINO"):
        p = [nome for nome, ok, _ in celle[eti] if ok]
        print("%-20s passano: %s" % (eti, ", ".join(p) if p else "(nessuno)"))


if __name__ == "__main__":
    main()
