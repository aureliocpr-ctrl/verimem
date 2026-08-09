"""La libreria delle skill si puo' deduplicare senza aprire il codice.

Il modulo che le unisce, `skill_name_dedup`, era completo, con i suoi test, e
irraggiungibile da ogni superficie: una manutenzione che nessuno poteva
eseguire.

QUANTO SERVE OGGI, misurato invece che sperato — e il numero ridimensiona la
cura, quindi va scritto:

    candidate     4 skill,   0 duplicati di nome
    promoted      6 skill,   0 duplicati
    retired     315 skill, 107 duplicati

Sulla libreria vera il comando trova ZERO gruppi, ed e' corretto: tocca solo le
`candidate`, e i 107 duplicati stanno fra le ritirate, che non ha senso unire.
Avevo misurato «33 nomi ripetuti su 325» e li avevo letti come lavoro da fare:
erano quasi tutti in un'area che il dedup giustamente ignora. Resta collegato
perche' e' manutenzione ordinaria che servira' quando le candidate cresceranno
— non perche' sblocchi qualcosa adesso.

E' gia' costruito per essere esposto, il che rende ancora piu' netto il fatto
che non lo fosse: `apply=False` di default (dry-run), `max_retire` come limite,
e tocca solo le `candidate` — mai una skill promossa.

Sta sulla CLI e non su MCP, come `requalify-quarantined` che e' l'operazione
gemella: e' manutenzione una-tantum sulla libreria, non una lettura che un
agente fa di continuo. La regola «una capacita' su un canale solo e' un
difetto» vale per cio' che si legge, non per cio' che si fa una volta.
"""
from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _out(args: list[str]) -> str:
    r = runner.invoke(app, args)
    assert r.exit_code == 0, _ANSI.sub("", r.output)
    return _ANSI.sub("", r.output)


@pytest.fixture
def libreria(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.agent import VerimemAgent
    a = VerimemAgent.build()
    from verimem.skill import Skill
    for i in range(3):
        a.skills.store(Skill(name="Provide Final Answer", trigger="t",
                             body="b", status="candidate"))
    a.skills.store(Skill(name="Un'altra skill", trigger="t", body="b",
                         status="candidate"))
    return a


def test_il_comando_esiste_e_di_default_non_tocca_niente(libreria):
    """Dry-run di default: una manutenzione che parte scrivendo e' un rischio
    che nessuno ha chiesto."""
    out = _out(["skills", "dedup"])
    assert "dry" in out.lower() or "dry-run" in out.lower(), out
    vivi = [s for s in libreria.skills.all() if s.status == "candidate"]
    assert len(vivi) == 4, "il dry-run ha modificato la libreria"


def test_trova_i_nomi_ripetuti(libreria):
    out = _out(["skills", "dedup"])
    assert "3" in out or "2" in out, f"non riporta il gruppo di duplicati:\n{out}"


def test_con_apply_unisce_davvero(libreria):
    _out(["skills", "dedup", "--apply"])
    nomi = [s.name for s in libreria.skills.all() if s.status == "candidate"]
    assert nomi.count("Provide Final Answer") == 1, (
        f"i duplicati non sono stati uniti: {nomi}")
    assert "Un'altra skill" in nomi, "ha toccato una skill che non c'entrava"


def test_non_tocca_le_promosse(libreria):
    """Una skill promossa ha superato una soglia con dei trial veri: una
    manutenzione automatica non la ritira."""
    from verimem.skill import Skill
    libreria.skills.store(Skill(name="Provide Final Answer", trigger="t",
                                body="b", status="promoted"))
    _out(["skills", "dedup", "--apply"])
    promosse = [s for s in libreria.skills.all() if s.status == "promoted"]
    assert len(promosse) == 1, "ha ritirato una skill promossa"
