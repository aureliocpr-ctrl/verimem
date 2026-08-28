r"""`norm(v)` chiude cinque buchi e ne apre cinque - **la cura non va scritta come veto**.

Il normalizzatore di numerali era **il pezzo assegnato a me** nel design F1 di
@ws3 («*`norm(v)`: pezzo separato, di @ws5, che serve anche a `L4.1`*») e non
l'ho mai scritto. Prima di scriverlo l'ho **prototipato nello scratchpad** e
misurato sui **due versi**. Il risultato dice di **non scriverlo come l'avevo
pensato**::

    A) I BUCHI - il claim inventa un numero a parole
       IT settantamila      estrattore=[]  norm=[70000.0]           OK
       IT dodici            estrattore=[]  norm=[12.0]              OK
       IT ventiquattro      estrattore=[]  norm=[24.0]              OK
       EN seventy thousand  estrattore=[]  norm=[1000.0, 70000.0]   OK
       EN twelve            estrattore=[]  norm=[12.0]              OK
       chiusi **5 su 5**

    B) GLI OMONIMI - il numerale NON e' una quantita'
       «tre giorni fa»                    norm=[3.0]    <== INVENTA
       «il controllo e' stato fatto due volte»  norm=[2.0]    <== INVENTA
       «sei sicuro che la consegna...»    norm=[6.0]    <== INVENTA
       «i venti di nord-ovest»            norm=[20.0]   <== INVENTA
       «one of the tests failed»          norm=[1.0]    <== INVENTA
       «the check often fails»            norm=[]
       puliti **1 su 6** (e l'unico pulito lo e' per il ``, non per merito)

⇒ **Chiude cinque buchi e ne apre cinque: rapporto 1 a 1.** Un normalizzatore
usato come **veto** trasformerebbe la classe `numerale-a-parole` da «*il falso
passa*» a «*il vero cade*» - lo stesso danno doppio che ho misurato su
`omissione` nella cella `W5-2`, solo spostato.

🔑 **E IL PRODOTTO AVEVA GIA' RAGIONE.** Il docstring di
`assenti_che_la_fonte_scrive_a_parole` dice: «*serve a DECLASSARE, mai ad
ammettere... un omonimo qui costa un avviso in piu' su un fatto che entra, non
un numero inventato che passa*». ⇒ La mia misura **conferma quella scelta dal
verso opposto**: loro l'avevano argomentata sul verso coperto, io la misuro sul
verso scoperto e arrivo allo stesso punto.
⇒ **Se `norm(v)` si scrive, si scrive come AVVISO.** Come veto no, e adesso c'e'
il numero che lo dice.

⚖️ PUNTI DEBOLI: il prototipo e' **grezzo di proposito** (una manciata di
numerali, due lingue, nessuna analisi grammaticale) - un normalizzatore vero
con disambiguazione potrebbe fare molto meglio sugli omonimi. ⇒ **Questo banco
NON dice «il normalizzatore e' impossibile»: dice che la versione ingenua costa
quanto rende**, e che chi lo scrive deve portare la popolazione B degli omonimi
insieme a quella dei buchi. Sei omonimi non sono un campione.

REGIME: build corrente · **nessun modello caricato** · **nessuna riga scritta
nel prodotto**: il prototipo vive qui.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-norm-chiude-cinque-buchi-e-ne-apre-cinque.py
"""
import re, sys
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.quantity_match import extract_quantities as EQ
from verimem.valore_non_nella_fonte import valori_non_nella_fonte as L41

# prototipo minimo: solo i numerali che servono al caso, IT+EN
UNI_IT = {"zero":0,"uno":1,"due":2,"tre":3,"quattro":4,"cinque":5,"sei":6,"sette":7,
          "otto":8,"nove":9,"dieci":10,"undici":11,"dodici":12,"venti":20,"trenta":30,
          "cento":100,"mille":1000,"mila":1000}
UNI_EN = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,
          "eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,"twenty":20,"thirty":30,
          "hundred":100,"thousand":1000}
_COMPOSTI_IT = {"settantamila":70000,"ventiquattro":24,"quarantacinque":45}
_RE_EN_COMP = re.compile(r"\b(seventy|sixty|fifty|forty|thirty|twenty)[- ]?(thousand|one|two|three|four|five|six|seven|eight|nine)?\b", re.I)

def norm(testo):
    """numerali -> valori. Prototipo grezzo: dichiara cosa NON fa."""
    out = set()
    t = testo.lower()
    for w, v in _COMPOSTI_IT.items():
        if w in t:
            out.add(float(v))
    m = _RE_EN_COMP.search(t)
    if m:
        dec = {"seventy":70,"sixty":60,"fifty":50,"forty":40,"thirty":30,"twenty":20}[m.group(1)]
        if m.group(2) == "thousand":
            out.add(float(dec * 1000))
        elif m.group(2):
            out.add(float(dec + UNI_EN.get(m.group(2), 0)))
        else:
            out.add(float(dec))
    for w, v in list(UNI_IT.items()) + list(UNI_EN.items()):
        if re.search(r"\b%s\b" % w, t):
            out.add(float(v))
    return out

# ---- A: i buchi. Il claim inventa un numero a parole ------------------------
BUCHI = [
 ("IT settantamila", "Il fatturato annuo e' di settantamila euro.", 70000.0),
 ("IT dodici",       "I dipendenti assunti sono dodici.", 12.0),
 ("IT ventiquattro", "La garanzia dura ventiquattro mesi.", 24.0),
 ("EN seventy thousand", "The annual revenue is seventy thousand euro.", 70000.0),
 ("EN twelve",       "Twelve employees were hired.", 12.0),
]
print("=== A: norm() estrae il valore che l'estrattore non vede? ===")
ok = 0
for nome, claim, atteso in BUCHI:
    v = norm(claim)
    hit = atteso in v
    ok += hit
    print("  %-22s estrattore=%-6s norm=%-22s %s"
          % (nome, str(sorted(EQ(claim))), str(sorted(v))[:22], "OK" if hit else "<== MANCATO"))
print("  chiusi %d su %d" % (ok, len(BUCHI)))

# ---- B: gli OMONIMI. Qui norm() puo' fare danno ----------------------------
OMONIMI = [
 ("'tre' in una data",      "La riunione si e' tenuta tre giorni fa."),
 ("'due' avverbiale",       "Il controllo e' stato fatto due volte."),
 ("'sei' verbo essere",     "Sei sicuro che la consegna sia avvenuta?"),
 ("'venti' sostantivo",     "I venti di nord-ovest hanno ritardato la nave."),
 ("'one' pronome EN",       "One of the tests failed."),
 ("'ten' dentro 'often'",   "The check often fails."),
]
print("\n=== B: e sugli OMONIMI, quanti valori INVENTA? ===")
sporchi = 0
for nome, t in OMONIMI:
    v = norm(t)
    if v:
        sporchi += 1
    print("  %-26s norm=%-18s %s" % (nome, str(sorted(v))[:18], "<== INVENTA UN VALORE" if v else ""))
print("  puliti %d su %d" % (len(OMONIMI) - sporchi, len(OMONIMI)))
