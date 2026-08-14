"""Backward-compat bridge for the cycle #41 rename (hippoagent → engram)
plus the product-brand env prefix (Verimem, 2026-07-15).

Two surfaces are bridged here so existing user configurations keep working:

1. **Environment variables**: every ``HIPPO_*`` env var visible at process
   start is mirrored to ``ENGRAM_*`` (and vice versa) via
   :func:`init_env_aliases`. Existing ``HIPPO_HOSTED=1``, ``HIPPO_DATA_DIR``,
   ``HIPPO_AUTH_TOKEN``, etc. continue to work without code changes; new
   ``ENGRAM_*`` names are picked up by older code paths through the same
   mirror. The mirror uses :py:meth:`os.environ.setdefault` so an explicit
   value on one side never overrides an explicit value on the other.

   The same mirror covers ``VERIMEM_*`` — the PRODUCT prefix (PyPI name is
   ``verimem``; ``engram`` is the architecture package): ``VERIMEM_X`` is
   seen by every reader of ``ENGRAM_X`` / ``HIPPO_X`` without touching any
   call-site, and ``ENGRAM_X`` is mirrored back to ``VERIMEM_X`` for
   introspection. Unlike ``HIPPO_*`` this prefix is NOT scheduled for
   removal — it is the brand-forward name.

2. **User data directory**: :func:`data_dir` returns ``~/.engram`` if it
   exists, falls back to ``~/.hippoagent`` if only the old dir exists,
   otherwise creates ``~/.engram``. This keeps existing installations
   reading their data while new installations get the new path.

The module is intentionally tiny and stdlib-only — it's imported by
``engram/__init__.py`` and must not have any heavy dependencies.

Removal is NOT dated. A date lived here — «~2026-08-13 (3 months from
rename)» — and passed on 2026-08-14 with the module still in place. When it
does happen, all code is expected to use ``ENGRAM_*`` env names and the
``~/.engram`` path; this module can be deleted and ``HIPPO_*`` configs will
start failing.

⚠️ AND THE CLOCK HAS NOT STARTED, for a reason worth writing down. The
justification here used to read «by then any user still on the old names has
had 3 months of clear deprecation warnings to migrate». Measured 2026-08-13:
THERE IS NO SUCH WARNING. The single ``warnings.warn`` in this module (below)
fires only when the DATA_DIR aliases DISAGREE — someone who sets ``HIPPO_*``
CONSISTENTLY trips ``len(distinti) > 1`` false and hears nothing, by
construction — and no ``DeprecationWarning`` for ``HIPPO_*`` exists anywhere in
the package. The case the removal would break is exactly the case the warning
does not cover, and it is not hypothetical: our own ``~/.mcp.json`` sets
``HIPPO_DATA_DIR``, ``HIPPO_DISABLED`` and ``HIPPO_EAGER_PRELOAD``, all
consistent. ⇒ **Write the deprecation warning first; the three months start
from the day it exists, and only then is a removal date honest.**

⚠️⚠️ AND WRITING THE WARNING IS STILL NOT ENOUGH — the sentence promises
*«migrate»*, and for most of these names **there is nowhere to migrate to**.
Measured 2026-08-14 — surfaced while auditing the configuration the product is
actually run with, then reproduced independently with ``git grep`` over the
shipped package — on the eight ``HIPPO_*`` names that config sets::

    HIPPO_DATA_DIR ............. VERIMEM_ ENGRAM_
    HIPPO_HOSTED ............... VERIMEM_
    HIPPO_OFFLINE .............. VERIMEM_ ENGRAM_
    HIPPO_EAGER_PRELOAD ........ no new name
    HIPPO_ENCODE_DELEGATE_ONLY . no new name
    HIPPO_LOG_STDERR ........... no new name
    HIPPO_PRELOAD_TIMEOUT_S .... no new name
    HIPPO_DISABLED ............. no new name
                                 **five of eight have no destination**

⇒ It is not that users failed to migrate: **the product never built the place
to migrate to.** A deprecation warning telling someone to move to a name that
does not exist is worse than silence — it costs them the search. So the order
is: create the new names, THEN warn, THEN count the months, THEN date the
removal. Skipping straight to a date is how this docstring got here.
"""
from __future__ import annotations

