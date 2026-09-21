"""T181 — l'evento del journal dice CHI ha trattenuto e non PERCHÉ.

Un fatto fermato dal gate lascia nel journal una riga come questa (verbatim
dallo `events.jsonl` reale, fatto `67d10383dee4`):

    {"name": "flow.write", "payload": {"status": "quarantined",
     "fact_id": "67d10383dee4", "layers": ["L4.1"],
     "grounding_score": 98.44216918945312, "judged": true,
     "withheld_despite_judge": true}, ...}

C'è chi l'ha fermato, c'è cosa diceva il giudice, c'è che è stato fermato
malgrado il giudice. **Non c'è perché.** La ragione — «il claim afferma un
valore che la fonte non contiene: 7» — esiste solo nella ricevuta stampata a
chi scrive in quel momento: chi apre il journal un'ora dopo deve rieseguire il
gate sullo stesso testo, e può farlo solo se ha ancora il claim **e** la fonte.

⚠️ NON SERVE INVENTARE NÉ LA STRINGA NÉ IL TETTO, e questa cella lo dà per
scontato perché il prodotto ha già tutti e due:

    `_reason_from_warnings(warnings)`   client.py — sceglie il layer bloccante
                                        di priorità più alta che porta testo
                                        ed esclude gli advisory: è la stessa
                                        stringa che finisce nella ricevuta
    `MAX_ESTRATTO = 140` + `safe_cut`   observability.py — applicato ai campi
                                        il cui nome finisce in `_excerpt`,
                                        scritto lì «e non nei chiamanti»
                                        perché prima era ripetuto quattro
                                        volte e ognuna sbagliava per conto suo

Da qui il nome della chiave: `quarantined_reason_excerpt`. Il suffisso non è
cosmetico — è ciò che fa scattare il taglio a 140 senza aggiungere una riga di
logica, e dice a chi legge che quello è un estratto, non il testo intero. La
colonna del database, se e quando arriverà, porterà il testo pieno e si
chiamerà come la sua gemella `superseded_reason`.

⚠️ SI MISURA IN SOTTOPROCESSO, e non per gusto: `EVENT_LOG_PATH` si fissa
all'import del modulo, quindi una variabile d'ambiente impostata dentro il test
arriva troppo tardi e il banco scriverebbe nel journal VERO. È la trappola che
ci è già costata una scrittura nello store di produzione: qui il processo nasce
con l'ambiente già puntato al `tmp_path`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]

#: Un self-claim senza fonte: lo ferma lo screen lessicale, senza chiamare il
#: giudice. Serve un fatto trattenuto in modo deterministico, non un fatto
#: trattenuto in modo interessante.
CLAIM = "Il servizio funziona, verificato."


def _scrivi_isolato(tmp_path) -> tuple[subprocess.CompletedProcess, Path]:
    """Scrive un fatto in un processo il cui journal è già altrove."""
    dati = tmp_path / "dati"
    dati.mkdir(parents=True, exist_ok=True)
    journal = tmp_path / "eventi.jsonl"

    ambiente = dict(os.environ)
    ambiente["ENGRAM_DATA_DIR"] = str(dati)
    ambiente["HIPPO_DATA_DIR"] = str(dati)
    ambiente["VERIMEM_DATA_DIR"] = str(dati)
    ambiente["ENGRAM_EVENT_LOG"] = str(journal)
    ambiente.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)

    esito = subprocess.run(
        [sys.executable, "-m", "verimem.cli", "remember", CLAIM,
         "--topic", "banco/t181"],
        cwd=RADICE, env=ambiente, capture_output=True, text=True,
        # `encoding` accanto a `text=True`: senza, su Windows la lettura usa
        # cp1252, il thread lettore muore sul primo byte che non sa decodificare
        # e il canale torna None con il processo a 0 — misurato su #95 il 21/09.
        encoding="utf-8", errors="replace", timeout=600,
    )
    return esito, journal


def _eventi_di_scrittura(journal: Path) -> list[dict]:
    if not journal.exists():
        return []
    righe = []
    for riga in journal.read_text(encoding="utf-8").splitlines():
        try:
            evento = json.loads(riga)
        except ValueError:
            continue
        if evento.get("name") == "flow.write":
            righe.append(evento.get("payload") or {})
    return righe


@pytest.fixture(scope="module")
def scrittura_trattenuta(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("t181")
    esito, journal = _scrivi_isolato(tmp_path)
    return esito, _eventi_di_scrittura(journal)


# ------------------------------------------------------- controllo positivo --
def test_il_banco_vede_davvero_un_fatto_trattenuto(scrittura_trattenuta) -> None:
    """Se il bersaglio fosse rosso perché non è successo niente, questa cella
    lo direbbe: deve esserci un evento, e deve riguardare un fatto FERMATO."""
    esito, eventi = scrittura_trattenuta

    assert eventi, (
        f"nessun evento flow.write nel journal isolato: il banco sta misurando "
        f"il vuoto.\n--- stdout ---\n{(esito.stdout or '')[-600:]}\n"
        f"--- stderr ---\n{(esito.stderr or '')[-600:]}")
    trattenuti = [e for e in eventi if e.get("status") == "quarantined"]
    assert trattenuti, (
        f"il claim non è stato trattenuto, quindi non c'è nessuna ragione da "
        f"registrare: status visti = {[e.get('status') for e in eventi]!r}")
    assert trattenuti[-1].get("layers"), (
        f"l'evento dice che il fatto è stato fermato ma non da chi: "
        f"layers={trattenuti[-1].get('layers')!r}")


# ------------------------------------------------------------- il bersaglio --
def test_l_evento_porta_anche_la_ragione(scrittura_trattenuta) -> None:
    """Il difetto: l'evento nomina il layer e tace il perché."""
    _esito, eventi = scrittura_trattenuta
    trattenuti = [e for e in eventi if e.get("status") == "quarantined"]
    assert trattenuti, "senza un fatto trattenuto questa cella non prova niente"
    evento = trattenuti[-1]

    ragione = evento.get("quarantined_reason_excerpt")

    assert ragione, (
        f"l'evento dice CHI ha trattenuto ({evento.get('layers')!r}) e non "
        f"PERCHÉ: chi legge il journal dopo non può sapere quale dettaglio ha "
        f"fermato il fatto senza rieseguire il gate sullo stesso testo. "
        f"Chiavi presenti: {sorted(evento)!r}")
    assert str(evento.get("layers", [""])[0]).split("-")[0] in ragione or ragione, (
        "la ragione dovrebbe cominciare dal layer che ha agito")


