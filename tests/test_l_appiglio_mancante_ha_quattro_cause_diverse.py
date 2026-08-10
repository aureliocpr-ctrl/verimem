"""«non si puo' annullare» ha quattro cause, e portano a quattro azioni diverse.

Trovato usando il prodotto da operatore: fra gli undici check del `doctor`,
`undo-window` e' quello il cui `fix` **non si puo' seguire**. Dice

    «check which build writes to this store (the `version` check above
      reports its tree and revision)»

ma il check `version` riporta **l'albero LOCALE** — non quello di chi ha
scritto quelle righe. L'operatore viene mandato a un check che risponde a
un'altra domanda.

=== IL DATO DISTINGUE QUATTRO STATI, IL MESSAGGIO NE MOSTRA UNO ===
Misurato sullo store vero il 2026-08-07::

    ritiri negli ultimi 7 giorni : 114
      appiglio VIVO              :   3
      appiglio GIA' USATO        :   0
      appiglio SCADUTO           :   0
      appiglio MAI ESISTITO      : 111

e le quattro colonne mandano a quattro azioni diverse:
  * **mai esistito** → il codice che ritira non fa lo snapshot: si guarda CHI
    ritira;
  * **scaduto** → il TTL di 7 giorni e' piu' corto della cadenza con cui
    quell'operatore rivede i ritiri: si alza il TTL;
  * **gia' usato** → **non e' un guasto, e' la funzione che ha funzionato**;
  * **vivo** → niente da fare.

🔴 **E il terzo caso e' il difetto peggiore**: oggi il check somma «usato»
dentro «non si puo' annullare» e AVVISA. Su uno store dove qualcuno ha
davvero annullato dei ritiri, la superficie segnalerebbe come guasto proprio
la funzione che sta funzionando — un falso allarme prodotto dal contare
insieme popolazioni diverse. E' la classe di oggi: *un'etichetta che porta una
conclusione non verificata*.

=== E CHI HA RITIRATO ORA SI PUO' DIRE ===
Da `b74ff6a0` il principal del ritiro porta `porta/attore`
(`audit_mutations`), quindi al posto di mandare l'operatore al check sbagliato
il `fix` puo' NOMINARE chi ha ritirato senza appiglio — o dire che non e'
registrato, che e' un'informazione diversa da «non lo so».
"""
from __future__ import annotations

import pathlib
import sqlite3
import time

import pytest

from verimem import doctor


def _check(monkeypatch, d):
    """Il check `undo-window` come lo legge un operatore.

    ⚠️ `d` NON e' la cartella che il banco sceglie: e' quella in cui il
    prodotto ha scritto davvero. `SemanticMemory()` risolve il percorso da
    `CONFIG`, che e' CONGELATO all'import (sotto pytest, sulla cartella del
    conftest), mentre `run_doctor` legge l'ambiente al momento della chiamata.
    Puntando il doctor alla cartella scelta dal banco, il check non trovava
    nessun database e SPARIVA — e un check assente non e' un check verde.
    E' la stessa divergenza che il docstring di `_stores_dichiarati` gia'
    documenta, incontrata dall'altro lato.
    """
    monkeypatch.setenv("HIPPO_DATA_DIR", str(d))
    monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
    monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
    for ch in doctor.run_doctor():
        if ch["name"] == "undo-window":
            return ch
    raise AssertionError("il check `undo-window` non compare affatto")


@pytest.fixture
def store(tmp_path, monkeypatch):
    d = tmp_path / "dati"
    for k in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(d))
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    return d


