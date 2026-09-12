"""T56 RED-2 — versionare: tre letture, tre promesse diverse allo stesso utente.

LA DECISIONE (12 settembre 2026, ruolo di prodotto con il voto del controllo):
fra ritirare, conservare e **versionare**, si versiona. Le due letture della
stessa evidenza restano entrambe nel corpus, e a cambiare è *cosa rende una
lettura*:

    lettura di default        -> 1 risposta, la più recente
    --include-superseded      -> 2 risposte, e si vede QUALE è superata
    --as-of <istante>         -> quella che valeva a quell'istante

⚠️ **PERCHÉ ALLA PORTA E NON DALL'SDK.** Il campo che distingue un fatto
superato (`superseded_by`) è già nel dizionario che l'SDK restituisce — è stato
aggiunto a `_fact_view` proprio perché «senza, quelli arrivano con l'aria di
essere vivi» (`verimem/client.py`, commento sopra `item = {...}`). Un test
scritto sull'SDK sarebbe quindi **verde** e il difetto resterebbe intero: la
riga che la riga di comando stampa (`riga_di_recall`, `verimem/cli.py:5204-5213`)
porta il testo, il punteggio e il moat — e **non** dice che un risultato è
superato. Il livello a cui si misura decide il verdetto: qui si misura dove
l'utente guarda.

PREDIZIONI DICHIARATE PRIMA DI ESEGUIRE (12 settembre, ore 18:50 lette):

    cella 1  default               -> VERDE oggi: il ritirato è già fuori
                                      dalla vista curata
    cella 2  --include-superseded   -> ROSSO: due righe indistinguibili,
                                      `riga_di_recall` non nomina il campo
    cella 3  --as-of                -> NON PREDETTA. `recall_as_of` filtra su
                                      `asserted_at` con ripiego su `created_at`
                                      (`verimem/temporal_context.py:258-259`),
                                      e nessuna porta valorizza `asserted_at`
                                      (0 fatti su 15.978, misurato il 30/08):
                                      il ripiego dovrebbe salvarla, ma
                                      «dovrebbe» non è una misura.

🔴 UN DIFETTO TROVATO IN QUESTO BANCO PRIMA DI ESEGUIRLO (19:05): la cella 2
confrontava le due righe senza togliere i NUMERI, e la riga porta il punteggio
di rilevanza — diverso per due fatti diversi quasi sempre. Le due righe
sarebbero risultate distinte **anche senza nessuna cura**, cioè la cella
sarebbe passata per il motivo sbagliato. Con `xfail(strict=True)` un verde è un
fallimento, quindi il difetto si sarebbe visto lo stesso — ma il verdetto che
ne usciva non parlava del prodotto. Ora ogni numero diventa un segnaposto e
resta solo ciò che la porta DICE. È la stessa classe che questo ticket
racconta: il righello che sbaglia a favore di chi lo usa.

🔒 SOLO LA CELLA 2 PORTA `xfail(strict=True)`: è l'unica il cui esito è letto
nel codice. Marcare le altre significherebbe dichiarare un esito che non ho
misurato — e con `strict` un XPASS è un fallimento, quindi una marcatura
sbagliata rompe la CI dicendo il falso. La cella 3 va **eseguita prima del
merge**: se è rossa è un rosso vero da guardare, non da marcare.

Ticket: T56 (`docs/stato-reale/ticket/T56-supersessione.md`, §6bis).
Il primo RED è `tests/test_le_tre_porte_conservano_lo_stesso_numero.py`.

Comando (una sola esecuzione, un file solo)::

    HIPPO_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \\
    ENGRAM_ENCODE_SERVICE=0 pytest -q -p no:randomly -rsfE \\
    tests/test_una_versione_non_e_un_ritiro.py
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

import pytest

#: La coppia del corpus reale: due letture della STESSA esecuzione. Nessuna
#: delle due nega l'altra — è il caso che la supersessione cancella.
FONTE = "latency over 5 queries: min 16.3s, median 33.0s, max 41.2s"
PRIMA = "La latenza riporta mediana 33.0s su 5 query."
SECONDA = "La latenza riporta min 16.3s su 5 query."
TOPIC = "t56/versione"
DOMANDA = "latenza"

#: I due fatti condividono l'inizio e la fine: quello che sta PRIMA della testa
#: e DOPO la coda in una riga stampata è tutto e solo ciò che aggiunge la porta.
TESTA = "La latenza"
CODA = "su 5 query."


def _ambiente(dati: pathlib.Path) -> dict[str, str]:
    env = {**os.environ,
           "HIPPO_DATA_DIR": str(dati), "ENGRAM_ENCODE_SERVICE": "0",
           "HIPPO_OFFLINE": "1", "HF_HUB_OFFLINE": "1",
           "TRANSFORMERS_OFFLINE": "1",
           #: la riga non deve andare a capo: la griglia si restringe da sola
           #: sul terminale del banco, e una riga spezzata si conta due volte
           "COLUMNS": "200"}
    for alias in ("ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        env.pop(alias, None)
    return env


def _cli(env: dict[str, str], *argomenti: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "verimem.cli", *argomenti],
                          env=env, capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="module")
def store() -> dict[str, object]:
    """Scrive la coppia UNA volta e tiene l'istante che sta in mezzo.

    L'istante serve alla terza cella: `--as-of` chiede «cosa valeva allora», e
    «allora» deve cadere DOPO la prima scrittura e PRIMA della seconda. Si
    prende dall'orologio e non dal database di proposito — leggere
    `created_at` legherebbe il banco allo schema invece che al contratto.
    """
    dati = pathlib.Path(tempfile.mkdtemp(prefix="t56-versione-"))
    env = _ambiente(dati)
    prima = _cli(env, "facts", "add", "-p", PRIMA, "--source", FONTE,
                 "--topic", TOPIC)
    if prima.returncode != 0:
        pytest.skip("CONTROLLO POSITIVO SPENTO: la prima scrittura non è "
                    f"riuscita (exit {prima.returncode}), quindi nessuna di "
                    f"queste letture misura qualcosa. {prima.stderr[-400:]}")
    time.sleep(1.1)          # due istanti distinti, non due righe nello stesso
    in_mezzo = time.time()
    time.sleep(1.1)
    seconda = _cli(env, "facts", "add", "-p", SECONDA, "--source", FONTE,
                   "--topic", TOPIC)
    if seconda.returncode != 0:
        pytest.skip("CONTROLLO POSITIVO SPENTO: la seconda scrittura non è "
                    f"riuscita (exit {seconda.returncode}). "
                    f"{seconda.stderr[-400:]}")
    return {"env": env, "in_mezzo": in_mezzo, "dati": dati}


def _righe(uscita: str) -> list[str]:
    """Le righe di risposta di `recall`: quelle che cominciano con «- »."""
    return [r.strip() for r in uscita.splitlines() if r.strip().startswith("- ")]


def _elenco(righe: list[str]) -> str:
    return os.linesep.join(righe)


def test_CONTROLLO_la_coppia_e_leggibile_dalla_porta(store):
    """⚠️ SENZA QUESTO le tre celle sotto possono essere verdi per il motivo
    sbagliato: una ricerca che non trova NIENTE rende zero righe, e «zero» si
    confronta bene con qualunque attesa formulata al ribasso. Qui si pretende
    che la domanda risponda, prima di chiedere che risponda in un certo modo."""
    esito = _cli(store["env"], "recall", DOMANDA, "--include-superseded")
    assert esito.returncode == 0, esito.stderr[-400:]
    assert _righe(esito.stdout), (
        "la domanda non rende niente nemmeno chiedendo anche i superati: le "
        "tre letture qui sotto non misurerebbero il versionamento, "
        f"misurerebbero un silenzio. {esito.stdout[-600:]}")


def test_la_lettura_di_default_rende_una_risposta_ed_e_la_piu_recente(store):
    """CELLA 1 — «ti do l'ultima»."""
    esito = _cli(store["env"], "recall", DOMANDA)
    assert esito.returncode == 0, esito.stderr[-400:]
    righe = _righe(esito.stdout)
    assert len(righe) == 1, (
        f"la lettura di default rende {len(righe)} risposte invece di una: "
        "versionare promette che l'ultima versione è quella servita. "
        + _elenco(righe))
    assert "16.3" in righe[0], (
        "la risposta servita non è la più recente: il versionamento serve "
        f"l'ultima, e questa è la prima. {righe[0]}")


