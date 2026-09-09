"""README:505-506 — «imports nothing until you pass --ids or --all».

IL CLAIM, testuale dal README pubblicato (righe 505-506):

    verimem import conversations.json   # list a ChatGPT/Claude export (imports nothing
                                        # until you pass --ids or --all)

PERCHE' QUESTO FILE ESISTE, quando `test_cli_import.py` gia' invoca la stessa
porta senza flag. Quel test — `test_import_default_lists_only` — asserisce tre
cose, e tutte e tre guardano l'OUTPUT:

    assert r.exit_code == 0
    assert "cl-1" in r.output and "Recipe ideas" in r.output
    assert "--ids" in r.output or "--all" in r.output

Nessuna guarda lo STORE. Il nome dice `lists_only`, e «only» e' esattamente la
meta' che non viene asserita: il test verifica che il comando ELENCHI, non che
elenchi SOLTANTO. Se domani `import_cmd` importasse tutto **e in piu'**
stampasse la lista, quelle tre asserzioni resterebbero verdi e il difetto
passerebbe. Un test non puo' presidiare una promessa che non nomina.

E la promessa qui non e' cosmetica: senza consenso il comando riceve un export
di conversazioni personali. Rotta, non «legge male» — SCRIVE dati che l'utente
non ha chiesto di scrivere, e se ne accorge solo dopo.

COSA AGGIUNGE QUESTO FILE: la seconda meta'. Guarda i fatti nello store, non le
righe a schermo. E porta il proprio controllo positivo, perche' «zero fatti» e'
verde anche quando il sensore e' scollegato — se lo store non si aprisse, o se
l'estrazione non producesse mai niente, l'asserzione passerebbe per la ragione
sbagliata. Il controllo mostra che LO STESSO righello, sullo STESSO store, vede
i fatti quando il consenso c'e'.

FALSIFICATO, non solo scritto (09/09/2026 00:15). Il difetto e' stato simulato
nel prodotto per un minuto — `cli.py:1194`, `raise typer.Exit(0)` sostituito con
`import_all = True`, cioe' «elenca E importa» — e i due presidi sono stati
eseguiti sullo STESSO difetto, uno dopo l'altro:

    python -m pytest tests/test_cli_import.py -q -p no:randomly
      -> EXIT=0   3 passed          (il presidio vecchio non se ne accorge)
    python -m pytest tests/test_import_senza_consenso_non_scrive_niente.py -q -p no:randomly
      -> EXIT=1   1 failed          «lo store contiene 1 fatti»

E il messaggio del rosso porta il reperto che vale piu' del test:

    output del comando:
    1 conversations found (format: claude) — nothing imported yet:

il comando STAMPA «nothing imported yet» mentre ha importato. Un presidio che
guarda l'output non puo' che credere all'output: e' la ragione strutturale per
cui un claim del README va tenuto fermo sull'EFFETTO, non sul TESTO. `cli.py`
e' stato ripristinato con `git checkout --` e verificato identico al backup.

Senza il difetto, `EXIT=0`, 3 passed.

ws7 «Iris», 09/09/2026 23:55.
"""
from __future__ import annotations

import json

from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()


class _GiudiceFinto:
    """Estrattore deterministico: NON serve un modello per provare la promessa.

    Rende sempre una proposizione, cosi' che «zero fatti» dopo l'invocazione
    senza consenso non possa essere spiegato con «non c'era niente da estrarre».
    """

    def complete(self, system, messages, **kw):
        class R:
            text = "The user dislikes snakes and cats"

        return R()


