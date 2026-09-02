"""`L1.20` si spegne per sempre proprio quando l'encoding costerebbe zero.

Il detector semantico di self-claim (`L1.20`) non vuole pagare un cold-load del
modello sul percorso di scrittura — ~32s — e per questo il suo encoder è
*guarded*: se codificare qui provocherebbe un caricamento a freddo, declina e il
detector si disarma. La scelta è giusta e dichiarata.

Il guard però chiede la cosa sbagliata (``semantic_selfclaim.py``)::

    if not (embedding.is_loaded() or embedding._delegate_only()):
        raise _ColdEncoderDeclined(...)

Sono **due vie su tre**. La terza — il servizio condiviso — è quella che
`_encode_one` prova **per prima** (``embedding.py``, «*shared service first,
in-process fallback*»), ed è invisibile al guard.

MISURATO il 2026-08-28, tre scritture in fila, nessuna delega:

    daemon ATTIVO    lo storage codifica via servizio -> mai un cold-load
                     -> ``is_loaded()`` resta False PER SEMPRE
                     -> L1.20 assente 3 volte su 3
    daemon ASSENTE   lo storage è costretto al cold-load
                     -> ``is_loaded()`` True dalla 1ª -> L1.20 presente dalla 2ª

⇒ Il docstring del guard elenca la delega fra le condizioni che rendono il
disarmo innocuo («*production servers pre-warm at boot or delegate, so this only
ever skips the literal first write*»). È il contrario: **con il daemon il
disarmo diventa permanente**. Una mitigazione che è la causa.

⚖️ QUANTO COSTA, misurato e non gonfiato: in 6 casi su 6 il self-claim è stato
**quarantinato lo stesso** da `L1.10`, `L1.13` e `L1.15`. Nessun falso è passato.
Il danno è che un presidio è spento **e la ricevuta non lo dice**: chi legge
`warnings` conta tre difese e non sa che una quarta esiste e tace.

📌 LA CURA sta già nel prodotto, che alla stessa domanda risponde altrove
(``mcp_server.py``, `hippo_warmup_status`)::

    "cold_load_estimate_s": 0 if (in_proc or daemon_ok) else 20

cioè: se il daemon è utilizzabile, **il cold-load non c'è**. Il guard deve
chiedere *«un vettore è ottenibile senza cold-load?»*, non *«il modello è
caricato QUI?»* — e `encode_service.daemon_usable()` risponde già.

⚠️ PERCHÉ IN SOTTOPROCESSO, e non è un vezzo: **questo difetto è invisibile alla
suite per costruzione.** ``tests/conftest.py:144-147`` spegne il daemon per tutti
i test, e lo dichiara — *«Tests must use the stub, never a live shared encode
daemon»* → ``ENGRAM_ENCODE_SERVICE=0`` — più ``delenv`` della delega alla 143.
Sono due scelte giuste: un test che parla con un daemon vivo non è isolato.
Ma la conseguenza è che **la condizione che produce il difetto è esattamente
quella che la suite esclude**: sotto `pytest`, `L1.20` tace per la ragione giusta
e nessun test potrebbe mai accorgersi che tace anche per quella sbagliata.

⇒ Il regime di produzione va ricostruito **dentro il figlio**, che è già una
sandbox: store temporaneo, nessuna delega, e il servizio **riabilitato**
togliendo la variabile che `conftest` impone al padre. Il figlio non tocca nulla
di condiviso — legge il daemon, non lo avvia né lo spegne.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pytest

from tests._esito import esito

# Il figlio costruisce il regime PRIMA di importare il prodotto, scrive un
# self-claim e riporta cosa ha visto. Stampa una riga sola, in JSON, così il
# padre non deve indovinare niente dall'output.
_FIGLIO = r"""
import json, os, io, contextlib, tempfile
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)   # niente delega: e' il regime dell'utente
os.environ.pop("ENGRAM_ENCODE_SERVICE", None)        # conftest lo mette a 0 per isolare la
                                                     # suite: qui serve il regime di PRODUZIONE
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()    # store isolato, mai quello di casa
from verimem import Memory, embedding
from verimem import encode_service

