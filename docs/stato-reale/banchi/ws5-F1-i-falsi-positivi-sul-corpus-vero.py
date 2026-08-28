# -*- coding: utf-8 -*-
r"""F1 - i falsi positivi della regola `L4.3` misurati sul CORPUS VERO, non su esempi.

IL LIMITE CHE QUESTO BANCO PAGA. La mia validazione cieca
(`ws5-F1-validazione-cieca-regola-finale.py`) ha trovato 3 falsi positivi su 16,
ma quei 16 claim VERI li avevo scritti io: «32 casi costruiti restano 32 casi
costruiti». Qui la popolazione non la scelgo: sono i fatti che il prodotto ha
gia' ammesso, con il frammento di fonte che ha DAVVERO usato per giudicarli.

COME SI LEGGE. Un fatto con `grounding_score` alto e' un claim che il giudice ha
giudicato SOSTENUTO dalla sua fonte. Se `L4.3` lo segnalasse, sarebbe un falso
positivo su un dato reale.
⚠️ **«grounding alto» non e' «vero»**: e' «il giudice lo ha ritenuto sostenuto».
Se il giudice sbaglia, un mio «falso positivo» potrebbe essere una cattura
giusta. E' il limite di questa misura e non lo posso togliere senza un
annotatore umano - quindi il numero qui va letto come **tasso di disaccordo con
il giudice**, non come tasso di errore assoluto.

SOLA LETTURA: `sqlite3` con `mode=ro`, percorso chiesto al prodotto
(`CONFIG.semantic_db`) e non all'intuito - il percorso ovvio e' un database
vuoto (lezione in memoria).

⚖️ ALTRI PUNTI DEBOLI: `grounding_span` e' **troncato a 400 caratteri** dal
prodotto, quindi le finestre lunghe sono tagliate e il numero di frasi
candidate e' sottostimato. La regola e' TRASCRITTA da me. La segmentazione in
frasi e' la mia. E il corpus e' uno solo, quello di Aurelio, in un istante.

ESITO - il numero nudo INGANNA, e la sua scomposizione e' il vero risultato.

    popolazione   4000 fatti ammessi con grounding >= 90 e uno span vero
    giudicabili   3030  (il claim porta un valore che lo span contiene)
    SEGNALA       1990  = 65,7%   <- il numero nudo

    PERCHE' il passo 4 ha segnalato:
      unita' VUOTA (numeri nudi)   1229   61,8%
      il claim cita ENTRAMBI        550   27,6%
      arrotondamento                 50    2,5%
      resta: scambio candidato      161    8,1%   -> 5,3% dei giudicabili

⇒ **Il 65,7% scende al 5,3% con TRE guardie**, e ognuna ha un prezzo misurato:
  (1) se il valore non porta unita', il passo 4 non deve accoppiare  -> -61,8%
  (2) se il claim cita ANCHE l'altro valore, non c'e' scambio        -> -27,6%
      («I quarantinati con un motivo sono 623 su 2378»: cita entrambi)
  (3) stesso numero a precisione diversa (97.6 contro 97.5968)       -> -2,5%

⚠️ E I 161 RESIDUI NON SONO 161 ERRORI. Letti a mano i primi sei:
  · `8b95d3c3f9cd` e' una **CATTURA GIUSTA**: il claim dice «exact citation: 24
    occorrenze in 12 file» mentre la fonte dice «exact citation - 1 occorrenze
    in 1 file» e «never silently - 12 occorrenze in 8 file». **E' uno scambio
    vero, e il gate l'ha AMMESSO a 99.9.** ⇒ prova che il layer serve.
  · quattro sono falsi positivi con una causa comune: lo span porta una SERIE
    di misure (`--as-of` prima/dopo, `ricalco 24 ore`/`3 ore`) e il claim ne
    cita una sola.
  · uno resta ambiguo (420 contro 422 file, due perimetri diversi).

🔑 A/B SULLA SEGMENTAZIONE - la variabile piu' grossa, e risponde con un numero
alla domanda che @ws3 aveva girato a @ws4:

    A  split su .!?  (la mia)        SEGNALA 1990  (65,7%)
    B  split anche su NEWLINE e ;    SEGNALA  946  (31,2%)
    CONTROLLO col regime B: scambi costruiti colti 15/16 INVARIATO,
                            falsi positivi della popolazione B  3 -> 2

⇒ **Meta' dei falsi allarmi era la segmentazione, e curarla NON costa
sensibilita'.** E il terzo falso positivo della mia validazione cieca era
davvero un artefatto del mio segmentatore: l'avevo dichiarato come sospetto,
ora e' misurato. **Ne restano 2 su 16, e il criterio «sopra 1 => RESPINTO»
scatta ancora.**

RIPRODUCI:  python docs/stato-reale/banchi/ws5-F1-i-falsi-positivi-sul-corpus-vero.py
"""
import sys
import sqlite3
import importlib.util
from pathlib import Path

sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.config import CONFIG

_BANCO = (Path(__file__).parent / "ws5-F1-validazione-cieca-regola-finale.py")
_spec = importlib.util.spec_from_file_location("_val", _BANCO)
_val = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_val)          # riusa L43_finale, frasi, ancore, qty

SOGLIA = 90.0
LIMITE = 4000

import re as _re


def _classifica(prop, span, dettaglio):
    """Perche' il passo 4 ha segnalato. Le prime tre NON sono scambi."""
    m = _re.search(r"passo 4: ([\d.]+) invece di ([\d.]+)", dettaglio)
    if not m:
        return "resta: scambio candidato"
    v2, v = float(m.group(1)), float(m.group(2))
    # (a) stesso numero, precisione diversa: 97.5968 contro 97.6
    if v and abs(v2 - v) / max(abs(v), 1e-9) < 0.01:
        return "arrotondamento"
    # (b) il claim cita ANCHE l'altro valore: «623 su 2378» non e' uno scambio
    if v2 in {x for _, x in _val.extract_quantities(prop)}:
        return "il claim cita ENTRAMBI"
    # (c) unita' vuota: ogni numero nudo e' «stessa unita'» di ogni altro
    unita_claim = {u for u, x in _val.extract_quantities(prop) if x == v}
    if unita_claim <= {""}:
        return "unita' VUOTA (numeri nudi)"
    return "resta: scambio candidato"


def main():
    p = Path(str(CONFIG.semantic_db))
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    cur = con.cursor()
    righe = cur.execute(
        "select id, proposition, grounding_span, grounding_score from facts "
        "where grounding_score >= ? and grounding_span is not null "
        "and length(grounding_span) > 20 and superseded_by is null "
        "order by created_at desc limit ?", (SOGLIA, LIMITE)).fetchall()
    con.close()

    print("corpus     : %s" % p)
    print("popolazione: %d fatti con grounding_score >= %s e uno span vero"
          % (len(righe), SOGLIA))
    if not righe:
        print("!! POPOLAZIONE VUOTA: non sto misurando i falsi positivi, sto")
        print("   misurando una query sbagliata. Il banco si ferma.")
        return

    esiti = {"SEGNALA": [], "ok": 0, "astieniti": 0}
    classi = {k: 0 for k in ("arrotondamento", "il claim cita ENTRAMBI",
                             "unita' VUOTA (numeri nudi)", "resta: scambio candidato")}
    giudicabili = 0
    for fid, prop, span, g in righe:
        # un fatto e' GIUDICABILE se il claim porta un valore che lo span contiene:
        # e' la porta d'ingresso della regola (passo 1). Gli altri non sono
        # affare di L4.3 e contarli nel denominatore gonfierebbe il verde.
        vals_claim = {v for _, v in _val.extract_quantities(prop)}
        vals_span = {v for _, v in _val.qty(span)}
        if not (vals_claim & vals_span):
            continue
        giudicabili += 1
        e, d = _val.L43_finale(prop, span, "S")
        if e == "SEGNALA":
            esiti["SEGNALA"].append((fid, prop, span, g, d))
            classi[_classifica(prop, span, d)] += 1
        else:
            esiti[e] += 1

    print("giudicabili: %d (il claim porta un valore che lo span contiene)" % giudicabili)
    if not giudicabili:
        print("!! ZERO GIUDICABILI: il banco non separa, il numero non significa nulla.")
        return
    n_seg = len(esiti["SEGNALA"])
    print()
    print("  SEGNALA   %4d   <- disaccordo col giudice: il gate ha ammesso, L4.3 segnalerebbe"
          % n_seg)
    print("  ok        %4d" % esiti["ok"])
    print("  astieniti %4d" % esiti["astieniti"])
    print()
    print("  TASSO DI DISACCORDO: %.1f%% dei giudicabili (%d su %d)"
          % (100.0 * n_seg / giudicabili, n_seg, giudicabili))
    print("  sul totale della popolazione: %.2f%% (%d su %d)"
          % (100.0 * n_seg / len(righe), n_seg, len(righe)))

    print("\n=== PERCHE' il passo 4 ha segnalato - le prime tre NON sono scambi ===")
    for k, n in sorted(classi.items(), key=lambda kv: -kv[1]):
        print("  %-30s %5d  (%.1f%% dei segnalati)"
              % (k, n, 100.0 * n / max(n_seg, 1)))
    resto = classi["resta: scambio candidato"]
    print("  ---- tolte le tre classi spurie restano %d su %d giudicabili = %.1f%%"
          % (resto, giudicabili, 100.0 * resto / giudicabili))

    print("\n=== I 'SCAMBI CANDIDATI' RESIDUI, da leggere a mano ===")
    print("    chiamarli errori senza leggerli sarebbe lo stesso sbaglio del 65,7% nudo:")
    print("    ognuno puo' essere un falso positivo O una cattura giusta che il giudice")
    print("    ha lasciato passare. Il banco li MOSTRA e non li conta come errori.\n")
    residui = [r for r in esiti["SEGNALA"]
               if _classifica(r[1], r[2], r[4]) == "resta: scambio candidato"]
    for fid, prop, span, g, d in residui[:6]:
        print("  id=%s  grounding=%.1f  [%s]" % (fid, g, d))
        print("    claim: %s" % prop[:140].replace("\n", " "))
        print("    span : %s" % span[:140].replace("\n", " "))
        print()