import os
from pathlib import Path

_PREFIX_OLD = "HIPPO_"
_PREFIX_NEW = "ENGRAM_"
_PREFIX_BRAND = "VERIMEM_"

# Old data dir (cycle #1 — #40).
_OLD_DIR_NAME = ".hippoagent"
# New data dir (cycle #41+).
_NEW_DIR_NAME = ".engram"
# Canonical data dir since the total rename (0.6.0). Existing ~/.engram (and the
# older ~/.hippoagent) are still READ and NEVER migrated — a machine with a large
# ~/.engram store keeps using it untouched; only fresh installs create ~/.verimem.
_VERIMEM_DIR_NAME = ".verimem"


#: I nomi che lo specchio ha CREATO lui, per distinguerli da quelli che ha
#: scelto l'operatore. La funzione rendeva gia' il NUMERO — «for tests /
#: introspection», dice il suo docstring — e buttava via QUALI: e' la classe
#: che questo progetto paga di piu', la capacita' c'era e mancava il
#: collegamento.
#:
#: ⚠️ Non e' un dettaglio estetico. Misurato il 2026-08-08: 8 variabili del
#: prodotto prima dell'import, 21 dopo. Una diagnosi che elencasse
#: `os.environ` presenterebbe come «impostate dall'operatore» tredici
#: variabili create dalla libreria — e il docstring di `_ALIAS_DATA_DIR`, qui
#: sotto, racconta un incidente del 2026-07-30 in cui proprio una variabile
#: creata dallo specchio ha scavalcato quella scelta dall'operatore.
_CREATI: set[str] = set()


def alias_creati() -> frozenset[str]:
    """I nomi che :func:`init_env_aliases` ha creato in questo processo.

    Tutto cio' che sta in `os.environ` col nostro prefisso e NON e' qui dentro
    l'ha messo l'operatore (o l'ambiente che lo ospita).
    """
    return frozenset(_CREATI)


def init_env_aliases() -> int:
    """Mirror VERIMEM_* / HIPPO_* ↔ ENGRAM_* env vars (idempotent).

    Three passes, all :py:meth:`os.environ.setdefault`-semantics (an explicit
    value on one side never overrides an explicit value on the other):

    1. ``VERIMEM_X`` → ``ENGRAM_X`` (brand prefix feeds the canonical readers)
    2. ``HIPPO_X`` ↔ ``ENGRAM_X``  (legacy mirror, unchanged — running it
       after pass 1 makes the brand value transitively visible as ``HIPPO_X``)
    3. ``ENGRAM_X`` → ``VERIMEM_X`` (symmetry, for introspection)

    Returns the number of mirror entries added (for tests / introspection);
    :func:`alias_creati` says WHICH ones.
    """
    added = 0

    def _mirror(src_prefix: str, dst_prefix: str) -> int:
        n = 0
        # Snapshot keys to avoid mutation-during-iteration warnings.
        for k, v in list(os.environ.items()):
            if k.startswith(src_prefix):
                dst = dst_prefix + k[len(src_prefix):]
                if dst not in os.environ:
                    os.environ[dst] = v
                    _CREATI.add(dst)
                    n += 1
        return n

    added += _mirror(_PREFIX_BRAND, _PREFIX_NEW)   # VERIMEM_ → ENGRAM_
    added += _mirror(_PREFIX_OLD, _PREFIX_NEW)     # HIPPO_   → ENGRAM_
    added += _mirror(_PREFIX_NEW, _PREFIX_OLD)     # ENGRAM_  → HIPPO_
    added += _mirror(_PREFIX_NEW, _PREFIX_BRAND)   # ENGRAM_  → VERIMEM_
    return added


