"""Il tetto ai thread di calcolo esiste, vale per tutte le strade, e non
sovrascrive chi ha scelto il proprio numero.

IL DIFETTO CHE CURA, misurato il 20/08: nessun punto del prodotto impostava un
tetto ai thread di torch. Su una macchina a 20 core ne sceglie 10 per processo,
e verimem ne fa girare undici — nove server MCP piu' due daemon.

E non era un compromesso memoria-contro-velocita'. A/B a una variabile::

    torch   thread   impegnato  residente   batch1   batch32   batch256
     10       35       1522MB      502MB    0,11ms    4,23ms     4,26ms
      4       13        997MB      492MB    0,10ms    0,55ms     3,66ms

A dieci thread si perde su ENTRAMBI gli assi: 525 MB di prenotazione in piu' e
un batch da 32 otto volte piu' lento, per contesa.

⚠️ IL TEST CHE CONTA E' L'ULTIMO. Gli altri collaudano la funzione; l'ultimo
collauda che qualcuno la CHIAMI. Una regola giusta che nessuno invoca e' la
forma piu' silenziosa di codice morto — e in questo repo e' gia' successo: una
colonna di provenienza scritta in un solo punto su cinque porte, curata cinque
volte in un giorno.
"""
from __future__ import annotations

import os

import pytest

from verimem._thread_budget import (
    _VARIABILI,
    TETTO_PREDEFINITO,
    applica_tetto_thread,
    tetto_richiesto,
)

_TUTTE = (*_VARIABILI, "VERIMEM_TORCH_THREADS", "ENGRAM_TORCH_THREADS",
          "HIPPO_TORCH_THREADS")


@pytest.fixture()
def ambiente_pulito(monkeypatch: pytest.MonkeyPatch):
    for nome in _TUTTE:
        monkeypatch.delenv(nome, raising=False)
    return monkeypatch


def test_il_tetto_viene_messo_dove_manca(ambiente_pulito):
    messe = applica_tetto_thread()
    assert set(messe) == set(_VARIABILI), messe
    for nome in _VARIABILI:
        assert os.environ[nome] == str(TETTO_PREDEFINITO), nome


def test_NON_sovrascrive_chi_ha_gia_scelto(ambiente_pulito):
    """⚖️ Chi ha messo il proprio numero lo tiene: e' la stessa disciplina di
    `_compat.init_env_aliases` e di `mode.apply_engram_mode`. Un tetto che
    scavalca la scelta dell'utente e' peggio di nessun tetto, perche' e'
    invisibile e cambia i suoi tempi senza dirlo."""
    ambiente_pulito.setenv("OMP_NUM_THREADS", "16")
    messe = applica_tetto_thread()
    assert os.environ["OMP_NUM_THREADS"] == "16", "ha scavalcato la scelta"
    assert "OMP_NUM_THREADS" not in messe
    assert os.environ["MKL_NUM_THREADS"] == str(TETTO_PREDEFINITO)


def test_lo_ZERO_disattiva_il_tetto(ambiente_pulito):
    """Chi fa lotti grandi e ha MISURATO di volere piu' thread deve poterlo
    dire senza toccare il codice."""
    ambiente_pulito.setenv("VERIMEM_TORCH_THREADS", "0")
    assert tetto_richiesto() == 0
    assert applica_tetto_thread() == {}
    assert os.environ.get("OMP_NUM_THREADS") is None


def test_un_numero_esplicito_vince_sul_predefinito(ambiente_pulito):
    ambiente_pulito.setenv("ENGRAM_TORCH_THREADS", "6")
    assert tetto_richiesto() == 6
    applica_tetto_thread()
    assert os.environ["OMP_NUM_THREADS"] == "6"


def test_un_valore_MALFORMATO_non_rompe_l_import(ambiente_pulito):
    """Un numero illeggibile non deve impedire a `import verimem` di
    riuscire: si ricade sul predefinito invece di sollevare."""
    ambiente_pulito.setenv("VERIMEM_TORCH_THREADS", "molti")
    assert tetto_richiesto() == TETTO_PREDEFINITO


def test_IMPORTARE_IL_PACCHETTO_LO_APPLICA_DAVVERO():
    """⚠️⚠️ LA META' CHE CONTA: i test sopra collaudano la funzione, questo
    collauda che qualcuno la CHIAMI.

    Sottoprocesso e non `importlib.reload`, perche' nel processo del banco
    `verimem` e' gia' importato e l'ambiente e' gia' stato toccato: rileggerlo
    qui misurerebbe lo stato del banco, non l'effetto dell'import.
    """
    import subprocess
    import sys

    codice = (
        "import os\n"
        "for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ.pop(k, None)\n"
        "import verimem\n"
        "print(os.environ.get('OMP_NUM_THREADS'), os.environ.get('MKL_NUM_THREADS'))\n"
    )
    r = subprocess.run([sys.executable, "-c", codice], capture_output=True,
                       encoding="utf-8", errors="replace", timeout=300)
    assert r.returncode == 0, f"rc={r.returncode} {r.stderr[-400:]}"
    letto = (r.stdout or "").split()
    assert letto == [str(TETTO_PREDEFINITO), str(TETTO_PREDEFINITO)], (
        f"`import verimem` non applica il tetto: ha stampato {letto!r}. "
        f"La funzione esiste e nessuno la chiama.")
