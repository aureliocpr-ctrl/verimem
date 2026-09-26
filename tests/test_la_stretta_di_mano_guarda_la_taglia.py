"""T86 — la stretta di mano col daemon guarda il NOME e non la TAGLIA.

MISURATO ALLA PORTA il 2026-09-13, store isolato e daemon finto (nessun modello
caricato, nessuna scrittura sullo store vero)::

    === dichiara giusto, SERVE 384 ===
        encode alla porta  : vettore di lunghezza 384  (byte attesi: 3072, questo ne fa 1536)
        store() dice       : None   (nessuna eccezione)
        sul disco          : [(1536, 'intfloat/multilingual-e5-base')]
        recall() TORNA     : 0 fatti  []

Il fatto entra, l'etichetta `embedding_model` dice il modello GIUSTO — e il
vettore e' di un altro. Il filtro del recall (`length(embedding) = ?`) lo esclude
in silenzio: nessun errore, nessun avviso, e chi ha scritto crede di aver
scritto. E' il «vettore muto».

⚠️ LA GUARDIA CHE C'E' GUARDA IL NOME: ``embedding.py`` rifiuta un daemon che
DICHIARA un modello diverso da quello di CONFIG, e quella meta' funziona (il
controllo positivo di questo file lo esercita). Ma di cio' che il daemon SERVE
non guarda niente: un daemon che dichiara giusto e serve un'altra taglia passa.

⚠️ E IL CONFRONTO GIUSTO ESISTE GIA' NEL PRODOTTO: ``vettore_compatibile()``
(`embedding.py`) chiede esattamente ``len(vec) * 4 == expected_embedding_bytes()``.
Mancava chi lo chiamasse sul vettore che arriva dal daemon — per questo la cura
non ne scrive una sesta copia, chiama quella.

⚠️ LA CELLA CHE DEVE RESTARE VERDE: quando la dimensione di CONFIG e' una
ASSUNZIONE (modello sconosciuto, nessun `HIPPO_EMBEDDING_DIM` fissato), il
prodotto ADOTTA la taglia osservata dal daemon — e' la cura iter 31/32 contro il
recall vuoto silenzioso. Quella non si tocca: rifiutare li' renderebbe muto un
daemon sano. La taglia si pretende solo quando la si CONOSCE.
"""
from __future__ import annotations

import json
import socket
import threading

import pytest

from verimem import embedding
from verimem import encode_service as svc
from verimem.config import CONFIG

FRASE = "una frase qualunque, che non conta"


@pytest.fixture
def dimensione_conosciuta():
    """CONFIG dichiara 768 e NON e' un'assunzione: il regime dello store vero."""
    vecchi = (CONFIG.embedding_dim, getattr(CONFIG, "embedding_dim_assumed", False))
    object.__setattr__(CONFIG, "embedding_dim", 768)
    object.__setattr__(CONFIG, "embedding_dim_assumed", False)
    yield
    object.__setattr__(CONFIG, "embedding_dim", vecchi[0])
    object.__setattr__(CONFIG, "embedding_dim_assumed", vecchi[1])


class _DaemonFinto:
    """Parla il protocollo di `encode_service` e serve la taglia che gli dico.

    ⚠️ Un socket VERO, non un doppio di `send_msg`: il pezzo che questa cura
    tocca e' proprio quello che legge la risposta dal filo, e un doppio piu' in
    alto salterebbe la riga da verificare.
    """

    def __init__(self, dim: int, dichiara: str):
        self.dim, self.dichiara = dim, dichiara
        self._s = socket.socket()
        self._s.bind(("127.0.0.1", 0))
        self._s.listen(8)
        self.porta = self._s.getsockname()[1]
        self._fermo = False
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while not self._fermo:
            try:
                conn, _ = self._s.accept()
            except OSError:
                return
            try:
                svc.recv_msg(conn)
                v = [0.0] * self.dim
                v[0] = 1.0
                svc.send_msg(conn, {"ok": True, "vec": v, "model": self.dichiara})
            except Exception:  # noqa: BLE001 — un finto non rompe la cella
                pass
            finally:
                conn.close()

    def chiudi(self):
        self._fermo = True
        self._s.close()


@pytest.fixture
def daemon(monkeypatch):
    """Restituisce una fabbrica: `daemon(dim, dichiara=...)` lo accende e lo
    rende scopribile. La scoperta si FISSA — mai il file della macchina."""
    vivi: list[_DaemonFinto] = []

    def _accendi(dim: int, dichiara: str | None = None) -> _DaemonFinto:
        d = _DaemonFinto(dim, dichiara or CONFIG.embedding_model)
        vivi.append(d)
        monkeypatch.setattr(svc, "read_discovery", lambda *a, **k: {
            "pid": 1, "port": d.porta, "host": "127.0.0.1", "model": d.dichiara})
        monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
        embedding._cached_encode.cache_clear()
        return d

    yield _accendi
    for d in vivi:
        d.chiudi()


