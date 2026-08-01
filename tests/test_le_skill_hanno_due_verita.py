"""La libreria delle skill vive in DUE store che non concordano.

TROVATO il 2026-07-30 verificando un finding del dogfooding in parallelo, che
segnalava conteggi contraddittori fra superfici e — correttamente — dichiarava
il proprio caveat: le sue due letture non erano contemporanee. Rifatte
contemporanee, la discrepanza resta, e la causa non e' quella che sembrava.

    skills/skills_index.db : 326 righe — promoted 8, candidate 162, retired 156
    file *.json su disco   : 325 file  — promoted 6, candidate   4, retired 315

    nel DB e non su disco : 2  ('fresh', 'stale' — fixture di test)
    su disco e non nel DB : 1
    STESSO id, STATUS DIVERSO: 159 su 325

Centocinquantanove skill su trecentoventicinque: quasi la meta' della libreria
ha due stati. ``SkillLibrary._load_all_skills`` legge i FILE
(``self.dir.glob("*.json")``), quindi tutto cio' che passa da ``all()`` /
``count()`` — ``verimem status`` compreso — vede la verita' dei file; chi
interroga l'indice ne vede un'altra. Non e' una cache stantia: e' una scrittura
andata a buon fine su un solo lato.

QUESTO FILE NON CURA NIENTE, e non deve: quale dei due store sia canonico e'
una decisione (i file sono il dato, l'indice e' quello che il prodotto
interroga), e riconciliarli significa decidere il destino di 159 record —
promuovere o ritirare — che nessun test puo' scegliere al posto di chi possiede
il prodotto.

Il test misura la divergenza e FALLISCE SE PEGGIORA. Cosi' il difetto non
cresce in silenzio mentre la decisione matura, e il giorno in cui i due store
verranno riconciliati questo file lo dira' — chiedendo di abbassare il numero,
come il cricchetto dei moduli irraggiungibili.
"""
from __future__ import annotations

import collections
import json
import sqlite3

import pytest

#: Misurato il 2026-07-30 sullo store vivo. Puo' solo SCENDERE.
DIVERGENZE_NOTE = 159


def _due_store():
    """Lo store VERO, non quello che il conftest isola su tmp_path.

    Prima passava da ``_compat.data_dir()`` e faceva SEMPRE skip: la fixture
    autouse del conftest ridefinisce la data dir, quindi il test non trovava
    nulla e passava per «3 skipped» — un presidio che sembra proteggere e non
    protegge. Esattamente il difetto che questo file documenta, commesso qui.

    Questo non e' un test unitario, e' un monitor sul dato reale: punta al
    percorso vero e fa skip solo dove quel dato non esiste (CI, installazione
    pulita). Il fallimento che deve produrre e' sulla macchina che ha lo store.
    """
    from pathlib import Path
    for radice in (Path.home() / ".verimem", Path.home() / ".engram",
                   Path.home() / ".hippoagent"):
        d = radice / "skills"
        if (d / "skills_index.db").exists() and any(d.glob("*.json")):
            break
    else:
        pytest.skip("store delle skill assente (CI, o installazione pulita)")
    indice = d / "skills_index.db"

    su_disco: dict[str, str] = {}
    for p in d.glob("*.json"):
        try:
            o = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un file illeggibile e' un dato, non un errore
            continue
        if o.get("id"):
            su_disco[o["id"]] = o.get("status")

    with sqlite3.connect(f"file:{indice}?mode=ro", uri=True) as c:
        nel_db = {r[0]: r[1] for r in c.execute("SELECT id, status FROM skills")}
    return su_disco, nel_db


def test_i_due_store_non_divergono_di_piu_di_prima():
    su_disco, nel_db = _due_store()
    comuni = set(su_disco) & set(nel_db)
    diverse = [i for i in comuni if su_disco[i] != nel_db[i]]
    assert len(diverse) <= DIVERGENZE_NOTE, (
        f"{len(diverse)} skill hanno due stati diversi nei due store, erano "
        f"{DIVERGENZE_NOTE}. Un ritiro o una promozione sta atterrando su un "
        f"lato solo:\n  "
        + "\n  ".join(f"{i}: db={nel_db[i]} disco={su_disco[i]}"
                      for i in diverse[:8]))


def test_se_sono_stati_riconciliati_il_numero_va_abbassato():
    """Un cricchetto che resta largo dopo la bonifica smette di presidiare."""
    su_disco, nel_db = _due_store()
    comuni = set(su_disco) & set(nel_db)
    n = len([i for i in comuni if su_disco[i] != nel_db[i]])
    assert n >= DIVERGENZE_NOTE - 20, (
        f"le divergenze sono scese a {n} (note {DIVERGENZE_NOTE}): abbassa "
        f"DIVERGENZE_NOTE, altrimenti la prossima scrittura a un lato solo "
        f"passa senza far rumore")


def test_le_fixture_di_test_stanno_nell_indice_dello_store_vero():
    """`fresh` e `stale` sono id letterali da fixture: stanno nell'indice di
    produzione e non fra i file. Non e' un dettaglio estetico — sono due degli
    otto `promoted` che l'indice dichiara, quindi contano nelle statistiche
    che descrivono «cosa il sistema ha imparato»."""
    su_disco, nel_db = _due_store()
    intrusi = {i for i in ("fresh", "stale") if i in nel_db and i not in su_disco}
    if not intrusi:
        pytest.skip("gia' bonificate")
    stati = collections.Counter(nel_db[i] for i in intrusi)
    assert intrusi, f"fixture nell'indice di produzione: {dict(stati)}"
