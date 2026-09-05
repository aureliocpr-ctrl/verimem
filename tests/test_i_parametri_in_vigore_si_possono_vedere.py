"""Chi installa non può sapere quali valori sono in vigore.

Verdetto della fetta ⑥ del 2026-08-08 (`docs/stato-reale/06-…`, commit
`5b417ccd`), assegnato a ws7 per la cura: *«i parametri esistono e funzionano,
ma non sono ISPEZIONABILI»*. Misurato allora:

* **173** variabili d'ambiente lette dal codice, di cui **5** passano da
  `config.py`; le altre 168 sono lette inline in ~40 moduli;
* **194** soglie numeriche, **181** fisse nel sorgente;
* `verimem doctor` — l'unica superficie di diagnosi — **non nomina né la soglia
  in vigore né una sola variabile impostata**. Provato eseguendo con
  `ENGRAM_SUPERSEDE_SAME_SOURCE=0` (che secondo il nostro archivio fa smettere
  la memoria di aggiornarsi): non compare.

=== E C'È UN NODO CHE VA SCIOLTO PRIMA, altrimenti la cura mente ===
`_compat.init_env_aliases()` **specchia** ogni `ENGRAM_X` in `HIPPO_X` e
`VERIMEM_X` all'import: misurato, 8 variabili prima e 21 dopo. Quindi una
diagnosi che elencasse `os.environ` presenterebbe come «impostate
dall'operatore» tredici variabili **che ha creato la libreria**.

🔗 La funzione **restituisce già il numero** di specchiature fatte («*Returns
the number of mirror entries added (for tests / introspection)*») e **butta via
quali**. È la classe che questo progetto paga di più: la capacità c'era e
mancava il collegamento. Qui basta ricordarsi i NOMI.

⚠️ E non è un dettaglio estetico: il docstring di `_ALIAS_DATA_DIR`, nello
stesso file, racconta un incidente del 2026-07-30 in cui **una variabile creata
dal mirror ha scavalcato quella scelta dall'operatore** e il prodotto scriveva
in uno store e leggeva da un altro.
"""
from __future__ import annotations

import pytest

from verimem import _compat, doctor


@pytest.fixture
def ambiente(monkeypatch):
    """Un ambiente PULITO: nessuna variabile del prodotto."""
    for k in list(__import__("os").environ):
        if k.startswith(("VERIMEM_", "ENGRAM_", "HIPPO_")):
            monkeypatch.delenv(k, raising=False)
    return monkeypatch


class TestLoSpecchioSiRICORDACosaHaCreato:

    def test_dichiara_i_NOMI_non_solo_il_numero(self, ambiente):
        ambiente.setenv("ENGRAM_PROVA_UNO", "x")
        _compat.init_env_aliases()
        creati = _compat.alias_creati()
        assert "HIPPO_PROVA_UNO" in creati, creati
        assert "VERIMEM_PROVA_UNO" in creati, creati

    def test_cio_che_ha_impostato_l_OPERATORE_non_e_fra_i_creati(self,
                                                                 ambiente):
        """LA DISTINZIONE CHE SERVE: se il mirror non la facesse, una diagnosi
        presenterebbe come scelta dell'utente ciò che ha creato la libreria."""
        ambiente.setenv("ENGRAM_PROVA_DUE", "x")
        _compat.init_env_aliases()
        assert "ENGRAM_PROVA_DUE" not in _compat.alias_creati()

    def test_una_variabile_gia_presente_non_viene_contata_come_creata(
            self, ambiente):
        """FALSIFICAZIONE: lo specchio usa la semantica di `setdefault`, quindi
        se l'operatore ha impostato ENTRAMBE le forme non ne crea nessuna — e
        non deve dichiararle sue."""
        ambiente.setenv("ENGRAM_PROVA_TRE", "x")
        ambiente.setenv("HIPPO_PROVA_TRE", "y")
        _compat.init_env_aliases()
        assert "HIPPO_PROVA_TRE" not in _compat.alias_creati()

    def test_il_conteggio_storico_continua_a_funzionare(self, ambiente):
        """PRESIDIO: la funzione rendeva un numero e c'è chi lo usa."""
        ambiente.setenv("ENGRAM_PROVA_QUATTRO", "x")
        n = _compat.init_env_aliases()
        assert isinstance(n, int) and n >= 2


