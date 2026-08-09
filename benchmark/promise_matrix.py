"""Ogni promessa, su OGNI canale. Il gate fra «l'ho verificato» e «è vero».

Tutti i difetti trovati il 2026-07-29 hanno la stessa forma, e non è «il codice
era rotto»: il meccanismo funzionava sul percorso che qualcuno aveva provato ed
era spento sugli altri.

    il moat girava da CLI            e non da MCP
    il verdetto usciva da 1 lettura  e non dalle altre 3
    l'astensione era accesa su MCP   e spenta su SDK/console/gateway
    l'ingest giudicava da SDK        e non dal comando import

Ogni volta la dichiarazione «fatto» era vera — del percorso guardato. Una prova
per promessa non basta: serve una prova per CELLA.

Questa matrice incrocia le promesse del prodotto con i canali che un utente usa
davvero. Una cella vuota è una dichiarazione che nessuno può fare, e le sei
regressioni di oggi sarebbero state tutte visibili qui prima di essere
raccontate.

    python -m benchmark.promise_matrix

Esce 0 se ogni cella regge; 1 con la matrice stampata e le celle rotte in fondo.
Non stampa «tutto ok»: stampa la griglia, così l'assenza di una colonna si vede.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import tempfile
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

SOURCE = "Runbook di produzione: il servizio di fatturazione ascolta sulla porta 8443."
FATTO = "Il servizio di fatturazione ascolta sulla porta 8443."
INVENZIONE = "quale compagnia aerea usa il reparto vendite di questa azienda?"


# --------------------------------------------------------------------------
# canali: ognuno sa scrivere (con e senza source), leggere e interrogare
# --------------------------------------------------------------------------
class _Canale:
    nome = "?"

    def scrivi(self, testo: str, source: str | None) -> dict[str, Any]:
        raise NotImplementedError

    def leggi(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def dossier(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def db(self) -> Path:
        raise NotImplementedError


class CanaleSDK(_Canale):
    nome = "SDK"

    def __init__(self, dir_: Path) -> None:
        from verimem.client import Memory
        self.m = Memory(path=dir_ / "semantic" / "semantic.db")

    def scrivi(self, testo, source):
        return self.m.add(testo, topic="matrice/prova", source=source)

    def leggi(self, query):
        rep = self.m.explain(query)
        return list(rep.get("facts") or [])

    def dossier(self, query):
        return list(self.m.explain(query).get("facts") or [])

    def db(self):
        return Path(self.m.semantic.db_path)


class CanaleCLI(_Canale):
    nome = "CLI"

    def __init__(self, dir_: Path) -> None:
        from typer.testing import CliRunner

        from verimem.cli import app
        self.app, self.run = app, CliRunner()
        self.dir = dir_

    def scrivi(self, testo, source):
        args = ["save", testo, "--topic", "matrice/prova"]
        if source:
            args += ["--source", source]
        r = self.run.invoke(self.app, args)
        # la ricevuta è testo: il punteggio si legge dallo store
        con = sqlite3.connect(str(self.db()))
        row = con.execute("SELECT id, grounding_score, status FROM facts "
                          "ORDER BY created_at DESC LIMIT 1").fetchone()
        con.close()
        return {"id": row[0] if row else None,
                "grounding_score": row[1] if row else None,
                "status": row[2] if row else None,
                "_output": r.output}

    def leggi(self, query):
        from verimem.client import Memory
        rep = Memory(path=self.db()).explain(query)
        return list(rep.get("facts") or [])

    def dossier(self, query):
        from verimem.client import Memory
        return list(Memory(path=self.db()).explain(query).get("facts") or [])

    def db(self):
        return self.dir / "semantic" / "semantic.db"


class CanaleMCP(_Canale):
    nome = "MCP"

    def __init__(self, dir_: Path) -> None:
        from verimem import mcp_server
        from verimem.semantic import SemanticMemory
        self.sm = SemanticMemory(db_path=dir_ / "semantic" / "semantic.db")
        self.srv = mcp_server

        class _A:
            def __init__(s):
                s.semantic = self.sm
        mcp_server._ag = lambda: _A()

    def _call(self, nome, args):
        from mcp.types import CallToolRequest, CallToolRequestParams
        h = self.srv.server.request_handlers[CallToolRequest]
        res = asyncio.run(h(CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name=nome, arguments=args))))
        payload = res.root if hasattr(res, "root") else res
        return json.loads(next(c.text for c in payload.content
                               if hasattr(c, "text")))

    def scrivi(self, testo, source):
        args = {"proposition": testo, "topic": "matrice/prova"}
        if source:
            args["source"] = source
        return self._call("hippo_remember", args)

    def leggi(self, query):
        return list(self._call("hippo_facts_search",
                               {"query": query, "limit": 5}).get("items") or [])

    def dossier(self, query):
        """Il DOSSIER, non la ricerca.

        La prima versione confrontava `hippo_facts_search` con `explain()` degli
        altri canali e segnava la cella dell'astensione come rotta. Il confronto
        era sbagliato: `facts_search` è una ricerca — restituisce il miglior
        match anche debole — mentre l'astensione il prodotto la promette per il
        dossier di custodia. Una matrice che incrocia superfici non equivalenti
        produce falsi allarmi, ed è esattamente il difetto che vuole prevenire.
        """
        return list(self._call("hippo_trust_report",
                               {"query": query, "k": 5}).get("facts") or [])

    def db(self):
        return Path(self.sm.db_path)


# --------------------------------------------------------------------------
# promesse: ognuna è una domanda a cui un canale risponde sì o no
# --------------------------------------------------------------------------
def p_giudica_con_source(c: _Canale) -> tuple[bool, str]:
    r = c.scrivi(FATTO, SOURCE)
    s = r.get("grounding_score")
    return isinstance(s, (int, float)), f"score={s}"


def p_non_finge_senza_source(c: _Canale) -> tuple[bool, str]:
    r = c.scrivi("Il totale della fattura e 1240 euro.", None)
    s = r.get("grounding_score")
    return s is None, f"score={s} (atteso None, non 0)"


def p_persiste_il_verdetto(c: _Canale) -> tuple[bool, str]:
    r = c.scrivi(FATTO, SOURCE)
    con = sqlite3.connect(f"file:{c.db()}?mode=ro", uri=True)
    row = con.execute("SELECT grounding_score FROM facts WHERE id LIKE ?",
                      (f"{str(r.get('id'))[:12]}%",)).fetchone()
    con.close()
    return bool(row and row[0] is not None), f"riga={row}"


def p_la_lettura_porta_il_verdetto(c: _Canale) -> tuple[bool, str]:
    c.scrivi(FATTO, SOURCE)
    letti = c.leggi("su quale porta ascolta il servizio di fatturazione")
    if not letti:
        return False, "la lettura non ha restituito nulla"
    return ("grounding_score" in letti[0],
            f"chiavi={sorted(letti[0].keys())[:6]}")


def p_si_astiene_su_cio_che_non_sa(c: _Canale) -> tuple[bool, str]:
    """Sul DOSSIER, che e' dove l'astensione e' promessa — non sulla ricerca."""
    c.scrivi(FATTO, SOURCE)
    letti = c.dossier(INVENZIONE)
    return not letti, f"ha risposto con {len(letti)} fatti"