#: Ordine di precedenza degli alias, UNO SOLO per tutto il prodotto.
#:
#: ``HIPPO_DATA_DIR`` per primo, come gia' faceva ``config._data_root`` per una
#: ragione documentata e valida: e' l'handle storico dell'isolamento nei test, e
#: una macchina la cui shell esporta ``ENGRAM_DATA_DIR`` non deve poter
#: scavalcare un isolamento esplicito. Qui invece vinceva il primo fra
#: VERIMEM/ENGRAM/HIPPO — due precedenze deliberate, prese in due file, mai
#: confrontate. Il 2026-07-30, su una macchina con ``ENGRAM_DATA_DIR`` esportata,
#: puntavano a store DIVERSI: il prodotto scriveva in quello isolato e le
#: quattordici superfici che passano di qui (``backup``, ``doctor``, ``cli``,
#: ``dashboard_routes.auth``) leggevano la produzione.
#: ``VERIMEM_DATA_DIR`` per ULTIMA, e non e' una preferenza di brand: e' l'unica
#: che ``init_env_aliases`` puo' aver CREATO LEI all'import, copiandola dal
#: valore ereditato dalla shell (pass 3, ENGRAM -> VERIMEM). Metterla davanti a
#: ENGRAM l'ha resa velenosa: un chiamante che cancella HIPPO e imposta ENGRAM
#: — cioe' `tests/test_config_data_dir.py::test_engram_data_dir_env_is_honored`,
#: e il quickstart del README che imposta ENGRAM_DATA_DIR in .mcp.json — si
#: vedeva scavalcare da un mirror del valore che voleva sostituire. Trovato
#: dalla suite intera due ore dopo averlo scritto: i test mirati non lo videro
#: perche' partono da un ambiente che non ha il mirror.
_ALIAS_DATA_DIR = ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR")

_avvisato_alias_discordi = False


def _env_data_dir() -> str:
    """L'override della data dir dall'ambiente, o "" se nessun alias e' posto.

    Quando piu' alias sono posti su percorsi DIVERSI lo dice — una volta per
    processo. Sceglierne uno in silenzio e' esattamente cio' che ha prodotto la
    divergenza: chi aveva impostato due variabili credeva di aver isolato lo
    store, e meta' del prodotto guardava altrove senza dirlo. Il caso normale
    (il mirror di compatibilita' che popola tutti gli alias con lo STESSO
    valore) non produce rumore.
    """
    global _avvisato_alias_discordi
    posti = {n: v.strip() for n in _ALIAS_DATA_DIR
             if (v := os.environ.get(n, "")) and v.strip()}
    if not posti:
        return ""
    scelto = next(posti[n] for n in _ALIAS_DATA_DIR if n in posti)
    distinti = {str(Path(v).expanduser().resolve()) for v in posti.values()}
    if len(distinti) > 1 and not _avvisato_alias_discordi:
        _avvisato_alias_discordi = True
        import warnings
        warnings.warn(
            "DATA_DIR aliases disagree: "
            + ", ".join(f"{n}={posti[n]}" for n in _ALIAS_DATA_DIR if n in posti)
            + f" — using {scelto} (HIPPO_DATA_DIR wins, it is the explicit "
              "isolation handle). Unset the ones you did not mean.",
            RuntimeWarning, stacklevel=3)
    return scelto


def data_dir() -> Path:
    """Return the canonical Verimem data directory.

    Order of preference (total rename 0.6.0):

    1. If ``~/.verimem`` exists, use it (canonical).
    2. Else if ``~/.engram`` exists, use it (legacy — NEVER migrated).
    3. Else if ``~/.hippoagent`` exists, use it (older legacy install).
    4. Else create ``~/.verimem`` and use it.

    A machine with an existing ``~/.engram`` store keeps reading it untouched:
    the rename never moves user data (a ~/.engram store can be many GB). Only a
    fresh install with no prior dir gets the new ``~/.verimem`` default.

    Never throws — best-effort. Callers should still handle :py:class:`OSError`
    on subsequent disk operations.

    Env override: see :func:`_env_data_dir` — the SAME resolver
    ``config._data_root`` uses, so the two can no longer disagree.
    """
    override = _env_data_dir()
    if override:
        p = Path(override).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    home = Path.home()
    verimem_dir = home / _VERIMEM_DIR_NAME
    engram_dir = home / _NEW_DIR_NAME
    hippo_dir = home / _OLD_DIR_NAME

    if verimem_dir.exists():
        return verimem_dir
    if engram_dir.exists():
        return engram_dir      # legacy store — read as-is, never migrated
    if hippo_dir.exists():
        return hippo_dir
    verimem_dir.mkdir(parents=True, exist_ok=True)
    return verimem_dir
