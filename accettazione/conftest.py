"""Il job di accettazione (T217): il pacchetto INSTALLATO, dal lato dell'utente.

Queste prove non girano con la suite: girano in `accettazione.yml`, dopo che il
wheel e' stato installato in un venv vergine e `verimem warmup` ha scaricato il
giudice, come dice il README. Parlano al prodotto come un utente: processi
nuovi (`python`, `verimem`, `verimem mcp`) con l'ambiente posto PRIMA
dell'import e una cartella dati propria. Nessuna importa `verimem` nel processo
di pytest: lo stato di un import condiviso non e' quello che un utente ha.

⚠️ IL CONTROLLO POSITIVO IN TESTA (`pacchetto_installato`). Se `import verimem`
risolve nell'albero del repo invece che nel site-packages del venv, ogni verde
qui sotto misurerebbe il codice sorgente e non il wheel: il difetto che questo
job esiste per chiudere. In quel caso la sessione si FERMA, non passa.

⚠️ NESSUNO SKIP, NESSUN XFAIL. Una riga rossa e' rossa finche' il ticket che la
chiude non e' fuso: il job diventa verde quando il prodotto mantiene la
promessa, non quando la prova si ammorbidisce.
"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

import pytest

#: Tetto per un singolo comando: la prima scrittura giudicata carica il giudice
#: nel processo (README: «judged in process in ~22 s»), su un runner lento anche
#: il doppio. Oltre, e' un difetto da vedere, non da aspettare.
TETTO_S = 300


def _eseguibile(nome: str) -> str:
    """Il comando `verimem` accanto all'interprete del venv (Scripts/ o bin/)."""
    cartella = Path(sys.executable).parent
    for candidato in (cartella / f"{nome}.exe", cartella / nome):
        if candidato.exists():
            return str(candidato)
    raise FileNotFoundError(
        f"`{nome}` non e' accanto a {sys.executable}: il wheel non ha installato "
        f"il comando che il README fa usare")


@pytest.fixture(scope="session", autouse=True)
def pacchetto_installato() -> Path:
    """`import verimem` deve risolvere nel site-packages di QUESTO venv."""
    uscita = subprocess.run(
        [sys.executable, "-c", "import verimem; print(verimem.__file__)"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=tempfile.gettempdir(), timeout=TETTO_S)
    if uscita.returncode != 0:
        pytest.exit(f"`import verimem` non riesce dal venv:\n{uscita.stderr}", returncode=2)
    trovato = Path(uscita.stdout.strip().splitlines()[-1]).resolve()
    sito = Path(sysconfig.get_paths()["purelib"]).resolve()
    if sito not in trovato.parents:
        pytest.exit(f"verimem risolve in {trovato}, fuori dal site-packages {sito}: "
                    f"la prova misurerebbe l'albero, non il wheel", returncode=2)
    return trovato


class Utente:
    """Un utente nuovo: la sua cartella dati, il suo giornale, i suoi processi."""

    def __init__(self, radice: Path) -> None:
        self.radice = radice
        self.dati = radice / "dati"
        self.dati.mkdir(parents=True, exist_ok=True)
        #: l'ambiente di chi installa: niente variabili nostre ereditate dalla
        #: macchina che esegue (sono lo strumento di chi sviluppa, non dell'utente)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
        env.update({
            "HIPPO_DATA_DIR": str(self.dati), "ENGRAM_DATA_DIR": str(self.dati),
            "VERIMEM_DATA_DIR": str(self.dati),
            "ENGRAM_EVENT_LOG": str(radice / "eventi.jsonl"),
            "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
        })
        self.env = env

    def _esegui(self, argv: list[str], **extra_env: str) -> subprocess.CompletedProcess:
        env = {**self.env, **extra_env}
        return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", cwd=self.radice, env=env,
                              timeout=TETTO_S)

    def python(self, codice: str, **extra_env: str) -> subprocess.CompletedProcess:
        """Uno script Python dell'utente, in un processo suo."""
        return self._esegui([sys.executable, "-c", codice], **extra_env)

    def cli(self, *argomenti: str, **extra_env: str) -> subprocess.CompletedProcess:
        """Il comando `verimem` come lo scrive il README."""
        return self._esegui([_eseguibile("verimem"), *argomenti], **extra_env)

    @contextlib.contextmanager
    def mcp(self, **extra_env: str):
        """`verimem mcp` via stdio, configurato come il quickstart MCP del README."""
        env = {**self.env, "VERIMEM_HOSTED": "1", "VERIMEM_TOOL_NAMESPACE": "verimem",
               **extra_env}
        proc = subprocess.Popen([_eseguibile("verimem"), "mcp"], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, encoding="utf-8", errors="replace",
                                cwd=self.radice, env=env)
        sessione = SessioneMCP(proc)
        try:
            sessione.inizia()
            yield sessione
        finally:
            proc.kill()
            proc.wait(timeout=30)


