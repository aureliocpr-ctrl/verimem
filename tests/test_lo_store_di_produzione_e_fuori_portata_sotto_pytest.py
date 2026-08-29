"""Sotto pytest, aprire il corpus di produzione deve essere IMPOSSIBILE, non
solo improbabile.

Il `conftest` di oggi pinna quattro nomi di variabile (`HIPPO_DATA_DIR`,
`ENGRAM_DATA_DIR`, `ENGRAM_DIR`, `VERIMEM_DATA_DIR`) perche' quattro volte, in
quattro date diverse, un risolutore ha guardato il nome che nessuno aveva
pinnato e i test hanno scritto nello store reale. Il commento del conftest lo
dice con parole sue: «*Questa e' la quarta: si pinnano TUTTI*».

⇒ Ma pinnare i nomi e' **enumerare le porte**. La quinta porta e' il prossimo
alias che qualcuno introdurra', e la si scoprira' come le altre quattro: da un
danno. La cura strutturale non chiede «quali nomi ho pinnato» ma **«il file che
sto per aprire sta dentro la tmp di questo test?»** — una domanda che si
risponde sul RISULTATO e resta vera per ogni alias futuro, compreso quello che
ancora non esiste.

Questo file e' il presidio di quella domanda. Verifica DUE cose, e servono
entrambe:

  1. la guardia ESISTE ed e' esposta come funzione pubblica del pacchetto;
  2. la guardia DISCRIMINA — respinge un percorso di produzione e lascia
     passare uno di test. Senza il secondo controllo, una guardia che dicesse
     sempre «no» (o sempre «si'») supererebbe il primo a pieni voti.

⚠️ NESSUN test in questo file apre il corpus reale, e nessuno lo scrive: la
guardia si interroga passandole un PERCORSO, che e' una stringa. Riprodurre il
danno per dimostrare che il danno e' possibile sarebbe il modo peggiore di
verificarlo — la domanda «e' successo?» si risponde guardando, non rifacendolo.
"""
from __future__ import annotations

import pathlib

import pytest


def test_la_guardia_esiste_come_funzione_pubblica():
    """RED finche' la guardia non esiste."""
    from verimem.test_isolation import assert_store_isolato  # noqa: F401


def test_la_guardia_respinge_un_percorso_di_produzione(tmp_path):
    """Il corpus vero, passato sotto pytest, deve sollevare."""
    from verimem.test_isolation import assert_store_isolato
    produzione = pathlib.Path.home() / ".engram" / "semantic" / "semantic.db"
    with pytest.raises(RuntimeError) as exc:
        assert_store_isolato(produzione, tmp_root=tmp_path)
    # il messaggio deve dire COSA e' successo e DOVE, non solo «errore»
    testo = str(exc.value)
    assert ".engram" in testo, (
        "il messaggio della guardia non nomina il percorso incriminato: chi "
        f"lo legge non sa cosa correggere. Messaggio: {testo!r}")


def test_la_guardia_lascia_passare_un_percorso_di_test(tmp_path):
    """⛔ CONTROLLO NEGATIVO — senza questo, una guardia che sollevasse SEMPRE
    supererebbe il test qui sopra ed e' inutile: bloccherebbe l'intera suite.

    La prova che la guardia discrimina e' che TOGLIENDO il motivo del veto — un
    percorso dentro la tmp del test invece del corpus reale — il verdetto
    cambi."""
    from verimem.test_isolation import assert_store_isolato
    isolato = tmp_path / "semantic" / "semantic.db"
    assert_store_isolato(isolato, tmp_root=tmp_path)  # non deve sollevare
