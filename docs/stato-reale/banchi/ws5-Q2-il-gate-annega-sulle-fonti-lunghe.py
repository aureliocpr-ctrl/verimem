# -*- coding: utf-8 -*-
r"""Q2 — SUL REGIME VERO IL GATE ANNEGA: il numero inventato passa a 10000 parole.

    1 frase       VERO=AMM  OMIS=AMM  SFUM=AMM  FALS=blc
    200 parole    VERO=AMM  OMIS=AMM  SFUM=blc  FALS=blc
    1000 parole   VERO=AMM  OMIS=AMM  SFUM=blc  FALS=blc
    3000 parole   VERO=AMM  OMIS=AMM  SFUM=blc  FALS=blc
    10000 parole  VERO=AMM  OMIS=AMM  SFUM=blc  FALS=AMM   <- g=100.0

    VERO-verbatim  ammesso 5/5   g: 100.0 x5
    OMISSIONE      ammesso 5/5   g: 99.7, 100.0, 100.0, 100.0, 100.0
    SFUMATURA      ammesso 1/5   g: 99.6, 44.3, 28.7, 28.7, 0.1
    FALSO-cifra    ammesso 1/5   g: 94.2, 100.0, 100.0, 100.0, 100.0

⛔ IL CONTROLLO CHE DOVEVA FALLIRE **HA FALLITO NEL POSTO PEGGIORE**: `FALSO-cifra`
porta un numero inventato IN CIFRA (22/24 = 92% al posto di 15/24 = 62%) ed e'
bloccato su tutte le fonti corte — poi passa sulla piu' lunga, con grounding 100.0.
Non e' un banco riuscito a meta': e' la risposta alla domanda.

⇒ QUALE LAMA TACE, e dove::

     3000 parole  fonte contiene «15/24»=True  downgrade  layers=L4.1,L4.2
     5000 parole  fonte contiene «15/24»=True  persist    layers=L4.2
    10000 parole  fonte contiene «15/24»=True  persist    layers=L4.2

`L4.1` sparisce fra 3000 e 5000 parole — e la fonte contiene ANCORA il valore vero.
Chiamando direttamente `valori_non_nella_fonte(claim, source)` la soglia si stringe::

    4000 parole (28021 char)  assenti trovati = 1  ['92.0']
    4500 parole (31395 char)  assenti trovati = 0  []

⇒ LA CAUSA, ed e' peggio di un limite di lunghezza — e' una COLLISIONE::

    4000 parole: «92» compare 0 volte nella fonte
    4500 parole: «92» compare 1 volta:
        «...reconcile still misses > ~92% of true updates...»

Il claim inventa «clean-admission 22/24 = **92%**». La fonte, cinquecento parole piu'
in la', parla di un'ALTRA grandezza — quante aggiornamenti la riconciliazione manca —
e per caso dice **92**. `L4.1` confronta valori NUDI, senza contesto: vede un 92 nella
fonte e conclude che il numero non e' inventato.
⇒ **IL GATE NON SI SPEGNE SUL LUNGO: ANNEGA.** Piu' la fonte e' lunga, piu' numeri
contiene, piu' e' probabile che un valore inventato collida con uno vero altrove. Su
un contratto di quaranta pagine quasi ogni numero a due cifre trova un gemello.
🔑 E il difetto **scala con la lunghezza della fonte**, cioe' esattamente nella
direzione del caso d'uso reale: e' tanto peggiore quanto piu' il documento e' vero.

⇒ E LE ALTRE TRE CLASSI DICONO IL RESTO DELLA STORIA:
 · **OMISSIONE 5/5, sempre a 100.0.** «Il gate ha una noise-rejection del 100%» e' VERO
   e tace il 62% di clean-admission che sta nella stessa riga della fonte. Nessun layer
   parla mai. E' la classe piu' pericolosa in un dominio legale: nessuna parola falsa.
 · **SFUMATURA 1/5, e il punteggio CROLLA con la lunghezza** (99.6 → 44.3 → 28.7 → 0.1).
   Piu' la fonte e' lunga, piu' il vago viene rifiutato: e' l'unico comportamento che
   MIGLIORA col regime vero, ed e' anche il piu' severo (un riassunto onesto cade).
 · **VERO-verbatim 5/5 a 100.0**: la popolazione di controllo positiva regge ovunque.

⚖️ IL PUNTO DEBOLE, e lo consegno io: **una fonte sola**. La collisione dipende da
quanti numeri contiene il documento, e `BENCHMARKS.md` e' un testo DENSO di misure —
un contratto ha meno numeri per pagina. ⇒ La soglia «4000-4500 parole» e' di QUESTO
documento, non una costante: su un testo povero di cifre servira' piu' lunghezza, su
un bilancio molto meno. **Il meccanismo e' generale, la soglia no.**
⛔ E un secondo limite: i claim sono quattro, costruiti da me sulla stessa ancora.
Quattro classi x cinque lunghezze = 20 celle, nessuna n=1, ma **una sola ancora**.

REGIME: build `f5dedf34` · python 3.13.12 · fonte `docs/BENCHMARKS.md` (10349 parole,
documento VERO del repo) · store temporaneo · nessuna delle 10 variabili d'ambiente
di questa macchina e' letta da `anti_confab_gate.py` (dettaglio in
`ws5-il-traino-contro-la-cifra.py`).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-Q2-il-gate-annega-sulle-fonti-lunghe.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA: scrive in HIPPO_DATA_DIR, mai lo store principale.
"""
import io, os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

