"""Il cricchetto dei moduli senza porta deve mordere (regola R2).

Come per `copie.py`: due esecuzioni, non una. Il pacchetto com'è deve uscire 0,
il pacchetto con un modulo in più che nessuno importa deve uscire 1.

I due casi in fondo non sono decorazione: hanno trovato due difetti veri in
questo righello il 09/09 — gli `__init__.py` di sottopacchetto contati con un
nome che il grafo non collegava, e il livello degli import relativi dentro un
`__init__` (che punta al pacchetto stesso, non al genitore). Senza di loro il
righello dichiarava senza chiamante nove moduli di `dashboard_routes/` che
`dashboard.py:35` importa.

    python -m pytest tests/test_senza_chiamante_cricchetto.py -q
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

RADICE = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("senza_chiamante", RADICE / "scripts" / "senza_chiamante.py")
sc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sc)


@pytest.fixture(scope="module")
def misura_di_oggi():
    return sc.analizza(sc.PACCHETTO)


def test_ogni_file_e_stato_letto(misura_di_oggi):
    """Un file non letto perde i suoi import: il numero diventerebbe un massimo."""
    assert misura_di_oggi["non_letti"] == []
    assert misura_di_oggi["moduli"] > 300


def test_i_tetti_non_salgono(misura_di_oggi):
    saliti = {}
    for chiave, tetto in (("C2_nessuna_porta", sc.TETTO_C2),
                          ("C1_solo_python_m", sc.TETTO_C1),
                          ("D_irraggiungibili", sc.TETTO_D)):
        quanti = len(misura_di_oggi[chiave])
        if quanti > tetto:
            saliti[chiave] = (quanti, tetto, misura_di_oggi[chiave])
    assert not saliti, (
        "un modulo è stato pubblicato senza una porta che lo raggiunga. "
        "Cablalo a una porta o tienilo fuori dal pacchetto; se deve restare così, "
        "alza il tetto in scripts/senza_chiamante.py, col motivo."
    )


def test_il_cricchetto_diventa_rosso_su_un_modulo_senza_porta():
    """IL CONTROLLO POSITIVO."""
    con_finto = sc.analizza(sc.PACCHETTO, modulo_finto="modulo_finto_senza_porta")
    assert "modulo_finto_senza_porta" in con_finto["C2_nessuna_porta"]
    assert sc.stampa(con_finto, dettaglio=False) == 1


def test_un_pacchetto_importato_non_e_senza_chiamante(misura_di_oggi):
    """`dashboard.py:35` fa `from .dashboard_routes import auth`: il pacchetto
    `dashboard_routes` HA un chiamante, e il grafo deve vederlo anche se il file
    sul disco si chiama `dashboard_routes/__init__.py`."""
    assert "dashboard_routes" not in misura_di_oggi["C2_nessuna_porta"]
    assert misura_di_oggi["importatori"].get("dashboard_routes"), (
        "nessun importatore per dashboard_routes: il grafo sta perdendo gli __init__"
    )


def test_un_import_relativo_dentro_un_init_punta_al_pacchetto_stesso(tmp_path):
    """In `pkg/__init__.py`, `from .modulo import x` importa `pkg.modulo`.
    Se il righello lo leggesse come `modulo` (senza il prefisso), ogni modulo di
    un sottopacchetto risulterebbe senza chiamante."""
    pkg = tmp_path / "finto"
    (pkg / "sotto").mkdir(parents=True)
    (pkg / "__init__.py").write_text("from .sotto import x\n", encoding="utf-8")
    (pkg / "sotto" / "__init__.py").write_text("from .foglia import x\n", encoding="utf-8")
    (pkg / "sotto" / "foglia.py").write_text("x = 1\n", encoding="utf-8")
    risultato = sc.analizza(pkg, pyproject=tmp_path / "non_esiste.toml")
    assert risultato["C2_nessuna_porta"] == [], risultato["C2_nessuna_porta"]
    assert risultato["D_irraggiungibili"] == [], risultato["D_irraggiungibili"]


def test_la_raggiungibilita_e_transitiva(tmp_path):
    """Un modulo importato SOLO da un modulo senza porta resta irraggiungibile:
    è il caso di `resonator_memory`, che ha due importatori e zero porte."""
    pkg = tmp_path / "finto"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "orfano.py").write_text("from .foglia import y\n", encoding="utf-8")
    (pkg / "foglia.py").write_text("y = 1\n", encoding="utf-8")
    risultato = sc.analizza(pkg, pyproject=tmp_path / "non_esiste.toml")
    assert risultato["C2_nessuna_porta"] == ["orfano"], risultato["C2_nessuna_porta"]
    assert risultato["importatori"].get("foglia") == {"orfano"}
    assert sorted(risultato["D_irraggiungibili"]) == ["foglia", "orfano"], (
        "foglia ha un importatore ma la catena non arriva a nessuna porta: "
        "deve risultare irraggiungibile"
    )
