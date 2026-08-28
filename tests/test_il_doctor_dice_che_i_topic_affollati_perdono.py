"""Stanotte, in otto, abbiamo scoperto a mano una perdita che il prodotto non dice.

Il 09/08 quattro istanze hanno misurato indipendentemente la stessa cosa: i
fatti scritti su un topic **gia' usato** sopravvivono molto meno di quelli su
un topic proprio. I miei numeri (istante 23:22, finestra dalle 00:00):

    topic con UNA scrittura : 107 topic · fatti vivi 101/107 = 94,4%
    topic con DUE o piu'    :  13 topic · fatti vivi  27/40  = 67,5%

e i sei persi fra i "singoli" erano **6 su 6 quarantena, zero ritiri** ⇒ la
supersessione colpisce **solo** i topic ripetuti. ws5 ha il campione opposto
piu' grande (75 fatti, 75 topic distinti, **zero ritirati**).

⚠️ **Ma nessuno di noi l'ha scoperto col prodotto: l'abbiamo scoperto scrivendo
SQL a mano.** Un utente che non ha questa stanza perde i fatti e non lo sa —
la perdita e' silenziosa per costruzione, perche' un fatto ritirato resta nel
DB e sparisce solo dal recall.

Cio' che il check deve dire, e ognuna manda a un'azione diversa:
  1. le DUE popolazioni, perche' e' la **separazione** a essere il segnale
     (un tasso da solo non dice se e' alto: e' la trappola che ci ha morso
     cinque volte oggi — «misura ENTRAMBE le popolazioni»);
  2. DOVE, cioe' i topic peggiori, o l'operatore non sa dove guardare;
  3. la FINESTRA, perche' una quota sul corpus senza il periodo si legge
     sbagliata (un solo giorno di ritiri in blocco domina ogni media per
     sempre — e stanotte quattro conteggi dello stesso numero differivano
     solo per l'ora in cui erano stati presi);
  4. che il check **non sa** distinguere un aggiornamento legittimo da un
     fratello perso. Senza (4) sarebbe un veto travestito da avviso: due
     misure diverse sullo stesso topic e un vero aggiornamento hanno la
     stessa forma nel DB, e affermare il contrario sarebbe la confabulazione
     che questo prodotto esiste per impedire.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from verimem import doctor

ORA = time.time()


def _store(d, righe: list[tuple[str, str, str | None]]) -> None:
    """`righe` = [(fact_id, topic, superseded_by)]. Scritte a mano: il banco
    misura il CHECK, non il percorso di scrittura."""
    p = d / "semantic" / "semantic.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT,"
                " topic TEXT, superseded_by TEXT, superseded_at REAL,"
                " status TEXT, grounding_score REAL, created_at REAL,"
                " embedding BLOB, embedding_model TEXT, last_verified_at REAL)")
    con.executemany(
        "INSERT INTO facts (id, proposition, topic, superseded_by,"
        " superseded_at, status, created_at) VALUES (?,?,?,?,?,'model_claim',?)",
        [(fid, "x", top, sup, (ORA if sup else None), ORA)
         for fid, top, sup in righe])
    con.commit()
    con.close()


def _check(monkeypatch, d, nome="topic-crowding"):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(d))
    monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
    monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
    for ch in doctor.run_doctor():
        if ch["name"] == nome:
            return ch
    return None


@pytest.fixture
def affollato(tmp_path):
    """4 fatti su un topic solo (2 ritirati) + 5 fatti su 5 topic distinti."""
    d = tmp_path / "affollato"
    _store(d, [
        ("a1", "t/audit", "a3"), ("a2", "t/audit", "a4"),
        ("a3", "t/audit", None), ("a4", "t/audit", None),
        ("s1", "t/uno", None), ("s2", "t/due", None), ("s3", "t/tre", None),
        ("s4", "t/quattro", None), ("s5", "t/cinque", None),
    ])
    return d


@pytest.fixture
def uno_per_topic(tmp_path):
    """Il corpus sano: ogni fatto ha il suo topic, nessun ritiro."""
    d = tmp_path / "sano"
    _store(d, [(f"x{i}", f"t/{i}", None) for i in range(6)])
    return d


class TestLaSuperficieEsiste:

    def test_il_check_c_e(self, monkeypatch, affollato):
        assert _check(monkeypatch, affollato) is not None, (
            "nessuna superficie dice che i topic affollati perdono fatti — "
            "stanotte l'abbiamo scoperto in otto scrivendo SQL a mano")

    def test_avvisa_quando_la_separazione_c_e(self, monkeypatch, affollato):
        ch = _check(monkeypatch, affollato)
        assert ch["status"] == doctor.WARN, ch


class TestDiceLeDuePopolazioni:
    """Un tasso solo non e' un segnale: e' la SEPARAZIONE a esserlo."""

    def test_dice_il_tasso_dei_topic_affollati(self, monkeypatch, affollato):
        ch = _check(monkeypatch, affollato)
        assert "2/4" in ch["detail"], ch["detail"]

    def test_dice_ANCHE_la_popolazione_opposta(self, monkeypatch, affollato):
        """Senza il gruppo di controllo il 50% non si sa se e' alto."""
        ch = _check(monkeypatch, affollato)
        assert "5/5" in ch["detail"], ch["detail"]


