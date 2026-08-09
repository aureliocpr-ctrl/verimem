"""Il giornale degli eventi scriveva nella home anche con lo store isolato.

IL DIFETTO, e ha inquinato le misure di tutte per un giorno intero::

    quarantene registrate in events.jsonl  1765
    con il fatto ancora nel database        108   (6%)
    L3            301 eventi ->   0 vivi
    tutti i L1.x  724 eventi ->   0 vivi

**Il 94% del giornale racconta store che non esistono più**: i `tmp` dei nostri
banchi. Con quei numeri il team si è dato per un giorno tabelle su «chi
quarantina davvero», e misuravano i nostri esperimenti credendo di misurare il
prodotto.

🔑 LA CAUSA, trovata da ws1 (io avevo proposto una cura più superficiale — un
campo `db` nel payload — che avrebbe reso il problema *leggibile* invece di
*risolverlo*): ``EVENT_LOG_PATH`` si risolve su ``Path.home()`` e **ignora
``HIPPO_DATA_DIR``**. Tutto il resto del prodotto lo rispetta — c'è UN solo
risolutore in ``config.py``, condiviso con ``_compat.data_dir``, con precedenza
``HIPPO_DATA_DIR`` → ``ENGRAM_DATA_DIR`` → default. Il giornale è l'unica
superficie che non ci passa.

⚠️ E il dato era in casa da due giorni: ws6 l'aveva registrato in memoria, e né
io né ws1 l'avevamo collegato al 94%. **Il fatto c'era, mancava il
collegamento** — la stessa forma del difetto che curiamo nel prodotto.

📌 IN PRODUZIONE NON CAMBIA NIENTE: ``HIPPO_DATA_DIR`` vale ``~/.engram``, quindi
il percorso resta ``~/.engram/events.jsonl`` byte per byte. Cambia solo per chi
isola lo store — cioè per noi, che è esattamente chi inquinava il giornale.
"""
from __future__ import annotations

import json
import subprocess
import sys

_PROGRAMMA = (
    "import sys; sys.path.insert(0, r'{repo}')\n"
    "from verimem.event_jsonl_log import EVENT_LOG_PATH\n"
    "print(str(EVENT_LOG_PATH))\n"
)
_REPO = r"C:\Users\aurel\Code\HippoAgent"


def _percorso_con(env_extra: dict, tmp_path) -> str:
    """Il path del giornale come lo vede un processo NUOVO.

    Subprocess e non import diretto perché ``EVENT_LOG_PATH`` si risolve a
    import-time: è così che lo vede ogni banco reale, che imposta
    ``HIPPO_DATA_DIR`` prima di importare.
    """
    import os
    env = dict(os.environ)
    env.pop("ENGRAM_EVENT_LOG", None)
    env.update(env_extra)
    out = subprocess.run(
        [sys.executable, "-c", _PROGRAMMA.format(repo=_REPO)],
        capture_output=True, text=True, env=env, cwd=_REPO, timeout=120)
    assert out.returncode == 0, out.stderr[-400:]
    return out.stdout.strip().splitlines()[-1]


def test_uno_store_ISOLATO_ha_il_suo_giornale(tmp_path):
    """IL CUORE: un banco che isola i dati non deve scrivere nel giornale di
    produzione. È ciò che ha reso il 94% del journal inutilizzabile."""
    altrove = tmp_path / "store_isolato"
    p = _percorso_con({"HIPPO_DATA_DIR": str(altrove),
                       "ENGRAM_DATA_DIR": str(altrove)}, tmp_path)
    assert str(altrove) in p, (
        f"con HIPPO_DATA_DIR={altrove} il giornale finisce in {p} — "
        f"cioè nel giornale di produzione")


def test_CONTROLLO_POSITIVO_il_giornale_STA_DOVE_STANNO_I_DATI(tmp_path):
    """⚠️ IL PRESIDIO CHE PROTEGGE LA PRODUZIONE, ed è l'INVARIANTE, non un
    path fisso: il giornale deve stare nella stessa cartella in cui il prodotto
    tiene i suoi dati. Se questo vale, in produzione il percorso resta
    ``~/.engram/events.jsonl`` byte per byte, e la dashboard che lo segue non si
    accorge di niente.

    ⚠️ La prima stesura fissava il path assoluto della home e cadeva — non per
    la cura, ma perché **sotto pytest il conftest imposta già una data dir di
    test**: «nessuna configurazione» non esiste in un banco. Fissare
    l'invariante invece del valore è più forte e non dipende dall'ambiente in
    cui gira il test.
    """
    import os
    import pathlib
    prog = (
        f"import sys; sys.path.insert(0, r'{_REPO}')\n"
        "from verimem.event_jsonl_log import EVENT_LOG_PATH\n"
        "from verimem.config import CONFIG\n"
        "print(str(EVENT_LOG_PATH)); print(str(CONFIG.data_dir))\n"
    )
    env = dict(os.environ)
    env.pop("ENGRAM_EVENT_LOG", None)
    out = subprocess.run([sys.executable, "-c", prog], capture_output=True,
                         text=True, env=env, cwd=_REPO, timeout=120)
    assert out.returncode == 0, out.stderr[-400:]
    righe = out.stdout.strip().splitlines()
    giornale, dati = pathlib.Path(righe[-2]), pathlib.Path(righe[-1])
    assert giornale.parent == dati, (
        f"il giornale ({giornale.parent}) non sta con i dati ({dati})")
    assert giornale.name == "events.jsonl"


def test_l_override_esplicito_continua_a_VINCERE(tmp_path):
    """``ENGRAM_EVENT_LOG`` è documentato come override per testing/sandboxing:
    una scelta esplicita del chiamante deve battere la data dir, altrimenti la
    cura toglie una capacità dichiarata mentre ne aggiunge un'altra."""
    esplicito = tmp_path / "scelto_a_mano.jsonl"
    p = _percorso_con({"ENGRAM_EVENT_LOG": str(esplicito),
                       "HIPPO_DATA_DIR": str(tmp_path / "ignorata")}, tmp_path)
    assert p == str(esplicito)


def test_e_il_giornale_isolato_RICEVE_davvero_gli_eventi(tmp_path):
    """Non basta che il percorso cambi: gli eventi devono arrivarci. Senza
    questo, il test sopra sarebbe soddisfatto anche da un path calcolato bene e
    mai usato."""
    import os
    altrove = tmp_path / "store2"
    env = dict(os.environ)
    env.pop("ENGRAM_EVENT_LOG", None)
    env.update({"HIPPO_DATA_DIR": str(altrove), "ENGRAM_DATA_DIR": str(altrove)})
    prog = (
        f"import sys; sys.path.insert(0, r'{_REPO}')\n"
        "from verimem.event_jsonl_log import append_event, EVENT_LOG_PATH\n"
        "append_event('prova.isolamento', {'valore': 42})\n"
        "print(str(EVENT_LOG_PATH))\n"
    )
    out = subprocess.run([sys.executable, "-c", prog], capture_output=True,
                         text=True, env=env, cwd=_REPO, timeout=120)
    assert out.returncode == 0, out.stderr[-400:]
    import pathlib
    scritto = pathlib.Path(out.stdout.strip().splitlines()[-1])
    assert str(altrove) in str(scritto)
    assert scritto.exists(), "il giornale isolato non è stato creato"
    righe = [json.loads(r) for r in scritto.read_text(encoding="utf-8").splitlines() if r.strip()]
    assert any(r.get("name") == "prova.isolamento" for r in righe), righe[-3:]
