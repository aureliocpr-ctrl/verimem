"""La scheda di un fatto dice se e' SCADUTO. Prima non lo diceva, e lo consegnava.

L'INVARIANTE, e qui era violato nel verso peggiore — non un fatto taciuto, un fatto
SERVITO senza il suo marchio: «nulla scaduto si serve senza dirlo».

MISURATO PRIMA DELLA CURA, sullo store vero (SQL in sola lettura come controprova)::

    SQL       id=103a30c7a651  valid_until=1788571647.5  SCADUTO
    recall    no facts found + «⚠ 1 fatto/i esclusi perche' SCADUTI ... chiedili per id»
    facts get id · topic · status model_claim · confidence · verified_by · testo
              ^ nessuna riga diceva «scaduto», e `status` era quello di un fatto VIVO

Il comando MANDAVA a se stesso: l'avviso del recall dice «Per vederli lo stesso,
chiedili per id», e questo comando restituiva il fatto con l'aspetto di uno valido.
`facts_get` costruiva il pannello con sei campi fissi e `valid_until` non era fra
questi — il docstring dice «proposition + provenance + status», e nel modello
dell'autore la scadenza non ci rientrava.

⚠️ QUESTO FILE SCRIVE DALLA CLI, NON DALL'SDK, e non e' un dettaglio di stile:
`Memory()` senza path non rilegge la data dir dopo il primo uso nel processo (si
aggancia alla prima e ci resta), mentre `_facts_sm()` della CLI la rilegge a ogni
chiamata — misurato::

    Memory() dopo A -> ...\\dirA-...\\semantic\\semantic.db
    Memory() dopo B -> ...\\dirA-...\\semantic\\semantic.db     <- resta su A
    CLI      dopo A -> ...\\cliA-...\\semantic\\semantic.db
    CLI      dopo B -> ...\\cliB-...\\semantic\\semantic.db     <- segue l'env

Con piu' test nello stesso processo pytest, un `Memory()` scriverebbe dove il
comando poi non guarda. Scrivendo e leggendo dalla stessa porta il problema non
esiste.

⚠️ E NON si chiede `isolated_corpus`: il conftest ha gia' una fixture AUTOUSE che
pinna tutti e quattro gli alias della data dir su una tmp per-test. Chiedere anche
`isolated_corpus` ne crea una SECONDA dopo, e i due comandi finiscono in due store:
`remember` rispondeva `admitted id=...` e `facts get` sullo stesso id rispondeva
`not found`. L'isolamento c'era gia': la copia in piu' era il difetto.
"""
from __future__ import annotations

import time

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod

GIORNO = 86400.0


def _cli(*argv: str):
    return CliRunner().invoke(cli_mod.app, list(argv))


def _scrivi(testo: str, *, topic: str, valid_until: float | None = None) -> str:
    """Scrive dalla CLI e restituisce l'id. 🔑 Verifica che il fatto ci sia DAVVERO:
    senza, un write respinto darebbe una scheda vuota e le celle sotto direbbero
    «la scadenza non compare» — accusando il prodotto per un difetto del banco."""
    argv = ["remember", testo, "--topic", topic]
    if valid_until is not None:
        argv += ["--valid-until", str(valid_until)]
    r = _cli(*argv)
    assert r.exit_code == 0, f"il banco: `remember` e' uscito {r.exit_code}:\n{r.output}"
    fid = ""
    for pezzo in r.output.split():
        if pezzo.startswith("id="):
            fid = pezzo[3:]
    assert fid, f"il banco: nessun id nell'uscita di `remember`:\n{r.output}"
    return fid


def _scheda(fact_id: str) -> str:
    """⚠️ Si controlla anche l'EXIT CODE, non solo l'output: `facts get` esce 1 con
    «not found», e in quel caso l'output esiste ma non e' una scheda — gli assert
    fallirebbero dicendo che manca la scadenza, quando invece manca il FATTO."""
    r = _cli("facts", "get", fact_id)
    assert r.exit_code == 0, (
        f"il banco: `facts get {fact_id}` e' uscito {r.exit_code}:\n{r.output}")
    return r.output


# ---- il fatto scaduto lo dichiara --------------------------------------------