class TestDiceDoveEQuando:

    def test_nomina_il_topic_peggiore(self, monkeypatch, affollato):
        ch = _check(monkeypatch, affollato)
        assert "t/audit" in ch["detail"], ch["detail"]

    def test_dichiara_la_finestra(self, monkeypatch, affollato):
        """Una quota sul corpus senza il periodo si legge sbagliata."""
        ch = _check(monkeypatch, affollato)
        assert "7 days" in ch["detail"], ch["detail"]


class TestNonPretendeDiSapereCioCheNonSa:

    def test_dichiara_di_non_distinguere_l_aggiornamento(self, monkeypatch,
                                                         affollato):
        testo = (_check(monkeypatch, affollato)["fix"] or "")
        assert "legitimate" in testo.lower(), testo

    def test_su_un_corpus_sano_non_inventa_un_rapporto(self, monkeypatch,
                                                       uno_per_topic):
        """Zero su zero non e' «zero per cento»."""
        ch = _check(monkeypatch, uno_per_topic)
        assert ch is not None and ch["status"] == doctor.OK, ch
        assert "%" not in ch["detail"], ch["detail"]


@pytest.fixture
def solo_affollati(tmp_path):
    """IL CORPUS DELL'UTENTE NUOVO: due scritture, un topic solo, una ritirata.

    Non e' un caso di laboratorio: e' cio' che ha chiunque abbia appena
    cominciato — o chi estrae due fatti da un solo documento (misurato il
    29/08: due annualita' dello stesso contratto, e alla domanda sul 2025 il
    recall risponde col 2026). Qui il gruppo di controllo NON ESISTE."""
    d = tmp_path / "utente_nuovo"
    _store(d, [("a1", "t/canone", "a2"), ("a2", "t/canone", None)])
    return d


class TestSenzaGruppoDiControlloIlCheckTACE:
    """LA CECITA' E' DELIBERATA E GIUSTA — ma nessuno la dichiarava.

    `doctor.py` pone il tasso di controllo UGUALE a quello dei topic affollati
    quando i topic a scrittura singola sono assenti (`_rs = _vs / _ns if _ns
    else _ra`), quindi `_ra < _rs` e' falso e il livello resta OK. Il commento
    accanto ne da' la ragione, ed e' la disciplina che il registro predica:
    «la SEPARAZIONE e' il segnale: senza il gruppo di controllo un tasso non si
    sa se e' alto».

    ⚖️ Questa classe NON presidia un difetto: presidia una SCELTA, e la rende
    visibile. Le due fixture che c'erano coprivano «affollati PIU' singoli» e
    «solo singoli»; il terzo caso — SOLO affollati — non era presidiato, ed e'
    proprio quello in cui il check non puo' parlare.

    🔑 Perche' scriverlo: la cecita' cade sull'utente NUOVO, cioe' nella
    finestra in cui prende le abitudini che poi gli costeranno i fatti. Se un
    giorno qualcuno decide di far parlare il check anche senza controllo,
    questo test diventa rosso e chiede di aggiornare la scelta invece di
    lasciarla cambiare di nascosto."""

    def test_il_check_esiste_anche_qui(self, monkeypatch, solo_affollati):
        assert _check(monkeypatch, solo_affollati) is not None

    def test_NON_avvisa_perche_manca_la_popolazione_opposta(
            self, monkeypatch, solo_affollati):
        ch = _check(monkeypatch, solo_affollati)
        assert ch["status"] == doctor.OK, (
            "il check ha avvisato senza gruppo di controllo: o la scelta e' "
            f"cambiata, e allora aggiorna questa classe, oppure e' un difetto. {ch}")

    def test_il_dettaglio_dice_comunque_la_perdita(self, monkeypatch,
                                                  solo_affollati):
        """Il dato c'e' anche quando il livello tace: e' l'unica cosa che
        l'utente nuovo puo' leggere, e va conservata."""
        ch = _check(monkeypatch, solo_affollati)
        assert "1/2" in ch["detail"], ch["detail"]
        assert "t/canone" in ch["detail"], ch["detail"]

    def test_il_gruppo_di_controllo_e_dichiarato_vuoto(self, monkeypatch,
                                                      solo_affollati):
        """⚠️ QUI IL PRESIDIO E' DEBOLE DI PROPOSITO, e lo dichiaro.

        Oggi il testo stampa «against 0/0 on topics used once», che si legge
        come «zero perdite nell'altro gruppo» invece che «l'altro gruppo non
        esiste». Il test accetta ENTRAMBE le forme: quella di oggi e una frase
        che dica l'assenza. Cosi' non blocca chi vuole migliorare la
        formulazione, ma si accorge se il conteggio dell'altro gruppo sparisce
        del tutto."""
        det = _check(monkeypatch, solo_affollati)["detail"].lower()
        assert ("0/0" in det or "no control" in det or "nessun" in det), det
