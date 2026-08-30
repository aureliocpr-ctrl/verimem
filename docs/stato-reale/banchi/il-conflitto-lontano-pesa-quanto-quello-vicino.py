"""IL CONFLITTO LONTANO PESA QUANTO QUELLO VICINO?

\U0001f4cc **L'ULTIMA IPOTESI RIMASTA SUL PERIMETRO DI @ws5.** `W7-97` ha
escluso **lunghezza** (fino a 12000 caratteri), **posizione** dell'evidenza e
**forma tabellare** del riempimento: 30 celle su 30 sopra `99,78`. Restava il
**CONTENUTO**, e in particolare un riempimento che **CONFLIGGE** col claim —
il mio era deliberatamente **neutro**.

\U0001f3af **LA DOMANDA NON E' «cade?»**: e' **giusto** che un gate sia
prudente su una fonte che si contraddice. La domanda e'::

    il conflitto ADIACENTE all'evidenza  e  il conflitto a 11000 caratteri
    di distanza  pesano  UGUALE?

Se pesano uguale, **il selettore raccoglie il conflitto ovunque sia ma
l'evidenza no** — e sarebbe un'**asimmetria**: il pessimismo viaggia piu' lontano
dell'ottimismo. Se il conflitto lontano pesa **meno**, il selettore e' coerente
con se stesso e non c'e' difetto.

⚖️ **E c'e' una terza possibilita' che va nominata prima**: che il gate **non
veda affatto** il conflitto. In quel caso il punteggio resta alto ovunque, ed e'
un difetto **opposto** — una fonte che si contraddice dovrebbe far dubitare.

ATTESA DICHIARATA PRIMA: **il conflitto adiacente abbattera' il punteggio,
quello lontano molto meno**, perche' il selettore lavora su una finestra. ⚠️
**Se pesassero uguale, e' l'asimmetria** e lo dico. ⚠️ **Se il conflitto non
mordesse mai, il gate non vede le contraddizioni interne alla fonte** — ed e'
il reperto piu' grosso dei tre.

CONTROLLI CHE POSSONO FALLIRE:
 (1) ✅ **il baseline senza conflitto deve restare alto** (in `W7-97` era
     `99,98` a 12000 caratteri): se cadesse, sto misurando la lunghezza e non
     il conflitto.
 (2) ⚖️ **una sola variabile**: claim, evidenza, riempimento e lunghezza
     restano identici; cambia SOLO dove sta la riga confliggente.
 (3) 🪞 **il conflitto e' NETTO e sullo stesso fatto** (*318 pezzi* contro
     *250 pezzi*, stessa linea, stesso turno): un conflitto vago misurerebbe
     la vaghezza.
 (4) ⚠️ **PREFLIGHT sul moat** (`W7-87`).

    python -u docs/stato-reale/banchi/il-conflitto-lontano-pesa-quanto-quello-vicino.py
"""

from __future__ import annotations

import sys
import time

CUT = 40.0
CLAIM = "Il collaudo della linea 4 ha prodotto 318 pezzi conformi."
EVIDENZA = ("Verbale di collaudo: la linea 4 ha prodotto 318 pezzi conformi"
            " durante la sessione del mattino.")
#: (3) conflitto NETTO e sullo stesso fatto: stessa linea, stesso turno,
#: numero diverso. Non «circa 250» e non «un'altra linea».
CONFLITTO = ("Verbale di collaudo: la linea 4 ha prodotto 250 pezzi conformi"
             " durante la sessione del mattino.")
RIEMPIMENTO = (
    "La riunione operativa si tiene ogni lunedi nella sala al primo piano. "
    "Il parcheggio interno resta aperto fino alle venti e trenta. "
    "La mensa propone due primi e un secondo, con menu affisso all'ingresso. "
    "Le pratiche amministrative passano dall'ufficio protocollo. "
    "Il corso di aggiornamento sulla sicurezza dura quattro ore. "
    "La rassegna stampa viene distribuita per posta elettronica ogni mattina. ")
LUNGHEZZA = 12000


