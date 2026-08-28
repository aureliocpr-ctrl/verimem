# -*- coding: utf-8 -*-
r"""La collisione sui valori CATEGORICI non e' generale: 1 caso su 4. Il giorno e' l'anomalia.

    giorno    senza=downgrade  8.2   CON=persist    99.3   <- unico che collide
    mese      senza=downgrade  0.6   CON=downgrade   1.1
    colore    senza=downgrade  0.9   CON=downgrade   0.7
    nome      senza=downgrade  0.9   CON=downgrade   7.8

Ogni riga: **stesso claim falso**, due fonti identiche salvo che una CONTIENE il
valore falso altrove, in un'altra proposizione. La cella «senza» blocca sempre:
il banco separa.

NASCE DAL RITIRO di `ws5-il-contorno-pertinente-difende.py`, dove il gradino
«quasi identico» conteneva «lunedi'» — il valore che il claim inventa — e il falso
passava a 100.0. **Era n=1**, e il protocollo lo vieta: qui la conferma su quattro
tipi di valore.

⇒ ❌ PREDIZIONE SBAGLIATA. Avevo previsto che la collisione valesse per qualunque
valore da un insieme chiuso, «perche' il meccanismo e' *il valore compare nella
fonte*, non *e' un numero*». **Falso: mese, colore e nome resistono.**
⇒ ✅ E RIDIMENSIONA IL FATTO CHE AVEVO APPENA ANNUNCIATO. «Anche i giorni della
settimana collidono» **non e' una classe: e' un'anomalia dei giorni**, uno su quattro.
⛔ **NON SO PERCHE'.** L'ipotesi che verrebbe — «il reso si accetta lunedi'» e' un
evento logistico datato come «la consegna e' prevista per lunedi'», quindi rende
plausibile il claim — **non spiega perche' «il telone di ricambio e' rosso» non renda
plausibile «il furgone e' rosso»**, che ha la stessa forma. **Non la scrivo come
spiegazione.**

⚖️ PUNTO DEBOLE: un caso per tipo, quattro tipi, fonti costruite. **Serve piu' di un
esempio per tipo prima di dire che mese/colore/nome sono SEMPRE difesi**: qui so solo
che in questi quattro casi lo sono. E la collisione NUMERICA — misurata su piu' casi
in `ws5-Q2bis-la-rarita-del-numero-decide.py` — resta il fenomeno solido; questa
categorica no.

REGIME: build corrente · python 3.13.12 · store temporaneo · `run_validation_gate`
(porta della CLI, `cli.py:1867`) · letti i `warnings`, non `layers`.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-collisione-categorica-non-e-generale.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

CASI = [
 ("giorno",  "La consegna e' prevista per giovedi'. Il magazzino e' aperto.",
             "La consegna e' prevista per giovedi'. Il reso si accetta lunedi'.",
             "La consegna e' prevista per lunedi'."),
 ("mese",    "Il contratto scade a marzo. Il rinnovo e' automatico.",
             "Il contratto scade a marzo. Il preavviso parte a settembre.",
             "Il contratto scade a settembre."),
 ("colore",  "Il furgone consegnato e' bianco. Il carico e' completo.",
             "Il furgone consegnato e' bianco. Il telone di ricambio e' rosso.",
             "Il furgone consegnato e' rosso."),
 ("nome",    "Il responsabile e' Rossi. Il turno e' diurno.",
             "Il responsabile e' Rossi. Il magazziniere e' Bianchi.",
             "Il responsabile e' Bianchi."),
]
print("")
for eti, f_senza, f_con, claim in CASI:
    out = []
    for k, src in (("senza", f_senza), ("CON  ", f_con)):
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=src, grounding_llm=None, ground_write=True)
        g = getattr(r, "grounding_score", None)
        out.append("%s=%-9s g=%5s" % (k, getattr(r, "action", "?")[:9],
                   ("%.1f" % g) if isinstance(g, (int, float)) else "-"))
    print("   %-9s %s" % (eti, "  ".join(out)))
