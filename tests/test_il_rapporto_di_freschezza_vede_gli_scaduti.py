"""Il rapporto di freschezza vede anche i fatti oltre la loro validita'.

TERZA superficie della stessa famiglia, dopo `assess_freshness` e
`find_stale_facts`. Qui la cecita' era doppia:

① `facts_freshness_check` chiama `live` ogni fatto **non superseduto** — e un
   fatto scaduto e' non-superseduto, quindi era `live`;
② non poteva fare altrimenti: **il campo non arrivava**. `summary_topic`, da cui
   questo modulo prende i fatti, serviva un dizionario di nove chiavi in cui
   `valid_until` non c'era (misurato: `'valid_until' in f` -> False).

⇒ La cecita' non nasceva in `freshness_check`: nasceva a monte. La cura e' in due
punti — il campo nel payload (additivo, non filtra: stessa forma della riga che
sopra rende visibili i quarantinati) e il criterio qui.

📌 CONTA PERCHE' QUESTA LISTA E' QUELLA DELLA MANUTENZIONE: alimenta
`dashboard_overview_v2` ed e' esposta come `hippo_facts_freshness_check`. Un fatto
scaduto che il recall toglie e che il rapporto non mostra e' invisibile proprio a
chi lo cerca.

📌 PORTATA, misurata: sul corpus **0 fatti su 17.855 hanno `valid_until`** ⇒ oggi
non cambia nessun numero pubblicato. Serve il giorno in cui qualcuno scrive il
primo `--valid-until`.
"""
from __future__ import annotations

import time

from verimem.client import Memory
from verimem.freshness_check import facts_freshness_check

GIORNO = 86400.0


def _memoria(tmp_path):
    """Path ESPLICITO: `Memory()` senza path si aggancia alla prima data dir
    vista nel processo e con piu' test finirebbe nello store di un altro."""
    return Memory(tmp_path / "f.db")


# ---- il campo arriva fino a qui ----------------------------------------------

def test_il_payload_del_riepilogo_porta_la_scadenza(tmp_path):
    """🔑 LA PREMESSA, e va provata prima del resto: senza questo campo il
    criterio sotto non potrebbe esistere. Misurato prima della cura: le chiavi
    erano nove e `valid_until` non era fra quelle."""
    m = _memoria(tmp_path)
    scad = time.time() - GIORNO
    r = m.add("il feature flag del checkout resta acceso", topic="flag",
              valid_until=scad)
    assert r.get("id"), f"il banco: `add` non ha restituito un id ({r!r})"
    f = m.semantic.summary_topic("flag", max_facts=10)["facts"][0]
    assert "valid_until" in f, f"il payload deve portare la scadenza: {sorted(f)}"
    assert f["valid_until"] is not None, f"e valorizzata quando c'e': {f}"


# ---- e il rapporto lo vede ----------------------------------------------------

def test_un_fatto_scaduto_compare_fra_gli_stantii(tmp_path):
    """Scaduto ieri, scritto oggi: era `live` (non superseduto) e troppo giovane
    per la soglia d'eta', quindi non compariva da nessuna parte."""
    m = _memoria(tmp_path)
    m.add("il feature flag del checkout resta acceso", topic="flag",
          valid_until=time.time() - GIORNO)
    out = facts_freshness_check(m.semantic, "flag", threshold_days=30.0)
    assert out["n_stale"] == 1, f"un fatto oltre la validita' e' stantio: {out}"
    assert out["stale"][0]["reason"] == "valid_until", (
        f"e la riga deve dire quale causa l'ha accesa: {out['stale']}")


# ---- 🔑 COSA LA CURA NON DEVE ROMPERE ----------------------------------------

def test_un_fatto_vivo_e_recente_non_diventa_stantio(tmp_path):
    """CONTROLLO: la cura non declassa tutto. Nessuna scadenza, scritto ora."""
    m = _memoria(tmp_path)
    m.add("la sala macchine di Genova ha due gruppi elettrogeni", topic="sedi")
    out = facts_freshness_check(m.semantic, "sedi", threshold_days=30.0)
    assert out["n_stale"] == 0, f"un fatto vivo e nuovo non e' stantio: {out}"


def test_una_scadenza_ancora_valida_non_declassa(tmp_path):
    """CONTROLLO: `valid_until` NEL FUTURO e' un fatto vivo."""
    m = _memoria(tmp_path)
    m.add("il certificato del dominio e stato rinnovato a marzo", topic="rete",
          valid_until=time.time() + 30 * GIORNO)
    out = facts_freshness_check(m.semantic, "rete", threshold_days=30.0)
    assert out["n_stale"] == 0, f"una scadenza futura non declassa: {out}"