def _fonte(distanza: int | None) -> str:
    """Evidenza in testa, riempimento neutro, conflitto a `distanza` caratteri.

    `distanza=None` = nessun conflitto (il baseline di `W7-97`).
    """
    resto = max(0, LUNGHEZZA - len(EVIDENZA))
    riemp = (RIEMPIMENTO * (resto // len(RIEMPIMENTO) + 1))[:resto]
    if distanza is None:
        return EVIDENZA + " " + riemp
    d = min(distanza, len(riemp))
    return EVIDENZA + " " + riemp[:d] + " " + CONFLITTO + " " + riemp[d:]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.local_grounding import judge_state, warm_local_judge_async
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print("  -- preflight: il moat deve essere CALDO")
    warm_local_judge_async()
    t0 = time.time()
    stato = judge_state()
    while stato == "warming" and time.time() - t0 < 180:
        time.sleep(2)
        stato = judge_state()
    print(f"     `judge_state()` = {stato!r}  dopo {time.time() - t0:.1f}s")
    if stato != "ready":
        print("NON RIUSCITO: giudice non pronto, misurerei il warmup.")
        return 1

    def _g(fonte: str) -> float:
        try:
            res = run_validation_gate(
                proposition=CLAIM, verified_by=None, topic="banco/conflitto",
                agent=None, source=fonte, ground_write=True)
        except Exception:  # noqa: BLE001
            return -1.0
        return (float(res.grounding_score)
                if res.grounding_score is not None else -1.0)

    # (1) il baseline
    base = _g(_fonte(None))
    print(f"\n  -- (1) baseline SENZA conflitto ({LUNGHEZZA} char) -> "
          f"{base:.2f}")
    if base < 80:
        print("     CADUTO: il baseline non regge, sto misurando la lunghezza")
        print("     e non il conflitto. Mi fermo.")
        return 1

    distanze = [0, 200, 1000, 4000, 11000]
    print(f"\n     {'distanza':>10}{'punteggio':>12}{'caduta':>10}")
    esiti = {}
    for d in distanze:
        g = _g(_fonte(d))
        esiti[d] = g
        marca = "🔴" if g < CUT else ("🟡" if g < 80 else "  ")
        print(f"  {marca} {d:>10}{g:>12.2f}{base - g:>10.2f}")

    print("\n  == LA RIGA CHE CONTA")
    vicino, lontano = esiti[0], esiti[distanze[-1]]
    cad_v, cad_l = base - vicino, base - lontano
    if cad_v < 5.0 and cad_l < 5.0:
        print("     🔴 **IL GATE NON VEDE IL CONFLITTO**: con una riga che dice"
              " 250")
        print(f"     invece di 318, sullo stesso fatto, il punteggio resta"
              f" {vicino:.2f}")
        print(f"     (baseline {base:.2f}). ⇒ **Una fonte che si contraddice non fa"
              " dubitare**")
        print("     il giudice, e questo e' piu' grave delle due ipotesi che")
        print("     stavo confrontando.")
    elif abs(cad_v - cad_l) < 5.0:
        print(f"     🔴 **ASIMMETRIA**: il conflitto pesa uguale vicino"
              f" ({cad_v:.2f}) e a")
        print(f"     {distanze[-1]} caratteri ({cad_l:.2f}). ⇒ **Il selettore"
              " raccoglie il")
        print("     conflitto ovunque, ma l'evidenza lontana la trova"
              " comunque** (`W7-97`):")
        print("     il pessimismo e l'ottimismo viaggiano alla stessa"
              " distanza. Non e'")
        print("     un difetto, e' coerenza — e la mia attesa e'"
              " falsificata.")
    else:
        print(f"     🟢 **IL CONFLITTO VICINO PESA DI PIU'**: caduta"
              f" {cad_v:.2f} contro {cad_l:.2f}")
        print(f"     a {distanze[-1]} caratteri. ⇒ Il selettore lavora su una"
              " finestra e")
        print("     l'attesa dichiarata regge.")

    # ⚠️ IL TEST DECISIVO, aggiunto dopo la prima esecuzione: il punteggio da
    #    solo non basta. Un layer poteva fermare il fatto lasciandolo alto, e
    #    il banco non l'avrebbe visto. E soprattutto: se la fonte contiene
    #    ENTRAMBI i valori, passano ENTRAMBI i claim?
    print("\n  -- il test decisivo: una fonte con ENTRAMBI i valori,"
          " tre claim")
    fonte2 = EVIDENZA + " " + CONFLITTO
    for n, atteso in (("318", "nella fonte"), ("250", "nella fonte"),
                      ("400", "NON nella fonte — controllo positivo")):
        cl = f"Il collaudo della linea 4 ha prodotto {n} pezzi conformi."
        try:
            res = run_validation_gate(
                proposition=cl, verified_by=None, topic="banco/conflitto",
                agent=None, source=fonte2, ground_write=True)
        except Exception as e:  # noqa: BLE001
            print(f"     claim {n}: ERRORE {type(e).__name__}: {e}")
            continue
        lay = [w.get("layer") for w in (res.warnings or [])
               if isinstance(w, dict)]
        g = (res.grounding_score if res.grounding_score is not None else -1)
        print(f"     claim {n:>4} pezzi ({atteso:<34}) -> "
              f"action={res.action:<10} g={g:6.2f}  layers={lay or '[]'}")

    print("\n  ⚠️ COSA NON DICE: **un solo claim e un solo conflitto** · il")
    print("  conflitto e' NETTO (stesso fatto, numero diverso): uno vago"
          " darebbe")
    print("  altro · e questo NON dice se il gate DOVREBBE bocciare — dice"
          " solo")
    print("  se la distanza cambia il verdetto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
