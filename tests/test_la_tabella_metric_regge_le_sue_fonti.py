"""I file che la tabella «Metric» cita esistono e contengono i numeri che dichiara.

PERCHÉ QUESTO FILE ESISTE, e perché NON POTEVA ESISTERE FINO A UN'ORA FA.
La tabella «Metric» del README non dichiarava le proprie fonti: sette numeri
nostri e nessun riferimento all'artefatto. Un presidio scritto in quelle
condizioni deve INDOVINARE quale file sostenga quale numero, e indovinare non
funziona — misurato il 2026-08-15 provando tre ancoraggi, tutti e tre falliti::

    il VALORE              0.66 compare come valore in 27 file di risultati
    il NOME della metrica  assente in 5 casi su 7 (i JSON dicono `accuracy`,
                           la tabella dice «End-to-end QA, cross-user»)
    il NOME del file       parlante, ma non collegato ad alcuna riga

Il primo dei tre fu perfino scritto: passava **verde** trovando omonimie, ed è
stato cancellato prima di entrare. *Un presidio verde per la ragione sbagliata
non è inutile: certifica.*

⇒ La cura è stata scrivere il legame (`66ce8cd0`), non indovinarlo. Questo file
è il **complemento** di quella cura, e arriva subito dopo per una ragione
imparata a spese nostre: una cura che tocca una promessa deve portarsi dietro il
presidio della promessa NUOVA, o scambia un difetto documentato con un buco
silenzioso.

COME È ANCORATO, e perché adesso il rumore non c'è più:
  · **setup** — la lista dei file esce DAL README a ogni esecuzione, non è
    ricopiata: se la dichiarazione cambia, il caso la segue;
  · **assert** — i numeri vengono cercati SOLO dentro i file che il README
    dichiara. È il perimetro ristretto a cancellare il rumore che aveva fatto
    passare il presidio sbagliato: `0.66` compare in 27 file *del repository*,
    ma la domanda giusta è se compaia **nei cinque che citiamo**.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
README = RADICE / "README.md"
RISULTATI = RADICE / "benchmark" / "results"

#: L'ancora della sezione che dichiara le fonti, come compare nel README.
_ANCORA = "Where each of our numbers comes from"

#: Numeri che il README dichiara ESPLICITAMENTE come privi di file di risultati:
#: eccezioni SCRITTE, non omissioni, e restano qui finché la riga le dice.
#:
#: Sono DUE voci per UN solo numero, e la ragione merita di essere scritta: la
#: tabella riporta `0.739`, il testo che lo scusa dice «(as `0.7394`)» perché è
#: la forma con cui compare in BENCHMARKS.md. Un'eccezione ancorata a una sola
#: delle due stringhe lascia l'altra scoperta — ed è esattamente come questo
#: presidio si è acceso la prima volta che l'ho eseguito, rosso su `0.7394`.
SENZA_FILE_DICHIARATO = frozenset({"0.739", "0.7394"})

_FILE = re.compile(r"`([A-Za-z0-9_.-]+\.json)`")
_NUM = re.compile(r"`(0\.\d{2,4})`")


def _zona_delle_fonti() -> str:
    testo = README.read_text(encoding="utf-8")
    i = testo.find(_ANCORA)
    if i < 0:
        return ""
    # fino alla riga vuota che chiude il paragrafo
    fine = testo.find("\n\n", i)
    return testo[i:fine if fine > 0 else i + 2000]


def _valori(nodo) -> list[float]:
    if isinstance(nodo, bool):
        return []
    if isinstance(nodo, (int, float)):
        return [float(nodo)]
    if isinstance(nodo, dict):
        return [v for x in nodo.values() for v in _valori(x)]
    if isinstance(nodo, list):
        return [v for x in nodo for v in _valori(x)]
    return []


def test_la_dichiarazione_delle_fonti_e_ancora_nel_readme() -> None:
    """Precondizione: senza la sezione, i casi sotto tacerebbero per assenza."""
    zona = _zona_delle_fonti()
    assert zona, (
        f"il README non contiene più «{_ANCORA}»: se la sezione è stata "
        f"riscritta aggiorna _ANCORA, se è stata TOLTA va tolto anche questo "
        f"file — insieme alla possibilità di verificare quei numeri"
    )
    assert _FILE.findall(zona), "la sezione non cita alcun file di risultati"
    assert _NUM.findall(zona), "la sezione non cita alcun numero"


@pytest.mark.parametrize("nome", _FILE.findall(_zona_delle_fonti()))
def test_il_file_citato_esiste(nome: str) -> None:
    assert (RISULTATI / nome).is_file(), (
        f"il README cita `{nome}` come fonte di un suo numero e quel file non "
        f"esiste in benchmark/results/. Un riferimento che non si apre è peggio "
        f"di nessun riferimento: promette una verifica che non si può fare"
    )


@pytest.mark.parametrize("numero", _NUM.findall(_zona_delle_fonti()))
def test_il_numero_compare_in_un_file_citato(numero: str) -> None:
    """Il numero si cerca SOLO nei file dichiarati, ed è ciò che toglie il rumore."""
    if numero in SENZA_FILE_DICHIARATO:
        pytest.skip(
            f"{numero} è dichiarato NEL README come privo di file di risultati "
            f"(è riportato in BENCHMARKS.md): l'eccezione è scritta, non "
            f"silenziosa. Quando il run del terzo utente verrà committato, "
            f"togliere questa voce e il caso diventerà un controllo come gli altri"
        )
    atteso, decimali = float(numero), len(numero.split(".")[1])
    trovato = []
    for nome in _FILE.findall(_zona_delle_fonti()):
        p = RISULTATI / nome
        if not p.is_file():
            continue
        try:
            dati = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        if any(round(v, decimali) == atteso for v in _valori(dati)):
            trovato.append(nome)
    assert trovato, (
        f"il README dichiara {numero} e nessuno dei file che cita lo contiene. "
        f"O il numero è stato aggiornato senza rigenerare l'artefatto, o "
        f"l'artefatto è stato rigenerato e la riga è rimasta indietro: in "
        f"entrambi i casi chi legge trova un riferimento che non conferma"
    )
