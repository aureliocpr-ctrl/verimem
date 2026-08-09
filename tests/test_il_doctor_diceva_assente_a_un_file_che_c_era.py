"""«assente» detto di un file che sta li', con lo stesso nome.

Trovato mentre verificavo un salvataggio contando le righe nel DB: al percorso
ovvio `~/.engram/semantic.db` la tabella `facts` ha ZERO righe, e lo store vero
sta in `~/.engram/semantic/semantic.db` con 8758. Due disposizioni, stesso nome
di file.

=== IL PRODOTTO NON E' D'ACCORDO CON SE STESSO SU DOVE STA LO STORE ===
Cinque moduli risolvono ENTRAMBE le disposizioni e preferiscono la nidificata —
`auto_dream_trigger.py:177-178`, `auto_dream_worker.py:58-59`, `cli.py:2246-2247`,
`corpus_size.py:51-53`, `hooks/pre_tool_use.py:162`. `CONFIG` invece dichiara
solo la nidificata. La disposizione piatta e' quindi una cosa che meta' del
prodotto si aspetta di incontrare.

=== IL DIFETTO, ed e' nella SUPERFICIE DI DIAGNOSI ===
`doctor` stampa `p.name`. Ma `p.name` e' `"semantic.db"` per TUTTE E DUE le
disposizioni: il nome butta via la sottocartella, che e' l'unica cosa che le
distingue. Misurato sul vero, prima della cura::

    piatto      ->  semantic.db (assente)      <- e il file c'e', con un fatto
    nidificato  ->  semantic.db 12.3 KB

E il check complessivo risulta **`ok`**. L'operatore legge «assente», guarda la
cartella, vede `semantic.db`, e conclude che il doctor sbaglia — mentre la cosa
vera da fare e' un'altra: «lo store che hai e' nel tracciato legacy, il prodotto
ne usera' un altro».

🔑 E' la stessa forma della cura che ws3 ha preso su `search` (distinguere «non
trovato» da «trovato ma nascosto») e della famiglia `quarantined_by` /
`trattenuto_da`: **un'assenza e' utile solo se dice DOVE**. Qui, in piu', il
difetto e' nel MISURATORE: l'etichetta che il doctor sceglie non e' in grado di
esprimere la differenza che il doctor sta decidendo.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem import doctor


def _crea_store(p) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT,"
                " superseded_by TEXT, grounding_score REAL, status TEXT)")
    con.execute("INSERT INTO facts VALUES ('a','x',NULL,99.0,'model_claim')")
    con.commit()
    con.close()


@pytest.fixture
def piatto(tmp_path):
    """La disposizione LEGACY: `<dati>/semantic.db`."""
    d = tmp_path / "piatto"
    _crea_store(d / "semantic.db")
    return d


@pytest.fixture
def nidificato(tmp_path):
    """La disposizione CANONICA: `<dati>/semantic/semantic.db`."""
    d = tmp_path / "nidificato"
    _crea_store(d / "semantic" / "semantic.db")
    return d


class TestLaRigaDegliStore:

    def test_il_piatto_non_viene_dichiarato_assente_e_basta(self, piatto):
        """IL ROSSO: c'e' un `semantic.db` con un fatto dentro, e la riga dice
        «assente» senza aggiungere altro."""
        riga = doctor._stores_dichiarati(piatto)
        pezzo = riga.split(",")[0]
        assert "(assente)" not in pezzo, (
            f"dice assente di un file che c'e': {pezzo!r}")

    def test_la_riga_dice_DOVE_e_lo_store_che_ha_trovato(self, piatto):
        """Un'assenza e' utile solo se dice dove: il nome della cartella in cui
        lo store sta davvero deve comparire."""
        riga = doctor._stores_dichiarati(piatto)
        assert str(piatto / "semantic.db") in riga or "semantic.db" in riga
        assert "12" in riga or "KB" in riga, (
            f"non riporta la dimensione dello store trovato: {riga!r}")

    def test_l_etichetta_dichiarata_assente_non_e_il_file_che_c_e(
            self, piatto):
        """L'INVARIANTE, e ci sono arrivato per correzione: **il doctor non deve
        dichiarare assente una stringa che nomina un file presente.**

        Due formalizzazioni sbagliate prima di questa, ed entrambe dicono
        qualcosa. (1) «le due righe devono differire»: passava gia' prima della
        cura, perche' differivano nel suffisso — non misurava niente. (2) «il
        token di percorso deve differire fra le due disposizioni»: e'
        IMPOSSIBILE, il percorso DICHIARATO e' lo stesso in entrambe per
        definizione — chiedevo al prodotto una cosa che non poteva dare, e il
        rosso era mio, non suo.
        Cio' che si puo' pretendere e' questo: l'etichetta che porta «assente»
        non deve coincidere col nome del file che sta li'."""
        etichetta = doctor._stores_dichiarati(piatto).split()[0]
        presente = (piatto / "semantic.db")
        assert presente.is_file()
        assert etichetta != presente.name, (
            f"dichiara assente {etichetta!r}, che e' il nome del file presente")

    def test_presidio_il_nidificato_resta_come_prima(self, nidificato):
        """PRESIDIO: sulla disposizione giusta la cura non deve cambiare il
        VERDETTO — dimensione riportata, nessuna nota di altrove, nessun
        «assente». Il token di percorso invece cambia (`semantic/semantic.db`
        invece di `semantic.db`) ed e' voluto: e' proprio quel token che prima
        non sapeva distinguere le due disposizioni. Lo dichiaro qui invece di
        pretendere una stringa identica, che sarebbe un presidio falso."""
        pezzo = doctor._stores_dichiarati(nidificato).split(",")[0]
        assert "KB" in pezzo
        assert "assente" not in pezzo
        assert "altrove" not in pezzo and "invece" not in pezzo

    def test_la_riga_resta_divisibile_per_virgole(self, piatto):
        """La riga unisce i tre store con «, »: un frammento che contiene una
        virgola spezza il campo. Preso dal mio sondaggio, che tagliava a meta'
        il messaggio nuovo — il difetto era nella cura, non nel prodotto."""
        riga = doctor._stores_dichiarati(piatto)
        assert len(riga.split(", ")) == 3, riga

    def test_falsificazione_se_non_c_e_proprio_niente_resta_assente(
            self, tmp_path):
        """FALSIFICAZIONE: una cura che dice sempre «ce n'e' uno altrove»
        passerebbe le prove sopra ed e' sbagliata. Cartella vuota: assente."""
        vuota = tmp_path / "vuota"
        vuota.mkdir()
        pezzo = doctor._stores_dichiarati(vuota).split(",")[0]
        assert "assente" in pezzo
        assert "/" not in pezzo.replace("semantic/semantic.db", "")


class TestFinoAllaSuperficie:
    """Non basta la funzione: il 04/08 una cura corretta a livello di funzione
    era sbagliata end-to-end, e il 05/08 il contrario. Si misura la riga che
    l'operatore LEGGE."""

    def _check_data_dir(self, monkeypatch, d):
        monkeypatch.setenv("HIPPO_DATA_DIR", str(d))
        monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
        monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
        for ch in doctor.run_doctor():
            if ch["name"] == "data-dir":
                return ch
        raise AssertionError("il check data-dir non c'e' piu'")

    def test_il_check_data_dir_non_dice_assente_a_uno_store_che_c_e(
            self, monkeypatch, piatto):
        ch = self._check_data_dir(monkeypatch, piatto)
        assert "semantic.db (assente)" not in ch["detail"], ch["detail"]

    def test_presidio_end_to_end_il_nidificato_resta_ok(
            self, monkeypatch, nidificato):
        ch = self._check_data_dir(monkeypatch, nidificato)
        assert ch["status"] == "ok"
        assert "semantic.db (assente)" not in ch["detail"], ch["detail"]
