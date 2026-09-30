"""Il motivo di un rifiuto appartiene alla CHIAMATA che l'ha ricevuto, non al processo.

LO STATO CONDIVISO. `embedding._encode_via_service` conserva il motivo del rifiuto in due
globali di modulo (`_ULTIMO_RIFIUTO`, `_ULTIMO_RIFIUTO_MIO`): le azzera all'inizio di ogni
chiamata, e `_encode_one` le rilegge subito dopo. Fra quelle due righe il motivo e' di tutti:

  · fra due TEST: la cella del rifiuto lo lascia pieno, e quella che parte dopo lo trova
    sporco (il rosso d'ordine del 29/09: seme 3608823368, «1 failed, 3 passed»);
  · fra due RICHIESTE nello stesso processo (il server MCP, il gateway): la chiamata B
    azzera il motivo della chiamata A prima che A lo legga, e l'utente di A riceve
    «unavailable» su un daemon che gli aveva detto perche' — la diagnosi falsa che
    `test_il_daemon_dice_perche_e_il_prodotto_lo_ripete.py` esiste per impedire.

Ripulire la globale fra un test e l'altro spegne il primo sintomo e lascia il secondo. La
cura e' togliere la globale: il motivo viaggia con la risposta della chiamata.

LA PROVA. Due fili, e l'intreccio si FISSA invece di sperarlo: A riceve il rifiuto del daemon
(CUDA); nel punto fra la chiamata al servizio e la lettura del motivo (`_delegate_only`, che
`_encode_one` interroga proprio li') A aspetta che B finisca una chiamata a un daemon che non
c'e' (scoperta assente). Poi A solleva il suo errore: deve contenere CUDA.

CONTROLLO: lo stesso banco senza B. Se li' il motivo non arriva, e' rotto il banco, non il
prodotto.
"""
from __future__ import annotations

import threading

import pytest

from verimem import embedding as E
from verimem import encode_service as svc

MOTIVO = "AcceleratorError: CUDA error: unknown error"


class _ConnFinta:
    """Una connessione che non parla con nessuno: la risposta la decide il test."""

    def settimeout(self, _s) -> None:
        pass

    def close(self) -> None:
        pass


@pytest.fixture()
def due_chiamanti(monkeypatch):
    """Per il filo A il daemon c'e' e rifiuta col suo motivo; per il filo B non c'e'."""
    import socket as _s

    def scoperta():
        if threading.current_thread().name == "B":
            return None
        return {"host": "127.0.0.1", "port": 55587,
                "model": E.CONFIG.embedding_model, "token": "x"}

    monkeypatch.setattr(svc, "read_discovery", scoperta)
    monkeypatch.setattr(E, "_service_enabled", lambda: True)
    monkeypatch.setattr(_s, "create_connection", lambda *a, **k: _ConnFinta())
    monkeypatch.setattr(svc, "send_msg", lambda *a, **k: None)
    monkeypatch.setattr(svc, "recv_msg", lambda *a, **k: {"ok": False, "error": MOTIVO})
    # il ramo che solleva vive dietro `_delegate_only() and not is_loaded()`: si fissa
    monkeypatch.setattr(E, "is_loaded", lambda: False)


def _messaggio_di_a(monkeypatch, *, b_in_mezzo: bool) -> str:
    """Il messaggio che l'utente del filo A riceve; B passa nel mezzo se richiesto."""

    def delegate_only() -> bool:
        if b_in_mezzo and threading.current_thread().name == "A":
            filo_b = threading.Thread(target=lambda: E._encode_via_service("b"), name="B")
            filo_b.start()
            filo_b.join(timeout=30)
            assert not filo_b.is_alive(), "il filo B non ha finito: banco appeso"
        return True

    monkeypatch.setattr(E, "_delegate_only", delegate_only)
    esito: dict[str, str] = {}

    def chiamata_a() -> None:
        try:
            E._encode_one("a")
            esito["messaggio"] = "NESSUN ERRORE: _encode_one e' tornato"
        except E.EncodeDelegateUnavailable as exc:
            esito["messaggio"] = str(exc)

    filo_a = threading.Thread(target=chiamata_a, name="A")
    filo_a.start()
    filo_a.join(timeout=60)
    assert not filo_a.is_alive(), "il filo A non ha finito: banco appeso"
    return esito.get("messaggio", "")


def test_controllo_senza_una_chiamata_in_mezzo_il_motivo_arriva(due_chiamanti,
                                                                 monkeypatch) -> None:
    messaggio = _messaggio_di_a(monkeypatch, b_in_mezzo=False)
    assert "CUDA" in messaggio, (
        f"banco rotto: anche senza intreccio il motivo non arriva: {messaggio!r}")


def test_una_chiamata_in_mezzo_non_cancella_il_motivo_di_un_altra(due_chiamanti,
                                                                   monkeypatch) -> None:
    messaggio = _messaggio_di_a(monkeypatch, b_in_mezzo=True)
    assert "CUDA" in messaggio, (
        "la chiamata B ha azzerato il motivo della chiamata A prima che A lo leggesse: "
        f"l'utente di A legge {messaggio!r} su un daemon che gli aveva detto perche'")
