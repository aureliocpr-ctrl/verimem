"""T85 — la scrittura non dice se la verifica di conflitto è avvenuta.

MISURATO il 13 settembre 2026, con `HIPPO_ENCODE_DELEGATE_ONLY=1` (la
configurazione che l'utente ha davvero), `--validate full` e il demone in
ascolto. Ecco la ricevuta **intera**, non riassunta::

    inserted: 1 fact(s). quarantined=0 rejected=0 parse_errors=0
      id=43a8f6e62dde  status=ok
    inserted: 1 fact(s). quarantined=0 rejected=0 parse_errors=0
      id=dd529e8d58f1  status=ok

e lo stato che ne è seguito::

    43a8f6e6 | model_claim | superseded_by=- | moat 98.9 | mediana 33.0s
    dd529e8d | model_claim | superseded_by=- | moat 99.1 | mediana 41.2s
    RITIRATI: 0

Quattro campi, `status=ok`, e nessuna parola sulla verifica di conflitto. La
stessa identica coppia, con la stessa riga di comando ma **senza** la delega,
ritira: `superseded_by` valorizzato e motivo «same-source evolution». Una
variabile sola separa i due esiti, e la ricevuta non la nomina.

🔑 IL MOAT HA GIUDICATO — 98,9 e 99,1 — quindi non è «l'inferenza è spenta»: è
che il giudice delle RELAZIONI, quello che decide se due scritture sono in
conflitto, è un modello diverso da quello del moat e in delega non c'è. Uno dei
due sopravvive e l'altro no, e chi scrive vede `ok` in entrambi i casi.

⚠️ PERCHÉ È UN DIFETTO E NON UNA PREFERENZA: il prodotto promette di dire cosa
fa a ciò che gli viene scritto. Una verifica che non è stata eseguita è una
promessa non mantenuta, e passarla sotto silenzio è la forma già catalogata su
questo prodotto (T26a, «non giudicato in silenzio»): chi legge `ok` conclude
che i controlli sono passati, non che uno non è stato fatto.

📌 QUESTO FILE NON PRETENDE UNA DICITURA. Pretende che la ricevuta **nomini** la
verifica: la parola esatta la sceglie chi disegna l'interfaccia. Un test che
imponesse la frase deciderebbe al posto suo e si romperebbe alla prima
riformulazione.

Ticket: T85. Il campo che il gate calcola e la riga di comando non legge è
`contradicting_fact_ids` (zero occorrenze in `cli.py`, misurato), gemello di
`supersede_fact_ids` che la cura di T56 ha collegato.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import tempfile

import pytest

FONTE = ("Rapporto latenza: la mediana era 33.0s nel giro del mattino, poi "
         "41.2s dopo la ricostruzione dell'indice.")
PRIMA = "La latenza mediana e' 33.0s."
SECONDA = "La latenza mediana e' 41.2s."
TOPIC = "t85/ricevuta"

#: Le parole con cui una ricevuta POTREBBE nominare la verifica. È un elenco
#: largo di proposito: qui si misura se la porta ne dice QUALCOSA, non come.
PAROLE = ("conflitto", "conflict", "contraddi", "contradict", "relazion",
          "relation", "supersed", "ritir", "giudice", "judge", "verifica",
          "non eseguit", "not evaluated", "skipped", "non disponibile",
          "unavailable")


def _ambiente(dati: pathlib.Path) -> dict[str, str]:
    """La configurazione DELL'UTENTE: delega attiva, nessun ripiego locale.

    ⚠️ Qui la delega si METTE, non si toglie — al contrario degli altri banchi
    di questo ramo. Il difetto che si misura vive proprio lì: togliendo la
    delega il conflitto viene valutato e la domanda non si pone.
    """
    env = {**os.environ, "HIPPO_DATA_DIR": str(dati), "COLUMNS": "200",
           "HIPPO_ENCODE_DELEGATE_ONLY": "1"}
    for v in ("HIPPO_OFFLINE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE",
              "ENGRAM_ENCODE_SERVICE", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        env.pop(v, None)
    return env


def _scrivi(env: dict[str, str], testo: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "verimem.cli", "facts", "add", "-p", testo,
         "--source", FONTE, "--topic", TOPIC, "--validate", "full"],
        env=env, capture_output=True, text=True, timeout=900)


@pytest.fixture(scope="module")
def seconda_ricevuta() -> str:
    """Scrive la coppia e rende la ricevuta della SECONDA — quella per cui il
    conflitto con la prima andava valutato."""
    dati = pathlib.Path(tempfile.mkdtemp(prefix="t85-"))
    env = _ambiente(dati)
    for testo, quale in ((PRIMA, "prima"), (SECONDA, "seconda")):
        esito = _scrivi(env, testo)
        if esito.returncode != 0:
            pytest.skip(
                f"CONTROLLO POSITIVO SPENTO: la {quale} scrittura non è "
                f"riuscita (exit {esito.returncode}); senza le due scritture "
                f"non c'è nessun conflitto da valutare. {esito.stderr[-400:]}")
        if quale == "seconda":
            return esito.stdout + esito.stderr
    raise AssertionError("irraggiungibile")


@pytest.mark.slow
def test_CONTROLLO_la_scrittura_e_davvero_avvenuta(seconda_ricevuta):
    """⚠️ SENZA QUESTO la cella sotto sarebbe verde su una ricevuta vuota: una
    scrittura fallita non nomina la verifica di conflitto per l'ottimo motivo
    che non ha scritto niente, e il presidio la conterebbe come difetto."""
    assert re.search(r"inserted:\s*1 fact", seconda_ricevuta), (
        "la ricevuta non dice di aver inserito un fatto: questo banco non ha "
        f"misurato la ricevuta di una scrittura. {seconda_ricevuta[-400:]}")


@pytest.mark.slow
def test_la_ricevuta_nomina_la_verifica_di_conflitto(seconda_ricevuta):
    """LA PROMESSA: chi scrive sa che cosa è stato fatto al suo fatto.

    Oggi la ricevuta ha quattro campi — quanti inseriti, quanti quarantenati,
    quanti rifiutati, quanti errori di lettura — più id e stato. Nessuno di
    questi dice se il confronto con ciò che era già scritto sia avvenuto,
    quindi `status=ok` copre due mondi diversi: «valutato, nessun conflitto» e
    «non valutato, non lo sapremo mai».
    """
    trovate = [p for p in PAROLE if p in seconda_ricevuta.lower()]
    assert trovate, (
        "la ricevuta non nomina in alcun modo la verifica di conflitto: chi "
        "scrive legge «status=ok» e conclude che i controlli sono passati, "
        "mentre in questa configurazione il giudice delle relazioni non c'è e "
        "il confronto non è stato fatto. Nessuna di queste parole compare: "
        f"{', '.join(PAROLE)}.\n--- ricevuta intera ---\n{seconda_ricevuta}")
