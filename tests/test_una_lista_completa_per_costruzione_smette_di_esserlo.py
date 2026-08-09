"""«è», «già», «perché», «può» sono diventate unità di misura. Per colpa mia.

IL DIFETTO, misurato da ws4 sul corpus reale (5874 fatti vivi con una cifra)
come popolazione opposta della cura ``5e78549a`` — la mia, di un'ora prima::

    fatti in cui l'estrazione CAMBIA:        314  (5,3%)
    fatti che GUADAGNANO un'unità nuova:      66  (1,1%)
    e le unità nuove sono:  +e ← «è» · +gia ← «già» · +perche ← «perché» · +puo ← «può»

🔑 LA CAUSA NON È «LA LISTA È CORTA»: È L'ORDINE DI DUE OPERAZIONI, e la
diagnosi è di ws4, verbatim::

    'e'   in _NON_UNIT_WORDS?  True      norm_unit('e')  -> 'e'
    'è'   in _NON_UNIT_WORDS?  False     norm_unit('è')  -> 'e'

``extract_quantities`` confronta ``unit_s.lower()`` — la forma ACCENTATA — con
la lista, e ``norm_unit``, che toglie l'accento, gira **dopo**. Il filtro vede
``è``, la lista contiene ``e``, e la normalizzazione che le farebbe incontrare
arriva troppo tardi.

🔑 E LA TESI CHE VALE OLTRE QUESTO CASO, ed è la ragione per cui vale la pena
scriverlo: **``_NON_UNIT_WORDS`` era completa PER COSTRUZIONE**. Finché il regex
catturava solo ``[A-Za-z]``, le parole accentate non ci arrivavano nemmeno: la
lista non aveva bisogno di contenerle. Allargando la cattura a «una lettera di
qualunque alfabeto» ho reso incompleta una lista che nessuno aveva sbagliato.

⇒ **Una cura che allarga un input rende incomplete tutte le liste a valle**, e
  quelle liste non sembrano difettose perché per anni non lo erano. È la classe
  ② vista dal lato opposto: non «chi altro fa la stessa cosa?», ma **«chi
  RICEVE ciò che ho appena allargato?»**.

📌 LE DUE POPOLAZIONI SI SOMMANO, e vanno curate diversamente:
  · ACCENTATE (`è`, `già`, `perché`, `può`) — 66 fatti, ws4: la lista le
    contiene già nella forma piana, serve confrontare la forma NORMALIZZATA.
  · ASCII (`ma` 43, `ne` 14, `si` 10, `se` 7) — misurate da me sullo stesso
    corpus: sono particelle italiane che nella lista non ci sono MAI state, e
    lì la normalizzazione non serve a niente. Due difetti, due cure.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities

#: ws4, dal corpus: parole accentate che la lista contiene in forma piana.
ACCENTATE = [
    "il totale è 146",
    "la criticità 3/5 è alta",
    "sono già 200 i fatti",
    "ne restano 100 perché cosi' e'",
    "il valore 40 può variare",
]

#: Le mie, dallo stesso corpus: particelle italiane mai state in lista.
#: 43 occorrenze di «ma», 14 di «ne», 10 di «si», 7 di «se» su 45381 unità.
PARTICELLE = [
    "il bench ha fatto 120 ma 45 in media",
    "ne restano 30 ne piu' ne meno",
    "sono 40 se contiamo i doppioni",
    "si contano 40 si per volta",
]

#: ⚠️ LA POPOLAZIONE OPPOSTA. Le unità corte e accentate VERE devono restare —
#: sul corpus le più frequenti sono h 2059, s 1402, ms 745, gb 177, kb 143.
UNITA_VERE_CORTE = [
    ("il job dura 3 h", "h"),
    ("la latenza e' 45 ms", "ms"),
    ("il file pesa 72 gb", "gb"),
    ("il delta e' 12 pp", "pp"),
    ("il magazzino contiene 40 unità", "unita"),
    ("das Lager hat 40 Stück", "stuck"),
    ("la riunione e' durata 45 minuti", "minuto"),
]


@pytest.mark.parametrize("frase", ACCENTATE)
def test_una_parola_ACCENTATA_della_lista_non_e_una_unita(frase):
    """IL CUORE (ws4): la lista contiene «e», il testo dice «è», e il confronto
    avviene sulla forma accentata mentre la normalizzazione arriva dopo."""
    unita = {u for u, _v in extract_quantities(frase) if u}
    assert not unita, f"«{frase}» produce unità {unita}"


@pytest.mark.parametrize("frase", PARTICELLE)
def test_una_PARTICELLA_italiana_non_e_una_unita(frase):
    """L'altra metà, che la normalizzazione non tocca: «ma», «ne», «se», «si»
    sono in ASCII e nella lista non ci sono mai state. Qui serve la lista."""
    unita = {u for u, _v in extract_quantities(frase) if u}
    assert not unita, f"«{frase}» produce unità {unita}"


@pytest.mark.parametrize("frase,attesa", UNITA_VERE_CORTE)
def test_CONTROLLO_POSITIVO_le_unita_corte_e_accentate_restano(frase, attesa):
    """⚠️ IL PRESIDIO. Le unità di una o due lettere sono le PIÙ FREQUENTI del
    corpus — h 2059, s 1402, ms 745 — e una cura che filtrasse per lunghezza
    spegnerebbe il rilevamento numerico su metà dei fatti. E «unità»/«Stück»
    devono continuare a passare: sono la cura di un'ora fa."""
    unita = {u for u, _v in extract_quantities(frase) if u}
    assert attesa in unita, f"«{frase}» -> {unita}"