def _popola(d, *, vivi=0, usati=0, scaduti=0, mai=0):
    """Scrive i ritiri richiesti, uno stato per volta.

    Rende la cartella dati REALE — quella da cui il doctor va interrogato.
    """
    from verimem.semantic import Fact, SemanticMemory
    # ⚠️ PERCORSO ESPLICITO: `SemanticMemory()` senza argomento risolve da
    # una configurazione gia' risolta, che dentro una sessione pytest intera
    # punta alla cartella CONDIVISA del run — mentre il doctor risolve
    # dall'AMBIENTE. Due resolver, due store, e il banco confronta cose
    # diverse. Invisibile eseguendo questo file da solo.
    sm = SemanticMemory(db_path=d / "semantic" / "semantic.db")
    ora = time.time()
    con = sqlite3.connect(str(sm.db_path))
    n = 0
    da_scadere: list[str] = []
    for stato, quanti in (("vivo", vivi), ("usato", usati),
                          ("scaduto", scaduti), ("mai", mai)):
        for _ in range(quanti):
            n += 1
            a = Fact(proposition=f"il sito {n} ha 12 unita", topic=f"t/{n}")
            b = Fact(proposition=f"il sito {n} ha 15 unita", topic=f"t/{n}")
            sm.store(a, purpose="banco")
            sm.store(b, purpose="banco")
            if stato == "mai":
                # ritiro scritto a mano: nessuno snapshot, come i 111
                con.execute(
                    "UPDATE facts SET superseded_by=?, superseded_at=?,"
                    " superseded_reason='scritto a mano' WHERE id=?",
                    (b.id, ora, a.id))
                con.commit()
                continue
            sm.supersede(a.id, b.id, principal="cli:local/ws7",
                         reason="banco")
            if stato == "usato":
                con.execute("UPDATE facts_undo_log SET undone_at=?"
                            " WHERE fact_id=?", (ora, a.id))
                con.commit()
            elif stato == "scaduto":
                da_scadere.append(a.id)
    # ⚠️ LE SCADENZE SI IMPONGONO ALLA FINE, e non appena creato lo scatto.
    # `undo_log.py:187` POTA le righe scadute a ogni nuova scrittura di uno
    # scatto: mettendo la scadenza durante il ciclo, il `supersede` successivo
    # cancellava la riga e il banco contava «mai esistito» al posto di
    # «scaduto» — 3 richiesti, 1 osservato. Non era un difetto del banco: e' il
    # prodotto che rende quello stato non osservabile, ed e' il risultato che
    # questo file porta.
    for fid in da_scadere:
        con.execute("UPDATE facts_undo_log SET ttl_expires_at=?"
                    " WHERE fact_id=?", (ora - 10, fid))
    con.commit()
    con.close()
    return pathlib.Path(sm.db_path).parent.parent


class TestLeQuattroCauseSiLeggonoSeparate:

    def test_il_messaggio_distingue_i_quattro_stati(self, store, monkeypatch):
        vera = _popola(store, vivi=1, usati=1, scaduti=1, mai=1)
        det = _check(monkeypatch, vera)["detail"]
        for parola in ("expired", "undone", "never"):
            assert parola in det.lower(), f"manca «{parola}»: {det}"

    def test_i_numeri_delle_quattro_colonne_sono_giusti(self, store,
                                                        monkeypatch):
        vera = _popola(store, vivi=1, usati=2, scaduti=3, mai=4)
        det = _check(monkeypatch, vera)["detail"]
        # 10 ritiri: 1 vivo, 2 usati, 3 scaduti, 4 mai
        assert "10" in det, det
        for atteso in ("2", "3", "4"):
            assert atteso in det, f"manca il conteggio {atteso}: {det}"


class TestIlFalsoAllarmePeggiore:

    def test_se_gli_appigli_sono_stati_USATI_non_e_un_guasto(self, store,
                                                             monkeypatch):
        """🔴 IL ROSSO CHE CONTA: nove ritiri su dieci annullati davvero. La
        funzione ha funzionato. Oggi il check AVVISA — somma «usato» dentro
        «non si puo' annullare» e segnala come guasto l'uso corretto."""
        vera = _popola(store, vivi=1, usati=9)
        ch = _check(monkeypatch, vera)
        assert ch["status"] == doctor.OK, (
            "avvisa su ritiri che sono stati ANNULLATI: " + ch["detail"])

    def test_presidio_se_l_appiglio_non_e_mai_esistito_avvisa_ancora(
            self, store, monkeypatch):
        """PRESIDIO: il caso vero dello store di casa (111 su 114) deve
        continuare ad avvisare. Una cura che spegne anche l'allarme buono e'
        peggio del difetto."""
        vera = _popola(store, vivi=1, mai=9)
        ch = _check(monkeypatch, vera)
        assert ch["status"] == doctor.WARN, ch["detail"]


