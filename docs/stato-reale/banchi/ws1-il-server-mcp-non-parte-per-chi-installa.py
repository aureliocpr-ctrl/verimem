"""Il server MCP del pacchetto PUBBLICATO non parte: banco riproducibile.

Le cifre di `docs/stato-reale/02n-…` e `02p-…` erano LEGGIBILI ma NON
RIPRODUCIBILI: i venv che le hanno prodotte stavano in uno scratchpad di
sessione, che muore. Questo banco le SCRIVE e si puo' RIESEGUIRE — le due
condizioni insieme (ws3, 27/08: «una cifra in vetrina dev'essere leggibile nel
banco, non solo producibile da esso»; il caso opposto era il mio).

COSA MISURA, a tre livelli crescenti:
  1. RISOLUZIONE  `pip install --dry-run verimem==0.7.0` in un venv pulito ->
     quale `mcp` sceglie il risolutore. (Installa ZERO.)
  2. API a RUNTIME  su ciascuna delle due versioni di `mcp`, `hasattr` per
     `list_tools`/`call_tool`/`list_resources` sulla CLASSE e su un'ISTANZA.
     La cella `mcp 1.26.0` e' il CONTROLLO POSITIVO: senza, un «assente» non
     significherebbe nulla.
  0. L'IMPORT DEL PRODOTTO: `from mcp.server import Server`, che e' la riga 53
     di `verimem/mcp_server.py` al tag v0.7.0 — NON `mcp.server.lowlevel`.
     Prima stesura (27/08 18:49) sondava `lowlevel`: su mcp 1.0.0 dava
     ModuleNotFoundError e sembrava una conferma clamorosa della tesi che
     il PAVIMENTO fosse falso. Era un artefatto del percorso scelto da me.
     Con l'import vero, 1.0.0 funziona. Si sonda dove il prodotto chiama.
  3. LA RIGA VERA  `@server.list_tools()` — il decoratore a
     `verimem/mcp_server.py:6804` nel tag `v0.7.0` — eseguito in entrambe.

COSA NON MISURA, dichiarato: l'avvio del processo `verimem mcp` completo, che
richiede l'installazione intera (~2 GB). Il residuo e' «l'import arriva fino a
quella riga», non «l'API manca» ne' «la riga fallisce»: quelle sono misurate.

USO:  python ws1-il-server-mcp-non-parte-per-chi-installa.py [--venv-dir DIR]
      Se i venv non esistono li crea e installa SOLO `mcp` (~70 MB l'uno, non
      il pacchetto intero). Scrive il referto in `<repo>/benchmark/results/`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import tempfile
import sys
import venv

VERSIONI = ("2.1.1", "1.26.0", "1.0.0")
ATTRIBUTI = ("list_tools", "call_tool", "list_resources")

SONDA = r'''
import json
from importlib.metadata import version
from mcp.server import Server
s = Server("banco")
out = {"mcp": version("mcp"), "classe": {}, "istanza": {}}
for n in %(attributi)r:
    out["classe"][n] = hasattr(Server, n)
    out["istanza"][n] = hasattr(s, n)
try:
    @s.list_tools()
    async def _handler():
        return []
    out["riga_6804"] = "funziona"
except Exception as e:
    out["riga_6804"] = f"{type(e).__name__}: {e}"
print(json.dumps(out))
'''


def _py(d: pathlib.Path) -> pathlib.Path:
    return d / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def prepara(base: pathlib.Path, v: str) -> pathlib.Path:
    d = base / f"venv_mcp_{v.replace('.', '_')}"
    if not _py(d).exists():
        venv.EnvBuilder(with_pip=True).create(d)
        subprocess.run([str(_py(d)), "-m", "pip", "install", "-q", f"mcp=={v}"],
                       check=True)
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venv-dir", default=None,
                    help="dove tenere i venv (default: accanto al banco)")
    a = ap.parse_args()
    # default in TEMP, mai dentro il repo: un banco che sporca l'albero
    # quando lo esegui coi default e' un difetto, non una comodita'.
    base = (pathlib.Path(a.venv_dir) if a.venv_dir
            else pathlib.Path(tempfile.gettempdir()) / "banco_ws1_mcp")
    base.mkdir(parents=True, exist_ok=True)

    referto: dict = {"attributi_sondati": list(ATTRIBUTI), "per_versione": {}}
    for v in VERSIONI:
        d = prepara(base, v)
        r = subprocess.run([str(_py(d)), "-c", SONDA % {"attributi": ATTRIBUTI}],
                           capture_output=True, text=True, check=True)
        referto["per_versione"][v] = json.loads(r.stdout)

    a211 = referto["per_versione"]["2.1.1"]
    a126 = referto["per_versione"]["1.26.0"]
    referto["verdetto"] = {
        "assenti_su_2_1_1": sorted(n for n in ATTRIBUTI
                                   if not a211["classe"][n] and not a211["istanza"][n]),
        "presenti_su_1_26_0": sorted(n for n in ATTRIBUTI
                                     if a126["classe"][n] and a126["istanza"][n]),
        "riga_6804_su_2_1_1": a211["riga_6804"],
        "riga_6804_su_1_26_0": a126["riga_6804"],
        # Il PAVIMENTO dichiarato da pyproject al tag v0.7.0 e' `mcp>=1.0.0`
        # (tre volte: righe 72, 84, 141 — conta di ws3). Questa cella misura se
        # quella dichiarazione e' vera. Se la riga funziona in 1.0.0, il vincolo
        # e' onesto e il difetto e' SOLO il tetto mancante.
        "riga_6804_su_1_0_0": referto["per_versione"]["1.0.0"]["riga_6804"],
        "pavimento_mcp_1_0_0_regge": referto["per_versione"]["1.0.0"]["riga_6804"] == "funziona",
    }
    print(json.dumps(referto, indent=2, ensure_ascii=False))

    dest = pathlib.Path(__file__).resolve().parents[3] / "benchmark" / "results"
    if dest.is_dir():
        p = dest / "ws1_mcp_api_assente.json"
        p.write_text(json.dumps(referto, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nreferto scritto in {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