def test_la_scheda_di_un_fatto_scaduto_lo_dichiara():
    """Chi arriva qui seguendo l'avviso del recall SA che e' scaduto. Chi ci arriva
    con un id preso da un log, da un ticket o da un handoff NO — e il prodotto
    glielo consegnava con lo stesso aspetto di un fatto vivo."""
    fid = _scrivi("il feature flag del checkout resta acceso",
                  topic="flag", valid_until=time.time() - GIORNO)
    out = _scheda(fid)
    assert "scadut" in out.lower(), (
        f"la scheda di un fatto SCADUTO deve dirlo:\n{out}")
    assert "checkout" in out, f"il banco: la scheda non e' quella attesa:\n{out}"


# ---- e la scadenza ancora da venire si vede ----------------------------------

def test_la_scheda_dichiara_anche_una_scadenza_ancora_da_venire():
    """Non e' «un bollino rosso»: e' il CAMPO. Un fatto con `valid_until` nel futuro
    e' vivo, e chi legge deve poter sapere fino a quando.

    🪞 La prima stesura di questa cella passava per la ragione sbagliata: il testo
    del fatto era «vale FINO a primavera» e l'assert cercava «fino» — si accendeva
    sulla PROPOSIZIONE invece che sul CAMPO. Il testo qui sotto non contiene nessuna
    delle parole cercate: un criterio lessicale va provato anche contro il dato che
    NON deve farlo scattare.
    """
    fid = _scrivi("il certificato del dominio e stato rinnovato a marzo",
                  topic="rete", valid_until=time.time() + 30 * GIORNO)
    out = _scheda(fid)
    assert "valid_until" in out, f"la scadenza futura non compare nella scheda:\n{out}"
    assert "scadut" not in out.lower(), (
        f"una scadenza NEL FUTURO non deve essere marcata come scaduta:\n{out}")


# ---- e un fatto senza scadenza non guadagna righe ----------------------------

def test_un_fatto_senza_scadenza_non_guadagna_righe():
    """🔑 CONTROLLO ROVESCIATO: la cura non deve stampare una riga vuota o un
    «nessuna scadenza» su ogni fatto. Un campo sempre presente si legge come niente
    — e' la ragione per cui l'avviso del recall conta «quanti sarebbero entrati» e
    non «quanti ce ne sono»."""
    fid = _scrivi("la sala macchine di Genova ha due gruppi elettrogeni", topic="sedi")
    out = _scheda(fid)
    assert "valid_until" not in out, (
        f"un fatto senza `valid_until` non deve nominare la scadenza:\n{out}")


# ---- e un valore illeggibile non fa cadere la scheda -------------------------

def test_una_scadenza_illeggibile_non_fa_cadere_la_scheda(monkeypatch):
    """Un `valid_until` non numerico farebbe esplodere `float()`/`fromtimestamp()`, e
    il comando morirebbe su un campo DECORATIVO mentre il resto della scheda e'
    perfettamente leggibile. Il precedente e' in `client.py` («una data illeggibile
    non fa cadere nulla»), e la prima stesura di questa cura non ce l'aveva: l'ha
    trovata una rilettura a freddo, DOPO che il ciclo RED->GREEN era gia' verde.
    ⇒ Un RED->GREEN prova la cura sui dati GIUSTI: sui dati ROTTI non dice niente.
    """
    class _Rotto:
        id = "abcdef123456"
        topic = "t"
        status = "model_claim"
        confidence = 0.5
        verified_by: list[str] = []
        proposition = "una proposizione qualsiasi"
        valid_until = "non-una-data"

    monkeypatch.setattr(cli_mod, "_facts_sm", lambda *a, **k: None)
    monkeypatch.setattr(cli_mod, "_fact_id_resolve", lambda sm, fid: _Rotto())
    r = _cli("facts", "get", "abcdef")
    assert r.exit_code == 0, f"una scadenza illeggibile non deve far cadere la scheda:\n{r.output}"
    assert "illeggibile" in r.output, f"il campo deve dire che non sa leggerlo:\n{r.output}"
    assert "una proposizione qualsiasi" in r.output, (
        f"il resto della scheda deve arrivare lo stesso:\n{r.output}")