class TestIlDoctorDiceLaSogliaInVigore:

    def _check(self, monkeypatch, nome="parameters"):
        # ⚠️ IL REGIME SI FORZA, NON SI SPERA (stessa lezione del file gemello
        # `test_il_doctor_dichiara_ENTRAMBE_le_soglie.py`): il giudice in vigore
        # lo decide `_autodetect_provider()` DALL'AMBIENTE, e una chiave di un
        # provider esterno presente nel processo (in CI c'e', e la guardia di
        # conftest protegge solo VERIMEM_/ENGRAM_/HIPPO_) lo sposta su quel
        # provider: la soglia diventa 70 e questa classe cadeva su 4 job del run
        # 33993804265 (06/09) mentre era verde su ogni macchina di sviluppo.
        # Qui si chiede «la soglia col giudice LOCALE», quindi le chiavi esterne
        # si tolgono per la durata del test.
        from verimem import llm as _llm
        for _spec in getattr(_llm, "PROVIDERS", {}).values():
            _k = (_spec or {}).get("env")
            if _k:
                monkeypatch.delenv(_k, raising=False)
        for _k in ("ANTHROPIC_API_KEY", "OLLAMA_HOST"):
            monkeypatch.delenv(_k, raising=False)
        for ch in doctor.run_doctor():
            if ch["name"] == nome:
                return ch
        raise AssertionError("il check `parameters` non c'e'")

    def test_il_check_esiste(self, monkeypatch):
        assert self._check(monkeypatch) is not None

    def test_dice_la_soglia_di_ammissione_EFFETTIVA(self, monkeypatch):
        """È il numero che decide cosa entra in memoria, e non compariva in
        nessuna superficie. Vale 40 col giudice locale e 70 con gli altri."""
        from verimem.grounding_gate import resolve_write_threshold_for
        det = self._check(monkeypatch)["detail"]
        atteso = f"{resolve_write_threshold_for('local'):.0f}"
        assert atteso in det, det
        # ⚠️ «40» come sottostringa non basta: in locale compariva dentro
        # ENGRAM_BRIEFING_THRESHOLD=0.40 e il test passava anche col doctor
        # che diceva «70/100, decided by the openai judge» (06/09, run
        # 33993804265 rosso su 4 job, verde su ogni macchina di sviluppo).
        assert "decided by the `local` judge" in det, det

    def test_dice_QUALE_giudice_decide_quella_soglia(self, monkeypatch):
        """Senza, il numero non si può interpretare: la stessa installazione
        ammette a 40 o a 70 a seconda del giudice disponibile."""
        det = self._check(monkeypatch)["detail"].lower()
        assert "judge" in det or "giudice" in det, det


class TestIlDoctorDiceCosaEImpostato:

    def _check(self, monkeypatch):
        for ch in doctor.run_doctor():
            if ch["name"] == "parameters":
                return ch
        raise AssertionError("il check `parameters` non c'e'")

    def test_nomina_una_variabile_che_l_operatore_ha_impostato(
            self, ambiente):
        ambiente.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "0")
        _compat.init_env_aliases()
        det = self._check(ambiente)["detail"]
        assert "SUPERSEDE_SAME_SOURCE" in det, det

    def test_NON_conta_come_impostate_quelle_create_dallo_specchio(
            self, ambiente):
        """Il punto di tutto: con UNA variabile impostata dall'operatore, lo
        specchio ne crea altre due. La diagnosi deve dire UNA."""
        ambiente.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "0")
        _compat.init_env_aliases()
        det = self._check(ambiente)["detail"]
        assert det.count("SUPERSEDE_SAME_SOURCE") == 1, det

    def test_su_ambiente_pulito_lo_dice_invece_di_tacere(self, ambiente):
        """Un check che sparisce quando non ha niente da dire lascia il dubbio
        fra «non c'è niente» e «non ha guardato»."""
        ch = self._check(ambiente)
        assert ch["status"] == doctor.OK
        assert ch["detail"], ch

    def test_NON_STAMPA_il_valore_di_un_segreto(self, ambiente):
        """FALSIFICAZIONE: una diagnosi che perde una chiave è peggio di
        nessuna diagnosi. Il nome sì, il valore mai."""
        ambiente.setenv("ENGRAM_AUTH_TOKEN", "segretissimo-123")
        ambiente.setenv("HIPPO_API_KEY", "sk-parola-magica")
        _compat.init_env_aliases()
        det = self._check(ambiente)["detail"] + (self._check(ambiente).get("fix") or "")
        assert "segretissimo-123" not in det, det
        assert "sk-parola-magica" not in det, det
        assert "AUTH_TOKEN" in det, "il NOME va detto: è un parametro in vigore"