def _export_con_contenuto(tmp_path):
    """Un export che ha DAVVERO qualcosa dentro da importare."""
    data = [{"uuid": "cl-1", "name": "Recipe ideas",
             "created_at": "2026-01-02T10:00:00Z",
             "updated_at": "2026-01-02T11:00:00Z",
             "chat_messages": [
                 {"uuid": "m1", "sender": "human", "text": "I dislike snakes and cats."},
                 {"uuid": "m2", "sender": "assistant", "text": "Noted!"},
             ]}]
    p = tmp_path / "conversations.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _quanti_fatti() -> int:
    """I fatti che lo store contiene DAVVERO, aperto come lo apre il prodotto.

    ⚠️ `SemanticMemory()` SENZA argomenti, esattamente come fa `import_cmd`
    (`cli.py:1208`): la cartella la decide `HIPPO_DATA_DIR`, che il test
    imposta con monkeypatch. Un `data_dir=` inventato qui e' costato tre rossi
    alle 23:58 — e li ha classificati il controllo positivo, che e' caduto
    insieme agli altri due: quando cade anche lui, il difetto e' nel righello.

    ⚠️ E non conta i file ne' le righe a schermo: uno store CREATO e vuoto ha
    gia' i suoi byte sul disco, quindi contare il .db direbbe > 0 su un
    database senza un solo fatto.
    """
    from verimem.semantic import SemanticMemory

    sm = SemanticMemory()
    try:
        return len(sm.list_facts(limit=10000, offset=0))
    finally:
        chiudi = getattr(sm, "close", None)
        if callable(chiudi):
            chiudi()


def _con_estrattore_finto(monkeypatch):
    import verimem.cli as cli_mod

    monkeypatch.setattr(cli_mod, "_import_llm", lambda model=None: _GiudiceFinto())


# ── LA PROMESSA ─────────────────────────────────────────────────────────────


def test_senza_consenso_lo_store_resta_VUOTO(tmp_path, monkeypatch):
    """README:505-506: senza --ids/--all/--all-matching non entra NIENTE."""
    dati = tmp_path / "data"
    monkeypatch.setenv("HIPPO_DATA_DIR", str(dati))
    _con_estrattore_finto(monkeypatch)
    p = _export_con_contenuto(tmp_path)

    r = runner.invoke(app, ["import", str(p)])

    assert r.exit_code == 0, r.output
    dopo = _quanti_fatti()
    assert dopo == 0, (
        f"README:505-506 promette «imports nothing until you pass --ids or --all», "
        f"e dopo l'invocazione senza consenso lo store contiene {dopo} fatti.\n"
        f"output del comando:\n{r.output}"
    )


# ── IL CONTROLLO POSITIVO: lo stesso righello DEVE vedere i fatti ───────────


def test_CONTROLLO_col_consenso_lo_STESSO_righello_VEDE_i_fatti(tmp_path, monkeypatch):
    """Se questo e' verde e il precedente pure, «zero» significa zero.

    Senza questo, `_quanti_fatti` potrebbe rendere 0 sempre — store che non si
    apre, estrazione muta, cartella sbagliata — e il test della promessa
    passerebbe per la ragione sbagliata: il difetto del sensore scollegato.
    """
    dati = tmp_path / "data"
    monkeypatch.setenv("HIPPO_DATA_DIR", str(dati))
    _con_estrattore_finto(monkeypatch)
    p = _export_con_contenuto(tmp_path)

    r = runner.invoke(app, ["import", str(p), "--ids", "cl-1"])

    assert r.exit_code == 0, r.output
    dopo = _quanti_fatti()
    assert dopo > 0, (
        "il righello non vede i fatti nemmeno QUANDO il consenso c'e': "
        f"lo store ne conta {dopo} dopo un import esplicito.\n"
        f"output del comando:\n{r.output}"
    )


# ── E LA TERZA VIA DI CONSENSO CHE IL README NON NOMINA ─────────────────────


def test_il_README_nomina_due_vie_di_consenso_e_il_codice_ne_ha_TRE(tmp_path, monkeypatch):
    """`--all-matching` importa, e la parentesi del README non la nomina.

    Non e' una falsita' — la riga 507-508 la insegna poco sotto — ma la
    parentesi delle 505-506, letta da sola, elenca due vie su tre. Questo test
    tiene ferma l'esistenza della terza: se domani `--all-matching` sparisse o
    smettesse di importare, il README continuerebbe a insegnarla alla 507.
    """
    dati = tmp_path / "data"
    monkeypatch.setenv("HIPPO_DATA_DIR", str(dati))
    _con_estrattore_finto(monkeypatch)
    p = _export_con_contenuto(tmp_path)

    r = runner.invoke(app, ["import", str(p), "--match", "Recipe", "--all-matching"])

    assert r.exit_code == 0, r.output
    assert _quanti_fatti() > 0, (
        "`--all-matching` con un filtro non ha importato niente: e' la terza via "
        f"di consenso che il README insegna alla riga 507.\noutput:\n{r.output}"
    )