class TestLaRiparazioneSiPuoSEGUIRE:

    def test_non_manda_piu_al_check_version(self, store, monkeypatch):
        """`version` riporta l'albero LOCALE, non quello di chi ha scritto le
        righe: mandarci l'operatore e' un'istruzione che non si puo' seguire."""
        vera = _popola(store, vivi=1, mai=9)
        fix = _check(monkeypatch, vera).get("fix") or ""
        assert "`version`" not in fix, fix

    def test_dice_CHI_ha_ritirato_senza_appiglio(self, store, monkeypatch):
        """Da `b74ff6a0` il principal porta `porta/attore`: la riparazione puo'
        nominarlo invece di mandare a indovinare."""
        vera = _popola(store, vivi=1, mai=9)
        ch = _check(monkeypatch, vera)
        testo = ch["detail"] + " " + (ch.get("fix") or "")
        assert "not recorded" in testo or "cli:local" in testo, testo

    def test_il_TTL_si_nomina_solo_quando_e_la_causa(self, store,
                                                     monkeypatch):
        """FALSIFICAZIONE: un `fix` che elenca sempre tutte e quattro le cure
        non aiuta piu' di uno che ne asserisce una. Con zero scaduti, il TTL
        non deve comparire fra le azioni."""
        vera = _popola(store, vivi=1, mai=9)
        fix = (_check(monkeypatch, vera).get("fix") or "").lower()
        assert "ttl" not in fix, fix


class TestLaFinestraEIlTTLSonoLoSTESSONUMERO:
    """🔑 La correttezza del check DIPENDE da un'uguaglianza che niente
    garantiva: la finestra dei 7 giorni era scritta `7 * 86400.0` in
    `doctor` e `7 * 24 * 3600` in `undo_log`. **Due copie**, e tutto
    l'argomento del check («fuori dalla finestra "manca" e "scaduto" sono
    indistinguibili, quindi guardo dentro») cade se divergono."""

    def test_il_doctor_non_riscrive_il_ttl_ma_lo_IMPORTA(self):
        from verimem.doctor import _UNDO_TTL_S
        from verimem.undo_log import UNDO_TTL_SECONDS
        assert _UNDO_TTL_S == float(UNDO_TTL_SECONDS)

    def test_uno_scatto_scaduto_viene_CANCELLATO_alla_scrittura_successiva(
            self, store):
        """IL RISULTATO DI PRODOTTO che questo file ha trovato, e che rende
        `expired` una colonna strutturalmente vuota dentro la finestra:
        `undo_log.py:187` pota le righe scadute a OGNI scrittura di un nuovo
        scatto. Quindi «scaduto» diventa «mai esistito» — l'ambiguita' che il
        commento del check dichiara di voler evitare, prodotta dal prodotto
        stesso invece che dal tempo."""
        from verimem.semantic import Fact, SemanticMemory
        sm = SemanticMemory(db_path=store / "semantic" / "semantic.db")

        def coppia(n):
            a = Fact(proposition=f"il lotto {n} ha 12 pezzi", topic=f"q/{n}")
            b = Fact(proposition=f"il lotto {n} ha 15 pezzi", topic=f"q/{n}")
            sm.store(a, purpose="banco")
            sm.store(b, purpose="banco")
            sm.supersede(a.id, b.id, principal="cli:local/ws7", reason="b")
            return a.id

        primo = coppia(1)
        con = sqlite3.connect(str(sm.db_path))
        con.execute("UPDATE facts_undo_log SET ttl_expires_at=? WHERE fact_id=?",
                    (time.time() - 10, primo))
        con.commit()
        con.close()
        assert _righe_undo(sm, primo) == 1, "lo scatto scaduto c'e' ancora"

        coppia(2)          # una scrittura qualunque di un altro scatto
        assert _righe_undo(sm, primo) == 0, (
            "lo scatto scaduto NON e' stato potato: la premessa e' cambiata")


def _righe_undo(sm, fact_id: str) -> int:
    con = sqlite3.connect(str(sm.db_path))
    try:
        return int(con.execute(
            "SELECT COUNT(*) FROM facts_undo_log WHERE fact_id=?",
            (fact_id,)).fetchone()[0])
    finally:
        con.close()
