"""`verimem recall` non diceva che su quel record c'e' un fatto trattenuto.

CENSIMENTO del 2026-08-05, sulla garanzia nata la notte stessa::

    SDK   Memory.recall        SI
    HTTP  GET /v1/search       SI   (passa gratis, e un test lo inchioda)
    CLI   verimem recall       NO   <- questo file
    MCP   SemanticMemory       NO   (territorio di ws6, dichiarato)

La riga che la CLI stampa porta il testo, la somiglianza e il verdetto del
moat. Su un registro dove il fatto giusto e' stato archiviato, chi usa la riga
di comando riceve la risposta sbagliata con un punteggio alto e **nulla che lo
lasci sospettare** — mentre lo stesso identico store, interrogato dall'SDK,
dichiara `hidden_records`.

E' la classe che questa casa sorveglia con
`test_le_capacita_senza_porta_non_aumentano`: una capacita' che esiste
nell'SDK e non ha una porta. Qui pero' e' peggio del solito — la capacita' non
e' un comando in piu' da scoprire, e' un AVVISO su una risposta che si sta gia'
leggendo.

Il codice della CLI aveva gia' la frase giusta, scritta per la storia::

    «La storia si chiede e va MOSTRATA: passare il flag e stampare la stessa
     riga di prima sarebbe una porta che si apre sul muro.»
"""
from __future__ import annotations

from typer.testing import CliRunner

from verimem.cli import app, riga_di_recall

HIT_CON_NASCOSTI = {
    "text": "Il campione S-025 contiene zinco a 35 milligrammi per litro.",
    "score": 0.8786,
    "hidden_records": [
        {"code": "S-007", "id": "a2", "why": "retired",
         "text": "Il campione S-007 contiene zinco a 17 milligrammi per litro."},
    ],
}


def test_la_riga_da_sola_non_basta():
    """La riga di risultato NON deve gonfiarsi: l'avviso e' una riga a parte,
    perche' `riga_di_recall` e' condivisa da piu' comandi."""
    riga = riga_di_recall(HIT_CON_NASCOSTI)
    assert "S-025" in riga
    assert "S-007" not in riga


def test_il_comando_stampa_l_avviso(tmp_path, monkeypatch):
    """IL CUORE: chi legge la risposta dalla riga di comando deve sapere che
    su quel record c'e' dell'altro."""
    import verimem.cli as cli

    class _M:
        def search(self, *a, **k):
            return [HIT_CON_NASCOSTI]

    monkeypatch.setattr(cli, "_open_memory", lambda *a, **k: _M())
    res = CliRunner().invoke(app, ["recall", "Quanto zinco contiene S-007?"])
    assert res.exit_code == 0, res.output
    assert "S-007" in res.output, res.output
    assert "retired" in res.output or "ritirato" in res.output, res.output


def test_senza_nascosti_l_uscita_non_cambia(tmp_path, monkeypatch):
    """IL PRESIDIO: sulla lettura ordinaria — 4356 fatti su 5333 del corpus
    vero non contengono nemmeno un codice — non compare niente di nuovo."""
    import verimem.cli as cli

    class _M:
        def search(self, *a, **k):
            return [{"text": "Il progetto procede bene.", "score": 0.9}]

    monkeypatch.setattr(cli, "_open_memory", lambda *a, **k: _M())
    res = CliRunner().invoke(app, ["recall", "Come va il progetto?"])
    assert res.exit_code == 0, res.output
    assert "trattenut" not in res.output.lower()
    assert "retired" not in res.output.lower()