PROMESSE: list[tuple[str, Callable[[_Canale], tuple[bool, str]]]] = [
    ("giudica una scrittura con source", p_giudica_con_source),
    ("non finge un verdetto senza source", p_non_finge_senza_source),
    ("persiste il verdetto sulla riga", p_persiste_il_verdetto),
    ("la lettura riporta il verdetto", p_la_lettura_porta_il_verdetto),
    ("si astiene su cio' che non sa", p_si_astiene_su_cio_che_non_sa),
]

CANALI = [CanaleSDK, CanaleCLI, CanaleMCP]


#: Promesse che senza un giudice non sono verificabili. Su una macchina senza il
#: modello CE (la CI, un'installazione fresca) segnarle "NO" sarebbe un falso
#: rosso — la promessa non e' violata, e' NON MISURABILE. Distinguere le due cose
#: e' esattamente cio' che questo prodotto vende, e una matrice che le confonde
#: non merita di essere creduta.
RICHIEDONO_GIUDICE = {
    "giudica una scrittura con source",
    "persiste il verdetto sulla riga",
    "la lettura riporta il verdetto",
    "si astiene su cio' che non sa",
}


def main() -> int:
    rotte: list[str] = []
    griglia: dict[tuple[str, str], str] = {}
    try:
        from verimem.local_grounding import local_ce_available
        _giudice = local_ce_available()
    except Exception:  # noqa: BLE001
        _giudice = False
    if not _giudice:
        print("\nnessun giudice locale installato: le promesse che ne dipendono "
              "sono NON MISURABILI qui, non violate.\n"
              "  `verimem warmup` scarica il modello (~656 MB).")

    for cls in CANALI:
        for nome, prova in PROMESSE:
            if not _giudice and nome in RICHIEDONO_GIUDICE:
                griglia[(nome, cls.nome)] = "n/d"
                continue
            d = Path(tempfile.mkdtemp(prefix="matrice_"))
            for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
                os.environ[k] = str(d)
            os.environ.pop("ENGRAM_MIN_RELEVANCE", None)
            try:
                c = cls(d)
                ok, det = prova(c)
            except Exception as exc:  # noqa: BLE001
                ok, det = False, f"{type(exc).__name__}: {exc}"
                traceback.clear_frames(exc.__traceback__)
            griglia[(nome, cls.nome)] = "ok" if ok else "NO"
            if not ok:
                rotte.append(f"{nome} @ {cls.nome}: {det}")

    larg = max(len(n) for n, _ in PROMESSE) + 2
    print()
    print(" " * larg + "".join(f"{c.nome:>6}" for c in CANALI))
    print("-" * (larg + 6 * len(CANALI)))
    for nome, _ in PROMESSE:
        riga = "".join(f"{griglia[(nome, c.nome)]:>6}" for c in CANALI)
        print(f"{nome:<{larg}}{riga}")
    print()
    if rotte:
        print(f"=== {len(rotte)} CELLE ROTTE su {len(PROMESSE) * len(CANALI)} ===")
        for r in rotte:
            print(f"  {r}")
        return 1
    _nd = sum(1 for v in griglia.values() if v == "n/d")
    _ok = sum(1 for v in griglia.values() if v == "ok")
    if _nd:
        # NON "tutte le celle reggono": 12 celle n/d con 3 ok non e' un verde,
        # e dirlo cosi' sarebbe il difetto che questa matrice esiste per
        # trovare — dichiarare misurato cio' che non e' stato misurato.
        print(f"{_ok} celle verificate, {_nd} NON MISURABILI senza giudice "
              f"(su {len(griglia)}). Questo non e' un verde: e' un verde "
              f"parziale, e la parte che conta di piu' e' quella non misurata.")
    else:
        print(f"tutte le {len(griglia)} celle reggono")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