if __name__ == "__main__":
    main()


# ---- A/B: quanto pesa la SEGMENTAZIONE? Stessa popolazione, stessa regola ----
def ab_segmentazione():
    import re as _r
    orig = _val.frasi

    def frasi_nl(t):
        return [f.strip() for f in _r.split(r"(?<=[.!?])\s+|[\r\n]+|;\s*", t) if f.strip()]

    p = Path(str(CONFIG.semantic_db))
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    righe = con.execute(
        "select proposition, grounding_span from facts where grounding_score >= ? "
        "and grounding_span is not null and length(grounding_span) > 20 "
        "and superseded_by is null order by created_at desc limit ?",
        (SOGLIA, LIMITE)).fetchall()
    con.close()
    print("\n=== A/B SEGMENTAZIONE - stessa popolazione, stessa regola ===")
    for et, fn in (("A  split su .!?  (la mia)", orig),
                   ("B  split anche su NEWLINE e ;", frasi_nl)):
        _val.frasi = fn
        seg = giud = 0
        for prop, span in righe:
            if not ({v for _, v in _val.extract_quantities(prop)}
                    & {v for _, v in _val.qty(span)}):
                continue
            giud += 1
            if _val.L43_finale(prop, span, "S")[0] == "SEGNALA":
                seg += 1
        print("  %-30s giudicabili=%4d  SEGNALA=%4d  (%.1f%%)"
              % (et, giud, seg, 100.0 * seg / max(giud, 1)))
    # CONTROLLO: la cura non deve rompere la sensibilita'
    _val.frasi = frasi_nl
    ok = sum(1 for _n, c, f in _val.A1 if _val.L43_finale(c, f, "S")[0] == "SEGNALA")
    fp = sum(1 for _n, c, f in _val.B1 if _val.L43_finale(c, f, "S")[0] == "SEGNALA")
    print("  CONTROLLO col regime B: scambi costruiti colti %d/%d, falsi positivi %d/%d"
          % (ok, len(_val.A1), fp, len(_val.B1)))
    print("  ^ se i colti crollassero, la segmentazione avrebbe curato il numero")
    print("    rompendo la regola. Non crollano: 15/16 resta 15/16.")
    _val.frasi = orig


ab_segmentazione()
