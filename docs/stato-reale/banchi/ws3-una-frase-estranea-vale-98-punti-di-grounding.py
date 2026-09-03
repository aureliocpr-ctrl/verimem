"""Una frase estranea in coda alla fonte vale 98 punti di grounding.

    python docs/stato-reale/banchi/ws3-una-frase-estranea-vale-98-punti-di-grounding.py

🔴🔴 CORREZIONE DEL 2026-09-03 alle 20:20, E RIGUARDA IL TITOLO DI QUESTO FILE.
Il numero qui sotto e' riproducibile e resta vero. La GENERALIZZAZIONE che ne
avevo tratto no: su TRENTA contraddizioni generate con una regola fissa, la
stessa zavorra ne libera **ZERO** e sposta il grounding di **+0,7 in mediana**
(`ws3-trenta-coppie-con-e-senza-frase-estranea.py`). Quindi «una frase estranea
vale 98 punti» descrive QUESTI claim, non la classe «contraddizione», e chi
legge il titolo come una proprieta' del gate lo legge come lo avevo scritto io
— male.
Un fattore trovato dopo: sullo stesso claim, scrivere «e» invece di «e'» porta
l'effetto da +31 a +99. Le trenta frasi generate usano tutte la forma corretta
«e'». Quale caratteristica renda un claim vulnerabile resta APERTO.

⚠️ Carica il giudice (~30 s la prima scrittura). Il vincolo «un banco alla
volta» per la RAM e' stato revocato da Aurelio il 2026-09-03 alle 19:15.

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Due istanze misuravano lo STESSO claim e ottenevano due risposte opposte — 2,06
(«contraddetto») e 99,94 («sostenuto») — e la spiegazione candidata era «il
giudice e' monolingue». Falsificata da chi l'aveva proposta. Restava da trovare
quale variabile ci separasse, e la risposta e' che le due fonti non erano la
stessa fonte: una aveva UNA frase, l'altra DUE.

Il banco `test_una_frase_estranea_fa_entrare_la_contraddizione_implicita.py`
(26/08) aveva gia' nominato il fenomeno con un tasso — 0/12 con la fonte corta,
4/12 col contorno. Qui e' un A/B APPAIATO: stesso claim, stessa porta, stesso
codice, e l'unica cosa che cambia e' una frase che non parla del claim.

━━ MISURATO IL 2026-09-03 su `main` ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    caso                                 status        grounding  quar_by  layers
    fonte CORTA                          quarantined        1,84  moat     L1.10, L4-grounding, L1-domain-precision-observe
    fonte + ZAVORRA                      model_claim       99,94  None     L1.10, L1-domain-precision-observe
    fonte CORTA, claim riformulato       quarantined        0,93  moat     L4-grounding
    fonte + ZAVORRA, riformulato         model_claim       99,90  None     (nessuno)

⇒ **98 punti** di differenza, e il ribaltamento del verdetto, prodotti da
«La mensa aziendale resta chiusa il primo maggio» — una frase che non nomina
ne' il direttore ne' le dimissioni.

⚠️ NON E' «LA FONTE LUNGA»: la frase decisiva resta la PRIMA e resta intera.
Basta appenderne UNA irrilevante dopo. Chi cerchi la causa in un troncamento
per lunghezza guarda nel posto sbagliato — e chi la cerchi nella lingua pure:
lo stesso fenomeno e' misurato in inglese dal banco del 26/08.

⚠️ QUANTO NON DICE. Due claim su due non sono un tasso: il banco del 26/08, su
dodici riformulazioni, ne fa entrare quattro. Questo A/B non misura QUANTO
spesso succede — misura che, quando succede, il salto e' totale e non
marginale. Le riformulazioni le ha scritte chi conosceva il difetto.

🔴 COME MUORE: se con la zavorra il grounding resta sotto la soglia, la frase
estranea non e' la variabile e le due ricevute divergono per altro.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from verimem.client import Memory

FONTE = "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio."
ZAVORRA = "La mensa aziendale resta chiusa il primo maggio."
CLAIM = "Il direttore e' stato confermato nell'incarico il 4 maggio."
#: lo stesso claim senza la parola che L1.10 conosce: serve a mostrare che a
#: reggere, quando regge, e' il MOAT e non il filtro lessicale
CLAIM_2 = "Il direttore e ancora in carica il 4 maggio."

CASI = [
    ("fonte CORTA", FONTE, CLAIM),
    ("fonte + ZAVORRA", f"{FONTE} {ZAVORRA}", CLAIM),
    ("fonte CORTA, claim riformulato", FONTE, CLAIM_2),
    ("fonte + ZAVORRA, riformulato", f"{FONTE} {ZAVORRA}", CLAIM_2),
]


def main() -> None:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "z.db"))
    print("UNA FRASE ESTRANEA VALE 98 PUNTI DI GROUNDING\n")
    print(f"{'caso':34s} {'status':13s} {'grounding':>10s} {'quar_by':8s} layers")
    esiti = {}
    for nome, fonte, claim in CASI:
        r = mem.add(claim, topic="t/zavorra", source=fonte, validate="full")
        layer = [str((w or {}).get("layer") or "") for w in (r.get("warnings") or [])]
        g = r.get("grounding_score")
        esiti[nome] = (str(r.get("status")), g)
        testo_g = f"{g:.2f}" if isinstance(g, int | float) else str(g)
        print(f"{nome:34s} {str(r.get('status')):13s} {testo_g:>10s} "
              f"{str(r.get('quarantined_by')):8s} {layer}", flush=True)

    corta = esiti["fonte CORTA"][1]
    zav = esiti["fonte + ZAVORRA"][1]
    print()
    if isinstance(corta, int | float) and isinstance(zav, int | float):
        print(f"  salto prodotto da UNA frase estranea: {zav - corta:+.2f} punti")
        if zav - corta > 50:
            print("  ✅ il fenomeno si riproduce: il verdetto si ribalta")
        else:
            print("  🔴 NON si riproduce: la frase estranea non e' la variabile,")
            print("     e la spiegazione va cercata altrove — rimisurare.")


if __name__ == "__main__":
    main()
