"""All'avvio il server deve DIRE se scaldera' il giudice, e come cambiarlo.

Oggi non lo dice. ``_warm_moat_judge`` scrive
``mcp_preload_moat_judge_complete`` solo QUANDO parte: se
``_deve_scaldare_il_giudice()`` e' falso — e lo e' per chi non ha messo
``ENGRAM_GROUNDING_WRITE``, cioe' il caso normale — all'avvio non compare
NESSUNA riga. Chi legge il log non sa che il modello non verra' scaldato, non
sa che la prima scrittura con fonte se lo carichera' addosso, e non sa quale
variabile lo cambia.

E' la forma «una capacita' spenta non emette segnale»: il silenzio si legge
come «tutto a posto».

IL COSTO, misurato il 2026-09-06 nel venv del pacchetto (torch 2.14.0+cpu,
modello presente in ``~/.engram/models/local_gate_ce_v2``):

    RSS dopo-import-preload  =   18.0 MB
    RSS dopo-warm-giudice    =  504.3 MB      -> +486 MB per processo
    WARM-SECONDI = 12.7 (modello caldo) · 40.1 (primo giro, freddo)
    SCORER=True    <- il warm era davvero avvenuto

E' lo stesso ordine di grandezza dei ~450 MB dell'incidente RAM del 2026-07-10
citato in ``preload.py``. Percio' la riga di log non e' cosmetica: e' l'unico
posto dove un operatore puo' vedere che quel mezzo giga sta per essere comprato
(o che non lo sara', e cosa gli costera' invece).

⚠️ QUESTO TEST NON DECIDE IL DEFAULT. Vale identico che il default sia acceso o
spento: pretende solo che l'avvio DICHIARI quale dei due e' in vigore e come
uscirne. La scelta del default e' del lead (VIA 06/09 02:44) e sta in un altro
commit.

⚠️ NESSUN MODELLO VIENE CARICATO QUI: i thread sono finti (vedi ``_ThreadFinto``),
quindi il preload arriva in fondo senza toccare embedder, reranker o giudice.
Il thread ``hippo-embedding-preload`` registrato e' il CONTROLLO POSITIVO che
la funzione sia arrivata in fondo davvero, invece di uscire presto e lasciare
il test verde per il motivo sbagliato.
"""
import pytest

from verimem import preload


class _LogFinto:
    """Raccoglie evento + kwargs, come structlog li riceve."""

    def __init__(self) -> None:
        self.righe: list[tuple[str, dict]] = []

    def info(self, evento, **kw):
        self.righe.append((evento, kw))

    def warning(self, evento, **kw):
        self.righe.append((evento, kw))

    def error(self, evento, **kw):
        self.righe.append((evento, kw))

    def testo(self) -> str:
        pezzi = []
        for evento, kw in self.righe:
            pezzi.append(str(evento))
            for k, v in kw.items():
                pezzi.append(f"{k}={v}")
        return " ".join(pezzi)


class _ThreadFinto:
    """Registra il thread che SAREBBE partito, senza farlo partire."""

    partiti: list[str] = []

    def __init__(self, *a, **kw):
        self._nome = kw.get("name", "?")

    def start(self):
        _ThreadFinto.partiti.append(self._nome)

    def join(self, *a, **kw):
        return None


@pytest.fixture()
def avvio(monkeypatch):
    """Fa girare `preload_embedding` senza caricare un solo modello."""
    _ThreadFinto.partiti = []
    monkeypatch.setattr(preload.threading, "Thread", _ThreadFinto)
    # niente daemon, niente delegate-only: non c'entrano con la dichiarazione
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    monkeypatch.setenv("HIPPO_EAGER_PRELOAD", "1")
    monkeypatch.setenv("HIPPO_PRELOAD_BACKGROUND", "1")
    log = _LogFinto()

    def _esegui() -> _LogFinto:
        preload.preload_embedding(log=log)
        assert "hippo-embedding-preload" in _ThreadFinto.partiti, (
            "il preload non e' arrivato in fondo: il banco non sta misurando "
            f"quello che dice. Thread visti: {_ThreadFinto.partiti}")
        return log

    return _esegui


def test_se_non_scalda_il_giudice_l_avvio_lo_dice_e_dice_come_accenderlo(
        avvio, monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    assert preload._deve_scaldare_il_giudice() is False, (
        "questo caso presuppone il giudice NON scaldato; se il default e' "
        "cambiato, il test va aggiornato di conseguenza (non cancellato)")

    log = avvio()
    testo = log.testo()

    assert "moat_judge" in testo or "giudice" in testo, (
        "all'avvio non c'e' NESSUNA riga sul giudice quando non verra' "
        "scaldato: chi legge il log non sa che la prima scrittura con fonte se "
        "lo carichera' addosso (misurato: 12,7 s caldo, 40,1 s freddo). Il "
        f"silenzio si legge come «tutto a posto». Righe viste: {log.righe}")
    assert "ENGRAM_GROUNDING_WRITE" in testo, (
        "la riga non nomina la variabile che cambia il comportamento: senza, "
        "l'operatore vede un fatto e non una leva. Il VIA del 06/09 02:44 la "
        f"chiede «dichiarata nel log di avvio». Righe viste: {log.righe}")


def test_se_scalda_il_giudice_l_avvio_dichiara_il_costo(avvio, monkeypatch):
    """L'altro ramo: quando il modello VIENE comprato, il log dice quanto."""
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    assert preload._deve_scaldare_il_giudice() is True

    log = avvio()
    testo = log.testo()

    assert "moat_judge" in testo or "giudice" in testo, (
        f"nessuna riga sul giudice mentre lo si sta scaldando: {log.righe}")
    assert "486" in testo, (
        "l'avvio non dice quanto costa il modello che sta per caricare "
        "(+486 MB per processo, misurato il 06/09 su torch 2.14.0+cpu: RSS "
        "18,0 -> 504,3). E' lo stesso ordine di grandezza dell'incidente RAM "
        "del 2026-07-10 che ha prodotto il flag: se il numero non e' nel log, "
        f"lo paga chi non sa di pagarlo. Righe viste: {log.righe}")
