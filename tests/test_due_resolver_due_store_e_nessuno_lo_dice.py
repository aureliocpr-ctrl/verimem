"""La diagnosi può guardare uno store diverso da quello in cui il prodotto scrive.

Assegnato a ws7 da ws3 dopo la fetta ⑥ («l'import inchioda il percorso dello
store, ed è la causa del difetto env-dopo-import segnalato da ws6»).
**Misurato: la causa non è l'import che scrive nell'ambiente — è che ci sono DUE
resolver del percorso dati e danno risposte diverse nello stesso processo.**

Eseguito in un processo pulito, importando tutto PRIMA e impostando la cartella
DOPO (cioè ciò che fa chiunque incorpori verimem come libreria, e ogni banco)::

    PRIMA (nessuna variabile impostata)
       _compat.data_dir()  = C:\\Users\\aurel\\.engram
       CONFIG.data_dir     = C:\\Users\\aurel\\.engram

    DOPO  HIPPO_DATA_DIR = /tmp/tmp.XOPKsjMKaK
       _compat.data_dir()  = \\tmp\\tmp.XOPKsjMKaK      <- legge l'ambiente ORA
       CONFIG.data_dir     = C:\\Users\\aurel\\.engram   <- congelato all'import
       SemanticMemory().db_path = C:\\Users\\aurel\\.engram\\semantic\\semantic.db
       COINCIDONO: False

=== LO SWEEP: chi legge quale ===
    resolver VIVO (`_compat.data_dir`)   : backup · cli · config · dashboard_routes.auth
                                           · doctor · event_jsonl_log · flow_events
    CONFIG CONGELATO                     : audit_tail · backup · cli · curate_pipeline
                                           · dashboard_overview · doctor · documents
                                           · dream · entity_kg · mcp_server · memory …
🔴 **`backup.py`, `cli.py` e `doctor.py` usano ENTRAMBI**: dentro lo stesso
modulo due righe possono puntare a due store diversi.

=== PERCHÉ TOCCA A ME, e su quale popolazione ===
`doctor` è la superficie che dovrebbe dire cosa non va, e usa il resolver VIVO
mentre il prodotto scrive dove dice CONFIG. **Può quindi diagnosticare uno store
e lasciare che se ne usi un altro, senza dirlo.**
⚖️ **Popolazione**: non capita a chi lancia la CLI (l'ambiente è impostato prima
dell'import). Capita a **chi incorpora verimem come libreria e si configura
dopo**, a **chi cambia inquilino a processo vivo**, e a **ogni banco che
monkeypatcha l'ambiente** — è così che l'ho incontrato ieri, e il fatto che sia
un caso di sviluppo non lo rende meno reale: ieri mi ha fatto sparire un check
e ho perso mezz'ora a capire perché.

=== LA CURA CHE SCELGO, e quella che NON scelgo ===
⛔ NON faccio scegliere a `doctor` uno dei due: nasconderebbe la divergenza.
✅ `doctor` la **DICHIARA**. È la stessa forma del resto di questa superficie —
«un'assenza è utile solo se dice dove», «un rango ignoto non è un rango basso»:
quando due fonti non concordano, **il fatto che non concordino È la diagnosi.**
"""
from __future__ import annotations

import pytest

from verimem import doctor


def _check(nome="data-dir"):
    for ch in doctor.run_doctor():
        if ch["name"] == nome:
            return ch
    raise AssertionError(f"il check `{nome}` non c'e'")


class TestLaDivergenzaSiDICHIARA:

    def test_quando_i_due_resolver_discordano_il_doctor_lo_dice(
            self, tmp_path, monkeypatch):
        """IL ROSSO. `CONFIG` è già costruito (import di modulo), quindi
        impostare la cartella adesso crea esattamente la divergenza reale."""
        nuova = tmp_path / "altrove"
        nuova.mkdir()
        monkeypatch.setenv("HIPPO_DATA_DIR", str(nuova))
        monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
        monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)

        from verimem._compat import data_dir
        from verimem.config import CONFIG
        assert str(data_dir()) != str(CONFIG.data_dir), (
            "premessa del banco caduta: i due resolver concordano")

        det = _check()["detail"]
        assert str(CONFIG.data_dir) in det, (
            "la diagnosi non nomina lo store in cui il prodotto SCRIVE: " + det)

    def test_dice_QUALE_dei_due_usa_il_prodotto(self, tmp_path, monkeypatch):
        """Sapere che divergono non basta: chi legge deve sapere dove finiranno
        i suoi dati."""
        nuova = tmp_path / "altrove2"
        nuova.mkdir()
        monkeypatch.setenv("HIPPO_DATA_DIR", str(nuova))
        monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
        monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
        det = _check()["detail"].lower()
        assert "write" in det or "scriv" in det, det

    def test_non_e_un_FAIL(self, tmp_path, monkeypatch):
        """Un avviso, non un guasto: i dati ci sono, sono in due posti e uno dei
        due non è quello che stai guardando. Un FAIL manderebbe a cercare una
        corruzione che non c'è."""
        nuova = tmp_path / "altrove3"
        nuova.mkdir()
        monkeypatch.setenv("HIPPO_DATA_DIR", str(nuova))
        assert _check()["status"] != doctor.FAIL


class TestPresidio:

    def test_quando_concordano_nessun_rumore(self, monkeypatch):
        """PRESIDIO: nel caso normale — l'ambiente impostato PRIMA dell'import,
        cioè ogni uso da riga di comando — la riga non deve cambiare. Un avviso
        che compare sempre si impara a ignorare."""
        from verimem.config import CONFIG
        monkeypatch.setenv("HIPPO_DATA_DIR", str(CONFIG.data_dir))
        monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
        monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
        ch = _check()
        assert ch["status"] == doctor.OK, ch["detail"]
        for parola in ("diverge", "differs", "mismatch"):
            assert parola not in ch["detail"].lower(), ch["detail"]

    def test_e_diverso_dall_avviso_sui_TRE_PREFISSI(self, tmp_path,
                                                    monkeypatch):
        """FALSIFICAZIONE: esiste già un avviso per quando VERIMEM_/ENGRAM_/
        HIPPO_DATA_DIR discordano fra loro. È un difetto DIVERSO — lì il
        disaccordo è fra tre variabili, qui fra due modi di risolverle — e
        confonderli farebbe sparire questo dentro quello.
        Qui i tre prefissi concordano e la divergenza resta."""
        nuova = tmp_path / "altrove4"
        nuova.mkdir()
        for k in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
            monkeypatch.setenv(k, str(nuova))
        from verimem._compat import data_dir
        from verimem.config import CONFIG
        assert str(data_dir()) == str(nuova)          # i tre concordano
        assert str(CONFIG.data_dir) != str(nuova)     # e la divergenza c'e'
        assert str(CONFIG.data_dir) in _check()["detail"]
