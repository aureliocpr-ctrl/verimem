"""«Pure-local» era scritto nella descrizione di un tool e non lo provava nessuno.

LA PROMESSA, dalla descrizione di `hippo_dashboard_overview_v2`: *«Unified
dashboard: ONE call returns health metrics + orphan suggestions + per-project
freshness signals. Drops 3-5 separate MCP calls to ~250ms total. **Pure-local.**»*

SWEEP DELLA COPERTURA, fatto PRIMA di scrivere:

    tests/test_dashboard_overview.py     presidiano il CONTENUTO (sezioni,
    tests/test_dashboard_overview_v2.py  health, orphan, topology)
    tests/test_airgap_no_egress.py       prova il NO-EGRESS, ma dell'EMBEDDING:
                                         un solo test, e non nomina nessun
                                         tool `hippo_*`

⇒ Nessun test verifica che una chiamata alla PORTA MCP non apra connessioni.
«Pure-local» era un'affermazione senza presidio.

📌 PERCHE' UN FILE NUOVO E NON ACCANTO AL FRATELLO. `test_airgap_no_egress.py`
ha `pytestmark = requires_real_model` a livello di MODULO: un test aggiunto li'
verrebbe saltato dove il modello non e' in cache — e un test che si salta e' un
sensore scollegato, non una copertura. Questo test non ha bisogno del modello
reale, quindi non deve ereditarne il gate. ⚠️ Il costo, dichiarato: la prova
anti-egress vive ora in due file, e chi ne cambia il criterio deve toccarli
entrambi — per questo il criterio qui sotto e' COPIATO da li' con una nota,
invece di essere reinventato peggio.

⚖️ COSA QUESTO TEST NON PROVA: che il tool sia veloce (l'altra affermazione,
«~250ms», e' misurata nel banco e NON presidiata qui: un assert sui
millisecondi in CI fallisce per la macchina, non per il prodotto — sarebbe un
rosso che non riproduce nulla). E non prova che NESSUN tool apra connessioni:
prova questi.

Banco: ``docs/stato-reale/banchi/ws3-un-numero-senza-il-corpus-su-cui-vale.py``
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

# Gli host che contano come LOCALI. ⚠️ Copiato da
# `tests/test_airgap_no_egress.py`: il daemon di encoding vive su localhost, e
# una connessione a 127.0.0.1 NON e' egress. Se quel criterio cambia li', va
# cambiato anche qui — due copie divergono, ed e' il prezzo dichiarato sopra.
_TOOL_PROVATI = ("hippo_dashboard_overview_v2", "hippo_health", "hippo_stats")


def test_i_tool_locali_non_aprono_connessioni_verso_l_esterno() -> None:
    script = textwrap.dedent(
        """
        import asyncio, json, os, socket, tempfile
        os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
        os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
        for f in ("HIPPO_OFFLINE", "ENGRAM_OFFLINE", "HF_HUB_OFFLINE",
                  "TRANSFORMERS_OFFLINE"):
            os.environ[f] = "1"

        _LOCAL = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}
        fuori = []

        def _host(addr):
            return str(addr[0]) if isinstance(addr, tuple) and addr else str(addr)

        _real_connect = socket.socket.connect
        _real_create = socket.create_connection

        def _rec_connect(self, address, *a, **k):
            h = _host(address)
            if h.strip().lower() not in _LOCAL:
                fuori.append(h)
            return _real_connect(self, address, *a, **k)

        def _rec_create(address, *a, **k):
            h = _host(address)
            if h.strip().lower() not in _LOCAL:
                fuori.append(h)
            return _real_create(address, *a, **k)

        socket.socket.connect = _rec_connect
        socket.create_connection = _rec_create

        from verimem import mcp_server

        riusciti = []
        for nome in %(tool)r:
            try:
                out = asyncio.run(mcp_server._call_tool_impl(nome, {}))
                d = json.loads(out[0].text)
                if isinstance(d, dict) and not d.get("error"):
                    riusciti.append(nome)
            except Exception as e:
                print("ECCEZIONE " + nome + " " + type(e).__name__)

        # UNA riga sola con tutto: se il processo muore prima, manca l'intera
        # riga e il test dice «non e' arrivato in fondo», non «air-gap
        # violato». Il commento del file fratello segnala proprio lo scambio
        # opposto come il piu' costoso di quel banco.
        print("ESITO=" + json.dumps({"riusciti": riusciti, "fuori": fuori}))
        """
    ) % {"tool": list(_TOOL_PROVATI)}

    out = subprocess.run([sys.executable, "-c", script],
                         capture_output=True, text=True, timeout=300)

    riga = [r for r in out.stdout.splitlines() if r.startswith("ESITO=")]
    assert riga, (
        "il processo non e' arrivato in fondo: nessun esito da leggere, quindi "
        "questo test NON dice niente sull'air-gap.\n"
        f"exit={out.returncode}\nstdout={out.stdout[-600:]}\n"
        f"stderr={out.stderr[-800:]}")
    esito = __import__("json").loads(riga[-1][len("ESITO="):])

    # IL CONTROLLO CHE DEVE POTER FALLIRE: se nessuna chiamata riesce, zero
    # connessioni e' un risultato VUOTO — non una prova di localita'.
    assert esito["riusciti"], (
        "nessuno dei tool ha risposto: zero connessioni non prova nulla.\n"
        f"stdout={out.stdout[-600:]}")

    assert not esito["fuori"], (
        "AIR-GAP VIOLATO — un tool dichiarato «Pure-local» ha aperto una "
        f"connessione verso un host non locale: {esito['fuori']}\n"
        f"tool riusciti: {esito['riusciti']}")


def test_il_rilevatore_vede_una_connessione_esterna() -> None:
    """⚠️ IL CONTROLLO POSITIVO, e senza di esso il test qui sopra non e'
    leggibile: asserisce uno ZERO, e uno zero puo' venire da «nessuna
    connessione» o da «un rilevatore scollegato». Qui si tenta di raggiungere
    un indirizzo esterno e si pretende che il rilevatore lo REGISTRI.

    L'indirizzo e' `192.0.2.1` — TEST-NET-1, riservato alla documentazione e
    non instradabile: il tentativo non arriva da nessuna parte e non genera
    traffico utile. Non serve che RIESCA: il rilevatore annota l'host PRIMA di
    passare la chiamata alla connect vera, ed e' esattamente quel passaggio che
    questa cella verifica.
    """
    script = textwrap.dedent(
        """
        import json, socket

        _LOCAL = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}
        fuori = []

        def _host(addr):
            return str(addr[0]) if isinstance(addr, tuple) and addr else str(addr)

        _real_create = socket.create_connection

        def _rec_create(address, *a, **k):
            h = _host(address)
            if h.strip().lower() not in _LOCAL:
                fuori.append(h)
            return _real_create(address, *a, **k)

        socket.create_connection = _rec_create
        try:
            socket.create_connection(("192.0.2.1", 80), timeout=0.05)
        except Exception:
            pass          # irrilevante: conta che il rilevatore abbia annotato
        print("ESITO=" + json.dumps({"fuori": fuori}))
        """
    )
    out = subprocess.run([sys.executable, "-c", script],
                         capture_output=True, text=True, timeout=120)
    riga = [r for r in out.stdout.splitlines() if r.startswith("ESITO=")]
    assert riga, f"il controllo positivo non e' arrivato in fondo: {out.stdout[-400:]}"
    fuori = __import__("json").loads(riga[-1][len("ESITO="):])["fuori"]
    assert fuori == ["192.0.2.1"], (
        "IL RILEVATORE E' CIECO: una connessione verso un host esterno non e' "
        f"stata registrata (fuori={fuori}). Finche' questa cella e' rossa, il "
        "verde del test qui sopra non prova la localita' di nulla.")
