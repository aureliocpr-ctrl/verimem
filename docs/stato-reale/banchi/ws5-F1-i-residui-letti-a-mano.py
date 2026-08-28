# -*- coding: utf-8 -*-
r"""F1 - i 161 'scambi candidati' residui: ne leggo VENTI. 20 su 20 falsi positivi.

Nel banco `ws5-F1-i-falsi-positivi-sul-corpus-vero.py` avevo scritto che i 161
residui «NON sono 161 errori: chiamarli cosi' sarebbe lo stesso sbaglio del
65,7% nudo». Questo banco paga quel debito: li stampa per esteso e li legge.

CRITERIO DICHIARATO **PRIMA** di guardarli, per non confermare la mia tesi:
  CATTURA GIUSTA  leggendo lo span, il claim attribuisce il valore a un soggetto
                  a cui la fonte lo attribuisce diversamente => il claim e' FALSO
  FALSO POSITIVO  leggendo lo span, il claim e' sostenuto: il valore giusto e'
                  li' per il soggetto giusto
  AMBIGUO         non decidibile dallo span (troncato a 400, o manca contesto)

ESITO: **20 FALSI POSITIVI, 0 CATTURE, 0 AMBIGUI.**

    id             perche' il passo 4 ha sbagliato
    8227dd32b20f   lo span confronta DIRETTA (1 su 4) e PORTA (4 su 4); il claim
                   dice PORTA ed e' esatto
    8b95d3c3f9cd   lo span dice testualmente «sul sorgente: exact citation - 24
                   occorrenze in 12 file». Il claim e' sostenuto  [vedi il RITIRO]
    e645ddbab02b   «cartella verimem/: file .py esaminati: 420» c'e', accanto ai
                   422 dell'sdist: due perimetri, entrambi nella fonte
    3c4cd5473d7f   `--as-of` dopo -> 5252. Nello span ci sono anche i 4141 del prima
    f06a04007ba2   `--as-of` prima -> 4141. Speculare al precedente
    dd4136f64c5a   «same-source evolution 157» c'e'; il passo 4 ha preso il «7»
                   di «ultimi 7 giorni» e l'ha accoppiato col «30» di «30 giorni»
    f0b37a8f246d   «ricalco 3 ore ... downgrade ... L4-negazione» c'e'; accanto
                   ci sono «ricalco 24 ore» e «VERO 72 ore»
    c091cf3ce06b   «10000 parole MEDIA 0.13s» c'e'; accanto c'e' «10 parole»
    ec325101a313   «uses 200MB -> NESSUNA DELLE 4 REGEX LO VEDE» c'e'; accanto
                   c'e' «memoria <512MB» dentro il commento citato
    5a13b1ea88a7   la riga «testa 2k C falso ... L4.1,L4-review» c'e'; accanto
                   le righe degli altri regimi
    52ac608b8e9c   «5000 parole ... persist layers=L4.2» c'e'; accanto 3000 e 4000
    97c886e44d3c   «37 MB», «893 MB», «1940 MB» ci sono tutti; accanto c'e' 1978
    9f07dcabe6d5   «verdetti distinti sul claim vago: ['model_claim']» e «7 su 7»
    0cc42ab75560   idem (stesso claim, altro id)
    5483cdb5e703   idem (stesso claim, terzo id)
    cf5e11ec5086   «quante volte ha parlato il gate? -> 1322 fatti» c'e'
    1dd053c29914   «how many facts does the corpus have? -> 95 fatti» c'e'
    2a44408637b5   «quanti fatti ha il corpus? -> 208 fatti» c'e'
    01af680f0827   «12 passed ... 28.28s ... 28.48s» ci sono tutti

🔑 LA FORMA PURA DEL DIFETTO sono i tre casi `cf5e11ec5086` / `1dd053c29914` /
`2a44408637b5`: **tre claim VERI sullo stesso span**, ognuno cita il proprio
numero (1322, 95, 208), e il passo 4 li segnala **tutti e tre** incrociandoli a
vicenda. Non c'e' nessuno scambio: c'e' una tabella a tre righe.

⇒ **CONCLUSIONE, e cambia il perimetro del design.** Su questo corpus `L4.3` non
cattura niente e produce solo rumore. Ma il corpus e' fatto di **output di
strumenti** — log, tabelle, referti — dove lo stesso claim ha il suo valore in
una riga e valori omogenei nelle righe vicine. Sulla **prosa** la stessa regola
coglie **15 scambi su 16** (`ws5-F1-validazione-cieca-regola-finale.py`).
⇒ Non e' «la regola non funziona»: e' **la regola non e' applicabile a fonti
tabellari**, e oggi non ha modo di saperlo. O si aggiunge un passo 0 che si
astiene quando la fonte e' tabellare, o il layer va limitato per contratto alle
fonti in prosa - e detto nella ricevuta.

⚖️ PUNTI DEBOLI: la classificazione l'ho fatta IO, non in cieco, e sono la
stessa che sostiene la tesi - il criterio l'ho scritto prima, ma chi vuole
falsificarmi rilegga gli span, che sono stampati apposta. Venti su 161: se i
141 non letti fossero diversi, la proporzione cambierebbe. Lo span e' troncato
a 400 caratteri dal prodotto, quindi **su un claim la cui prova sta oltre il
troncamento la mia lettura sbaglierebbe in direzione «cattura giusta»** - ed e'
esattamente l'errore che ho gia' commesso una volta qui.

REGIME: build corrente - sola lettura (`mode=ro`), percorso da `CONFIG.semantic_db`
- nessun modello caricato - stampa a 420 caratteri di span.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-F1-i-residui-letti-a-mano.py
"""
import sys
import io
import sqlite3
import contextlib
import importlib.util
from pathlib import Path

sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.config import CONFIG

_B = Path(__file__).parent / "ws5-F1-i-falsi-positivi-sul-corpus-vero.py"
_sp = importlib.util.spec_from_file_location("_cv", _B)
_cv = importlib.util.module_from_spec(_sp)
with contextlib.redirect_stdout(io.StringIO()):
    _sp.loader.exec_module(_cv)
_val = _cv._val

# la mia lettura, id -> esito. Chi rilegge gli span puo' falsificarla.
LETTURA = {
    "8227dd32b20f": "FALSO POSITIVO", "8b95d3c3f9cd": "FALSO POSITIVO",
    "e645ddbab02b": "FALSO POSITIVO", "3c4cd5473d7f": "FALSO POSITIVO",
    "f06a04007ba2": "FALSO POSITIVO", "dd4136f64c5a": "FALSO POSITIVO",
    "f0b37a8f246d": "FALSO POSITIVO", "c091cf3ce06b": "FALSO POSITIVO",
    "ec325101a313": "FALSO POSITIVO", "5a13b1ea88a7": "FALSO POSITIVO",
    "52ac608b8e9c": "FALSO POSITIVO", "97c886e44d3c": "FALSO POSITIVO",
    "9f07dcabe6d5": "FALSO POSITIVO", "0cc42ab75560": "FALSO POSITIVO",
    "5483cdb5e703": "FALSO POSITIVO", "cf5e11ec5086": "FALSO POSITIVO",
    "1dd053c29914": "FALSO POSITIVO", "2a44408637b5": "FALSO POSITIVO",
    "01af680f0827": "FALSO POSITIVO",
}


def main():
    p = Path(str(CONFIG.semantic_db))
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    righe = con.execute(
        "select id, proposition, grounding_span from facts "
        "where grounding_score >= 90 and grounding_span is not null "
        "and length(grounding_span) > 20 and superseded_by is null "
        "order by created_at desc limit 4000").fetchall()
    con.close()

    n = 0
    visti = []
    for fid, prop, span in righe:
        if not ({v for _, v in _val.extract_quantities(prop)}
                & {v for _, v in _val.qty(span)}):
            continue
        e, d = _val.L43_finale(prop, span, "S")
        if e != "SEGNALA" or _cv._classifica(prop, span, d) != "resta: scambio candidato":
            continue
        n += 1
        if n > 20:
            break
        visti.append(fid)
        print("\n--- %2d) id=%s   [%s]   la mia lettura: %s"
              % (n, fid, d, LETTURA.get(fid, "(non letto: il corpus e' cambiato)")))
        print("CLAIM: %s" % " ".join(prop.split())[:260])
        print("SPAN : %s" % " ".join(span.split())[:420])

    noti = [f for f in visti if f in LETTURA]
    print("\n=== ESITO ===")
    print("  stampati            %d" % len(visti))
    print("  gia' letti da me    %d" % len(noti))
    print("  di cui FALSI POSITIVI %d  ·  CATTURE %d  ·  AMBIGUI %d"
          % (sum(1 for f in noti if LETTURA[f] == "FALSO POSITIVO"),
             sum(1 for f in noti if LETTURA[f] == "CATTURA GIUSTA"),
             sum(1 for f in noti if LETTURA[f] == "AMBIGUO")))
    if len(noti) < len(visti):
        print("  ⚠️ %d casi NUOVI rispetto alla mia lettura: il corpus si muove,"
              % (len(visti) - len(noti)))
        print("     vanno letti prima di riusare la proporzione.")


if __name__ == "__main__":
    main()
