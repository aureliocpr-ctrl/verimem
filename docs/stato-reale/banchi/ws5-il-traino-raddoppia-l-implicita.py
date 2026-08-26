r"""Il traino preso dalla fonte RADDOPPIA l'implicita in italiano (3/10 -> 6/10)
e in inglese la APRE (0/10 -> 2/10). L'esplicita resta 0/10 in tutte e due.

Incrocia due variabili misurate separatamente da due istanze diverse:
  · @ws3 (`ws3-la-contraddizione-implicita.py`): contraddizione IMPLICITA vs
    ESPLICITA. Suoi numeri: IT implicita 3/10, IT esplicita 0/10, EN 0/10 su
    entrambe.
  · @ws5 (`tests/test_una_falsita_in_compagnia_non_deve_passare.py`): una falsita'
    accompagnata da una verita' PRESA DALLA FONTE entra a 100.0, la stessa falsita'
    con una verita' qualunque e' bloccata a 0.7.

Nessuna delle due aveva misurato le celle incrociate. Il traino e' il `vero` del
banco di ws3, che e' per costruzione preso dalla fonte::

    IT implicita  SOLA      ammesse  3/10   g piu' alti: 99.9, 95.9, 87.7
    IT esplicita  SOLA      ammesse  0/10   g piu' alti: 6.1, 4.7, 3.7
    IT implicita +TRAINO    ammesse  6/10   g piu' alti: 99.9, 99.7, 99.6
    IT esplicita +TRAINO    ammesse  0/10   g piu' alti: 11.7, 4.7, 4.6
    EN implicita  SOLA      ammesse  0/10   g piu' alti: 9.6, 1.6, 1.3
    EN esplicita  SOLA      ammesse  0/10   g piu' alti: 4.3, 3.5, 2.8
    EN implicita +TRAINO    ammesse  2/10   g piu' alti: 98.7, 92.6, 48.3
    EN esplicita +TRAINO    ammesse  0/10   g piu' alti: 12.0, 5.7, 4.6

    IT implicita +TRAINO    passano: deceduto, dimissioni, scaduto, vuoto, annullata, sospeso
    EN implicita +TRAINO    passano: fallimento, vuoto

🔑 IL CONTROLLO E' DENTRO LA MISURA, ed e' la ragione per cui le quattro celle
«SOLA» sono qui: riproducono il 3/10, lo 0/10 e i due 0/10 EN di ws3. Se non
fossero tornate, starei misurando a un livello diverso dal suo e l'incrocio non
direbbe niente — la lezione «il livello a cui misuri decide il verdetto», che in
questo repo ha gia' prodotto cinque ritiri in un giorno.

⇒ ① IL TRAINO NON FA LA STESSA COSA NELLE DUE LINGUE. In italiano RADDOPPIA una
strada che esisteva (3 -> 6). In inglese ne APRE una che non esisteva (0 -> 2), e
non di striscio: 98.7 e 92.6.
⚠️ La prima stesura di questo banco diceva «il traino non apre una strada nuova,
la raddoppia». Era vero sui soli dieci casi italiani ed e' FALSO in inglese. La
riga e' rimasta in piedi venti minuti, il tempo di misurare la meta' che avevo
dichiarato come limite invece di lasciarla li'.

⇒ ② SUL PAVIMENTO ZERO DELL'INGLESE non c'era niente da raddoppiare, e infatti
non e' un raddoppio: e' una comparsa. ⇒ UNA CELLA A ZERO NON DICE «QUI NON SI
PASSA»: dice «qui non si passa CON QUESTO CLAIM». Cambia il claim di una frase
presa dalla fonte e lo zero si muove. Chi legge «EN 0/10» come una garanzia sta
leggendo un limite come un'assicurazione.

⇒ ③ E LA NEGAZIONE ESPLICITA E' IMMUNE IN TUTTE E DUE LE LINGUE: 0/10 col traino
esattamente come senza, quattro celle su quattro, e i punteggi restano a UNA
CIFRA (12.0 il massimo) mentre l'implicita col traino sta a 99.9 e 98.7.

⇒ ④ TESI, ed e' quello che le due misure separate non potevano dire: NON C'E' UN
SOLO MECCANISMO. C'e' un VETO lessicale sulla negazione visibile, che il traino
non scavalca in nessuna delle due lingue, e un PUNTEGGIO semantico che il traino
compra in tutte e due. Chi guarda solo il numero del giudice vede una scala
continua e conclude «il CE e' impreciso»; qui si vede che sotto ci sono due cose
diverse, e solo una delle due e' comprabile con la sovrapposizione.

⇒ RICADUTA SULLA VETRINA («a claim the source contradicts does not come back as
truth»): non basta qualificarla con «esplicita». Sulle implicite e' 6/10 in
italiano e 2/10 in inglese appena il claim porta con se' una frase presa dalla
fonte — che e' esattamente cio' che fa un LLM quando riassume. Il caso realistico
non e' il 3 e non e' lo zero.

⚠️ QUELLO CHE QUESTO BANCO NON DICE, e lo dichiaro perche' e' il salto che mi
verrebbe voglia di fare: NON spiega l'asimmetria lasciata aperta nel docstring di
`test_una_falsita_in_compagnia_non_deve_passare.py` (nel dominio dei test una
falsita' passa anche con un valore ASSENTE dalla fonte, nei magazzini no). Che sia
lo stesso veto e' un'IPOTESI: qui il veto e' stato osservato solo sui negatori
espliciti.

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
    for (nome, src_it, vero_it, impl_it, espl_it,
         src_en, vero_en, impl_en, espl_en) in _wb.CASI:
        for lg, src, vero, impl, espl in (("IT", src_it, vero_it, impl_it, espl_it),
                                          ("EN", src_en, vero_en, impl_en, espl_en)):
            for eti, claim in ((lg + " implicita  SOLA", impl),
                               (lg + " esplicita  SOLA", espl),
                               (lg + " implicita +TRAINO", vero + " " + impl),
                               (lg + " esplicita +TRAINO", vero + " " + espl)):
                ok, g = _ammesso(claim, src)
                celle.setdefault(eti, []).append((nome, ok, g))

    print("")
    for eti in ("IT implicita  SOLA", "IT esplicita  SOLA",
                "IT implicita +TRAINO", "IT esplicita +TRAINO",
                "EN implicita  SOLA", "EN esplicita  SOLA",
                "EN implicita +TRAINO", "EN esplicita +TRAINO"):
        righe = celle[eti]
        n = sum(1 for _, ok, _ in righe if ok)
        alti = sorted((g for _, _, g in righe), reverse=True)[:3]
        print("%-23s ammesse %2d/10   g piu' alti: %s"
              % (eti, n, ", ".join("%.1f" % x for x in alti)))
    print("")
    for eti in ("IT implicita +TRAINO", "EN implicita +TRAINO"):
        p = [nome for nome, ok, _ in celle[eti] if ok]
        print("%-23s passano: %s" % (eti, ", ".join(p) if p else "(nessuno)"))


if __name__ == "__main__":
    main()
