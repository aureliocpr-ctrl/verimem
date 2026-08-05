"""``verimem doctor`` — one-shot install diagnosis, fast by construction.

Answers "why doesn't it work?" in seconds instead of a support thread: every
check reports PASS / WARN / FAIL with the concrete fix. Deliberately loads NO
model (presence checks and socket probes only) so it finishes in ~2s even on a
broken install — a doctor that hangs is a patient.

Every incident from 2026-07-18 maps to a check here: encode daemon down
(``daemon``), moat CE missing on a fresh machine (``moat-judge``), offline pins
(``offline``), legacy/brand env confusion (``data-dir`` shows which dir won).
"""
from __future__ import annotations

import os
import sqlite3
import sys
from typing import Any

OK = "ok"
WARN = "warn"
FAIL = "fail"

#: Cosa succede DAVVERO alle scritture quando non c'e' nessun giudice.
#: La riga diceva «writes are admitted with an L4-skipped advisory (moat
#: OFF)» — vero solo per le scritture che portano una fonte. Misurato il
#: 2026-08-05 con giudice assente: `add(testo)` torna `warnings []`, e
#: `add(testo, source=...)` torna l'avviso L4-skipped. Cioe' la stragrande
#: maggioranza delle scritture (6445 su 8267 sul corpus reale non hanno
#: una fonte dichiarata) entrava in silenzio mentre il referto prometteva
#: un avviso: la piu' rassicurante delle frasi sbagliate, e per questo la
#: peggiore. Una sola definizione, importata anche da `verimem warmup`:
#: due copie della stessa frase divergono.
AVVISO_SENZA_GIUDICE = (
    "writes that CARRY A SOURCE are admitted with an L4-skipped advisory; "
    "writes without a source get no advisory at all — there was nothing to "
    "check them against")


def _misura(byte: int) -> str:
    for unita, soglia in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if byte >= soglia:
            return f"{byte / soglia:.1f} {unita}"
    return f"{byte} B"


def _stores_dichiarati(d) -> str:
    """I database che CONFIG dichiara, con la loro dimensione — «c'e' un file
    di nome episodes.db» e «quel file e' vuoto» mandano l'operatore a fare cose
    diverse, e prima si leggeva solo il nome.

    Da CONFIG si prende la STRUTTURA (quali file, in quali sottocartelle) e la
    si ri-ancora alla data dir corrente ``d``: ``CONFIG`` e' congelato alla
    costruzione, quindi su un processo puntato altrove — un operatore
    multi-tenant, o un test isolato — dichiarerebbe assenti file che esistono.
    """
    from .config import CONFIG
    righe = []
    for attributo in ("semantic_db", "episodes_db", "skills_db"):
        p = getattr(CONFIG, attributo, None)
        if p is None:
            continue
        try:
            p = d / p.relative_to(CONFIG.data_dir)
        except (ValueError, AttributeError):
            pass                     # path fuori dalla data dir: si usa com'e'
        try:
            righe.append(f"{p.name} {_misura(p.stat().st_size)}"
                         if p.exists() else f"{p.name} (assente)")
        except OSError:
            righe.append(f"{p.name} (illeggibile)")
    return ", ".join(righe) or "none yet"


def _residui_dei_test(d) -> tuple[int, int]:
    """(quanti, quanti byte) fra gli snapshot il cui nome dice «pytest».

    Sullo store vero, il 2026-07-30: 284 file per 9.5 GB, il 77% di tutta la
    cartella dati. Nessuna superficie lo diceva — per accorgersene bisognava
    guardare il disco a mano.
    """
    cartella = d / "snapshots"
    if not cartella.is_dir():
        return 0, 0
    try:
        residui = [p for p in cartella.glob("*.db") if "pytest" in p.name.lower()]
        return len(residui), sum(p.stat().st_size for p in residui)
    except OSError:
        return 0, 0