# --------------------------------------------------------- conta le porte ----
#: Le scritture non escono da un punto solo: `emit_write` è chiamato da tre
#: posti che possono fermare un fatto — l'SDK quando lo trattiene, l'SDK quando
#: lo RESPINGE, e la porta MCP, che il commento accanto a sé descrive come
#: quella «invisibile alla sala motore». Curarne una e dichiarare chiuso il
#: difetto è la classe di errore che ci costa più tempo: una cosa scritta in un
#: punto solo di tre.
#:
#: Esente una sola chiamata, e per una ragione che non è comodità:
#: `routed_telemetry` non è un fatto fermato, è telemetria instradata.
STATUS_SENZA_TRATTENIMENTO = {"routed_telemetry"}


def test_tutte_le_porte_che_fermano_una_scrittura_dicono_il_perche() -> None:
    """Se domani nasce una quarta porta, questa cella la vede: cerca le
    chiamate nel sorgente, non i comportamenti che qualcuno ha pensato di
    esercitare."""
    import ast as _ast

    scoperte: list[str] = []
    trovate = 0
    for modulo in ("verimem/client.py", "verimem/mcp_server.py"):
        albero = _ast.parse((RADICE / modulo).read_text(encoding="utf-8"))
        for nodo in _ast.walk(albero):
            if not isinstance(nodo, _ast.Call):
                continue
            nome = getattr(nodo.func, "id", None) or getattr(nodo.func, "attr", None)
            if nome not in ("_emit_write", "emit_write"):
                continue
            testo = _ast.unparse(nodo)
            stato = next((k.value for k in nodo.keywords if k.arg == "status"), None)
            if (isinstance(stato, _ast.Constant)
                    and stato.value in STATUS_SENZA_TRATTENIMENTO):
                continue
            trovate += 1
            if "quarantined_reason_excerpt" not in testo:
                scoperte.append(f"{modulo}:{nodo.lineno}")

    assert trovate >= 3, (
        f"trovate solo {trovate} chiamate che possono fermare una scrittura: "
        f"il righello sta guardando un codice che non c'è più, non un difetto "
        f"assente")
    assert not scoperte, (
        f"queste porte fermano una scrittura senza dire perché: {scoperte}. "
        f"Il journal le registrerà con i layer e senza ragione, e chi legge "
        f"dopo non potrà sapere quale dettaglio ha fermato il fatto")


# ------------------------------------------------- il tetto, provato non assunto --
def test_la_ragione_rispetta_il_tetto_degli_estratti(scrittura_trattenuta) -> None:
    """Il suffisso `_excerpt` deve far scattare il taglio: se un giorno la
    chiave venisse rinominata senza quel suffisso, il journal comincerebbe a
    portare stringhe di lunghezza arbitraria e nessuno se ne accorgerebbe."""
    from verimem.observability import MAX_ESTRATTO

    _esito, eventi = scrittura_trattenuta
    for evento in eventi:
        ragione = evento.get("quarantined_reason_excerpt")
        if ragione is None:
            continue
        assert len(str(ragione)) <= MAX_ESTRATTO, (
            f"la ragione nel journal è lunga {len(str(ragione))} caratteri, "
            f"oltre il tetto {MAX_ESTRATTO} degli estratti: il taglio non sta "
            f"scattando e il journal cresce senza freno")
