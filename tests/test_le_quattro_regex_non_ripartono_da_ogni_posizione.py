r"""T173 — le quattro regex che ripartono da ogni posizione.

Quattro `py/polynomial-redos` aperti, tutti veri **come regex**: misurati su
8000 caratteri con crescita x3,7-4,3.

    1265  _NOME_DI_PARAMETRO   1129 ms   l1_tested_detector
    1460  _COMPOSTO            1681 ms   vicinato_del_valore
    1236  _LABEL_RE             702 ms   quantity_match  (sulla corsa ROTTA)
    1275  _APRE_LA_FRASE_RE     487 ms   quantity_match

⚠️⚠️ MA DAL PERCORSO DEL PRODOTTO NE RESTA **UNO**, e la misura sta qui perché
cambia cosa questa richiesta promette:

    dal percorso (2000/4000/8000 caratteri)
      l1: e_tested_dichiarato            0.1    0.1    0.1 ms   lineare
      vv: valori_riusati_da_altro_...  110.8  366.3 1659.2 ms   QUADRATICO
      qm: claim_span                     0.0    0.0    0.1 ms   lineare
      qm: _nomi_propri                   0.1    0.1    0.2 ms   lineare

  · `_NOME_DI_PARAMETRO` non è raggiungibile **per costruzione**: chi la chiama
    le passa `testo[inizio-40:inizio]`, una finestra di quaranta caratteri
    (`l1_tested_detector.py:79`). È una prova strutturale, non un campione.
  · `_LABEL_RE` e `_APRE_LA_FRASE_RE` non sono esplose **con gli ingressi che
    ho provato**: è una prova empirica, e non esclude che un ingresso diverso
    le raggiunga. Le curo lo stesso, perché il costo è nullo e l'avviso va
    chiuso, ma la differenza fra le due prove è dichiarata.
  · `_COMPOSTO` è **raggiungibile e quadratica dalla porta**: 1,66 s su 8000
    caratteri di `proposition`, cioè testo dell'utente.

LA CURA È LA STESSA PER TUTTE: **quantificatori limitati**. Un `\w*` o un `\s*`
illimitato dentro un'alternativa costringe il motore a riprovare da ogni
posizione; con un tetto il lavoro per posizione è costante. I tetti sono
generosi (32-64 caratteri) e ognuno ha la sua cella di equivalenza PRIMA del
cronometro: una cura che va più veloce cambiando un risultato è un difetto
nuovo con un buon cronometro.
"""
from __future__ import annotations

import time

import pytest

from verimem.l1_tested_detector import _NOME_DI_PARAMETRO
from verimem.quantity_match import _APRE_LA_FRASE_RE, _LABEL_RE
from verimem.vicinato_del_valore import _COMPOSTO

# ─────────────────────────────────── equivalenza, PRIMA del cronometro

#: (regex, testo, atteso) — i casi vengono dagli USI nel prodotto, non dalla
#: mia memoria: nomi di parametro da riga di comando, composti orario/data/
#: rapporto, etichette di sezione maiuscole, aperture di frase.
CASI = [
    (_NOME_DI_PARAMETRO, "il flag --verbose ", True),
    (_NOME_DI_PARAMETRO, "exit status ", True),
    (_NOME_DI_PARAMETRO, "lo stato del sistema ", False),
    (_NOME_DI_PARAMETRO, "-v ", True),
    (_COMPOSTO, "alle 03:27 di ieri", True),
    (_COMPOSTO, "il 2026-09-06", True),
    (_COMPOSTO, "un rapporto 3/40", True),
    (_COMPOSTO, "la versione 1.2.3", True),
    (_COMPOSTO, "solo 400 metri", False),
    (_LABEL_RE, "EMPIRICAL EVIDENCE", True),
    (_LABEL_RE, "PROVA_1", True),
    (_LABEL_RE, "Riferendosi alla fonte", False),
    (_APRE_LA_FRASE_RE, "Questo e' un caso.", True),
    (_APRE_LA_FRASE_RE, ". Marco ha scritto", True),
    (_APRE_LA_FRASE_RE, "- Elenco puntato", True),
    (_APRE_LA_FRASE_RE, "tutto minuscolo qui", False),
]


@pytest.mark.parametrize("rx,testo,atteso", CASI)
def test_EQUIVALENZA_il_tetto_non_cambia_nessun_caso(rx, testo: str, atteso: bool):
    """Il controllo positivo che viene prima del tempo: se un solo esito
    cambia, il tetto non è generoso — è sbagliato."""
    assert bool(rx.search(testo)) is atteso, f"{rx.pattern!r} su {testo!r}"


# ─────────────────────────────────────────────────── il cronometro

#: (nome, regex, carattere della corsa). La coda «!» rompe il match finale: è
#: l'ingresso che fa ripartire il motore da ogni posizione, e per `_LABEL_RE`
#: è l'UNICO che lo fa — sulla corsa pura era lineare, ed è per questo che una
#: verifica del 25/07 l'aveva giudicata falso positivo.
CRONOMETRO = [
    ("_NOME_DI_PARAMETRO", _NOME_DI_PARAMETRO, "0"),
    ("_COMPOSTO", _COMPOSTO, "0"),
    ("_LABEL_RE", _LABEL_RE, "A"),
    ("_APRE_LA_FRASE_RE", _APRE_LA_FRASE_RE, "\n"),
]


@pytest.mark.parametrize("nome,rx,char", CRONOMETRO)
def test_IL_TEMPO_ottomila_caratteri_stanno_sotto_i_cinquanta_millisecondi(
        nome: str, rx, char: str):
    """⏱️ La soglia è 50 ms su 8000 caratteri. Prima della cura: 1129, 1681,
    702 e 487 ms — fra i due regimi c'è un ordine di grandezza, non una
    sfumatura, quindi la cella non è instabile su una macchina lenta."""
    testo = char * 8000 + "!"
    inizio = time.perf_counter()
    rx.search(testo)
    ms = 1000 * (time.perf_counter() - inizio)
    assert ms < 50, f"{nome} su 8000 caratteri costa {ms:.1f} ms"


def test_IL_TEMPO_dalla_PORTA_che_lo_raggiunge_davvero():
    """L'unico dei quattro che il prodotto raggiunge con testo dell'utente:
    `_COMPOSTO` dentro `valori_riusati_da_altro_contesto`. 1659 ms prima."""
    from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto

    claim = "0" * 8000 + "!"
    inizio = time.perf_counter()
    valori_riusati_da_altro_contesto(claim, "la superficie e' 400 mq")
    ms = 1000 * (time.perf_counter() - inizio)
    assert ms < 200, (
        f"dalla porta, una proposizione di 8000 caratteri costa {ms:.1f} ms")