def _provenienza_del_codice() -> str:
    """Da quale albero gira il pacchetto, e a quale revisione.

    Il numero di versione e' lo stesso in ogni checkout: dice cosa
    dovrebbe essere il codice, non quale codice e'. Qui si legge la
    cartella che lo contiene e — se e' un albero git — la revisione, dal
    file ``.git/HEAD`` senza lanciare nessun processo (un doctor che si
    impianta e' un paziente). Un pacchetto installato non ha un albero, e
    allora si dice solo dove sta: e' comunque l'informazione che
    distingue due installazioni.
    """
    from pathlib import Path
    try:
        radice = Path(__file__).resolve().parent.parent
    except OSError:
        return "unknown"
    testa = ""
    try:
        g = radice / ".git"
        if g.is_file():                       # worktree: .git e' un puntatore
            riga = g.read_text(encoding="utf-8").strip()
            if riga.startswith("gitdir:"):
                g = Path(riga.split(":", 1)[1].strip())
        if g.is_dir():
            h = (g / "HEAD").read_text(encoding="utf-8").strip()
            if h.startswith("ref:"):
                ref = h.split(":", 1)[1].strip()
                # il nome INTERO del ramo: `ws6/control-room` e
                # `ws3/control-room` condividono l'ultimo segmento, ed e'
                # esattamente il tipo di ambiguita' che questo campo esiste
                # per togliere
                testa = ref[len("refs/heads/"):] if ref.startswith(
                    "refs/heads/") else ref
                # In un WORKTREE i ref non stanno nella sua gitdir ma nel
                # repo principale, indicato dal file `commondir`: leggere
                # solo la gitdir dava il ramo senza revisione — meta'
                # risposta, e la meta' mancante era quella che distingue
                # due checkout allo stesso ramo.
                radici = [g]
                try:
                    cd = (g / "commondir").read_text(encoding="utf-8").strip()
                    radici.append((g / cd).resolve())
                except OSError:
                    pass
                for base in radici:
                    p = base / ref
                    if p.exists():
                        testa += "@" + p.read_text(
                            encoding="utf-8").strip()[:8]
                        break
                    pr = base / "packed-refs"
                    if pr.exists():
                        for r in pr.read_text(encoding="utf-8").splitlines():
                            if r.endswith(" " + ref):
                                testa += "@" + r.split(" ", 1)[0][:8]
                                break
                        else:
                            continue
                        break
            else:
                testa = "detached@" + h[:8]
    except (OSError, ValueError, IndexError):
        testa = ""                            # un albero illeggibile non e' un errore
    return f"{radice}" + (f" [{testa}]" if testa else "")


