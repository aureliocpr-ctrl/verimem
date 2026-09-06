"""Il modulo del tempo conosce la scadenza. Prima diceva `fresh` di un fatto scaduto.

MISURATO PRIMA DELLA CURA — stesso fatto, stesso istante, due porte::

    fatto 103a30c7a651 · valid_until 1788571647.5 · adesso 1788659283.3 -> scaduto
    recall                  -> non lo serve: «⚠ 1 fatto/i esclusi perche' SCADUTI»
    assess_freshness(fatto) -> {'status': 'fresh', 'age_days': 0.0, ...}

E non era una scelta dichiarata da qualche parte: `valid_until` aveva **0 occorrenze**
in `time_decay.py` (controllo positivo: `created_at`/`confidence` 16 nello stesso
file), cioe' era una dimensione che in quel modulo non esisteva. Stessa cecita' in
`find_stale_facts`, che guardava solo l'eta': un fatto scaduto IERI ma scritto OGGI
non compariva ne' fra gli stantii (troppo giovane) ne' fra i serviti (il recall lo
toglie) — invisibile proprio a chi fa manutenzione.

⚖️ PERCHE' `expired_reason` E NON SOLO `status`: `expired` significava gia' «piu'
vecchio di 3 emivite». Usare la stessa parola per due grandezze diverse e' il difetto
che il prodotto difende esplicitamente altrove («un solo segnale per due
significati»), e qui sarebbe stato nel vocabolario PUBBLICO di uno strumento MCP.
Lo `status` dice se il fatto vale; `expired_reason` dice perche'.

📌 PORTATA, misurata e dichiarata: sul corpus **0 fatti su 17.855 hanno `valid_until`**
⇒ oggi questa cura non cambia nessun numero pubblicato. Serve il giorno in cui
qualcuno scrivera' il primo `--valid-until`, ed e' il giorno in cui il difetto
avrebbe morso.
"""
from __future__ import annotations

import time

from verimem.time_decay import assess_freshness, find_stale_facts

GIORNO = 86400.0


class _Fatto:
    """Le funzioni sono PURE e prendono un oggetto con attributi: qui un doppio e'
    la cosa giusta, il difetto sta nella funzione e non nel percorso dei dati."""

    def __init__(self, *, eta_giorni=0.0, valid_until=None, fid="f1"):
        self.id = fid
        self.topic = "t"
        self.proposition = "il feature flag del checkout resta acceso"
        self.confidence = 0.9
        self.created_at = time.time() - eta_giorni * GIORNO
        self.valid_until = valid_until


# ---- la scadenza decide, e dice perche' --------------------------------------

def test_un_fatto_oltre_la_sua_validita_non_e_fresco():
    """Il recall lo toglie perche' scaduto; questa porta lo dichiarava fresco."""
    out = assess_freshness(_Fatto(eta_giorni=0.0, valid_until=time.time() - GIORNO))
    assert out["status"] != "fresh", (
        f"un fatto oltre `valid_until` non puo' essere fresco: {out}")
    assert out["expired_reason"] == "valid_until", (
        f"e deve dire che e' la SCADENZA, non l'eta': {out}")


def test_la_lista_degli_stantii_vede_anche_gli_scaduti():
    """Scaduto ieri, scritto oggi: non compariva da nessuna parte."""
    f = _Fatto(eta_giorni=0.0, valid_until=time.time() - GIORNO)
    out = find_stale_facts([f], threshold_days=30.0)
    assert "stale_facts" in out, f"il banco legge la chiave sbagliata: {sorted(out)}"
    trovati = [x["id"] for x in out["stale_facts"]]
    assert f.id in trovati, f"un fatto oltre la sua validita' deve comparire: {out}"
    assert out["stale_facts"][0]["reason"] == "valid_until", (
        f"e la riga deve dire quale delle due cause l'ha accesa: {out}")


# ---- 🔑 COSA LA CURA NON DEVE ROMPERE ----------------------------------------

def test_un_fatto_vivo_e_recente_resta_fresco():
    """CONTROLLO: la cura non declassa tutto. Nessuna scadenza, scritto ora."""
    out = assess_freshness(_Fatto(eta_giorni=0.0))
    assert out["status"] == "fresh", f"un fatto vivo e nuovo resta fresco: {out}"
    # ⚠️ `.get()` e non `[...]`: questa cella deve reggere anche SENZA la cura,
    # altrimenti cadrebbe per la CHIAVE MANCANTE invece che per il comportamento
    # — e non distinguerebbe piu' «la cura non c'e'» da «la cura ha rotto il caso
    # normale», che e' l'unica cosa che le si chiede di sorvegliare.
    assert out.get("expired_reason") is None, f"e non ha un motivo di scadenza: {out}"


def test_l_eta_continua_a_decidere_quando_non_c_e_scadenza():
    """CONTROLLO: il comportamento storico resta intatto — 400 giorni con emivita
    90 fanno `expired` per ETA', esattamente come prima della cura."""
    out = assess_freshness(_Fatto(eta_giorni=400.0))
    assert out["status"] == "expired", f"senza scadenza decide l'eta': {out}"
    # `.get()` per la stessa ragione della cella sopra: il campo e' nuovo, il
    # COMPORTAMENTO che questa cella sorveglia e' vecchio.
    assert out.get("expired_reason") in (None, "age"), f"il motivo e' l'eta': {out}"


def test_una_scadenza_ancora_valida_non_declassa():
    """CONTROLLO: `valid_until` NEL FUTURO e' un fatto vivo, non uno scaduto."""
    out = assess_freshness(_Fatto(eta_giorni=1.0, valid_until=time.time() + 30 * GIORNO))
    assert out["status"] == "fresh", f"una scadenza futura non declassa: {out}"
    assert out.get("expired_reason") is None


# ---- e un valore illeggibile non cambia il verdetto ne' fa cadere ------------

def test_una_scadenza_illeggibile_si_comporta_come_assente():
    """Un `valid_until` non numerico farebbe esplodere `float()`. La scelta e' la
    stessa di `client.py` («una data illeggibile non fa cadere nulla»): si comporta
    come un fatto senza scadenza, e il verdetto resta quello dell'eta'.
    ⇒ Questa cella esiste perche' una rilettura a freddo ha trovato la stessa
    omissione nella cura gemella DOPO che il ciclo RED->GREEN era gia' verde: un
    RED->GREEN prova la cura sui dati GIUSTI e sui dati ROTTI non dice niente.
    """
    out = assess_freshness(_Fatto(eta_giorni=0.0, valid_until="non-una-data"))
    assert out["status"] == "fresh", f"illeggibile ⇒ come assente: {out}"
    f = _Fatto(eta_giorni=0.0, valid_until="non-una-data")
    lista = find_stale_facts([f], threshold_days=30.0)
    assert lista["n_stale"] == 0, f"e non finisce fra gli stantii per sbaglio: {lista}"