from verimem.config import CONFIG
_disc = encode_service.read_discovery() or {}
esito = {
    "daemon_usable": bool(encode_service.daemon_usable()),
    "loaded_prima": bool(embedding.is_loaded()),
    # PERCHE', se non e' usabile: uno skip che non dice la ragione e' un
    # sensore scollegato — resta muto per sempre e nessuno se ne accorge.
    "discovery": bool(_disc),
    "raggiungibile": bool(encode_service.is_reachable()),
    "modello_daemon": _disc.get("model"),
    "modello_config": CONFIG.embedding_model,
    "servizio_env": os.environ.get("ENGRAM_ENCODE_SERVICE"),
}
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    ricevuta = Memory().add("It works, verified, all tests pass, done.", topic="l120/tdd")
esito["layers"] = [w.get("layer") for w in (ricevuta.get("warnings") or [])]
esito["status"] = ricevuta.get("status")
esito["loaded_dopo"] = bool(embedding.is_loaded())
print("ESITO " + json.dumps(esito))
"""


def _prima_scrittura_senza_delega() -> dict:
    """Esegue il figlio e restituisce la sua riga di esito."""
    # Il figlio deve vedere il regime di PRODUZIONE, non quello della suite.
    # `conftest` impone (giustamente, per isolare i test): servizio a 0, delega,
    # store temporaneo e soprattutto un MODELLO STUB diverso — 384 dimensioni
    # contro le 768 del daemon vero. Su quel mismatch `_encode_via_service`
    # rifiuta il daemon per disegno (un daemon di altra config darebbe vettori
    # in uno spazio diverso: poisoning silenzioso), quindi `daemon_usable()`
    # sarebbe False per una ragione che con questo difetto non c'entra.
    fuori = {
        "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_ENCODE_DELEGATE_ONLY",
        "HIPPO_ENCODE_SERVICE", "ENGRAM_ENCODE_SERVICE",
        "HIPPO_EMBEDDING_MODEL", "ENGRAM_EMBEDDING_MODEL",
        "HIPPO_EMBEDDING_DIM", "ENGRAM_EMBEDDING_DIM",
        "HIPPO_OFFLINE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE",
    }
    env = {k: v for k, v in os.environ.items() if k not in fuori}
    proc = subprocess.run([sys.executable, "-c", _FIGLIO], capture_output=True,
                          text=True, env=env, errors="replace", timeout=900,
                          cwd=tempfile.gettempdir())
    # ⚠️ `esito()` dichiara PRIMA com'e' finito il processo: se il figlio muore,
    # il messaggio dice «PROCESSO-MORTO exit=N» invece di «manca la stringa
    # ESITO», che e' il difetto misurato il 14/08 e curato una volta sola in
    # `tests/_esito.py`. Prima qui si leggeva `proc.stdout` senza guardare il
    # codice d'uscita: un figlio ucciso lasciava un output tronco e il banco
    # accusava se stesso.
    for riga in esito(proc).splitlines():
        if riga.startswith("ESITO "):
            return json.loads(riga[6:])
    raise AssertionError(
        "il sottoprocesso non ha riportato nessun esito: il banco è rotto, non "
        f"il prodotto.\nstdout:\n{proc.stdout[-1500:]}\nstderr:\n{proc.stderr[-1500:]}")


def test_l120_parla_quando_l_encoding_non_costa_un_cold_load():
    """Il cuore: col daemon disponibile il vettore c'è a costo zero, quindi il
    presidio semantico non ha ragione di disarmarsi."""
    esito = _prima_scrittura_senza_delega()
    if not esito["daemon_usable"]:
        pytest.skip(
            "daemon non utilizzabile ⇒ il guard declina per la ragione GIUSTA "
            "(un cold-load ci sarebbe davvero) e questo test non misura niente. "
            "La ragione, per non lasciare un sensore muto:\n"
            f"  discovery letto = {esito['discovery']}   "
            f"raggiungibile = {esito['raggiungibile']}\n"
            f"  modello del daemon = {esito['modello_daemon']!r}\n"
            f"  modello di CONFIG  = {esito['modello_config']!r}   "
            f"(coincidono: {esito['modello_daemon'] == esito['modello_config']})\n"
            f"  ENGRAM_ENCODE_SERVICE = {esito['servizio_env']!r}")

    assert "L1.20" in esito["layers"], (
        "il daemon è utilizzabile — quindi un vettore è ottenibile senza "
        "cold-load — eppure il presidio semantico `L1.20` non ha parlato.\n"
        f"  daemon_usable = {esito['daemon_usable']}\n"
        f"  is_loaded()   = {esito['loaded_prima']} prima, {esito['loaded_dopo']} dopo\n"
        f"  layers        = {esito['layers']}\n"
        "Il guard di `semantic_selfclaim` chiede `is_loaded() or _delegate_only()` "
        "e non vede la terza via (`_encode_via_service`), che `_encode_one` prova "
        "per prima. ⇒ il disarmo, dichiarato temporaneo, è permanente.")


def test_CONTROLLO_il_self_claim_viene_fermato_comunque():
    """La difesa, e senza di lei il test qui sopra si legge come un allarme più
    grosso di quanto sia.

    `L1.20` è spento, ma il self-claim NON passa: lo fermano `L1.10`, `L1.13` e
    `L1.15`. Se un giorno questo controllo diventasse rosso, il difetto non
    sarebbe più «un presidio muto» ma «un falso che entra», e andrebbe riscritto
    tutto il referto, non solo il guard.
    """
    esito = _prima_scrittura_senza_delega()
    assert esito["status"] == "quarantined", (
        "il self-claim non supportato è ENTRATO: questo è molto peggio del "
        "difetto che il test sopra descrive.\n"
        f"  status = {esito['status']}   layers = {esito['layers']}")
    assert len(esito["layers"]) >= 3, (
        "meno di tre layer hanno parlato: la copertura che rende innocuo il "
        f"disarmo di L1.20 non c'è più.\n  layers = {esito['layers']}")


def test_CONTROLLO_il_banco_vede_davvero_lo_stato_del_daemon():
    """L'altra metà della difesa: se `daemon_usable()` restituisse sempre False,
    il test principale verrebbe SALTATO per sempre e nessuno se ne accorgerebbe
    — è la forma «una misura che non c'è si legge come una misura perfetta».
    Qui si verifica che il predicato sia almeno interrogabile e booleano.
    """
    from verimem import encode_service

    valore = encode_service.daemon_usable()
    assert isinstance(valore, bool), (
        "`daemon_usable()` non restituisce un booleano: il ramo di skip del "
        f"test principale non è affidabile.\n  valore = {valore!r}")