DOC = io.open("docs/BENCHMARKS.md", encoding="utf-8", errors="replace").read()
#: l'affermazione VERA da cui derivano tutti i claim (BENCHMARKS.md:411)
ANCORA = "Gate admission: **noise-rejection 24/24 = 100%**, clean-admission 15/24 = **62%**."
assert ANCORA.replace("**", "") in DOC.replace("**", ""), "ancora non trovata nel documento"
i = DOC.index("noise-rejection 24/24")

CLAIM = [
 ("VERO-verbatim", "Gate admission: noise-rejection 24/24 = 100%, clean-admission 15/24 = 62%."),
 ("OMISSIONE",     "Il gate ha una noise-rejection del 100%."),
 ("SFUMATURA",     "Il gate rifiuta praticamente tutto il rumore e ammette la maggior parte dei fatti puliti."),
 ("FALSO-cifra",   "Gate admission: noise-rejection 24/24 = 100%, clean-admission 22/24 = 92%."),
]

def finestra(parole):
    """Fonte reale centrata sull'ancora, della lunghezza chiesta."""
    if parole is None:
        return ANCORA.replace("**", "")
    tok = DOC.split()
    #: indice approssimato dell'ancora in parole
    centro = len(DOC[:i].split())
    meta = parole // 2
    a = max(0, centro - meta)
    return " ".join(tok[a:a + parole])

print("")
righe = {}
for parole, eti in ((None, "1 frase"), (200, "200 parole"), (1000, "1000 parole"),
                    (3000, "3000 parole"), (10000, "10000 parole")):
    src = finestra(parole)
    out = []
    for nome, claim in CLAIM:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=src, grounding_llm=None, ground_write=True)
        ok = getattr(r, "action", "?") == "persist"
        ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
              for w in (getattr(r, "warnings", None) or [])]
        g = getattr(r, "grounding_score", None)
        righe.setdefault(nome, []).append((eti, ok, g, ws))
        out.append("%s=%s" % (nome.split("-")[0][:4], "AMM" if ok else "blc"))
    print("   %-12s (%5d parole reali)  %s" % (eti, len(src.split()), "  ".join(out)))

print("")
for nome, _ in CLAIM:
    amm = sum(1 for _, ok, _, _ in righe[nome] if ok)
    gs = ", ".join(("%.1f" % g) if isinstance(g, (int, float)) else "-" for _, _, g, _ in righe[nome])
    print("   %-14s ammesso %d/5   g: %s" % (nome, amm, gs))
print("")
print("   REGIME: build %s · python %s · fonte docs/BENCHMARKS.md (10349 parole)"
      % (os.popen("git rev-parse --short HEAD").read().strip(), sys.version.split()[0]))
