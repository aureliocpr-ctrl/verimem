"""Il comando che si chiama «trust» dichiarava un controllo che non poteva eseguire.

Trovato il 2026-08-01 usando il prodotto. Ho scritto nello store e verificato
che ci fosse (`admitted id=a89def6b0dc4`), poi ho chiesto al gate col flag che
promette il confronto col corpus vivo::

    $ verimem trust "Il database di produzione del banco di prova e' MySQL." --validate full
      Anti-confab trust check   NO FLAGS ✓
      checked:     L1 lexical screens, L3 contradiction

LA CAUSA. `cli.py` chiamava `run_validation_gate(..., agent=None,
validate=validate)`, e in `anti_confab_gate` il controllo L3 comincia cosi'::

    if agent is None or getattr(agent, "semantic", None) is None:
        return None

L3 confronta col corpus VIVO: senza agente non c'e' corpus, quindi non gira. Ma
la riga che dice cosa e' stato controllato era derivata dal FLAG, non
dall'esecuzione::

    f"{', L3 contradiction' if validate == 'full' else ''}"

E' LA STESSA CLASSE CURATA TRE RIGHE SOPRA il 2026-07-29, come dice il commento
rimasto nel file: «"TRUSTED" is earned by what actually ran». Quella cura rese
onesto il VERDETTO e lascio' `checked:` derivata dall'intenzione — un difetto
sopravvissuto alla cura del suo gemello, nello stesso blocco.

CIO' CHE QUESTA CURA FA, E CIO' CHE NON FA — e la seconda meta' conta quanto la
prima, perche' senza dirla si spaccerebbe per risolto un problema che resta.

FA: `--validate full` costruisce l'agente, quindi L3 gira DAVVERO, e `checked:`
elenca cio' che ha girato invece di cio' che e' stato chiesto.

NON FA: L3, anche girando, non vede QUELLA contraddizione. Misurato::

    salienti della CLAIM : caps=['MySQL']      -> totale 1
    salienti del FATTO   : caps=['PostgreSQL']
    overlap claim->fatto : 0.0000   (soglia 0.6)
    regola a validate_claim.py:146: «Se totale < 2 ⇒ unknown»

Due ragioni indipendenti, e la seconda e' strutturale: l'aggancio richiede che i
nomi propri della claim compaiano nel fatto, ma due frasi che si contraddicono
differiscono PROPRIO sul nome proprio. Piu' netta la contraddizione, meno
probabile l'aggancio — il criterio penalizza il caso che deve rilevare.

Cambiarlo e' un cambio di semantica del gate sul write path, e non lo si fa di
iniziativa in una nottata: qui lo si INCHIODA come limite noto, con i numeri,
cosi' che il giorno in cui verra' affrontato ci sia un test che cambia colore.
"""
from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _pulito(r) -> str:
    return _ANSI.sub("", r.output)


def _riga_checked(out: str) -> str:
    for riga in out.splitlines():
        if "checked:" in riga:
            return riga
    return ""


@pytest.fixture()
def store_con_un_fatto(tmp_path, monkeypatch):
    """La CLI legge da CONFIG, congelato all'import: si scrive DOVE LEGGE."""
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.config import CONFIG
    from verimem.semantic import Fact, SemanticMemory
    sm = SemanticMemory(db_path=CONFIG.semantic_db)
    sm.store(Fact(proposition="Il database di produzione e' PostgreSQL.",
                  topic="infra/db"), embed="sync")
    return sm


def test_validate_full_fa_girare_L3_davvero(store_con_un_fatto, monkeypatch):
    """Il difetto: l'agente era None, quindi L3 tornava subito None."""
    visti: list = []
    import verimem.cli as cli_mod
    vero = cli_mod._agente_per_l3

    def _spia():
        a = vero()
        visti.append(a)
        return a

    monkeypatch.setattr(cli_mod, "_agente_per_l3", _spia)
    r = runner.invoke(app, ["trust", "Il database di produzione e' MySQL.",
                            "--validate", "full"])
    assert r.exit_code in (0, 1), _pulito(r)
    assert visti and visti[0] is not None, (
        "`--validate full` non ha costruito l'agente: L3 non ha nessun corpus "
        "contro cui confrontare, e torna None prima di guardare qualunque cosa")
    assert getattr(visti[0], "semantic", None) is not None, visti


def test_checked_dice_cio_che_ha_girato_non_cio_che_e_stato_chiesto(
        tmp_path, monkeypatch):
    """La seconda meta'. Con lo store irraggiungibile L3 non puo' confrontare
    niente: la riga deve dirlo invece di ereditare il flag.

    Senza questo presidio la cura sarebbe solo «adesso funziona», e il difetto
    tornerebbe il giorno in cui L3 smette di poter girare per un'altra ragione."""
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    import verimem.cli as cli_mod

    def _esplode():
        raise RuntimeError("store irraggiungibile")

    monkeypatch.setattr(cli_mod, "_agente_per_l3", _esplode)
    r = runner.invoke(app, ["trust", "Una frase qualunque e' vera.",
                            "--validate", "full"])
    out = _pulito(r)
    assert r.exit_code in (0, 1), out
    assert "L3 contradiction" not in _riga_checked(out), (
        f"`checked:` nomina L3 anche se non ha potuto girare:\n{out}")


def test_il_default_fast_non_promette_L3(store_con_un_fatto):
    """Controprova: senza `--validate full` la riga non deve nominare L3 —
    altrimenti il primo test passerebbe per la ragione sbagliata."""
    r = runner.invoke(app, ["trust", "Il database di produzione e' MySQL."])
    assert "L3" not in _pulito(r)


def test_LIMITE_NOTO_una_contraddizione_su_UN_solo_nome_proprio_non_aggancia():
    """Il perimetro vero di L3, inchiodato coi numeri invece che raccontato.

    Se un giorno questo test diventa rosso, significa che qualcuno ha cambiato
    il criterio di aggancio — ed e' esattamente il momento in cui si vuole
    saperlo."""
    from verimem.validate_claim import _extract_salients, _subj_overlap
    claim = "Il database di produzione e' MySQL."
    fatto = "Il database di produzione e' PostgreSQL."
    caps, anni = _extract_salients(claim)
    assert len(caps) + len(anni) < 2, (
        f"la claim ha {len(caps)+len(anni)} salienti: sopra 1 la regola "
        f"«totale < 2 ⇒ unknown» non scatta piu' e questo test misura altro")
    assert _subj_overlap(caps, fatto) == 0.0, (
        f"i salienti della claim {sorted(caps)} non compaiono nel fatto: e' il "
        f"motivo strutturale per cui una contraddizione NETTA aggancia MENO di "
        f"una vaga")