def run_doctor() -> list[dict[str, Any]]:
    """Run all checks; each returns ``{name, status, detail, fix?}``.

    Pure inspection — no model load, no network beyond a loopback socket probe,
    no writes outside a 1-byte probe file that is removed.
    """
    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, detail: str, fix: str | None = None) -> None:
        c: dict[str, Any] = {"name": name, "status": status, "detail": detail}
        if fix:
            c["fix"] = fix
        checks.append(c)

    # -- version ---------------------------------------------------------------
    try:
        from . import __version__
        # QUALE codice sta girando, non solo che numero porta. Cinque
        # istanze lavorano sullo stesso repo da checkout diversi e
        # `verimem 0.7.0` e' identico in tutti: la versione non
        # distingue, e il 2026-08-05 e' costato tre volte in un giorno
        # (una misura sul ramo di un'altra creduto il main; una cura
        # verificata e assente dall'albero dove il prodotto gira). Il
        # percorso del pacchetto lo dice sempre; la revisione git solo
        # quando il codice gira da un albero, e allora vale doppio.
        add("version", OK,
            f"verimem {__version__} · python {sys.version.split()[0]} · "
            f"code from {_provenienza_del_codice()}")
    except Exception as e:  # noqa: BLE001 — a doctor never crashes on a check
        add("version", WARN, f"unreadable: {e}")

    # -- data dir --------------------------------------------------------------
    try:
        from ._compat import data_dir
        d = data_dir()
        probe = d / ".doctor-probe"
        try:
            probe.write_text("x")
            probe.unlink()
            writable = True
        except OSError:
            writable = False
        # I DATABASE CHE IL PRODOTTO USA, non quelli che si trovano in giro.
        # `d.glob("*.db")` guardava solo il livello alto, dove vivono scheletri
        # di layout vecchi da 0 byte (episodes.db, hippo.db, memory.db...),
        # mentre i database veri sono annidati: la diagnosi elencava file vuoti
        # e taceva sui 79 MB di semantic/semantic.db. Un glob trova i file; il
        # prodotto SA quali sono i suoi, e stanno in CONFIG.
        add("data-dir", OK if writable else FAIL,
            f"{d} (writable={writable}; stores: {_stores_dichiarati(d)})",
            None if writable else "fix directory permissions, or set VERIMEM_DATA_DIR")
        # Residui dei test nello store di PRODUZIONE: una suite che scrive
        # dove vive la memoria dell'utente e' un difetto di igiene, e finche'
        # nessuno lo misura cresce in silenzio.
        _n_res, _byte_res = _residui_dei_test(d)
        if _n_res:
            add("test-leftovers", WARN,
                f"{_n_res} snapshot con 'pytest' nel nome occupano "
                f"{_misura(_byte_res)} nella cartella dati di produzione",
                "these are left by the test suite writing into the real data "
                "dir. Delete `snapshots/*pytest*.db` after checking none is "
                "needed, and isolate the suite with HIPPO_DATA_DIR")
    except Exception as e:  # noqa: BLE001
        add("data-dir", FAIL, str(e), "set VERIMEM_DATA_DIR to a writable path")

    # -- embedding model + shared encode daemon --------------------------------
    try:
        from . import encode_service as svc
        from .config import CONFIG
        info = svc.read_discovery()
        if info and svc.daemon_usable(info):
            add("daemon", OK,
                f"shared encode daemon warm on :{info.get('port')} "
                f"(model {info.get('model')})")
        elif info:
            add("daemon", WARN,
                f"discovery file present but daemon not usable "
                f"(model={info.get('model')!r} vs config={CONFIG.embedding_model!r})",
                "it respawns on demand; or run `verimem warmup` to spawn+warm now")
        else:
            add("daemon", WARN,
                "no shared encode daemon — first encode in each process "
                "cold-loads the model (~20s)",
                "run `verimem warmup` once")
    except Exception as e:  # noqa: BLE001
        add("daemon", WARN, f"probe failed: {e}")

    # -- moat judge (the product's #1 claim) -----------------------------------
    # Below this share of entailment-judged facts the moat-judge check WARNS
    # instead of passing. The alarm used to fire only at exactly zero, so a
    # single judged write turned it green: measured on the real store the
    # evening it was added, 3 of 4723 judged (0.06%) reported OK. Half is a
    # declared choice, not a measurement — the point is that the check reads a
    # FRACTION, so it cannot be silenced by one write.
    _MOAT_COVERAGE_WARN = 0.5
    try:
        from .llm import _autodetect_provider
        from .local_grounding import (
            _resolve_model_dir,
            judge_state,
            local_ce_available,
        )
        ce = local_ce_available()
        # Lo STATO nel processo che chiede, dalla funzione unica (la stessa che
        # legge l'advisory L4 e la ricevuta MCP) — non ri-dedotto qui.
        _stato_giudice = judge_state()
        provider = None
        try:
            provider = _autodetect_provider()
        except Exception:  # noqa: BLE001 — provider detection is best-effort
            provider = None
        # "the moat is ON" is true of the JUDGE and gets read as "my store is
        # protected". The moat only runs on writes that carry a source, so an
        # installed judge and an unjudged corpus coexist happily — measured
        # 2026-07-28 on the real store: judge present, 0 of 6414 facts ever
        # judged. Two COUNTs keep doctor inside its ~2s budget.
        #
        # 2026-07-29: counted OUTSIDE the `if ce` branch. How much of the corpus
        # was judged is a fact about the STORE — it does not become unknowable
        # because the judge is missing today, and the machine without a judge is
        # exactly the one whose corpus is most likely unjudged. CI found this:
        # there the CE is not installed, and doctor answered about the model
        # while saying nothing about the corpus.
        _n = _judged = 0
        _con_fonte_non_giud = _senza_fonte = None
        _readable = True
        try:
            import sqlite3 as _sq

            from ._compat import data_dir as _dd
            # _compat.data_dir(), the same resolver the data-dir check above
            # uses — it reads the environment at call time, so doctor reports
            # on the store the operator is actually pointed at.
            _db = _dd() / "semantic" / "semantic.db"
            if _db.exists():
                with _sq.connect(str(_db)) as _c:
                    _n = int(_c.execute(
                        "SELECT COUNT(*) FROM facts "
                        "WHERE superseded_by IS NULL").fetchone()[0])
                    _judged = int(_c.execute(
                        "SELECT COUNT(*) FROM facts WHERE superseded_by "
                        "IS NULL AND grounding_score IS NOT NULL"
                    ).fetchone()[0])
                    # LE DUE POPOLAZIONI, contate invece che nominate. Il
                    # messaggio elencava due cause alla pari; sul corpus
                    # reale pesano 6445 contro 32, e l'operatore andava a
                    # inseguire la piccola.
                    #
                    # In un try SUO: `source_signature` e' una colonna piu'
                    # giovane, e su uno store che non ce l'ha la query
                    # fallisce. Dentro il try grande faceva cadere anche la
                    # copertura — cioe' il dato che c'era gia' — e il
                    # referto rispondeva «UNKNOWN» a una domanda a cui
                    # sapeva rispondere. Preso in regressione, non a
                    # ragionamento: un test del 2026-07 e' andato rosso.
                    try:
                        _con_fonte_non_giud = int(_c.execute(
                            "SELECT COUNT(*) FROM facts WHERE superseded_by "
                            "IS NULL AND grounding_score IS NULL "
                            "AND source_signature IS NOT NULL "
                            "AND source_signature != ''").fetchone()[0])
                        _senza_fonte = int(_c.execute(
                            "SELECT COUNT(*) FROM facts WHERE superseded_by "
                            "IS NULL AND grounding_score IS NULL "
                            "AND (source_signature IS NULL "
                            "OR source_signature = '')").fetchone()[0])
                    except Exception:  # noqa: BLE001
                        # None, non 0: «non ho potuto separarle» non e'
                        # «sono zero», ed e' la distinzione che questo
                        # referto difende in ogni sua riga.
                        _con_fonte_non_giud = _senza_fonte = None
        except Exception:  # noqa: BLE001 — a doctor that hangs is a patient
            # NOT silently zero: a locked, corrupt or schema-drifted store
            # would then be indistinguishable from a healthy empty one, and
            # this check would print its most reassuring line exactly when
            # it could not look (adversarial review, 2026-07-28).
            _n = _judged = 0
            _con_fonte_non_giud = _senza_fonte = None
            _readable = False

        if not _readable:
            _coverage = ("coverage of the moat is UNKNOWN, not zero — the "
                         "store could not be read")
        elif _n:
            _coverage = (f"{_judged} of {_n} stored facts entailment-judged "
                         f"({100 * _judged / _n:.1f}%)")
        else:
            _coverage = "no facts stored yet, so nothing to have judged"

        if ce:
            if not _readable:
                add("moat-judge", WARN,
                    f"local CE gate model installed, but {_coverage}",
                    "check the store with `verimem status`; a store predating "
                    "the grounding_score column, locked or corrupt will fail "
                    "this read")
            elif _n and _judged / _n < _MOAT_COVERAGE_WARN:
                # DUE cause, e ora CONTATE invece che nominate alla pari.
                #
                # Questa riga asseriva: «on the MCP channel the judge loads
                # in the background: writes that arrive while it is warming
                # are admitted unjudged». Era una generalizzazione di UNA
                # osservazione (2026-07-30, un write con fonte non giudicato
                # su MCP), scritta come proprieta' del prodotto — e la
                # catena che ne e' seguita, il 2026-08-05, e' il motivo per
                # cui non si fa: ws5 l'ha letta qui e me l'ha passata come
                # misura, io l'ho messa in due commit e in un commento, poi
                # lei l'ha misurata sul canale SDK (4 thread simultanei,
                # tutti 42.60s, 0 NULL su 4) e l'ha ritirata. Nessuno aveva
                # inventato niente: il prodotto non distingueva una misura
                # da un'ipotesi, e chi legge non poteva farlo per lui.
                #
                # E le due cause non pesano uguale: sul corpus reale 6445
                # fatti senza fonte contro 32 con la fonte e senza verdetto.
                # Elencarle alla pari mandava l'operatore a impostare una
                # variabile d'ambiente per inseguire i 32.
                _riga = (f"local CE gate model installed (state here: "
                         f"{_stato_giudice}), but only {_coverage}")
                if _senza_fonte is not None and _con_fonte_non_giud is not None:
                    _riga += (f" — of the unjudged: {_senza_fonte} carry NO "
                              f"declared source (the moat had nothing to "
                              f"check) and {_con_fonte_non_giud} declared a "
                              f"source and still have no verdict")
                if _con_fonte_non_giud:
                    _riga += (" — for those the reason is NOT recorded per "
                              "fact; candidates are write-time grounding "
                              "switched off, a judge that failed to load, or "
                              "a judge still warming (observed once on the "
                              "MCP channel, 2026-07-30, and NOT reproduced on "
                              "the SDK channel on 2026-08-05)")
                _fix = ("pass source='<the evidence text>' on add() (or "
                        "--source on `verimem save`); a verified_by ref "
                        "records WHO vouches and does not run the check")
                if _con_fonte_non_giud:
                    _fix += (f" — that closes the {_senza_fonte}. For the "
                             f"other {_con_fonte_non_giud}, check "
                             f"ENGRAM_GROUNDING_WRITE in the writing "
                             f"process's env and `verimem doctor` there")
                add("moat-judge", WARN, _riga, _fix)
            else:
                add("moat-judge", OK,
                    f"local CE gate model installed — the grounding moat is ON "
                    f"with no llm (multilingual); {_coverage}")
        elif provider and provider != "mock":
            add("moat-judge", WARN,
                f"local CE gate model NOT installed; an llm provider is available "
                f"({provider}) — the moat runs only when you pass llm=... to "
                f"Memory; {_coverage}",
                "run `verimem warmup` to download the gate model (~656 MB), or "
                "pass llm= to Memory")
        else:
            add("moat-judge", FAIL,
                f"NO grounding judge: local CE model missing at "
                f"{_resolve_model_dir(None)} and no llm provider detected "
                f"(moat OFF) — {AVVISO_SENZA_GIUDICE}; {_coverage}",
                "run `verimem warmup` to download the published gate model "
                "(~656 MB, no account needed), or pass llm= to Memory")
    except Exception as e:  # noqa: BLE001
        add("moat-judge", WARN, f"probe failed: {e}")

    # -- offline pins ----------------------------------------------------------
    try:
        from .airgap import _OFFLINE_FLAGS
        set_flags = [f for f in _OFFLINE_FLAGS
                     if os.environ.get(f, "").strip().lower() in
                     ("1", "true", "yes", "on")]
        if set_flags:
            add("offline", OK, f"offline-pinned via {', '.join(set_flags)} "
                               "(no HF Hub round-trips)")
        else:
            add("offline", WARN,
                "no offline flag set — cold model loads may hit the HF Hub",
                "for air-gapped deploys set VERIMEM_OFFLINE=1 (see `verimem airgap`)")
    except Exception as e:  # noqa: BLE001
        add("offline", WARN, f"probe failed: {e}")

    # -- llm provider (names only — never values) ------------------------------
    try:
        from .llm import _autodetect_provider
        p = _autodetect_provider()
        if p and p != "mock":
            add("llm", OK, f"provider auto-detected: {p}")
        else:
            add("llm", WARN,
                "no llm provider detected — extraction from raw conversations "
                "and the highest-quality judge need one",
                "set an API key (e.g. ANTHROPIC_API_KEY) or run Ollama")
    except Exception as e:  # noqa: BLE001
        add("llm", WARN, f"probe failed: {e}")

    # -- gateway ---------------------------------------------------------------
    try:
        from ._compat import data_dir
        keys_db = data_dir() / "gateway_keys.db"
        if keys_db.exists():
            add("gateway", OK, f"keys db present ({keys_db.name}) — "
                               "`verimem gateway serve` ready")
        else:
            add("gateway", OK, "no gateway keys yet (only needed for the "
                               "self-host team server)")
    except Exception as e:  # noqa: BLE001
        add("gateway", WARN, f"probe failed: {e}")

    # -- confidenza vs verifica ------------------------------------------------
    # Misurato sul corpus vivo il 2026-07-30: i 35 fatti giudicati dal moat
    # stavano TUTTI a confidenza 0.5 esatta, i 4720 mai giudicati a 0.866 di
    # media con 293 a 1.0 — e per canale, system_hook 0.954 con zero giudicati,
    # agent_inference 0.876 con zero giudicati, user 0.652 con tutti i 35.
    # Chi ordina per confidenza mette i fatti verificati sotto quelli che si
    # sono auto-dichiarati certi.
    #
    # La confidenza non si ricalibra: significherebbe cambiare il senso di un
    # campo su migliaia di righe per far tornare un ordinamento. Il prodotto lo
    # DICE, che e' il mestiere di doctor.
    try:
        from ._compat import data_dir
        _db = data_dir() / "semantic" / "semantic.db"
        if not _db.exists():
            add("confidence-vs-verifica", OK, "nessuno store da esaminare")
        else:
            _con = sqlite3.connect(f"file:{_db}?mode=ro", uri=True)
            try:
                _n_g, _avg_g, _n_u, _avg_u = _con.execute(
                    "SELECT SUM(CASE WHEN grounding_score IS NOT NULL THEN 1 "
                    "ELSE 0 END), AVG(CASE WHEN grounding_score IS NOT NULL "
                    "THEN confidence END), SUM(CASE WHEN grounding_score IS "
                    "NULL THEN 1 ELSE 0 END), AVG(CASE WHEN grounding_score "
                    "IS NULL THEN confidence END) FROM facts "
                    "WHERE superseded_by IS NULL").fetchone()
            finally:
                _con.close()
            _n_g, _n_u = int(_n_g or 0), int(_n_u or 0)
            if _n_g < 5:
                # Sotto una manciata di fatti giudicati il confronto e' rumore,
                # e gridare su due righe sarebbe inventare una tendenza.
                add("confidence-vs-verifica", OK,
                    f"{_n_g} fatti giudicati dal moat: troppo pochi per "
                    f"confrontare le confidenze (ne servono 5)")
            elif _avg_g is not None and _avg_u is not None and _avg_g < _avg_u:
                add("confidence-vs-verifica", WARN,
                    f"la confidenza ordina AL CONTRARIO della verifica: i "
                    f"{_n_g} fatti giudicati dal moat stanno a "
                    f"{float(_avg_g):.3f} di media, i {_n_u} mai giudicati a "
                    f"{float(_avg_u):.3f}. Chi ordina per confidenza mette i "
                    f"fatti verificati sotto quelli che si sono "
                    f"auto-dichiarati certi.",
                    "usa grounding_score per la fiducia, non confidence: "
                    "`verimem facts list` e `hippo_facts_search` ora portano "
                    "entrambi. La confidenza e' un default per-canale, non "
                    "una scala comune.")
            else:
                add("confidence-vs-verifica", OK,
                    f"{_n_g} giudicati a {float(_avg_g or 0):.3f}, {_n_u} mai "
                    f"giudicati a {float(_avg_u or 0):.3f}")
    except Exception as e:  # noqa: BLE001 — un doctor non crolla su un check
        add("confidence-vs-verifica", WARN, f"probe failed: {e}")

    return checks


def worst_status(checks: list[dict[str, Any]]) -> str:
    order = {OK: 0, WARN: 1, FAIL: 2}
    return max((c["status"] for c in checks), key=lambda s: order.get(s, 2),
               default=OK)