@pytest.mark.xfail(strict=True, reason=(
    "T56: chiedendo anche i superati la porta stampa due righe della stessa "
    "forma — `riga_di_recall` porta testo, punteggio e moat e non nomina "
    "`superseded_by`, che pure è nel dizionario dell'SDK. L'utente riceve due "
    "valori e nessuno dei due dichiara di essere quello vecchio"))
def test_chiedendo_anche_i_superati_si_vede_quale_e_superato(store):
    """CELLA 2 — «te le do tutte, e ti dico quale vale».

    Non pretende una parola precisa: pretende che le due righe **si
    distinguano**. Un test che imponesse la dicitura deciderebbe la forma
    dell'interfaccia al posto di chi la disegna; qui la promessa è che una
    differenza ci sia, e oggi non c'è.
    """
    esito = _cli(store["env"], "recall", DOMANDA, "--include-superseded")
    assert esito.returncode == 0, esito.stderr[-400:]
    righe = _righe(esito.stdout)
    assert len(righe) == 2, (
        f"chiedendo anche i superati le risposte sono {len(righe)} invece di "
        "due: versionare tiene entrambe le letture. " + _elenco(righe))
    vecchia = [r for r in righe if "33.0" in r]
    nuova = [r for r in righe if "16.3" in r]
    assert vecchia, "la lettura superata non torna affatto. " + _elenco(righe)
    assert nuova, "la lettura più recente non torna. " + _elenco(righe)

    #: ⚠️ IL CONFRONTO NON PUÒ INCLUDERE IL TESTO: le due righe differiscono
    #: già per quello, e sarebbe un verde gratis. Si guarda solo ciò che sta
    #: fuori dal testo del fatto.
    for riga in (vecchia[0], nuova[0]):
        if TESTA not in riga or CODA not in riga:
            pytest.skip(
                "BANCO SPENTO: la riga stampata non contiene il testo com'è "
                "stato scritto, quindi non si può separare ciò che aggiunge "
                f"la porta da ciò che viene dal fatto. {riga}")

    def _forma(riga: str) -> str:
        """La riga SENZA il fatto e SENZA i numeri che cambiano a ogni giro.

        🔴 I NUMERI VANNO TOLTI, e questo banco per poco non lo faceva: la
        riga porta il punteggio di rilevanza, che per due fatti diversi è
        quasi sempre diverso. Confrontando le code così come sono, le due
        righe risultano DIVERSE sempre — anche oggi, senza nessuna cura — e
        questa cella sarebbe passata per il motivo sbagliato. Con
        `xfail(strict=True)` un verde è un fallimento, quindi il difetto si
        sarebbe visto; ma il verdetto che ne usciva non parlava del
        prodotto. Sostituendo ogni numero con un segnaposto resta solo ciò
        che la porta DICE, che è quanto questa cella misura.
        """
        fuori = riga[:riga.index(TESTA)] + "|" + riga[riga.index(CODA) + len(CODA):]
        return re.sub(r"[0-9]+(?:[.,][0-9]+)?", "#", fuori)

    assert _forma(vecchia[0]) != _forma(nuova[0]), (
        "le due righe sono indistinguibili una volta tolto il testo del "
        "fatto: la porta non dice quale delle due è la versione superata, e "
        "chi legge riceve due numeri diversi per la stessa domanda senza un "
        f"ordine. superata: {vecchia[0]} — corrente: {nuova[0]}")


def test_al_passato_si_riceve_la_versione_che_valeva_allora(store):
    """CELLA 3 — «ti do quella che valeva allora».

    📌 NESSUNA PREDIZIONE DICHIARATA: il filtro del viaggio nel tempo guarda
    `asserted_at` e ripiega su `created_at`, e `asserted_at` non è valorizzato
    da nessuna porta. Il ripiego dovrebbe bastare — «dovrebbe» non è una
    misura, e questo file esiste per non scriverne.
    """
    esito = _cli(store["env"], "recall", DOMANDA,
                 "--as-of", f"{store['in_mezzo']:.3f}")
    assert esito.returncode == 0, esito.stderr[-400:]
    righe = _righe(esito.stdout)
    assert righe, (
        "la lettura al passato non rende niente all'istante in cui la prima "
        f"versione era l'unica scritta. {esito.stdout[-600:]}")
    assert any("33.0" in r for r in righe), (
        "al passato non si riceve la versione che a quell'istante era l'unica "
        "scritta. " + _elenco(righe))
    assert not any("16.3" in r for r in righe), (
        "al passato torna anche la versione scritta DOPO quell'istante: "
        "allora non era ancora vera. " + _elenco(righe))