def test_il_vettore_della_taglia_sbagliata_e_RIFIUTATO(
        dimensione_conosciuta, daemon):
    """IL CUORE: 384 valori dove lo store ne pretende 768 non e' un vettore
    utilizzabile, e passarlo a valle e' scrivere un fatto che nessuno rileggera'."""
    daemon(384)

    vec = embedding._encode_via_service(FRASE)

    assert vec is None, (
        f"il client ha ACCETTATO un vettore di {0 if vec is None else len(vec)} "
        f"valori dove ne servono {CONFIG.embedding_dim}: quel fatto entra nello "
        f"store e il filtro del recall lo esclude in silenzio")


def test_chi_rifiuta_lo_DICE_e_dice_le_due_taglie(dimensione_conosciuta, daemon):
    """Il motivo si conserva e nomina le due taglie: un «unavailable» su un
    daemon vivo manda a cercare un processo morto, ed e' la stessa classe di
    diagnosi falsa gia' pagata il 06/09."""
    daemon(384)

    embedding._encode_via_service(FRASE)
    motivo = embedding.ultimo_rifiuto_del_client()

    assert motivo, ("il vettore e' stato rifiutato senza dire perche': chi legge "
                    "l'errore non puo' sapere che il daemon serve un'altra taglia")
    assert "384" in motivo and "768" in motivo, motivo


def test_in_delegate_only_l_errore_dice_che_ha_rifiutato_il_CLIENT(
        dimensione_conosciuta, daemon, monkeypatch):
    """⚠️ CHI ha rifiutato, non solo CHE si e' rifiutato. Qui il daemon ha
    risposto e sta benissimo: e' il client a non potersi fidare della risposta.
    Dire «the daemon REFUSED» sarebbe falso su una cosa verificabile."""
    daemon(384)
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    monkeypatch.setattr(embedding, "is_loaded", lambda: False)

    with pytest.raises(embedding.EncodeDelegateUnavailable) as e:
        embedding._encode_one(FRASE)

    testo = str(e.value)
    assert "daemon REFUSED" not in testo, (
        f"l'errore attribuisce al daemon un rifiuto che e' del client: {testo}")
    assert "384" in testo and "768" in testo, testo


def test_il_vettore_della_taglia_GIUSTA_passa(dimensione_conosciuta, daemon):
    """⚠️ IL CONTROLLO POSITIVO, senza il quale «rifiuta sempre» supererebbe le
    celle di sopra."""
    daemon(768)

    vec = embedding._encode_via_service(FRASE)

    assert vec is not None and len(vec) == 768
    assert embedding.ultimo_rifiuto_del_client() is None


def test_il_daemon_che_DICHIARA_un_altro_modello_e_gia_rifiutato(
        dimensione_conosciuta, daemon):
    """⚠️ LA META' CHE GIA' FUNZIONA, e che la cura non deve rompere: qui il
    rifiuto avviene PRIMA di aprire il socket, sul nome dichiarato.

    ⚠️ IL NOME ESTRANEO E' INVENTATO APPOSTA. La prima stesura usava il nome di
    un modello vero — e sotto pytest quel modello E' quello di CONFIG
    (`MiniLM-L12-v2`, dim 384, letto eseguendo), quindi la cella misurava due
    nomi UGUALI e cadeva accusando il prodotto. Il difetto era del banco.
    """
    daemon(768, dichiara="un-modello/che-non-esiste-da-nessuna-parte")

    assert embedding._encode_via_service(FRASE) is None


def test_se_la_dimensione_e_ASSUNTA_la_taglia_osservata_si_ADOTTA(daemon):
    """⚠️ LA CURA PRECEDENTE NON SI TOCCA (iter 31/32): con un modello
    sconosciuto la dimensione di CONFIG e' un'ipotesi, e il primo vettore del
    daemon la CORREGGE. Pretendere la taglia qui renderebbe muto un daemon sano
    — che e' il danno opposto, e piu' grande."""
    vecchi = (CONFIG.embedding_dim, getattr(CONFIG, "embedding_dim_assumed", False))
    object.__setattr__(CONFIG, "embedding_dim", 768)
    object.__setattr__(CONFIG, "embedding_dim_assumed", True)
    try:
        daemon(384)

        vec = embedding._encode_one(FRASE)

        assert vec is not None and len(vec) == 384
        assert CONFIG.embedding_dim == 384, (
            "la dimensione ASSUNTA non e' stata corretta dal vettore osservato: "
            "la cura iter 31/32 e' stata rotta da questa")
    finally:
        object.__setattr__(CONFIG, "embedding_dim", vecchi[0])
        object.__setattr__(CONFIG, "embedding_dim_assumed", vecchi[1])
