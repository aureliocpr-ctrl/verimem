"""T91 — la porta dichiara in quale store ha scritto, e quale variabile l'ha deciso.

L'incidente (14/09): tre variabili puntate a uno store di prova, e la scrittura
finita nello store VERO. Il meccanismo, misurato il 16/09: ``HIPPO_DATA_DIR`` e'
gia' posta sullo store vero in ogni shell e VINCE per precedenza
(``_compat.py:168``); chi isola con ``ENGRAM_DATA_DIR`` non isola niente, e
l'unico segnale e' un ``RuntimeWarning`` che di default si stampa una volta per
posizione — quindi nella pratica non lo vede nessuno.

⚠️ Il primo test e' il CONTROLLO POSITIVO e oggi DEVE essere verde: se la deriva
non si riproduce, gli altri due non provano niente e il banco e' rotto.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from verimem._compat import _ALIAS_DATA_DIR as _ALIAS
from verimem.cli import app

runner = CliRunner()


def _due_store(tmp_path: Path, monkeypatch):
    """L'ambiente dell'incidente: HIPPO gia' posta, ENGRAM posta dall'utente."""
    vero = tmp_path / "quello-vero"
    creduto = tmp_path / "quello-che-credo-di-usare"
    for d in (vero, creduto):
        (d / "semantic").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HIPPO_DATA_DIR", str(vero))      # gia' nell'ambiente
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(creduto))  # posta per isolare
    monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
    from verimem import _compat
    monkeypatch.setattr(_compat, "_avvisato_alias_discordi", False, raising=False)
    return vero, creduto


def _fatti(store: Path) -> int:
    db = store / "semantic" / "semantic.db"
    if not db.is_file():
        return 0
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    except sqlite3.DatabaseError:
        return 0
    finally:
        con.close()


def _testo_del_check(referto: str, nome: str) -> str:
    """Il testo del check `nome`, e SOLO quello.

    ⚠️ Cercare il nome di una variabile nel referto INTERO non prova niente: il
    referto contiene un dump dell'ambiente che elenca ``HIPPO_DATA_DIR`` e
    ``ENGRAM_DATA_DIR`` (troncati) e un consiglio che nomina ``HIPPO_DATA_DIR``.
    Scritto largo, questo test passava senza che `data-dir` dichiarasse nulla.
    """
    righe: list[str] = []
    dentro = False
    for riga in referto.splitlines():
        nudo = riga.strip("│| ").rstrip("│| ")
        if nudo[:1] in {"✓", "✗", "!", "⚠"}:
            dentro = nome in nudo
        if dentro and nudo:
            righe.append(nudo)
    return "\n".join(righe)


def test_il_banco_riproduce_la_deriva(tmp_path: Path, monkeypatch) -> None:
    """CONTROLLO POSITIVO: la variabile posta per isolare NON decide lo store."""
    vero, creduto = _due_store(tmp_path, monkeypatch)
    from verimem import _compat

    scelto = _compat.data_dir()

    assert scelto == vero, (
        "il banco non riproduce l'incidente: ha vinto la variabile che l'utente "
        f"ha posto per isolare ({creduto}), quindi non c'e' niente da dichiarare"
    )


def test_la_ricevuta_di_una_scrittura_nomina_lo_store(tmp_path: Path, monkeypatch) -> None:
    """La ricevuta deve dire DOVE ha scritto: e' l'unico momento in cui l'utente
    puo' accorgersi che lo store non e' quello che credeva."""
    vero, creduto = _due_store(tmp_path, monkeypatch)
    prima_vero, prima_creduto = _fatti(vero), _fatti(creduto)

    r = runner.invoke(app, [
        "facts", "add",
        "--proposition", "La soglia di ammissione vale 19.0s.",
        "--topic", "prova/t91",
    ])
    assert r.exit_code == 0, r.output

    # Il conteggio sqlite prima/dopo: la deriva e' avvenuta davvero.
    assert _fatti(vero) == prima_vero + 1, r.output
    assert _fatti(creduto) == prima_creduto, "la scrittura non e' derivata: banco rotto"

    # ⇒ E la ricevuta deve dirlo. Oggi non nomina nessuno dei due percorsi.
    assert str(vero) in r.output, (
        "la ricevuta non nomina lo store in cui ha scritto: l'utente crede di "
        f"aver scritto in {creduto} e non ha modo di accorgersene.\n{r.output}"
    )


def test_la_ricevuta_della_libreria_nomina_lo_store(tmp_path: Path, monkeypatch) -> None:
    """La terza porta: il dict che torna da `Memory.add` — ed e' lo stesso che
    la porta MCP restituisce al chiamante, che non vede nessuna console."""
    vero, creduto = _due_store(tmp_path, monkeypatch)
    from verimem import Memory

    mem = Memory(path=str(vero / "semantic" / "semantic.db"))
    ricevuta = mem.add("La soglia di ammissione vale 12.0s.", topic="prova/t91")

    assert ricevuta.get("stored") is True, ricevuta
    assert str(vero) in str(ricevuta.get("store", "")), (
        "la ricevuta della libreria non dice in quale store ha scritto: alla "
        f"porta MCP non c'e' nemmeno una console da leggere.\n{ricevuta}")
    assert ricevuta.get("store_decided_by") == "HIPPO_DATA_DIR", (
        "la ricevuta non dice quale variabile ha deciso lo store.\n"
        f"{ricevuta}")


def test_la_ricevuta_della_porta_mcp_nomina_lo_store(tmp_path: Path, monkeypatch) -> None:
    """La terza porta DAVVERO: il gestore MCP, chiamato in-process.

    ⚠️ «È lo stesso dict della libreria» era una mia affermazione, non una
    misura, ed era falsa: `mcp_server.py` ricostruisce la ricevuta campo per
    campo — il commento accanto lo dichiara («questa lista di campi è
    ESPLICITA, quindi un campo aggiunto in `client.py` non arriverebbe mai su
    questa porta»). Un pari ha contato 17 chiavi qui contro 10 alla libreria.
    """
    import asyncio
    import json

    vero, creduto = _due_store(tmp_path, monkeypatch)
    monkeypatch.setenv("HIPPO_HOSTED", "0")
    import verimem.mcp_server as server

    risposta = asyncio.run(server._call_tool_impl("hippo_remember", {  # noqa: SLF001
        "proposition": "La soglia di ammissione vale 7.0s.",
        "topic": "prova/t91",
    }))
    ricevuta = json.loads(risposta[0].text)

    assert ricevuta.get("ok") is True, ricevuta
    assert ricevuta.get("store"), (
        "la ricevuta della porta MCP non dice in quale store ha scritto, ed è "
        f"l'unica porta senza una console da leggere.\n{ricevuta}")
    assert "store_decided_by" in ricevuta, ricevuta

    # ⚠️ NON si pretende che sia `vero`: il server apre lo store alla
    # costruzione e se lo tiene, quindi l'ambiente posto qui può non averlo
    # deciso. Si pretende che le due metà della dichiarazione parlino DELLO
    # STESSO store — che è il contratto: chi ha deciso QUESTO percorso.
    chi = ricevuta["store_decided_by"]
    percorso = Path(ricevuta["store"]).resolve()
    if chi == "default":
        assert all(
            Path(v).resolve() not in percorso.parents
            for v in (os.environ.get(n, "") for n in _ALIAS)
            if v
        ), f"dice `default` ma una variabile punta proprio lì: {ricevuta}"
    else:
        radice = Path(os.environ[chi]).resolve()
        assert radice == percorso or radice in percorso.parents, (
            f"la ricevuta dichiara `{chi}` accanto a un percorso che quella "
            f"variabile non ha deciso: {os.environ[chi]} vs {percorso}")


def test_una_ricevuta_non_fa_cadere_una_scrittura_riuscita() -> None:
    """Se il percorso non è noto, la ricevuta lo DICE — non solleva.

    ⚠️ Questa cella nasce da un rosso vero: `str(a.semantic.db_path)` alla porta
    MCP ha fatto cadere 15 celle in CI con `AttributeError: '_FakeSemantic'
    object has no attribute 'db_path'`, riprodotto in locale `10 failed`. Ed è
    la SECONDA volta con lo stesso doppio di test: il 13/09 non aveva `get`.
    Il campo di una ricevuta descrive una scrittura già avvenuta: se non sa,
    dice `unknown`, e `unknown` non è `default` — «non lo so» non è «l'ha
    deciso il disco»."""
    from verimem._compat import provenienza_data_dir

    prov = provenienza_data_dir()

    assert prov.deciso_da_per("") == "unknown"
    assert prov.deciso_da_per(None) == "unknown"  # type: ignore[arg-type]


def test_senza_variabili_la_ricevuta_dice_default(tmp_path: Path, monkeypatch) -> None:
    """Nessuna variabile posta: il campo c'è lo stesso e vale `default`.

    Un'assenza non è una dichiarazione: chi legge non distingue «l'ha deciso il
    disco» da «questa porta non lo dice» né da «sto leggendo una versione
    vecchia del prodotto»."""
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.delenv(nome, raising=False)
    from verimem import Memory
    from verimem._compat import ProvenienzaDataDir

    db = tmp_path / "solo-disco" / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    ricevuta = Memory(path=str(db)).add("La soglia di ammissione vale 3.0s.",
                                        topic="prova/t91")

    assert ricevuta.get("store_decided_by") == ProvenienzaDataDir.DISCO, ricevuta


def test_doctor_dice_quale_variabile_ha_deciso_lo_store(tmp_path: Path, monkeypatch) -> None:
    """`doctor` mostra gia' la dir che vince; deve dire anche CHI l'ha decisa e
    quale alias ha ignorato — altrimenti la diagnosi non distingue «isolato» da
    «sembrava isolato»."""
    vero, creduto = _due_store(tmp_path, monkeypatch)

    referto = runner.invoke(app, ["doctor"]).output
    check = _testo_del_check(referto, "data-dir")

    assert check, "il referto non ha un check `data-dir`:\n" + referto
    assert "HIPPO_DATA_DIR" in check, (
        "il check `data-dir` non nomina la variabile che ha deciso lo store: "
        "mostra un percorso e lascia credere che sia quello richiesto.\n" + check)
    assert "ENGRAM_DATA_DIR" in check, (
        "il check `data-dir` non dice quale alias discorde ha ignorato.\n" + check)
