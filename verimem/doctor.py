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
import time
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
#: La finestra dello scatto di undo (`undo_log`: created_at + 7 giorni).
#: Il check sui ritiri guarda SOLO dentro questa finestra, perche' fuori
#: «lo scatto non c'e' mai stato» e «lo scatto e' scaduto» danno lo stesso
#: risultato — e distinguere le due e' tutto il punto del check.
#: ⚠️ IMPORTATA, non riscritta. Era `7 * 86400.0` qui e `7 * 24 * 3600` in
#: `undo_log`: due copie dello stesso numero, e la correttezza di questo check
#: DIPENDE dalla loro uguaglianza — l'intero argomento («fuori dalla finestra
#: manca e scaduto sono indistinguibili, quindi guardo dentro») cade se il TTL
#: delle righe e la finestra divergono. Niente lo impediva. C'e' un test.
def _ttl_undo() -> float:
    from .undo_log import UNDO_TTL_SECONDS
    return float(UNDO_TTL_SECONDS)


_UNDO_TTL_S = _ttl_undo()

#: Sotto questa quota di ritiri ancora annullabili il check avvisa. Meta'
#: e' una scelta dichiarata, non una misura: il punto e' che il check
#: legge un RAPPORTO, quindi non lo si zittisce con un ritiro fortunato.
_UNDO_HANDLE_WARN = 0.5

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
        rel = None
        try:
            rel = p.relative_to(CONFIG.data_dir)
            p = d / rel
        except (ValueError, AttributeError):
            pass                     # path fuori dalla data dir: si usa com'e'
        # IL PERCORSO RELATIVO E NON `p.name`: `p.name` e' `semantic.db` per
        # TUTTE E DUE le disposizioni che questo prodotto incontra — la
        # canonica `<dati>/semantic/semantic.db` e la legacy piatta
        # `<dati>/semantic.db` — perche' butta via la sottocartella, che e'
        # l'unica cosa che le distingue. Il 2026-08-07, verificando un
        # salvataggio, il doctor diceva «semantic.db (assente)» con un
        # `semantic.db` presente nella cartella dati.
        etichetta = str(rel).replace("\\", "/") if rel is not None else p.name
        try:
            if p.exists():
                righe.append(f"{etichetta} {_misura(p.stat().st_size)}")
                continue
            # ...E DIRE DOVE. Un'assenza manda l'operatore a fare una cosa
            # sbagliata («il file c'e', il doctor sbaglia»); un'assenza che
            # dice dove sta il file lo manda a fare quella giusta («il tuo
            # store e' nel tracciato legacy, il prodotto ne usera' un altro»).
            # Stessa forma di `quarantined_by` e di «trovato ma nascosto».
            # Si guarda SOLO l'altra disposizione che il prodotto stesso
            # risolve (auto_dream_trigger.py:177-178 e altri quattro), mai in
            # giro per la cartella: `dreams/auto-*/semantic.db` ha lo stesso
            # nome ed e' una COPIA, indicarla manderebbe fuori strada.
            altra = d / p.name
            if (rel is not None and len(rel.parts) > 1
                    and altra.is_file() and altra != p):
                # NIENTE VIRGOLE nel frammento: le righe si uniscono con
                # ", " e una virgola qui dentro spezza il campo in due. Preso
                # dal mio stesso sondaggio, che tagliava il messaggio a meta'.
                righe.append(
                    f"{etichetta} (assente; ce n'e' uno in {p.name} da "
                    f"{_misura(altra.stat().st_size)} — tracciato legacy "
                    f"che il prodotto non usa)")
            else:
                righe.append(f"{etichetta} (assente)")
        except OSError:
            righe.append(f"{etichetta} (illeggibile)")
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
                # il nome INTERO del ramo: due rami come `alfa/control-room`
                # e `beta/control-room` condividono l'ultimo segmento, ed e'
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
        # DUE RESOLVER, DUE RISPOSTE. `_compat.data_dir()` — quello che questo
        # check usa — legge l'ambiente AL MOMENTO; `CONFIG` e' costruito
        # all'IMPORT e non si aggiorna. In un processo che imposta la cartella
        # DOPO aver importato verimem (chi lo incorpora come libreria, chi
        # cambia inquilino a processo vivo, ogni banco che monkeypatcha
        # l'ambiente) i due divergono, e allora QUESTA DIAGNOSI DESCRIVE UNO
        # STORE MENTRE IL PRODOTTO NE USA UN ALTRO. Misurato il 2026-08-08:
        #     _compat.data_dir()  -> \tmp\tmp.XOPKsjMKaK   (l'ambiente ora)
        #     CONFIG.data_dir     -> ~/.engram               (l'import)
        #     SemanticMemory().db_path -> quello di CONFIG
        # Sette moduli leggono il primo, dodici il secondo, e `backup`, `cli` e
        # `doctor` LI LEGGONO ENTRAMBI.
        # ⛔ Non si sceglie uno dei due qui: nasconderebbe la divergenza. Si
        # DICHIARA — quando due fonti non concordano, il fatto che non
        # concordino E' la diagnosi. E' diverso dall'avviso sui tre prefissi
        # piu' sopra: li' discordano tre VARIABILI, qui due modi di risolverle.
        _divergenza = ""
        try:
            from .config import CONFIG as _CFG
            if str(_CFG.data_dir) != str(d):
                _divergenza = (
                    f" ⚠️ this diagnosis reads {d}, but the product WRITES to "
                    f"{_CFG.data_dir} — the data dir was set AFTER verimem was "
                    f"imported, and CONFIG is fixed at import time")
        except Exception:  # noqa: BLE001
            pass
        add("data-dir", OK if writable else FAIL,
            f"{d} (writable={writable}; stores: {_stores_dichiarati(d)})"
            + _divergenza,
            ("set the data dir BEFORE importing verimem (env var, or the "
             "parent process), or restart the process after changing it"
             if _divergenza else
             None if writable else
             "fix directory permissions, or set VERIMEM_DATA_DIR"))
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
            holds_the_weights,
            judge_state,
            local_ce_available,
        )
        ce = local_ce_available()
        # I PESI, non solo i metadati. `local_ce_available()` risponde True su
        # una cartella che contiene il solo `config.json` — ed è voluto: è quel
        # file a far partire il tentativo, ed è il tentativo a produrre la
        # dichiarazione onesta sulla ricevuta. Ma qui si RIFERISCE, e il 17/08
        # questa riga diceva «the grounding moat is ON» con EXIT=0 su
        # un'estrazione interrotta, mentre un write reale tornava judged=False
        # e ammetteva un claim smentito dalla propria fonte.
        _pesi = holds_the_weights(_resolve_model_dir(None))
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

        if ce and not _pesi:
            # I metadati senza i pesi: `warmup` in questo stato dice «✓ moat
            # gate model already installed» e non riscarica (misurato il 17/08,
            # EXIT=0, cartella invariata), quindi il rimedio NON è eseguirlo di
            # nuovo — è togliere di mezzo la cartella a metà e poi eseguirlo.
            _dir = _resolve_model_dir(None)
            _meta = (f"{_dir} has the model metadata but none of its weights "
                     f"(model.safetensors / pytorch_model.bin) — the load "
                     f"fails at the first judged write")
            _togli = (f"delete {_dir} and run `verimem warmup` — running it on "
                      f"the half-extracted dir reports success without "
                      f"downloading anything")
            if provider and provider != "mock":
                # Un llm c'è: il CE locale è rotto, ma una strada per far
                # girare il moat esiste. Dire «moat OFF» e basta manderebbe a
                # riparare 737 MB di modello chi può già far giudicare — ed è
                # la stessa distinzione che il ramo del CE ASSENTE fa da
                # sempre (WARN con la strada, non FAIL).
                add("moat-judge", WARN,
                    f"the local CE gate model is INCOMPLETE: {_meta}; an llm "
                    f"provider is available ({provider}) — the moat runs only "
                    f"when you pass llm=... to Memory; {_coverage}",
                    f"{_togli}; or pass llm= to Memory")
            else:
                add("moat-judge", FAIL,
                    f"NO working grounding judge: {_meta} and no llm provider "
                    f"detected, so the moat does NOT run (moat OFF) — "
                    f"{AVVISO_SENZA_GIUDICE}; {_coverage}",
                    _togli)
        elif ce:
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
                # cui non si fa: da qui la frase e' stata ripresa come se
                # fosse una misura ed e' finita in due commit e in un
                # commento, finche' qualcuno l'ha misurata davvero sul
                # canale SDK (4 thread simultanei, tutti 42.60s, 0 NULL su
                # 4) e l'ha ritirata. Nessuno aveva inventato niente: il
                # testo non distingueva una misura da un'ipotesi, e chi
                # legge non poteva farlo al posto suo.
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

    # -- vettori di un altro modello --------------------------------------------
    # Misurato il 2026-08-07: un backup del corpus non e' piu' interrogabile dopo un
    # cambio di modello — gli snapshot di maggio hanno vettori a 384
    # dimensioni, il motore di oggi ne vuole 768, e la ricerca semantica
    # restituisce ZERO risultati SENZA DIRE PERCHE'. Nessun crash: il
    # silenzio, che e' peggio, perche' «nessun risultato» si legge come «non
    # c'era niente».
    #
    # Tutto quello che si confronta qui e' LETTO, niente e' assunto: le
    # dimensioni stanno nei blob, il modello dichiarato sta in
    # `facts.embedding_model` riga per riga, e la dimensione ATTESA la
    # pubblica il daemon di encode nel suo discovery. Se il daemon non c'e',
    # si dice che non si sa invece di indovinare: un rilevatore che tace
    # perche' non ha guardato e' peggio di uno che dichiara di non sapere.
    #
    # Regge su store ESTRANEI di proposito: e' nato per guardare backup e
    # snapshot altrui, quindi una colonna assente non lo fa sparire. Un
    # referto che se ne va sullo store che doveva diagnosticare e' inutile
    # due volte.
    try:
        import sqlite3 as _sq4

        from ._compat import data_dir as _dd4
        _dbv = _dd4() / "semantic" / "semantic.db"
        if _dbv.exists():
            _dim_attesa = None
            try:
                from . import encode_service as _svc
                _info = _svc.read_discovery() or {}
                _dim_attesa = int(_info.get("dim")) if _info.get("dim") else None
            except Exception:  # noqa: BLE001
                _dim_attesa = None
            with _sq4.connect(f"file:{_dbv}?mode=ro", uri=True) as _c4:
                _cols = {r[1] for r in _c4.execute("PRAGMA table_info(facts)")}
                _dims: dict[int, int] = {}
                if "embedding" in _cols:
                    for (_b,) in _c4.execute(
                            "SELECT embedding FROM facts "
                            "WHERE embedding IS NOT NULL"):
                        _k = len(_b) // 4
                        _dims[_k] = _dims.get(_k, 0) + 1
                _modelli: list[tuple[str, int]] = []
                if "embedding_model" in _cols:
                    _modelli = [(r[0] or "(declared by no row)", int(r[1]))
                                for r in _c4.execute(
                                    "SELECT embedding_model, COUNT(*) FROM facts "
                                    "WHERE embedding IS NOT NULL GROUP BY 1 "
                                    "ORDER BY 2 DESC")]
            from .config import CONFIG as _CFG
            _atteso_nome = getattr(_CFG, "embedding_model", "")
            _tot = sum(_dims.values())
            _fonte = (f"expected {_dim_attesa} (from the running encode "
                      f"daemon)" if _dim_attesa
                      else "expected dimension NOT known here — no encode "
                           "daemon is running to declare it")
            _righe_dim = " · ".join(f"{d}d: {n}" for d, n in
                                    sorted(_dims.items(), key=lambda x: -x[1]))
            _righe_mod = " · ".join(f"{m}: {n}" for m, n in _modelli[:3])
            if not _tot:
                add("embedding-model", OK,
                    "no vectors stored yet — nothing that a model change "
                    "could have orphaned")
            else:
                # ⚠️ SENZA DAEMON LA DIMENSIONE ATTESA NON SI CONOSCE, e il
                # ripiego era `max(_dims.values())`: prendere la dimensione
                # PIU' FREQUENTE come se fosse quella giusta. Su uno store
                # scritto INTERAMENTE da un altro modello quel massimo e'
                # l'intero corpus, quindi zero righe «cattive» e verdetto OK —
                # con il dettaglio che dichiara, nella stessa riga, «expected
                # dimension NOT known here». Il referto diceva «non lo so» e lo
                # stato diceva «va bene».
                # 🔑 Ma il NOME del modello che ha scritto le righe c'e' gia'
                # (`_modelli`, letto sopra) e non chiede nessun daemon: quando
                # la dimensione non si puo' confrontare, si confrontano i nomi.
                # E' un confronto vero al posto di un'euristica cieca.
                if _dim_attesa:
                    _buoni = _dims.get(_dim_attesa, 0)
                elif _modelli and _atteso_nome:
                    _buoni = sum(n for m, n in _modelli if m == _atteso_nome)
                else:
                    _buoni = max(_dims.values())
                _cattivi = _tot - _buoni
                _dettaglio = (f"{_tot} vectors — {_righe_dim}; {_fonte}"
                              + (f"; declared: {_righe_mod}" if _righe_mod
                                 else "; no embedding_model column"))
                if (_dim_attesa or (_modelli and _atteso_nome)) and not _buoni:
                    add("embedding-model", FAIL,
                        f"NO vector matches the engine in use: {_dettaglio}. "
                        f"Semantic search returns ZERO rows here, and returns "
                        f"it SILENTLY — an empty answer reads as 'there was "
                        f"nothing'",
                        "this store was written by a different embedding "
                        "model (a backup or an older snapshot). Re-embed it "
                        "with the current model, or query it with the model "
                        "that wrote it — configure ENGRAM_EMBEDDING_MODEL to "
                        f"match {_atteso_nome!r} only if that is what wrote "
                        "these rows")
                elif _cattivi:
                    add("embedding-model", WARN,
                        f"{_buoni} vectors match the engine and {_cattivi} do "
                        f"not: {_dettaglio}. The mismatched rows are stored "
                        f"but unreachable by semantic search",
                        "re-embed the older rows, or keep them for the audit "
                        "trail knowing recall will never return them")
                else:
                    add("embedding-model", OK,
                        f"all {_tot} vectors match the engine in use "
                        f"({_righe_dim}); {_fonte}")
    except Exception:  # noqa: BLE001 — un check non rompe il doctor
        pass

    # -- finestra di riparazione dei ritiri -------------------------------------
    # Un ritiro con lo scatto di undo si annulla in un click; senza, il fatto
    # e' perso. Sul corpus di casa il 2026-08-05: 105 ritiri negli ultimi
    # sette giorni e DUE con l'appiglio vivo — cioe' la build che scrive su
    # questo store il timone non ce l'ha, e nessuna superficie lo diceva:
    # serviva una query fatta apposta da chi gia' sospettava.
    #
    # SETTE GIORNI e' il TTL dello scatto, e non una scelta di comodo: fuori
    # da quella finestra «manca» e «e' scaduto» sono indistinguibili, quindi
    # contare tutto il corpus direbbe sempre che qualcosa non va — e un
    # allarme che suona sempre si impara a ignorare.
    try:
        import sqlite3 as _sq3

        from ._compat import data_dir as _dd2
        _dbr = _dd2() / "semantic" / "semantic.db"
        if _dbr.exists():
            _ora = time.time()
            _da = _ora - _UNDO_TTL_S
            with _sq3.connect(f"file:{_dbr}?mode=ro", uri=True) as _c2:
                _rit = int(_c2.execute(
                    "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL "
                    "AND superseded_at >= ?", (_da,)).fetchone()[0])
                _con_app = int(_c2.execute(
                    "SELECT COUNT(*) FROM facts f WHERE f.superseded_by IS NOT "
                    "NULL AND f.superseded_at >= ? AND EXISTS (SELECT 1 FROM "
                    "facts_undo_log u WHERE u.fact_id = f.id AND u.op_type = "
                    "'supersede' AND u.undone_at IS NULL AND "
                    "u.ttl_expires_at > ?)", (_da, _ora)).fetchone()[0])
                # LE ALTRE TRE COLONNE. «non si puo' annullare» aveva
                # QUATTRO cause e il messaggio ne mostrava una, mentre il
                # dato le distingue tutte — e portano ad azioni diverse.
                # 🔴 La piu' grave e' `undone`: uno snapshot GIA' USATO non
                # e' un guasto, e' la funzione che ha funzionato. Sommandolo
                # agli altri, su uno store dove qualcuno ha davvero
                # annullato dei ritiri questa superficie avrebbe segnalato
                # come rotto proprio l'uso corretto.
                def _conta_ritiri(cond: str, *extra: Any) -> int:
                    return int(_c2.execute(
                        "SELECT COUNT(*) FROM facts f WHERE f.superseded_by "
                        "IS NOT NULL AND f.superseded_at >= ? AND " + cond,
                        (_da, *extra)).fetchone()[0])
                _usati = _conta_ritiri(
                    "EXISTS (SELECT 1 FROM facts_undo_log u WHERE "
                    "u.fact_id = f.id AND u.op_type = 'supersede' AND "
                    "u.undone_at IS NOT NULL)")
                _scaduti = _conta_ritiri(
                    "EXISTS (SELECT 1 FROM facts_undo_log u WHERE "
                    "u.fact_id = f.id AND u.op_type = 'supersede' AND "
                    "u.undone_at IS NULL AND u.ttl_expires_at <= ?)", _ora)
                _mai = _conta_ritiri(
                    "NOT EXISTS (SELECT 1 FROM facts_undo_log u WHERE "
                    "u.fact_id = f.id AND u.op_type = 'supersede')")
                # CHI ha ritirato senza lasciare uno scatto. Da `b74ff6a0` il
                # principal porta `porta/attore`, quindi si puo' NOMINARE
                # invece di mandare l'operatore a indovinare. «non
                # registrato» e' un'informazione diversa da «non lo so».
                # ⚠️ La connessione e' `mode=ro`: la tabella NON si puo'
                # creare qui, e su uno store che non ce l'ha la query fallisce.
                # Il fallimento va assorbito QUI e non dal try esterno, che
                # farebbe sparire l'intero check — e un check assente non e'
                # un check verde. (La prima stesura chiamava un `_AUDIT_DDL`
                # che in questo modulo non esiste: il `NameError` finiva nel
                # try e il codice funzionava per caso.)
                _chi: list[str] = []
                try:
                    _chi = [
                        f"{r[0] or '(not recorded)'} {int(r[1])}"
                        for r in _c2.execute(
                            """SELECT (SELECT m.principal FROM audit_mutations m
                                     WHERE m.resource_id = f.id
                                       AND m.action = 'supersede'
                                     ORDER BY m.ts DESC LIMIT 1), COUNT(*)
                           FROM facts f
                           WHERE f.superseded_by IS NOT NULL
                             AND f.superseded_at >= ?
                             AND NOT EXISTS (SELECT 1 FROM facts_undo_log u
                                             WHERE u.fact_id = f.id
                                               AND u.op_type = 'supersede')
                           GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 3""",
                            (_da,))]
                except sqlite3.Error:
                    _chi = []          # store senza tabella di audit
            if not _rit:
                # zero su zero non e' «zero per cento»: senza ritiri non c'e'
                # niente da dire, e stampare un rapporto inventato e' la
                # stessa forma che questo file cura da stasera
                add("undo-window", OK,
                    "no retirements in the last 7 days — nothing to repair "
                    "and no ratio to report")
            else:
                # LE QUATTRO COLONNE, e la riga le mostra tutte. `undone`
                # NON e' un guasto: e' un ritiro che qualcuno ha annullato
                # davvero, cioe' il timone che ha funzionato. Sommarlo agli
                # altri faceva avvisare la superficie proprio dove l'uso era
                # corretto — quindi non entra nel rapporto.
                _dettaglio = (
                    f"{_rit} retirements in the last 7 days: {_con_app} still "
                    f"reversible · {_usati} already undone · {_scaduti} "
                    f"expired · {_mai} never had a snapshot. The window is "
                    f"the snapshot TTL (7 days) because outside it a missing "
                    f"handle is indistinguishable from an expired one")
                _giudicabili = _rit - _usati
                if not _giudicabili or _con_app / _giudicabili >= _UNDO_HANDLE_WARN:
                    add("undo-window", OK, _dettaglio)
                else:
                    # UNA cura per la causa che DOMINA, non l'elenco di tutte:
                    # un `fix` che le elenca sempre non aiuta piu' di uno che
                    # ne asserisce una a caso.
                    if _mai >= _scaduti:
                        _cura = (
                            "a retirement with NO snapshot means the code "
                            "that performed it did not take one. Who did: "
                            + (", ".join(_chi) or "unknown")
                            + " — `(not recorded)` means the retirement left "
                            "no audit row either, so the actor is unknown "
                            "rather than anonymous. A caller that sets "
                            "VERIMEM_ACTOR is recorded as `<port>/<actor>`")
                    else:
                        _cura = (
                            "these snapshots EXPIRED: the 7-day TTL is "
                            "shorter than the cadence at which retirements "
                            "get reviewed here — either review sooner or "
                            "raise the TTL")
                    add("undo-window", WARN, _dettaglio, _cura)
    except Exception:  # noqa: BLE001 — un check non rompe il doctor
        pass

    # -- affollamento dei topic -------------------------------------------------
    # Il 2026-08-09 e' emerso, da query SQL scritte a mano, che i fatti scritti
    # su un topic gia' usato sopravvivono molto meno di quelli su un topic
    # proprio: 94,4% contro 67,5% sul corpus di casa, e in un campione di
    # controllo 75 fatti su 75 topic distinti hanno dato ZERO ritirati.
    # Nessuna superficie del prodotto lo mostrava.
    # 🔴 La perdita e' SILENZIOSA per costruzione — un fatto ritirato resta nel
    # DB e sparisce solo dal recall — quindi chi non ha quella stanza perde i
    # fatti e non lo sa. Questo e' il posto dove il prodotto lo dice da solo.
    # ⚖️ E dice solo cio' che sa: due misure diverse sullo stesso topic e un
    # aggiornamento legittimo hanno la STESSA forma nel DB. Il segnale non e' il
    # tasso, e' la SEPARAZIONE fra le due popolazioni — un tasso da solo non
    # dice se e' alto (la trappola che ci ha morso cinque volte in un giorno).
    try:
        import sqlite3 as _sq6

        from ._compat import data_dir as _dd6
        _db6 = _dd6() / "semantic" / "semantic.db"
        if _db6.exists():
            _da6 = time.time() - _UNDO_TTL_S      # la finestra di undo-window
            with _sq6.connect(f"file:{_db6}?mode=ro", uri=True) as _c6:
                _t6 = list(_c6.execute(
                    """SELECT topic, COUNT(*),
                              SUM(CASE WHEN superseded_by IS NULL AND status
                                  NOT IN ('quarantined') THEN 1 ELSE 0 END),
                              SUM(CASE WHEN superseded_by IS NOT NULL
                                  THEN 1 ELSE 0 END)
                       FROM facts WHERE created_at >= ? GROUP BY topic""",
                    (_da6,)))
            _aff = [r for r in _t6 if int(r[1]) >= 2]
            _sol = [r for r in _t6 if int(r[1]) == 1]
            _na, _va = (sum(int(r[1]) for r in _aff),
                        sum(int(r[2] or 0) for r in _aff))
            _ns, _vs = (sum(int(r[1]) for r in _sol),
                        sum(int(r[2] or 0) for r in _sol))
            _persi = sum(int(r[3] or 0) for r in _aff)
            # zero su zero non e' «zero per cento»: senza topic affollati non
            # c'e' niente da confrontare, e stampare un rapporto inventato
            # sarebbe la stessa forma che questo file cura.
            if not _aff:
                add("topic-crowding", OK,
                    "in the last 7 days every topic carries a single write — "
                    "nothing to compare and no ratio to report")
            elif not _persi:
                add("topic-crowding", OK,
                    f"{_na} facts on {len(_aff)} shared topics in the last 7 "
                    f"days and none of them was retired")
            else:
                _peggio = ", ".join(
                    f"{r[0]} ({int(r[3] or 0)} of {int(r[1])})"
                    for r in sorted(_aff, key=lambda r: -int(r[3] or 0))[:2])
                _det = (
                    f"facts written in the last 7 days survive {_va}/{_na} on "
                    f"topics that already had another write, against "
                    f"{_vs}/{_ns} on topics used once. Worst: {_peggio}. A "
                    f"retired fact stays in the DB and leaves only the recall, "
                    f"so this loss is silent unless someone counts")
                # la SEPARAZIONE e' il segnale: senza il gruppo di controllo un
                # tasso non si sa se e' alto. Se i due tassi coincidono, i
                # ritiri non sono legati all'affollamento e non c'e' avviso.
                _ra = _va / _na if _na else 1.0
                _rs = _vs / _ns if _ns else _ra
                if _ra < _rs:
                    add("topic-crowding", WARN, _det,
                        "one topic per measurement "
                        "(`project/<theme>/<name>`) keeps siblings apart. "
                        "This check CANNOT tell a legitimate update from a "
                        "sibling retired by mistake — in the DB they have the "
                        "same shape; the asymmetry between the two "
                        "populations is where to look, not a verdict")
                else:
                    add("topic-crowding", OK, _det)
    except Exception:  # noqa: BLE001 — un check non rompe il doctor
        pass

    # -- copertura della tabella dei ranghi di fiducia --------------------------
    # Il rovescio della cura `4d8c48a0`: fermare il ritiro automatico dei fatti
    # a rango ignoto era giusto, ma lascia un ARRETRATO — quelle coppie non si
    # risolveranno mai da sole. Sullo store di casa il 2026-08-07 erano 65515
    # contro 14679 a rango davvero pari. Una cura che crea un arretrato
    # silenzioso non e' finita: il posto per dirlo e' qui, e la riparazione e'
    # in mano all'operatore (normalizzare gli stati, o aggiungerli alla
    # tabella).
    try:
        import sqlite3 as _sq5

        from ._compat import data_dir as _dd5
        from .semantic import _rango_di_fiducia
        _db5 = _dd5() / "semantic" / "semantic.db"
        if _db5.exists():
            with _sq5.connect(f"file:{_db5}?mode=ro", uri=True) as _c5:
                _righe = list(_c5.execute(
                    "SELECT status, COUNT(*) FROM facts "
                    "WHERE superseded_by IS NULL GROUP BY status"))
            _vivi = sum(n for _, n in _righe)
            _senza = {s: n for s, n in _righe if _rango_di_fiducia(s) is None}
            _n_senza = sum(_senza.values())
            if not _vivi:
                pass                       # store vuoto: niente da dire
            elif not _n_senza:
                add("trust-rank-coverage", OK,
                    f"tutti i {_vivi} fatti vivi hanno uno stato con un rango "
                    f"di fiducia noto")
            else:
                # I nomi servono (sono cio' che si aggiunge alla tabella) ma
                # non tutti: una riga di diagnosi con quaranta nomi non si
                # legge. I primi per numerosita', poi il conto del resto.
                _ord = sorted(_senza.items(), key=lambda kv: -kv[1])
                _mostra = ", ".join(f"{s} {n}" for s, n in _ord[:4])
                if len(_ord) > 4:
                    _mostra += f", +{len(_ord) - 4} altri"
                add("trust-rank-coverage", WARN,
                    f"{_n_senza} of {_vivi} live facts carry a status with no "
                    f"trust rank ({_mostra}) — they are NEVER auto-retired in "
                    f"a contradiction, so those clashes pile up unresolved "
                    f"instead of being decided wrongly",
                    "normalise those statuses, or add them to _STATUS_RANK "
                    "(verimem/semantic.py) — until then nothing is lost, "
                    "only left for human judgement")
    except Exception:  # noqa: BLE001 — un check non rompe il doctor
        pass

    # -- parametri in vigore ---------------------------------------------------
    # Il verdetto della fetta ⑥ (2026-08-08): «i parametri esistono e
    # funzionano, ma non sono ISPEZIONABILI». Misurato allora: 173 variabili
    # d'ambiente lette dal codice, 5 delle quali passano da `config.py`; 194
    # soglie numeriche, 181 fisse nel sorgente; e QUESTA superficie — l'unica
    # diagnosi del prodotto — non nominava ne' la soglia in vigore ne' una sola
    # variabile impostata. Provato con `ENGRAM_SUPERSEDE_SAME_SOURCE=0`, che
    # secondo l'archivio fa smettere la memoria di aggiornarsi: non compariva.
    try:
        from .grounding_gate import resolve_write_threshold_for
        from .local_grounding import get_local_threshold

        # QUALE giudice, perche' senza il numero non si interpreta: la stessa
        # installazione ammette a 40 col giudice locale e a 70 con gli altri.
        _giudice = "local"
        try:
            from .llm import _autodetect_provider
            _p = _autodetect_provider()
            if _p and _p != "mock":
                _giudice = _p
        except Exception:  # noqa: BLE001
            pass
        _soglia = resolve_write_threshold_for(_giudice)
        _dichiarata = get_local_threshold() if _giudice == "local" else None
        _nota = ""
        if _dichiarata is not None and _dichiarata > 90.0:
            # DUE decimali e non zero: il valore vero e' 99.64 e `:.0f` lo
            # stampava «100» — arrotondare proprio il numero che questa riga
            # denuncia come artefatto lo farebbe sembrare una cifra tonda
            # scelta da qualcuno, che e' l'opposto di cio' che e'.
            _nota = (f" (the installed model ships {_dichiarata:.2f}, ignored "
                     f"as a calibration artifact)")

        # COSA HA IMPOSTATO L'OPERATORE — e non cio' che si e' creato da solo:
        # `init_env_aliases` specchia ogni ENGRAM_X in HIPPO_X e VERIMEM_X
        # all'import (8 variabili prima, 21 dopo, misurato). Elencarle tutte
        # presenterebbe come scelta dell'utente cio' che ha fatto la libreria.
        from ._compat import alias_creati
        _creati = alias_creati()
        _suoi = sorted(
            k for k in os.environ
            if k.startswith(("VERIMEM_", "ENGRAM_", "HIPPO_"))
            and k not in _creati)
        # IL NOME SI', IL VALORE MAI per chiave/token/segreto: una diagnosi che
        # perde una credenziale e' peggio di nessuna diagnosi.
        def _vale(k: str) -> str:
            v = os.environ.get(k, "")
            if any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
                return "(set)" if v else "(empty)"
            return v[:24] if v else "(empty)"
        _elenco = ", ".join(f"{k}={_vale(k)}" for k in _suoi[:12])
        if len(_suoi) > 12:
            _elenco += f", +{len(_suoi) - 12} altre"
        add("parameters", OK,
            f"admission threshold in force: {_soglia:.0f}/100, decided by the "
            f"`{_giudice}` judge{_nota} — a write scoring below it is "
            f"quarantined. Env set by you: "
            + (f"{len(_suoi)} ({_elenco})" if _suoi
               else "none (every parameter is at its built-in default)")
            + f"; {len(_creati)} more were created by the "
              "VERIMEM_/ENGRAM_/HIPPO_ compatibility mirror at import and are "
              "NOT your choices")
    except Exception:  # noqa: BLE001 — un check non rompe il doctor
        pass

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
            # OK e non WARN: il suggerimento qui sotto dice «for air-gapped
            # deploys», quindi NON esserlo e' la condizione normale. Un avviso
            # su una configurazione normale trascina l'intero verdetto a 1 (il
            # contratto di `doctor` e' 0 all-ok / 1 warnings / 2 failures) e
            # rende `all-ok` irraggiungibile per chi installa seguendo il
            # README. L'informazione resta: cambia il verdetto, non il testo.
            add("offline", OK,
                "not offline-pinned — cold model loads may reach the HF Hub "
                "(normal outside an air-gapped deploy)",
                "for air-gapped deploys set VERIMEM_OFFLINE=1 (see `verimem airgap`)")
    except Exception as e:  # noqa: BLE001
        add("offline", WARN, f"probe failed: {e}")

    # -- llm provider (names only — never values) ------------------------------
    try:
        from .llm import _autodetect_provider
        p = _autodetect_provider()
        if p and p != "mock":
            # DICE COME LO SA. `_autodetect_provider` guarda i NOMI delle
            # variabili d'ambiente: trova una chiave IMPOSTATA, non una chiave
            # valida. Provarla vorrebbe una chiamata al provider, che `doctor`
            # non fa — starebbe fuori dal budget di ~2 s, fallirebbe da sola su
            # una macchina air-gapped, e spenderebbe soldi dell'operatore per
            # una diagnosi. Ma senza dirlo una chiave scaduta o revocata esce
            # come riga verde, ed è la stessa forma con cui `moat-judge`
            # certificava un modello assente e `gateway` un registro
            # illeggibile: dichiarare una capacità partendo da un indizio.
            # Qui l'indizio è tutto ciò che si può avere a costo zero, quindi
            # la cura non è accertare — è non lasciar credere di averlo fatto.
            add("llm", OK,
                f"provider auto-detected: {p} — from the environment variable "
                f"only; the key is NOT contacted here, so an expired or "
                f"revoked one looks exactly like a working one",
                "check it with your own first call; the moat and recall do "
                "not need an llm at all")
        else:
            # OK e non WARN: il README promette DUE VOLTE che l'llm non serve
            # («It works with no llm», riga 36; «No llm needed for the moat»,
            # riga 252). Finche' era un avviso, chi installava seguendo il
            # README eseguiva il comando che il README stesso prescrive per
            # verificare l'install e riceveva EXIT=1 — in un Dockerfile o in una
            # CI, un deploy fallito su una macchina perfetta. Quel che manca
            # senza provider resta scritto qui e nel `fix`.
            add("llm", OK,
                "no llm provider — the moat and recall do not need one; "
                "extraction from raw conversations and the llm-judge tier "
                "stay off",
                "to turn those on: set an API key (e.g. ANTHROPIC_API_KEY) "
                "or run Ollama")
    except Exception as e:  # noqa: BLE001
        add("llm", WARN, f"probe failed: {e}")

    # -- gateway ---------------------------------------------------------------
    try:
        from ._compat import data_dir
        keys_db = data_dir() / "gateway_keys.db"
        if keys_db.exists():
            # Contare invece di dedurre. Fino al 17/08 questa riga prometteva
            # «`verimem gateway serve` ready» sulla SOLA esistenza del file, ed
            # è la stessa forma con cui `moat-judge` certificava un giudice che
            # non c'era: un file che esiste non è un registro di chiavi
            # leggibile. Misurato quel giorno — con dentro del testo qualunque
            # il referto dava `✓ ready` mentre sqlite rispondeva «file is not a
            # database», cioè lo stato peggiore usciva con la riga più
            # rassicurante. In sola lettura, così il referto non crea nulla.
            import sqlite3 as _sq3
            try:
                with _sq3.connect(f"file:{keys_db}?mode=ro",
                                  uri=True) as _ck:
                    _n_chiavi = int(_ck.execute(
                        "SELECT COUNT(*) FROM gateway_keys").fetchone()[0])
            except _sq3.OperationalError:
                # Nessuna tabella ancora: il file c'è ma non è mai stato
                # inizializzato. È benigno — `gateway keys create` la crea —
                # e va detto senza allarmare.
                add("gateway", OK,
                    f"{keys_db.name} present but no key registry in it yet",
                    "run `verimem gateway keys create` to register the first "
                    "key (only needed for the self-host team server)")
            except Exception as _e:  # noqa: BLE001
                add("gateway", WARN,
                    f"{keys_db.name} is present but cannot be read as a key "
                    f"registry ({type(_e).__name__}) — a referto that only "
                    f"checks the file NAME would call this ready",
                    f"inspect {keys_db}; it is only needed for the self-host "
                    f"team server, so removing it is safe if unused")
            else:
                add("gateway", OK,
                    f"{_n_chiavi} gateway key(s) registered in "
                    f"{keys_db.name} — `verimem gateway serve` can "
                    f"authenticate them")
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
