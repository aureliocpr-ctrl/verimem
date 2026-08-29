"""Perche' il grounding scende sulla prosa: e' il VOCABOLARIO ESTRANEO, non la lunghezza.

Nasce da un'anomalia dei due banchi gemelli sulla forma della fonte: lo stesso
claim vero prende 99.8 con la fonte tabellare e 98.3 con la prosa (99.9 e 98.0
in inglese). Sistematico in due lingue, e non spiegato.

PRIMO PASSO: provare a far CADERE il fronte, che costa un minuto. La stessa
cella tre volte, store nuovo ogni giro: 98.3 / 98.3 / 98.3. Il giudice e'
DETERMINISTICO qui, quindi il calo non e' rumore fra esecuzioni e il fronte
resta in piedi. (Dato utile a prescindere: chi misura il grounding non deve
preoccuparsi della varianza fra run, almeno su questa cella.)

ESITO misurato il 2026-08-29 alle 19:43, porta SDK, modello vero, fuori pytest,
store NUOVO per ogni cella, claim vero «Il magazzino di Verona contiene 480 pallet.»:

    secca (0 parole estranee)                    len  43   grounding 98.9
    corta CON parole estranee                    len  71   grounding 96.9   <- la piu' bassa
    lunga SENZA parole estranee (claim x4)       len 175   grounding 99.9   <- la piu' alta
    prosa piena del banco (baseline)             len 140   grounding 98.3

⇒ «E' LA LUNGHEZZA» e' FALSIFICATA E ROVESCIATA: la fonte piu' lunga ha il
  punteggio piu' alto, la piu' corta con parole estranee il piu' basso.
⇒ «SONO LE PAROLE ESTRANEE» REGGE: aggiungerne tre («verbale», «attesta»,
  «censiti») a una frase corta porta 98.9 -> 96.9, cambiando solo quelle.

LA CONSEGUENZA CHE VALE: il grounding premia la fonte che RIPETE il claim e
penalizza quella che lo CONTESTUALIZZA. Un verbale vero — con le formule di rito
che un documento reale ha per forza — viene giudicato peggio di una fonte che
ripete la stessa frase quattro volte. Si aggancia al fronte di ws3: il corpus
tipo-cliente non e' solo «tabellare contro prosa», e' anche «asciutto contro
contestualizzato», e il giudice preferisce l'asciutto.

⚖️ NON E' UN DIFETTO e il fronte e' CHIUSO: sono 1,5-2 punti su una soglia di
40, nessun verdetto cambia, tutte e quattro le varianti restano ammesse. E'
un comportamento misurato, non un problema — conta per chi usasse il grounding
come METRICA DI QUALITA' della fonte, che e' un uso diverso da quello per cui
esiste. Inseguirlo oltre sarebbe il contrario di «atomici».

⚠️ LIMITI: un claim, quattro varianti, una lingua, una porta. Le parole estranee
sono TRE e scelte da me: NON ho isolato quale delle tre pesa, ne' se conti il
numero di parole o il loro significato.

    B=docs/stato-reale/banchi/ws6-il-grounding-e-il-vocabolario-estraneo.py
    for v in secca corta_extra lunga_pulita prosa_piena; do
      HIPPO_DATA_DIR=$(mktemp -d) python $B $v
    done
"""
import sys

from verimem.config import CONFIG

assert "Temp" in str(CONFIG.semantic_db) or "tmp" in str(CONFIG.semantic_db), (
    "NON ISOLATO - questo banco scrive. Serve HIPPO_DATA_DIR su una tempdir "
    "NUOVA per ogni variante.")

from verimem import Memory  # noqa: E402

CLAIM = "Il magazzino di Verona contiene 480 pallet."

VARIANTI = {
    "secca": ("secca (0 parole estranee, cortissima)",
              "Il magazzino di Verona contiene 480 pallet."),
    "corta_extra": ("corta CON parole estranee (verbale/attesta/censiti)",
                    "Il verbale attesta: il magazzino di Verona contiene 480 "
                    "pallet censiti."),
    "lunga_pulita": ("lunga SENZA parole estranee (il claim ripetuto)",
                     ("Il magazzino di Verona contiene 480 pallet. " * 4).strip()),
    "prosa_piena": ("prosa piena del banco (baseline)",
                    "Il presente verbale attesta che, alla data odierna, il "
                    "magazzino di Verona contiene 480 pallet, regolarmente "
                    "censiti dall'ufficio logistico."),
}


def main() -> None:
    v = sys.argv[1] if len(sys.argv) > 1 else "secca"
    if v not in VARIANTI:
        raise SystemExit(f"variante sconosciuta: {v!r} - usa: {sorted(VARIANTI)}")
    etichetta, fonte = VARIANTI[v]
    m = Memory()
    r = m.add(CLAIM, topic=f"banco/{v}", source=fonte)
    print(f"  {etichetta:<52} len={len(fonte):>4}  "
          f"grounding={r.get('grounding_score'):>5.1f}")


if __name__ == "__main__":
    main()