class SessioneMCP:
    """Il minimo del protocollo MCP su stdio: initialize, tools/list, tools/call.

    Un filo legge lo stdout del server e mette ogni messaggio in una coda: cosi'
    ogni richiesta ha un tetto di tempo invece di una `readline` che puo' non
    tornare. Le richieste che il SERVER fa al client (il campionamento) ricevono
    un errore «non supportato»: il client del quickstart non campiona, e senza
    risposta il server aspetterebbe per sempre.
    """

    def __init__(self, proc: subprocess.Popen) -> None:
        import queue
        import threading
        self.proc = proc
        self._id = 0
        self._coda: queue.Queue = queue.Queue()

        def _leggi() -> None:
            for riga in proc.stdout:
                self._coda.put(riga)
            self._coda.put(None)

        threading.Thread(target=_leggi, daemon=True).start()

    def _scrivi(self, messaggio: dict) -> None:
        self.proc.stdin.write(json.dumps(messaggio) + "\n")
        self.proc.stdin.flush()

    def _richiesta(self, metodo: str, parametri: dict | None = None,
                   tetto_s: float = TETTO_S) -> dict:
        import queue
        import time
        self._id += 1
        mio = self._id
        self._scrivi({"jsonrpc": "2.0", "id": mio, "method": metodo,
                      "params": parametri or {}})
        scadenza = time.monotonic() + tetto_s
        while True:
            try:
                riga = self._coda.get(timeout=max(0.1, scadenza - time.monotonic()))
            except queue.Empty:
                raise TimeoutError(f"nessuna risposta a {metodo} in {tetto_s:.0f} s") from None
            if riga is None:
                raise RuntimeError(f"il server MCP ha chiuso prima di rispondere a {metodo}")
            msg = json.loads(riga)  # una riga non JSON su stdout e' gia' un difetto
            if msg.get("id") == mio and "method" not in msg:
                return msg
            if "method" in msg and "id" in msg:  # il server chiede qualcosa al client
                self._scrivi({"jsonrpc": "2.0", "id": msg["id"], "error": {
                    "code": -32601, "message": "il client di accettazione non campiona"}})

    def inizia(self) -> None:
        r = self._richiesta("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "accettazione", "version": "0"}})
        assert "result" in r, r
        self._scrivi({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def strumenti(self) -> list[dict]:
        return self._richiesta("tools/list")["result"]["tools"]

    def chiama(self, nome: str, argomenti: dict, tetto_s: float = TETTO_S) -> dict:
        """La risposta di uno strumento: il JSON del suo testo, o il testo grezzo."""
        r = self._richiesta("tools/call", {"name": nome, "arguments": argomenti},
                            tetto_s=tetto_s)
        if "error" in r:
            return {"errore_protocollo": r["error"]}
        blocchi = r["result"].get("content") or []
        testo = "".join(b.get("text", "") for b in blocchi if b.get("type") == "text")
        try:
            return json.loads(testo)
        except json.JSONDecodeError:
            return {"testo": testo, "isError": r["result"].get("isError")}


@pytest.fixture
def utente(tmp_path: Path) -> Utente:
    return Utente(tmp_path)


@pytest.fixture
def nuovo_utente(tmp_path: Path):
    """Piu' utenti nella stessa prova, ognuno col suo store (le tre porte)."""
    def _fabbrica(nome: str) -> Utente:
        return Utente(tmp_path / nome)
    return _fabbrica


def json_di(uscita: subprocess.CompletedProcess) -> dict:
    """Lo stdout di un comando `--json` DEVE essere un documento JSON e basta.

    Se una riga di giornale lo precede, una macchina che legge la ricevuta muore
    su `json.loads`: e' un difetto dal lato dell'utente, non un dettaglio.
    """
    try:
        return json.loads(uscita.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"lo stdout di un comando --json non e' JSON ({exc}); inizio: "
            f"{uscita.stdout[:300]!r}; stderr: {uscita.stderr[-300:]!r}") from exc
