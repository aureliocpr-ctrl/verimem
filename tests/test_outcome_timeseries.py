"""FORGIA pezzo #224 — Wave 23: outcome timeseries.

Per-day (or per-week) success/failure breakdown across episodes.
Powers the "trends over time" view: are we improving?

Bucketing: bucket="day" → 86400s windows; bucket="week" → 7-day.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _FakeEp:
    outcome: str = "success"
    created_at: float = 0.0


def test_empty_returns_empty_buckets():
    from verimem.outcome_timeseries import outcome_timeseries

    out = outcome_timeseries([])
    assert out["buckets"] == []
    assert out["bucket_kind"] in ("day", "week")


def _base_dello_stesso_giorno(ora_di_lancio: float) -> float:
    """La base che una cella usa quando i suoi eventi devono cadere TUTTI nello
    stesso giorno UTC.

    Ancorata a MEZZOGIORNO UTC del giorno in cui la suite gira: resta dentro
    `window_days=30` (non serve alzarlo) e mette 12 ore di margine da entrambi
    i confini, cosi' una cella puo' aggiungere minuti o ore senza cambiare
    giorno.

    ⚠️ PRIMA RESTITUIVA L'OROLOGIO, e negli ultimi 120 s del giorno UTC gli
    eventi cadevano su due giorni: `assert 2 == 1`, ~1 run su 720.

    ⛔ NON e' un pattern nuovo: il file curava gia' lo stesso difetto in
    `test_one_bucket_per_day` (timestamp fisso + `window_days` alto) e in
    `test_week_bucketing` (ancoraggio al lunedi'). Qui si usa l'ancoraggio,
    che lascia i parametri del prodotto ai loro valori veri.
    """
    return ora_di_lancio - (ora_di_lancio % 86400.0) + 43200.0


def test_one_bucket_per_day():
    from verimem.outcome_timeseries import outcome_timeseries

    # CYCLE #15 fix: usa timestamp DETERMINISTICO (mezzogiorno UTC fissato)
    # invece di time.time(). Con time.time() il test era brittle: se 'now'
    # cade vicino a midnight UTC, base-86400-100 può finire 2 giorni prima
    # invece di 1, producendo 3 bucket invece dei 2 attesi.
    # Fissato a 2026-01-15 12:00:00 UTC (lontano da midnight boundaries).
    base = 1_768_521_600.0  # 2026-01-15 12:00:00 UTC (mezzogiorno, no boundary issue)
    eps = [
        _FakeEp("success", created_at=base),
        _FakeEp("success", created_at=base + 3600),  # same day
        _FakeEp("failure", created_at=base - 86400 - 100),  # day before
    ]
    # window_days alto per non scartare il timestamp deterministico.
    out = outcome_timeseries(eps, bucket="day", window_days=99999)
    # We see 2 distinct days.
    assert len(out["buckets"]) == 2


def test_success_failure_counts_per_bucket():
    from verimem.outcome_timeseries import outcome_timeseries

    base = _base_dello_stesso_giorno(time.time())
    eps = [
        _FakeEp("success", created_at=base),
        _FakeEp("success", created_at=base + 60),
        _FakeEp("failure", created_at=base + 120),
    ]
    out = outcome_timeseries(eps, bucket="day")
    # All on the same day.
    assert len(out["buckets"]) == 1
    bucket = out["buckets"][0]
    assert bucket["n_success"] == 2
    assert bucket["n_failure"] == 1


def test_window_days_filters_old():
    from verimem.outcome_timeseries import outcome_timeseries

    base = time.time()
    eps = [
        _FakeEp("success", created_at=base),
        _FakeEp("failure", created_at=base - 86400 * 100),  # 100 days ago
    ]
    out = outcome_timeseries(eps, bucket="day", window_days=30)
    # Only the recent one survives.
    assert len(out["buckets"]) == 1
    assert out["buckets"][0]["n_success"] == 1


def test_buckets_sorted_chronologically():
    from verimem.outcome_timeseries import outcome_timeseries

    base = time.time()
    eps = [
        _FakeEp("success", created_at=base - 86400 * 5),
        _FakeEp("success", created_at=base - 86400 * 1),
        _FakeEp("success", created_at=base - 86400 * 3),
    ]
    out = outcome_timeseries(eps, bucket="day")
    starts = [b["bucket_start"] for b in out["buckets"]]
    assert starts == sorted(starts)


def test_includes_date_str():
    from verimem.outcome_timeseries import outcome_timeseries

    eps = [_FakeEp("success", created_at=time.time())]
    out = outcome_timeseries(eps)
    assert "date" in out["buckets"][0]
    # ISO format YYYY-MM-DD prefix.
    assert len(out["buckets"][0]["date"]) >= 10


def test_week_bucketing():
    """Two events 3 days apart should land in the same week bucket.

    Brittleness fix (cycle #88-CI 2026-05-16): the previous version used
    ``time.time()`` as base, so when the run happened on Fri/Sat/Sun the
    ``base + 3 days`` event crossed an ISO-week boundary and produced 2
    buckets instead of 1. We now floor ``time.time()`` to the current
    week's Monday 00:00 UTC so:
      * ``base`` always lands on a Monday (within window).
      * ``base + 3 days`` always lands on the Thursday of the same week.
    """
    from datetime import datetime, timedelta, timezone

    from verimem.outcome_timeseries import outcome_timeseries

    now_dt = datetime.now(timezone.utc)
    monday_dt = (now_dt - timedelta(days=now_dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    base = monday_dt.timestamp()
    eps = [
        _FakeEp("success", created_at=base),
        _FakeEp("success", created_at=base + 86400 * 3),
    ]
    out = outcome_timeseries(eps, bucket="week", window_days=30)
    # Single week bucket.
    assert len(out["buckets"]) == 1
    assert out["buckets"][0]["n_success"] == 2


def test_payload_shape_complete():
    from verimem.outcome_timeseries import outcome_timeseries

    out = outcome_timeseries([])
    for k in ("buckets", "bucket_kind", "window_days"):
        assert k in out


def test_PRESIDIO_la_base_del_banco_non_dipende_dall_ora_di_lancio():
    """I tre eventi che le celle costruiscono devono cadere nello STESSO giorno
    UTC, a qualunque ora giri la suite.

    ⚠️ QUESTA CELLA ESISTE PERCHE' IL DIFETTO E' NEL BANCO, NON NEL PRODOTTO.
    Con eventi a cavallo di mezzanotte due bucket sono la risposta GIUSTA: e'
    la cella che assume «tutti nello stesso giorno» senza garantirlo. Misurato
    il 2026-09-20: `assert 2 == 1` su ubuntu py3.10 nella conferma di main su
    `4ce8c2f9`, verde nella conferma successiva — 120 s su 86400, ~1 run su 720.

    Il file curava gia' questo difetto in DUE celle (`test_one_bucket_per_day`
    con un timestamp fisso, `test_week_bucketing` ancorando al lunedi'), con la
    spiegazione scritta accanto. Questa era rimasta indietro: la cura non e'
    nuova, e' quella di casa applicata dove mancava.
    """
    from verimem.outcome_timeseries import _bucket_floor

    rotti = []
    una_mezzanotte = 1_789_948_800.0  # 2026-09-20 00:00:00 UTC
    for passo in range(0, 86400, 30):          # un'ora di lancio ogni 30 s
        ora_di_lancio = una_mezzanotte - passo
        base = _base_dello_stesso_giorno(ora_di_lancio)
        giorni = {_bucket_floor(base + d, "day") for d in (0.0, 60.0, 120.0)}
        if len(giorni) != 1:
            rotti.append(ora_di_lancio)
    assert not rotti, (
        f"la base dipende dall'ora di lancio: {len(rotti)} istanti su 2880 "
        f"producono eventi su piu' di un giorno (il primo: {rotti[0]}). "
        "Una cella che asserisce «un solo bucket» li' fallisce con 2 == 1"
    )
