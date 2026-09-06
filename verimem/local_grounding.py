"""Local write-gate judge — the distilled CE backend for the grounding gate.

Why this exists: the write-gate's judge (``grounding_gate.fact_grounding_score``)
costs one ``claude -p`` call per candidate fact; headless subscription calls are
moving to paid, so the gate needs a subscription-independent backend. The model is a
cross-encoder fine-tuned on HaluMem ground truth (``benchmark/local_gate_finetune.py``)
with a binary head: sigmoid(logit)*100 on (source_span, fact) — same 0-100 scale as
the claude judge, thresholded by the gate.

Selection is env-gated and OFF by default (``ENGRAM_GROUNDING_BACKEND=local`` to opt
in; anything else = the injected-llm claude path, unchanged). The model directory is
``ENGRAM_LOCAL_GATE_MODEL`` or ``~/.engram/models/local_gate_ce`` and may carry a
``gate_config.json`` written by the fine-tune run ({threshold, focus_budget, ...});
env thresholds always beat the config (see ``grounding_gate.should_store_fact``).

Injection-only testability (house style, like cross_encoder_rerank): the judge takes
an optional ``scorer`` callable so unit tests never load transformers or download a
model; the real model is lazy-loaded on first use, behind a lock (the write path can
be called from multiple threads).
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from verimem.grounding_gate import select_relevant_span

Scorer = Callable[[list[tuple[str, str]]], list[float]]

_ENV_MODEL_DIR = "ENGRAM_LOCAL_GATE_MODEL"
# v2 (2026-07-02) is the shipped model: same HaluMem skill as v1 (heldout AUROC 0.99,
# false-memory admit 0.042 vs v1's 0.086) PLUS the real-corpus register (real-fact
# admit 0.82→0.98, agreement vs claude 0.76→0.88). Trained by distilling the claude
# DECISION on a mixed HaluMem-GT + real-corpus set (benchmark/local_gate_distill_v2.py).
# v1 (local_gate_ce) is kept on disk for comparison. Override with ENGRAM_LOCAL_GATE_MODEL.
#
# NOT under a data dir (~/.verimem, ~/.engram, ~/.hippoagent). `warmup` CREATES this
# path, and `_compat.data_dir()` picks the store by asking which of those exists — so a
# downloadable model would decide where the user's memory lives. Measured 2026-08-15,
# both directions: with the model under ~/.engram a fresh install stops getting the
# ~/.verimem the README promises; with it under ~/.verimem a 1.43 GB ~/.engram store
# drops out of sight. A cache dir is neither, so the resolver keeps its own answer.
DEFAULT_MODEL_DIR = Path.home() / ".cache" / "verimem" / "models" / "local_gate_ce_v2"
# Where warmup used to put it: still read (never written) so an existing install does
# not re-download 746 MB after upgrading.
_LEGACY_MODEL_DIR = Path.home() / ".engram" / "models" / "local_gate_ce_v2"
_DEFAULT_FOCUS_BUDGET = 1500


def _holds_a_model(d: Path) -> bool:
    """True only when the dir actually HOLDS a model — its mere existence is not
    enough: an empty dir is what `from_pretrained` chokes on, and what made the
    availability probe answer yes on nothing at all."""
    return (d / "config.json").is_file()


#: I nomi che `from_pretrained` cerca davvero. Non scelti a intuito: sono i due
#: che il prodotto stesso nomina quando fallisce — «Error no file named
#: model.safetensors, or pytorch_model.bin, found in directory ...».
_NOMI_DEI_PESI = ("model.safetensors", "pytorch_model.bin")


def holds_the_weights(d: Path) -> bool:
    """True quando la cartella tiene anche i PESI, non solo i metadati.

    ⚠️ Serve alle superfici che RIFERISCONO, non al percorso caldo, e la
    distinzione è deliberata. `_holds_a_model` guarda `config.json` e basta, ed
    è giusto così: è quel file a far partire il tentativo di caricamento, ed è
    il tentativo a produrre la dichiarazione onesta «the grounding judge failed
    to load» che l'utente legge sulla ricevuta. Renderlo severo spegnerebbe il
    ramo che quella dichiarazione produce.

    `doctor`, invece, non tenta: riferisce. Misurato il 17/08 su una cartella
    con il solo `config.json` — cioè ciò che un'estrazione interrotta lascia::

        verimem doctor   «local CE gate model installed - the moat is ON»  EXIT=0
        verimem save     flow.warmup phase=failed
                         reason='no file named model.safetensors, or
                                 pytorch_model.bin, found in directory'
                         judged=False   grounding_score=None
                         e un claim smentito dalla sua fonte veniva AMMESSO

    Una `stat` su due nomi separa i due casi; caricare il modello per scoprirlo
    costerebbe 737 MB e il budget di ~2 s che `doctor` dichiara e difende.
    """
    return any((d / n).is_file() for n in _NOMI_DEI_PESI)


def _resolve_model_dir(model_dir: str | Path | None) -> Path:
    env = os.environ.get(_ENV_MODEL_DIR, "").strip()
    if env or model_dir:
        return Path(env or model_dir).expanduser()
    if not _holds_a_model(DEFAULT_MODEL_DIR) and _holds_a_model(_LEGACY_MODEL_DIR):
        return _LEGACY_MODEL_DIR
    return DEFAULT_MODEL_DIR


#: Il peso del modello del giudice, per l'annuncio. Non e' una stima: e' la somma dei
#: byte dei 5 file che `ensure_gate_model()` installa, misurata il 02/09:
#:
#:     746 058 368 byte  =  746,1 MB decimali  =  711,5 MiB
#:     (737,7 MB il solo `model.safetensors`, 8,3 MB `tokenizer.json`, il resto ~0)
#:
#: ⚠️ IN MB DECIMALI, e l'unita' e' la meta' del numero. Questa costante ha detto «711 MB»
#: fino al 02/09: 711 e' il valore in MiB, e chi lo leggeva guardando il contatore di rete
#: del sistema — che conta in MB decimali, come i piani dati — ne vedeva scorrere 746.
#: Numero vero, unita' sbagliata: la stessa forma che smontiamo nei numeri degli altri.
#:
#: Il TEMPO invece non e' una proprieta' del modello ma della rete di chi installa: 13,4 s
#: nella misura del 02/09 (cioe' ~56 MB/s), che su una linea da 10 MB/s diventano 75 s.
#: Per questo il messaggio dice «su una connessione veloce» e non promette un numero.
#: (Il commento precedente diceva «13,4 s su una rete da ~26 MB/s»: i due numeri non
#: stanno insieme — 711,5/13,4 fa 53, non 26 — e non so quale dei due fosse buono.)
_PESO_DEL_GIUDICE_MB = 746


def annuncia_download_del_giudice() -> None:
    """Dice all'utente che stiamo scaricando 746 MB, PRIMA di farlo.

    Scaricare tre quarti di giga senza dirlo e' una sorpresa, non una cura: chi lancia
    `verimem remember` vede il comando fermo una quindicina di secondi e non sa perche'.

    Su **stderr** e non su stdout, perche' stdout porta l'output strutturato dei comandi
    e chi ne fa il parsing non deve trovarci un avviso. Una riga sola: e' un evento raro,
    non un log.

    ⚠️ E dice **«una volta sola»**: senza quella parte, «746 MB» sembra un costo che si
    ripete a ogni scrittura — cioe' esattamente la paura che fa spegnere la cura.

    ⚠️⚠️ E NON PUO' NUOCERE. Questa funzione e' chiamata dentro il blocco `except` di
    `_ensure_scorer()`, **una riga prima** del download: se solleva, l'eccezione
    sostituisce quella originale, il modello non viene preso e la cura si spegne —
    per colpa del messaggio che doveva solo raccontarla. Da qui le due difese:

    · **`print(file=None)` NON tace: stampa su stdout.** Con `pythonw` (un server MCP
      lanciato da un client GUI) `sys.stderr` E' `None`, e un avviso su stdout
      inquinerebbe il canale JSON-RPC — lo stesso incidente diagnosticato in CI
      il 02/09, causato stavolta da noi. Senza un canale nostro: si tace.
    · **Lo stream puo' esserci ed essere rotto** (chiuso, detached, o con una codifica
      che non mappa il testo: cp1252 su Windows). Scrivere e' `try`.
    """
    import sys as _sys
    canale = getattr(_sys, "stderr", None)
    if canale is None:
        return
    try:
        canale.write(
            f"verimem: scarico il giudice del moat ({_PESO_DEL_GIUDICE_MB} MB, ~15 s "
            "su una connessione veloce, una volta sola per macchina). Senza, le "
            "scritture con una fonte sono ammesse SENZA giudizio.\n")
        canale.flush()
    except Exception:
        # Nessun rilancio e nessun log: l'unico canale per dirlo e' proprio quello
        # che ha appena fallito. Il download prosegue, ed e' cio' che conta.
        pass


def _download_disattivato() -> bool:
    """True se l'operatore ha chiesto di non toccare la rete.

    Legge la lista CANONICA (`airgap._OFFLINE_FLAGS`: VERIMEM_OFFLINE, HIPPO_OFFLINE,
    ENGRAM_OFFLINE, HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE) invece di ricopiarne una
    propria — due liste divergono, e `doctor` promette gia' «*for air-gapped deploys set
    VERIMEM_OFFLINE=1*». Una cura che scaricasse ignorandola romperebbe quella promessa.
    L'import e' locale per non creare un ciclo fra i moduli.
    """
    import os as _os
    try:
        from .airgap import _OFFLINE_FLAGS as _flags
    except Exception:            # pragma: no cover — se airgap non e' importabile,
        _flags = ("VERIMEM_OFFLINE",)   # si resta prudenti invece di scaricare
    return any(str(_os.environ.get(f, "")).strip().lower() in ("1", "true", "yes", "on")
               for f in _flags)


def make_finetuned_scorer(model_dir: str | Path, *, max_length: int = 512,
                          batch_size: int = 32) -> Scorer:
    """Production scorer over the saved binary-head CE: sigmoid(logit)*100 per
    (premise, hypothesis) pair. Imports transformers lazily."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir)).to(device).eval()

    @torch.no_grad()
    def scorer(batch: list[tuple[str, str]]) -> list[float]:
        out: list[float] = []
        for i in range(0, len(batch), batch_size):
            chunk = batch[i:i + batch_size]
            enc = tok([p for p, _ in chunk], [h for _, h in chunk],
                      truncation="longest_first", max_length=max_length,
                      padding=True, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits.squeeze(-1)
            out.extend((torch.sigmoid(logits) * 100.0).float().cpu().tolist())
        return out

    return scorer


_A_CAPO = chr(10)


class LocalGroundingJudge:
    """Scores source ⊢ fact in [0, 100] with the local CE. The source is reduced to
    its fact-relevant span (production selector) before scoring — the CE window is
    512 tokens."""

    def __init__(self, model_dir: str | Path | None = None, *,
                 scorer: Scorer | None = None, max_length: int = 512,
                 focus_budget: int | None = None):
        self.model_dir = _resolve_model_dir(model_dir)
        self._scorer = scorer
        self._lock = threading.Lock()
        self.max_length = max_length
        self._focus_budget = focus_budget
        self._config: dict[str, Any] | None = None
        self._load_failed = False
        self._tok: Any | None = None
        self._tok_failed = False

    @property
    def config(self) -> dict[str, Any]:
        """gate_config.json from the model dir ({} when absent/corrupt)."""
        if self._config is None:
            try:
                self._config = json.loads(
                    (self.model_dir / "gate_config.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._config = {}
        return self._config

    @property
    def threshold(self) -> float | None:
        t = self.config.get("threshold")
        return float(t) if isinstance(t, (int, float)) else None

    @property
    def focus_budget(self) -> int:
        if self._focus_budget:
            return int(self._focus_budget)
        b = self.config.get("focus_budget")
        return int(b) if isinstance(b, (int, float)) and b > 0 else _DEFAULT_FOCUS_BUDGET

    def _ensure_scorer(self) -> Scorer:
        if self._scorer is None:
            if self._load_failed:
                raise RuntimeError(f"local gate model unavailable: {self.model_dir}")
            with self._lock:
                if self._scorer is None:
                    # flow.warmup va QUI e non nel costruttore: misurato
                    # 2026-08-05, `LocalGroundingJudge()` ritorna in 0.1ms e i
                    # 41 secondi si spendono in questa riga. Un evento "ready"
                    # emesso dal costruttore dichiarava pronto un giudice che
                    # non aveva ancora caricato niente — cioè esattamente la
                    # bugia che l'osservabilità serve a togliere.
                    from .flow_events import emit_flow as _emit_flow
                    _emit_flow("flow.warmup", what="moat-judge", phase="start")
                    t0 = time.time()
                    _gia_procurato = False      # un solo tentativo di download
                    try:
                        self._scorer = make_finetuned_scorer(
                            self.model_dir, max_length=self.max_length)
                    except Exception as exc:
                        # ASSENTE ≠ ROTTO — e la distinzione e' tutta la cura.
                        #
                        # Misurato da utente il 02/09 sul pacchetto 0.7.1 servito da
                        # PyPI, HOME vergine: `verimem remember <falso> --source <fonte
                        # che lo smentisce>` stampa `admitted` con EXIT=0 e `layers=[]`.
                        # Il claim falso entra perche' il modello non c'e' e nessuno lo
                        # procura: `ensure_gate_model()` era chiamata SOLO da `verimem
                        # warmup` (`cli.py:594`), che l'utente non sa di dover lanciare.
                        #
                        # ⚠️ Perche' NON basta «scarica quando fallisci»: il commento
                        # qui sotto dice che il fallimento va in cache perche' «un
                        # modello rotto o assente non deve ripagare il caricamento a
                        # ogni scrittura». Scaricare anche sopra un modello CORROTTO
                        # reintrodurrebbe esattamente quel costo. ⇒ Si scarica solo se
                        # la cartella NON ESISTE, una volta, e poi si ricade nella
                        # cache di sempre.
                        #
                        # Costo misurato (02/09, HOME nuova, una sola esecuzione):
                        # `ensure_gate_model()` 13,4s per 746,1 MB, contro i 54,1s del
                        # caricamento che si paga GIA' oggi senza nessuna cura.
                        if (not _gia_procurato
                                and not self.model_dir.exists()
                                and not _download_disattivato()):
                            _emit_flow("flow.warmup", what="moat-judge",
                                       phase="fetching", motivo="modello assente")
                            # l'evento va nel journal, che l'utente non legge: l'annuncio
                            # va sullo schermo, PRIMA dei 15 secondi di attesa
                            annuncia_download_del_giudice()
                            try:
                                _preso, _msg = ensure_gate_model(self.model_dir)
                            except Exception:
                                _preso, _msg = False, "download fallito"
                            if _preso:
                                _gia_procurato = True
                                try:
                                    self._scorer = make_finetuned_scorer(
                                        self.model_dir, max_length=self.max_length)
                                    self.load_s = round(time.time() - t0, 1)
                                    _emit_flow("flow.warmup", what="moat-judge",
                                               phase="ready", procurato=True,
                                               elapsed_ms=round(
                                                   (time.time() - t0) * 1000, 1))
                                    return self._scorer
                                except Exception:
                                    # il modello e' stato scaricato e NON si carica
                                    # lo stesso: si ricade nel percorso di sempre, e
                                    # l'eccezione originale resta quella che l'utente
                                    # vede — il download non ha cambiato la diagnosi.
                                    pass
                        # cache the failure: a broken/absent model must not re-pay
                        # the load attempt on every gated write
                        self._load_failed = True
                        # ⚠️ Il MOTIVO va nell'evento, non solo nell'eccezione.
                        # Fino al 2026-08-13 questo blocco emetteva `phase` ed
                        # `elapsed_ms` e nient'altro: chi leggeva il giornale
                        # vedeva un giudice fallito in 3 millisecondi e non
                        # poteva sapere perche'. In CI e' l'unica traccia che
                        # resta — l'eccezione viene rilanciata e muore la'.
                        # Due istanze hanno cercato `error=`, `reason=`, `exc=`
                        # e un traceback in quelle righe prima che si capisse
                        # che non esistevano per costruzione.
                        # Il commento sopra dice che un modello rotto o assente
                        # non deve ripagare il caricamento: giusto, ma allora il
                        # motivo del primo fallimento e' l'unica occasione che
                        # abbiamo di saperlo, perche' non ci sara' un secondo
                        # tentativo da osservare.
                        _emit_flow("flow.warmup", what="moat-judge",
                                   phase="failed",
                                   elapsed_ms=round((time.time() - t0) * 1000, 1),
                                   error=type(exc).__name__,
                                   reason=(str(exc) or "(nessun messaggio)")[:200])
                        raise
                    self.load_s = round(time.time() - t0, 1)
                    _emit_flow("flow.warmup", what="moat-judge", phase="ready",
                               elapsed_ms=round((time.time() - t0) * 1000, 1))
        return self._scorer

    def coppia(self, source: str, fact: str, *,
               focus_budget: int | None = None) -> tuple[str, str]:
        """La coppia (span, fatto) che il CE giudica.

        Estratta da ``score`` perche' ha DUE esecutori: lo scorer in-process e
        il daemon condiviso (``_gate_via_daemon``). La selezione dello span e'
        puro testo e costa poco, quindi resta di qua in entrambi i casi: al
        daemon si manda la coppia gia' pronta, cosi' non c'e' un secondo posto
        dove il budget possa essere applicato in modo diverso."""
        budget = int(focus_budget) if focus_budget else self.focus_budget
        span = select_relevant_span(source or "", fact or "", budget=budget)
        return (self._entro_la_finestra(span),
                fact or "")

    def _entro_la_finestra(self, span: str) -> str:
        """Riduce lo span finche' entra nella finestra del CE, contando TOKEN.

        `focus_budget` e' in CARATTERI, `max_length` in TOKEN: le due unita'
        coincidono solo sulla prosa. Misurato 2026-08-19 col tokenizzatore del
        gate, a budget 1500::

            prosa italiana      4.08 caratteri/token   ->  350 token   dentro
            tabella di misure   2.15                   ->  713 token   FUORI
            log applicativo     2.02                   ->  715 token   FUORI
            git diff --stat     1.70                   ->  879 token   FUORI

        Senza questa riduzione il tokenizzatore tronca da se' con
        ``longest_first``, cioe' DALLA CODA: su un `git diff` butta il 42% dello
        span DOPO che il selettore l'aveva scelto apposta, e taglia a meta' riga.
        Qui si tolgono RIGHE INTERE dal fondo, che e' la stessa perdita ma
        leggibile — e lo si fa una volta sola, in `coppia`, che serve tanto lo
        scorer in-process quanto il daemon condiviso.

        Best-effort: se il tokenizzatore non e' disponibile lo span esce
        invariato e il troncamento resta quello di prima, mai peggio.
        """
        if not span:
            return span
        tok = self._tokenizzatore()
        if tok is None:
            return span
        conta = lambda s: len(tok.encode(s, add_special_tokens=False))  # noqa: E731
        if conta(span) <= self.max_length:
            return span
        righe = span.splitlines()
        while len(righe) > 1:
            righe.pop()
            candidato = _A_CAPO.join(righe)
            if conta(candidato) <= self.max_length:
                return candidato
        return righe[0] if righe else span

    def _tokenizzatore(self) -> Any | None:
        """Il tokenizzatore del gate, caricato una volta e riusato. None quando
        il modello non c'e': il giudice deve poter fallire senza rumore.

        ⚠️ L'IMPORT STA FUORI DAL LOCK, e non e' un dettaglio di stile. Prima
        stava dentro, e misurato il 2026-09-06 sul server MCP significava questo:

            LOCK=False TOK=False TOKFAIL=False   <- prima che la richiesta arrivi
            LOCK=True  TOK=False TOKFAIL=False   <- per i 120 s successivi, 24 letture

        cioe' il lock veniva preso e non piu' rilasciato mentre il thread era
        fermo dentro ``from transformers import AutoTokenizer`` — e ogni altra
        scrittura con fonte che arrivava a questo punto si accodava dietro un
        IMPORT. Il lock serve a non costruire DUE tokenizzatori: quello che deve
        proteggere e' ``from_pretrained``, non l'import, che Python serializza
        gia' da se'.

        ⚠️ Questo NON fa tornare un import che non ritorna: toglie il contagio
        alle altre scritture, non il blocco. Il blocco lo toglie il preload
        (``preload.py``), che carica la catena PRIMA che il server serva.
        """
        if self._tok is None and not self._tok_failed:
            try:
                from transformers import AutoTokenizer
            except Exception:  # noqa: BLE001 — transformers assente: si prosegue
                self._tok_failed = True
                return self._tok
            with self._lock:
                if self._tok is None and not self._tok_failed:
                    try:
                        self._tok = AutoTokenizer.from_pretrained(str(self.model_dir))
                    except Exception:  # noqa: BLE001 — assente/corrotto: si prosegue
                        self._tok_failed = True
        return self._tok

    @staticmethod
    def normalizza(val: float) -> float:
        """Il punteggio in [0, 100], da qualunque esecutore arrivi."""
        return min(100.0, max(0.0, float(val)))

    def score(self, source: str, fact: str, *,
              focus_budget: int | None = None) -> float:
        coppia = self.coppia(source, fact, focus_budget=focus_budget)
        return self.normalizza(self._ensure_scorer()([coppia])[0])


_judge: LocalGroundingJudge | None = None
_judge_lock = threading.Lock()


def get_local_judge() -> LocalGroundingJudge:
    """Process-wide lazy singleton (model loads once).

    Emits ``flow.warmup`` around the load. Measured 2026-08-05 on a fresh
    store: the first grounded write takes 42.7s and the flow channel stays
    SILENT for all of them, then delivers both events at the end — so the
    live Engine Room shows a stopped engine exactly while the product is
    doing the most expensive thing it does. The cost belongs to whoever owns
    the write path; the SILENCE is what makes a working product look stuck,
    and that is observability. ``judge_state()`` already told this in one
    word "for every surface" — it just never reached the channel the live
    surfaces listen to.
    """
    global _judge
    if _judge is None:
        with _judge_lock:
            if _judge is None:
                _judge = LocalGroundingJudge()
    return _judge


def set_local_judge(judge: LocalGroundingJudge | None) -> None:
    """Inject a judge (tests) — pass None to clear."""
    global _judge
    _judge = judge


def reset_local_judge() -> None:
    global _bg_warm_started
    set_local_judge(None)
    _bg_warm_started = False   # tests: allow a fresh background warm


def get_local_threshold() -> float | None:
    """The fine-tune-calibrated admission threshold, if the model ships one."""
    return get_local_judge().threshold


def judge_state() -> str:
    """Lo stato del giudice locale in UNA parola, per tutte le superfici.

    ``ready`` (carico QUI, giudica adesso) · ``delegated`` (il daemon condiviso
    ha gia' giudicato per questo processo: il modello in casa non serve, e non
    servira') · ``warming`` (il modello c'e' e sta caricando su un thread di
    sfondo, e nessuno sta giudicando al posto suo: in delegate-only il primo
    write NON viene giudicato) · ``absent`` (il modello non e' su disco: si
    scarica) · ``failed`` (c'e' ma il caricamento e' fallito: si diagnostica).

    Esiste perche' tre superfici — l'advisory L4, la ricevuta MCP e ``doctor``
    — deducevano ognuna per conto suo perche' mancasse un punteggio, e nessuna
    distingueva «assente» da «sta scaldando». Misurato il 2026-07-30 con l'env
    del server MCP: per ~45 secondi il moat non giudica e annuncia «model
    missing or unloadable» mentre lo stesso modello, senza delegate-only,
    risponde 99.93 all'istante. Un posto solo che lo sa, come per il contratto
    di uscita dei fatti: quando in tanti ricostruiscono lo stesso dato, la cura
    non e' correggerli tutti, e' averne uno.
    """
    j = get_local_judge()
    if getattr(j, "_scorer", None) is not None:
        return "ready"
    if getattr(j, "_load_failed", False):
        return "failed"
    # Il daemon ha gia' giudicato per questo processo (2026-08-01, rilievo del
    # critic sul commit precedente, che l'aveva pero' declassato a «stringa
    # cosmetica»). Non e' cosmetica: e' la parola che tre superfici leggono per
    # dire perche' manca un punteggio, e dire «sto scaldando» mentre il giudizio
    # sta gia' avvenendo altrove e' la stessa classe curata tre volte questa
    # settimana. Sta DOPO `_load_failed` di proposito: un fallimento locale
    # conclamato e' una diagnosi piu' urgente della strada che ha funzionato.
    if _GATE_DELEGATO["ok"]:
        return "delegated"
    try:
        presente = _holds_a_model(j.model_dir)
    except OSError:
        presente = False
    if not presente:
        return "absent"
    # Il modello c'e' e lo scorer no. In delegate-only e' il caso NORMALE dei
    # primi secondi: il caricamento e' su un thread di sfondo per non bloccare
    # la richiesta. Fuori da delegate-only il caricamento e' sincrono alla
    # prima chiamata, quindi «pronto appena serve».
    return "warming" if _delegate_only() else "ready"


def daemon_del_giudice_annunciato() -> bool:
    """True quando un daemon condiviso si e' ANNUNCIATO: la quarta via al giudizio.

    ⚠️ PERCHE' ESISTE. Il gate chiede «c'e' un giudice?» con tre criteri (llm
    iniettato, backend `local`, modello CE su disco) e il DAEMON non era fra
    questi — mentre `try_local_score` gli chiede per PRIMO, ed e' cio' che
    rende giudicata la prima scrittura invece di ammetterla al buio. Con il
    modello locale assente e il daemon vivo, misurato il 2026-08-30 alle 22:33
    su due processi freschi::

        _have_judge (i tre criteri)      False
        try_local_score, stesso processo 0.5561      <- il daemon RISPONDE
        Memory().add(..., source=...)    gs=None     <- il write esce al buio

    E la cura NON e' togliere il predicato: nello stesso banco, il tentativo di
    giudizio in un processo SENZA alcun giudice costa **15.453 ms** (il write
    con la guardia ne costa 351, perche' non tenta). Un predicato che protegge
    quindici secondi si tiene: gli si aggiunge la via che gli manca.

    ECONOMICA COME LE ALTRE, ed e' il vincolo che questa funzione deve
    rispettare: legge il file di discovery e l'interruttore d'ambiente, non apre
    connessioni e non carica nulla — `local_ce_available` e' un `os.path`,
    questa e' una lettura di file. Un annuncio non e' una garanzia (il daemon
    puo' essere morto fra l'annuncio e la chiamata): serve a NON escludere una
    strada che esiste, e chi la percorre degrada gia' da solo.
    """
    try:
        import os as _os
        if _os.environ.get("ENGRAM_ENCODE_SERVICE", "1").strip().lower() in (
            "0", "false", "no", "off",
        ):
            return False
        from . import encode_service as _svc
        info = _svc.read_discovery()
        return bool(info and info.get("port"))
    except Exception:  # noqa: BLE001 — un predicato non rompe una scrittura
        return False


def local_ce_available() -> bool:
    """True when the local CE moat judge can score WITHOUT an injected llm — an
    injected scorer (tests) or a model dir present on disk. Cheap by design:
    it NEVER loads the model, so the gate can ask "is there a judge?" on the hot
    write path without paying the cold-start.

    WHY THE MOAT IS ON BY DEFAULT for a user who passed no llm — the honest
    version. This docstring used to say "(the CE is multilingual)". That was
    FALSE about the model that actually loads, and it was doing work: it was
    the stated reason for a default, so deleting it would have left the
    default unexplained. Measured 2026-08-25 on the loaded judge:

        base_model : cross-encoder/nli-deberta-v3-base   (gate_config.json)
        model_type : deberta-v2
        vocab_size : 128100      — mDeBERTa, the multilingual one, has ~251k

    Three facts, none of which cancels the others:
      1. the judge's VOCABULARY is English. It is an English DeBERTa-v3
         fine-tuned on HaluMem GT + real-corpus soft labels (val_auroc 0.9879).
      2. its measured BEHAVIOUR does not collapse on the Latin-script languages
         we have data for: `grounding_gate.py` (2026-07-18) scores entailments
         at ~97-99 and confabs at ~0.6 "in EN/IT/FR/ES alike", and attributes
         the earlier "English-only" look to a mis-calibrated 99.64 cut rather
         than to language. Vocabulary is a fact about the MODEL, separation is
         a fact about BEHAVIOUR — neither implies the other.
      3. on NON-LATIN script there is NO measurement of this judge at all. Not
         "it works", not "it fails": unmeasured. The lexical L1* layers ARE
         known blind there (`_has_negator` is False on KO/TH/HI/TR), so the
         absence of a CE number is the open end, not a reassurance.
    ⇒ The default is ON because this judge is validated and separates on the
    scripts we have measured — a claim bounded by (3), not by wishful reach.

    ⚠️ "CE" NAMES TWO DIFFERENT COMPONENTS in this codebase, which is what made
    RELEASE_GATE G10 look like it contradicted this docstring. It does not:
        retrieval rerank : cross-encoder/ms-marco-MiniLM-L-12-v2
                           (`cross_encoder_rerank.py`) — G10 calls this "CE"
        moat judge       : cross-encoder/nli-deberta-v3-base — G10 calls this
                           "NLI", and calls it EN, correctly, since 2026-07-04
    G10 was right all along; nobody connected it to this line. Guarded by
    `tests/test_il_docstring_del_giudice_nomina_il_modello_che_gira.py`, which
    reads the base model from `benchmark/local_gate_finetune.py` so that
    changing the model turns this text RED instead of letting it go stale."""
    j = get_local_judge()
    if getattr(j, "_scorer", None) is not None:
        return True
    if getattr(j, "_load_failed", False):
        return False
    try:
        return _holds_a_model(j.model_dir)
    except OSError:
        return False


# --- gate-model acquisition (2026-07-18, PUBLISHED) ----------------------------
# The fine-tuned gate CE (local_gate_ce_v2) is what makes the moat judge-less.
# On a FRESH machine the model dir does not exist and — demonstrated 2026-07-18 —
# the README quickstart's `assert status == "quarantined"` fails (the write is
# admitted with an L4-skipped advisory). `verimem warmup` calls ensure_gate_model
# to close that gap: it downloads the PUBLISHED model (a public GitHub release
# tarball — no auth), verifies its sha256, and extracts it. The claim is now
# true end-to-end for any downloader.
_ENV_GATE_HUB_ID = "VERIMEM_GATE_MODEL_HUB_ID"
_ENV_GATE_URL = "VERIMEM_GATE_MODEL_URL"

#: Published gate model: a public GitHub release tarball (config.json,
#: gate_config.json, model.safetensors, tokenizer*). No auth, no HF account.
DEFAULT_GATE_MODEL_URL = (
    "https://github.com/aureliocpr-ctrl/verimem/releases/download/"
    "gate-ce-v2/verimem-gate-ce-v2.tar.gz")
DEFAULT_GATE_MODEL_SHA256 = (
    "58255842348553f6b14c2463c795f3a40b951751166838c519916553fc0b2810")
#: Alternative source (HF Hub repo id) — used only if explicitly set.
DEFAULT_GATE_MODEL_HUB_ID: str | None = None


def _download_and_extract_tar(url: str, dest: Path, *,
                              sha256: str | None = None, opener=None) -> None:
    """Stream ``url`` to a temp file (verifying sha256), then extract the tar.gz
    into ``dest``. stdlib-only; extraction uses the ``data`` filter (py3.12+) to
    refuse path-traversal members."""
    import hashlib
    import tarfile
    import tempfile
    import urllib.request
    opener = opener or urllib.request.urlopen
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tf:
        tmp = Path(tf.name)
    try:
        h = hashlib.sha256()
        with opener(url) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                out.write(chunk)
        if sha256 and h.hexdigest() != sha256:
            raise ValueError(
                f"gate model sha256 mismatch: got {h.hexdigest()[:16]}… "
                f"expected {sha256[:16]}… — refusing to install")
        with tarfile.open(tmp, "r:gz") as tar:
            _safe_tar_extract(tar, dest)
    finally:
        tmp.unlink(missing_ok=True)


def _safe_tar_extract(tar, dest: str | Path) -> None:
    """Extract *tar* into *dest*, refusing any member that would escape it —
    the tar-slip guard (CodeQL py/tarslip). Python 3.12+ has the built-in
    ``filter="data"`` for exactly this; on 3.10/3.11 (no filter kwarg) we
    validate every member against the resolved destination ourselves and
    extract only the ones that stay inside — never a bare ``extractall``.
    """
    try:
        tar.extractall(dest, filter="data")   # py3.12+ hardened built-in filter
        return
    except TypeError:                          # py<3.12 — no filter kwarg
        pass
    dest_r = Path(dest).resolve()
    for m in tar.getmembers():
        if m.issym() or m.islnk() or m.isdev():
            continue  # the published gate-model tar is plain files only
        target = (dest_r / m.name).resolve()
        if target != dest_r and dest_r not in target.parents:
            raise ValueError(
                f"refusing tar member that escapes {dest_r}: {m.name!r}")
        tar.extract(m, dest)


def ensure_gate_model(model_dir: str | Path | None = None, *,
                      url: str | None = None, hub_id: str | None = None,
                      download=None) -> tuple[bool, str]:
    """Ensure the local gate CE exists at ``model_dir``; download+verify+extract
    the published model if absent. Returns ``(present, message)``.

    Source precedence: explicit ``url`` / ``VERIMEM_GATE_MODEL_URL`` → explicit
    ``hub_id`` / ``VERIMEM_GATE_MODEL_HUB_ID`` → the built-in public release URL.
    ``download`` is injectable for tests (called as ``download(source, dest)``).
    """
    dest = _resolve_model_dir(model_dir)
    if _holds_a_model(dest) and holds_the_weights(dest):
        return True, f"gate model present at {dest}"
    the_url = url or os.environ.get(_ENV_GATE_URL, "").strip()
    hub = hub_id or os.environ.get(_ENV_GATE_HUB_ID, "").strip()
    if download is not None:
        download(the_url or hub or DEFAULT_GATE_MODEL_URL, dest)
    elif the_url:
        _download_and_extract_tar(the_url, dest)
    elif hub:  # pragma: no cover — HF path exercised via injected download
        from huggingface_hub import snapshot_download
        dest.mkdir(parents=True, exist_ok=True)
        snapshot_download(repo_id=hub, local_dir=str(dest))
    else:  # the default: the published public release tarball
        _download_and_extract_tar(DEFAULT_GATE_MODEL_URL, dest,
                                  sha256=DEFAULT_GATE_MODEL_SHA256)
    return _esito_dell_installazione(dest)


def _esito_dell_installazione(dest: Path) -> tuple[bool, str]:
    """Se il modello sia utilizzabile dopo il download, e cosa manca se no.

    Il criterio era `config.json` e basta, in entrambi i punti di
    :func:`ensure_gate_model` — quello che decide di NON riscaricare e quello
    che dichiara l'esito. Misurato il 17/08: su una cartella con i soli
    metadati — ciò che un'estrazione interrotta lascia, visto che `config.json`
    pesa 1 KB e i pesi 737 MB — `verimem warmup` rispondeva

        ✓ moat gate model already installed        EXIT=0

    senza scaricare niente e lasciando la cartella com'era. Il comando che
    esiste apposta per procurare il giudice si dichiarava soddisfatto, e da lì
    non si usciva se non cancellando la cartella a mano.

    Il messaggio nomina ciò che manca invece di dire solo «no config.json»:
    l'operatore che legge deve sapere se ha scaricato metà modello o niente.
    """
    manca = [nome for nome, presente in
             (("config.json", _holds_a_model(dest)),
              ("weights (model.safetensors / pytorch_model.bin)",
               holds_the_weights(dest))) if not presente]
    if not manca:
        return True, f"gate model installed at {dest}"
    return False, f"download left no {' and no '.join(manca)} in {dest}"


_warned_fallback = False

# --- delegate-only: keep the CE cold-load OFF the request thread ---------------
# MCP-server processes run with HIPPO_ENCODE_DELEGATE_ONLY=1 (mirror of
# embedding._delegate_only, kept env-local so this module stays import-light).
# The moat CE cold-load (~30s measured 2026-07-18: import + model build under the
# judge lock) blocked the FIRST gated write of every fresh server — same class as
# the 2026-06-05 embedding hang, new site. In delegate-only mode the load runs on
# a background thread instead; until warm, try_local_score returns None and the
# caller degrades honestly (injected llm, or the L4-skipped advisory admit).
# Deliberately NOT a boot-time preload: that would charge every server ~400 MB
# whether it ever writes or not (the 2026-07-10 rerank RAM incident) — warming on
# first USE bills only processes that actually run the moat.
_DELEGATE_TRUTHY = {"1", "true", "yes", "on"}
_bg_warm_started = False
_bg_warm_lock = threading.Lock()


def _delegate_only() -> bool:
    return (os.environ.get("HIPPO_ENCODE_DELEGATE_ONLY", "").strip().lower()
            in _DELEGATE_TRUTHY)


#: Il daemon ha gia' risposto una volta: da qui in poi il giudizio e' «pronto»
#: anche senza modello in questo processo. Azzerato nel conftest fra i test
#: (classe imparata curando l'equivalente del rerank: un globale che sopravvive
#: al test lo rende dipendente dall'ordine).
_GATE_DELEGATO = {"ok": False}


def _gate_via_daemon(pairs, *, info=None) -> list[float] | None:
    """Punteggi del giudice del moat dal daemon condiviso, o None per degradare.

    Speculare a ``semantic._rerank_via_daemon``, e per la stessa ragione con una
    posta piu' alta. Il reranker che non gira costa RILEVANZA; il giudice che
    non gira costa la GARANZIA — una scrittura ammessa senza essere giudicata
    e' precisamente cio' che questo prodotto esiste per non fare, e il `doctor`
    misura quanto spesso accade: «only 107 of 4827 stored facts
    entailment-judged (2.2%)».

    Perche' il daemon lo cura davvero e non sposta solo il problema: 256
    processi su 293, nell'audit log, fanno UNA chiamata e muoiono. Un warm
    in-process non fa in tempo per costruzione, e ricomincia da capo a ogni
    respawn. Il daemon vive: carica una volta e serve tutti.

    Mai una dipendenza, sempre un'ottimizzazione: daemon spento, daemon vecchio
    che non conosce ``gate_pairs``, socket caduto -> None -> il chiamante fa
    esattamente cio' che faceva prima. E anche quando questo client scade, il
    daemon **continua a caricare**: il processo dopo lo trova caldo.
    """
    if os.environ.get("ENGRAM_ENCODE_SERVICE", "1").strip().lower() in (
        "0", "false", "no", "off",
    ):
        return None
    try:
        import socket as _socket

        from . import embedding as _emb
        from . import encode_service as _svc
        info = info if info is not None else _svc.read_discovery()
        if not info or not info.get("port"):
            return None
        conn = _socket.create_connection(
            (info.get("host", "127.0.0.1"), info["port"]),
            timeout=_emb._SERVICE_CONNECT_TIMEOUT_S,
        )
        try:
            conn.settimeout(_emb._SERVICE_READ_TIMEOUT_S)
            req = {"gate_pairs": [[p[0], p[1]] for p in pairs]}
            if info.get("token"):
                req["token"] = info["token"]
            _svc.send_msg(conn, req)
            resp = _svc.recv_msg(conn)
        finally:
            conn.close()
        # Un daemon VECCHIO non conosce 'gate_pairs' e risponde ok=False:
        # degradare qui e' cio' che rende sicuro un aggiornamento non atomico,
        # in cui client e daemon non ripartono nello stesso istante.
        if resp and resp.get("ok") and isinstance(resp.get("scores"), list):
            _GATE_DELEGATO["ok"] = True
            return [float(s) for s in resp["scores"]]
    except Exception:  # noqa: BLE001 — qualunque intoppo -> si degrada come prima
        return None
    return None


def warm_local_judge_async() -> None:
    """Warm the CE off the request thread (once per process). Load failure is
    cached on the judge, so the advisory path keeps working either way."""
    global _bg_warm_started
    with _bg_warm_lock:
        if _bg_warm_started:
            return
        _bg_warm_started = True

    def _warm() -> None:
        try:
            get_local_judge()._ensure_scorer()
        except Exception:  # noqa: BLE001 — cached on the judge; advisory continues
            pass

    threading.Thread(target=_warm, daemon=True, name="verimem-ce-warm").start()


def try_local_score(source: str, fact: str, *,
                    focus_budget: int | None = None,
                    ) -> tuple[float, float | None] | None:
    """(score, config_threshold) via the local judge, or None when the local model is
    unavailable (the caller falls back to its injected llm at the CLAUDE-scale
    threshold — the config cut must never be applied to a claude-scale score). The
    load failure is cached; the fallback warning fires once per process."""
    global _warned_fallback
    judge = get_local_judge()
    # DELEGATE-ONLY (MCP server): never pay the CE cold-load on this thread.
    # PRIMA si chiede al daemon condiviso — e' cio' che rende giudicata la
    # PRIMA scrittura invece di ammetterla al buio (doctor: 107 su 4827
    # giudicati; 256 processi su 293 fanno una chiamata sola, quindi il warm
    # in-process non fa in tempo per costruzione). Se il daemon non c'e', non
    # sa giudicare o e' lento, si degrada ESATTAMENTE come prima: warm in
    # background e None. Il daemon pero' continua a caricare, quindi il
    # processo successivo lo trova caldo.
    #
    # ⚠️ `_load_failed` NON E' PIU' NELLA CONDIZIONE, dal 2026-08-30, e la
    # ragione e' che dice una cosa su QUESTO processo e veniva usata per
    # decidere di un ALTRO. Il caricamento locale puo' fallire per RAM,
    # file corrotto, torch assente — e il daemon condiviso, che e' un
    # processo separato col modello gia' in memoria, sta benissimo. Da
    # quel momento il giudizio non veniva piu' chiesto a chi poteva darlo,
    # e la riga qui sopra prometteva l'opposto: «se il daemon non c'e',
    # non sa giudicare o e' lento, si degrada ESATTAMENTE come prima».
    # Li' non si degradava: si saltava il daemon a priori, senza avere
    # alcuna informazione sulla sua salute.
    #
    # MISURATO ALLA PORTA il 2026-08-30 alle 22:16, daemon vivo (porta 61574),
    # A/B nella stessa esecuzione — il banco che accompagna questa cura sta
    # sotto `docs/stato-reale/banchi/` e si chiama «un fallimento locale
    # spegne il daemon che sta bene»:
    #
    #     _load_failed=False  ->  try_local_score  = (0.5561, 99.64)
    #     _load_failed=True   ->  try_local_score  = None
    #     la STESSA strada a mano ->  _gate_via_daemon = [0.5561]
    #
    # Il costo di chiedere e' una connessione locale con timeout; il costo
    # di non chiedere e' una scrittura ammessa senza giudizio, che il
    # docstring di `_gate_via_daemon` chiama «precisamente cio' che questo
    # prodotto esiste per non fare». Il degrado resta quello di sempre:
    # daemon assente o muto -> None -> warm in background e il chiamante
    # fa esattamente cio' che faceva prima.
    if judge._scorer is None and _delegate_only():
        punteggi = _gate_via_daemon(
            [judge.coppia(source, fact, focus_budget=focus_budget)])
        if punteggi:
            return judge.normalizza(punteggi[0]), judge.threshold
        warm_local_judge_async()
        return None
    # LOAD phase — a missing / unloadable model is a legitimate "no local judge":
    # fail over to None (caller uses its injected llm, or emits the L4-skipped
    # advisory). Only load failure is swallowed here.
    try:
        judge._ensure_scorer()
    except Exception:  # noqa: BLE001 — model absent/unloadable -> fail over
        if not _warned_fallback:
            _warned_fallback = True
            import warnings
            warnings.warn(
                f"ENGRAM_GROUNDING_BACKEND=local but the model at {judge.model_dir} "
                f"is unavailable — falling back to the injected llm judge",
                RuntimeWarning, stacklevel=2)
        return None
    # The model IS loaded. An inference failure now (torch shape mismatch, CUDA
    # OOM) is a REAL fault, NOT an absent judge — let it PROPAGATE rather than
    # laundering it into "no judge -> admit" (opus re-review 2026-07-18, finding B:
    # this is the default out-of-the-box path, where the earlier fix did not reach).
    score = judge.score(source, fact, focus_budget=focus_budget)
    return score, judge.threshold


#: Le frasi di una fonte, ESATTAMENTE come nel banco P-E (docs/stato-reale/banchi/
#: P-E-il-max-per-frase-contro-il-focus-sulla-zavorra.py): solo punteggiatura.
#: Spezzare anche sul fine riga (output di programma) e' una variabile in piu',
#: NON misurata: si prova a RAM ok, una per volta.
_FRASI = re.compile(r"(?<=[.!?])\s+")


def frasi_della_fonte(source: str) -> list[str]:
    return [f.strip() for f in _FRASI.split(source or "") if f.strip()] or [source or ""]


def punteggi_max_per_frase(source: str, claims: list[str], *,
                           judge: LocalGroundingJudge | None = None,
                           ) -> list[float] | None:
    """Muro 1, pezzo 3b-bis: per ogni claim il MAX del punteggio sulle FRASI della fonte, in UN lotto.

    Perche' non il focus per claim (`coppia()` → `select_relevant_span`): nella
    cella P-E (3d1b5c90) sui 5 casi zavorra del lead il focus ferma <= 2/4
    falsi — la fonte D+Z entra intera nel budget e il CE ribalta — mentre il
    MAX per frase ne ferma 4/4 col vero intatto (0/1 perso). E perche' un
    lotto solo: P6c ha misurato che il lotto satura a 16 coppie, 5,3 ms per
    coppia contro ~64 una per volta (12x); con 3-4 claim e 5-8 frasi sono
    20-30 coppie in una chiamata.

    Ritorna ``None`` quando il lotto NON e' disponibile — giudice locale
    assente o non caricabile, daemon in delega che non risponde — e il
    chiamante resta sul focus per claim, DICHIARANDOLO nella ricevuta
    (`claims_verdict[i]["via"]`). Nessuna eccezione esce da qui: la cura
    degrada, non blocca.
    """
    if not source or not claims:
        return None
    j = judge or get_local_judge()
    frasi = frasi_della_fonte(source)
    try:
        lotto = [(j._entro_la_finestra(f), c) for c in claims for f in frasi]
        if j._scorer is None and _delegate_only():
            grezzi = _gate_via_daemon(lotto)          # il daemon accetta una lista
            if not grezzi:
                return None
        else:
            grezzi = j._ensure_scorer()(lotto)
    except Exception:  # noqa: BLE001 — il chiamante degrada al focus, dichiarato
        return None
    if len(grezzi) != len(lotto):
        return None
    n = len(frasi)
    return [max(j.normalizza(v) for v in grezzi[i * n:(i + 1) * n])
            for i in range(len(claims))]


__all__ = ["LocalGroundingJudge", "make_finetuned_scorer", "get_local_judge",
           "frasi_della_fonte", "punteggi_max_per_frase",
           "set_local_judge", "reset_local_judge", "get_local_threshold",
           "try_local_score", "local_ce_available", "warm_local_judge_async",
           "judge_state", "_gate_via_daemon", "daemon_del_giudice_annunciato",
           "ensure_gate_model", "DEFAULT_GATE_MODEL_URL",
           "DEFAULT_GATE_MODEL_SHA256", "DEFAULT_GATE_MODEL_HUB_ID",
           "DEFAULT_MODEL_DIR"]
