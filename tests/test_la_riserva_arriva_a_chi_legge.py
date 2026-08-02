"""La riserva veniva prodotta e nessuna superficie la stampava.

`ignorance_map` classifica una domanda `answerable` quando il migliore dei
risultati supera il pavimento dichiarato. Ma se quel punteggio sta SOTTO il
rumore che lo store ha misurato su se stesso, la riga porta un `caveat`:

    best hit 0.86 sits at or below the store's own measured noise level 0.88 —
    answerable, but this is the band where a nearest neighbour scores like a
    real match

Il commento sopra quella riga dice che cosa è: la cura del difetto per cui era
nata (male) la soglia `max(floor, noise_floor)`, ritirata il 01/08 perché
rendeva muta la mappa. La riserva è la forma corretta — si risponde, e si dice
che si è nella fascia dove un vicino qualunque vale quanto un match.

E `verimem ignorance` stampava `class`, `query` e `what_would_help`. Non il
caveat. La cura esisteva e avvisava soltanto sé stessa.

È l'ennesima della classe che questa serie di commit chiude, in una variante
sua: qui il valore non manca su un canale — manca su TUTTI i canali umani, e
vive solo nel `--json`.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod


class _MemFinta:
    """Restituisce un report con una riga che porta la riserva."""

    def ignorance(self, queries, **kw):
        return {
            "queries": [
                {"query": "una domanda al limite", "class": "answerable",
                 "what_would_help": None,
                 "caveat": ("best hit 0.86 sits at or below the store's own "
                            "measured noise level 0.88 — answerable, but this "
                            "is the band where a nearest neighbour scores "
                            "like a real match")},
                {"query": "una domanda comoda", "class": "answerable",
                 "what_would_help": None},
            ],
            "by_class": {"answerable": 2},
            "noise_floor": 0.88,
            "noise_floor_source": "measured",
            "deciding_floor": 0.8,
        }


@pytest.fixture()
def cli(monkeypatch):
    monkeypatch.setattr(cli_mod, "_open_memory", lambda *a, **k: _MemFinta())
    return CliRunner()


def _sotto(out: str, domanda: str) -> str:
    """Le righe SUBITO SOTTO quella della domanda, fino alla prossima domanda.

    Cercare una parola in tutto l'output sarebbe un test che passa per la
    ragione sbagliata: la riga di riepilogo contiene gia' `noise_floor=…`, e
    la prima stesura di questo file passava per quella.
    """
    righe = out.splitlines()
    idx = next((i for i, r in enumerate(righe) if domanda in r), None)
    if idx is None:
        return ""
    fuori = []
    for r in righe[idx + 1:]:
        if any(c in r for c in ("answerable", "conflict", "quarantined_only")):
            break
        fuori.append(r)
    return "\n".join(fuori)


def test_la_riserva_si_vede(cli):
    out = cli.invoke(cli_mod.app, ["ignorance", "una domanda al limite"]).output
    accanto = _sotto(out, "una domanda al limite")
    assert "nearest neighbour" in accanto or "noise" in accanto.lower(), (
        f"la riserva non arriva a chi legge:\n{out}")


def test_chi_non_ce_l_ha_non_riceve_rumore(cli):
    """Una riga senza riserva non deve guadagnare una nota: un avviso su tutto
    è un avviso su niente."""
    out = cli.invoke(cli_mod.app, ["ignorance", "una domanda comoda"]).output
    accanto = _sotto(out, "una domanda comoda")
    assert "nearest neighbour" not in accanto, accanto


def test_il_verdetto_resta_answerable(cli):
    """La riserva non declassa: il prodotto risponde e lo dice. Cambiare il
    verdetto è la cura sbagliata, già scritta e ritirata il 01/08 perché
    rendeva muta la mappa (7 domande su 8 che il corpus sa rispondere
    uscivano come ignoranza)."""
    out = cli.invoke(cli_mod.app, ["ignorance", "una domanda al limite"]).output
    assert "answerable" in out, out
