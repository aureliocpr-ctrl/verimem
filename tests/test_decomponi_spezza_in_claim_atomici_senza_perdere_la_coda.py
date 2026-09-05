"""`decomponi()` spezza una scrittura in claim atomici — senza perdere la coda,
senza fabbricare frammenti nudi, senza spezzare dentro le virgolette.

Funzione PURA, nessun gate, nessun modello: e' il «tempo 1» del design
docs/ricerca/2026-09-05-design-write-n-claim-atomici.md (approvato dal lead in
1b203709a2be2ed2, sezione A). Questo file e' il RED: scritto PRIMA del modulo.

OGNI CELLA HA IL NUMERO CHE L'HA DECISA (banchi in docs/stato-reale/banchi/):
  · soglia 1 parola — ws3-muro1-fase2-la-soglia-di-tre-parole-perde-la-coda:
    su 200 «<vero> ed e' verificata» l'intero ferma 115, l'atomico con soglia 3
    ne ferma 1, con soglia 1 ne ferma 135. La coda «e' verificata» ha due parole.
  · « ed » — ws3-muro1-le-due-regex-a-confronto: 301 fatti contengono « ed »,
    153 restavano interi.
  · apostrofo — ws3-muro1-l-apostrofo-spegne-l-eredita-del-soggetto: dopo `e'`
    il \\b non si accende mai; il corpus scrive `e'` 976 volte contro 357 `è`.
  · fusione dei nudi — ws3-muro1-il-falso-allarme-su-un-campione-non-scelto: i
    veri che cadevano erano frammenti degeneri («Indietro 16 con tracciato 0.»).
  · virgolette — ws3-muro1-le-quindici-sotto-decomposizione-atomica: la
    citazione spezzata («Il fatto 'La migrazione e' completata' da' None.»).

Le celle sono in DUE popolazioni, e si guardano entrambe: quelle in cui la
decomposizione DEVE isolare un pezzo (i falsi) e quelle in cui NON deve rompere
niente (i veri). Un decompositore che passa solo le prime e' un decompositore
ritagliato sulla cura.
"""
from __future__ import annotations

import pytest

from verimem.atomic_claims import decomponi

# ─────────────────────────────────────────────────────────────────────────────
# IDENTITA': una frase semplice resta UNA (N=1). E' il 51% delle scritture e
# tutte le 120 celle dei 60+60: la cura non tocca cio' che oggi funziona.
# ─────────────────────────────────────────────────────────────────────────────
SEMPLICI = [
    "Il direttore ha rassegnato le dimissioni il 4 maggio.",
    "La penale e' di 500 euro al giorno.",
    "The technician tested the plant.",
    "",
    "   ",
]


@pytest.mark.parametrize("testo", SEMPLICI)
def test_una_frase_semplice_resta_una(testo: str) -> None:
    out = decomponi(testo)
    assert len(out) == 1, out
    assert out[0].strip() == testo.strip() or (not testo.strip() and out == [testo])


# ─────────────────────────────────────────────────────────────────────────────
# COORDINATE: «A, e B» -> [A, B]; « ed » davanti a vocale; « and ».
# ─────────────────────────────────────────────────────────────────────────────
def test_spezza_sulla_coordinata_e() -> None:
    out = decomponi("Il tecnico ha collaudato l'impianto e ha firmato il verbale.")
    assert len(out) == 2, out
    assert out[0].startswith("Il tecnico ha collaudato")
    assert "firmato il verbale" in out[1]


def test_spezza_su_ed_davanti_a_vocale() -> None:
    # 301 fatti del corpus contengono « ed »; con la regex del 04/09 restavano interi.
    out = decomponi("Il comando warmup e' iniziato alle 14:50:24 ed e' finito alle 14:53:19.")
    assert len(out) == 2, out
    assert "iniziato alle 14:50:24" in out[0]
    assert "finito alle 14:53:19" in out[1]


def test_spezza_su_and_in_inglese() -> None:
    out = decomponi("The technician tested the plant and signed the report, and the feature is verified.")
    assert len(out) == 3, out
    assert "feature is verified" in out[-1]


# ─────────────────────────────────────────────────────────────────────────────
# SOGLIA 1 PAROLA: la coda corta NON si scarta. E' il numero che decide tutto:
# 115/200 -> 1/200 -> 135/200.
# ─────────────────────────────────────────────────────────────────────────────
def test_la_coda_di_due_parole_non_viene_scartata() -> None:
    out = decomponi("La funzionalita' funziona ed e' verificata.")
    assert len(out) == 2, out
    assert "verificata" in out[1], out


def test_la_coda_di_una_parola_non_viene_scartata() -> None:
    out = decomponi("L'implementazione e' finita e collaudata.")
    assert len(out) == 2, out
    assert "collaudata" in out[1], out


# ─────────────────────────────────────────────────────────────────────────────
# EREDITA' DEL SOGGETTO: il pezzo che comincia con un verbo riceve il soggetto
# del pezzo precedente — anche quando il verbo e' scritto `e'` con l'apostrofo,
# che e' la grafia del corpus (976 contro 357).
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("verbo", ["è", "e'"])
def test_il_pezzo_che_inizia_col_verbo_eredita_il_soggetto(verbo: str) -> None:
    out = decomponi(f"Il comando warmup {verbo} iniziato alle 14:50 ed {verbo} finito alle 14:53.")
    assert len(out) == 2, out
    assert out[1].lower().startswith("il comando warmup"), out[1]


def test_il_soggetto_ereditato_e_quello_del_pezzo_precedente_non_del_primo() -> None:
    out = decomponi("Il tecnico ha collaudato l'impianto e il verbale e' stato firmato ed e' stato archiviato.")
    assert len(out) == 3, out
    assert out[2].lower().startswith("il verbale"), out[2]


# ─────────────────────────────────────────────────────────────────────────────
# FUSIONE DEI NUDI: un pezzo che dopo lo split non ha ne' un verbo ne' un
# soggetto risolvibile NON diventa un claim: si fonde col precedente. E' la
# regola che protegge i veri di ieri («Indietro 16 con tracciato 0.», L1.17).
# ─────────────────────────────────────────────────────────────────────────────
def test_un_frammento_senza_verbo_si_fonde_col_precedente() -> None:
    testo = ("Dopo git rebase --abort il ramo risulta avanti 9 e indietro 16 con tracciato 0.")
    out = decomponi(testo)
    # «indietro 16 con tracciato 0» non ha un verbo: non deve uscire da solo
    assert all("indietro 16" not in p.lower() or "avanti 9" in p.lower() for p in out), out


def test_nessun_pezzo_esce_senza_un_verbo_finito() -> None:
    out = decomponi("Il deposito ha quattro banchine e un montacarichi e due rampe.")
    # «un montacarichi» e «due rampe» sono complementi, non claim: restano nel primo
    assert len(out) == 1, out


# ─────────────────────────────────────────────────────────────────────────────
# VIRGOLETTE: mai spezzare dentro « », " ", ' '. Uso contro menzione.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("testo", [
    "Il fatto 'Il lavoro e' completato' da' completion e il fatto 'La migrazione e' completata' da' None.",
    'La frase "il collaudo e\' concluso e firmato" viene fermata e la frase "il verbale e\' pronto" passa.',
    "Il messaggio «iniziato e finito» e' un titolo e non un claim.",
])
def test_non_spezza_dentro_le_virgolette(testo: str) -> None:
    out = decomponi(testo)
    for p in out:
        # ogni pezzo deve avere le virgolette bilanciate: nessuna citazione tagliata.
        # L'apice singolo NON si conta: in questo corpus e' tre volte piu' spesso un
        # accento («e'», «da'») che una virgoletta — la cella dedicata sta sotto.
        assert p.count('"') % 2 == 0, p
        assert p.count("«") == p.count("»"), p


def test_la_citazione_intera_resta_nello_stesso_pezzo() -> None:
    out = decomponi("Il fatto 'Il lavoro e' completato' da' completion e il fatto 'La migrazione e' completata' da' None.")
    assert len(out) == 2, out
    assert "'Il lavoro e' completato'" in out[0]
    assert "'La migrazione e' completata'" in out[1]


# ─────────────────────────────────────────────────────────────────────────────
# I DUE VERI DI IERI, come popolazione protetta: nessun frammento degenere.
# ─────────────────────────────────────────────────────────────────────────────
def test_ogni_pezzo_ha_almeno_un_soggetto_o_e_fuso() -> None:
    testo = ("L'ultimo run di ci concluso su main e' un success sullo SHA 397c6375, "
             "creato alle 22:30 e finito alle 22:32.")
    out = decomponi(testo)
    for p in out:
        low = p.lower()
        # «finito alle 22:32» da solo e' un completamento nudo: non deve esistere
        assert not low.startswith("finito"), out
        assert not low.startswith("creato"), out


# ─────────────────────────────────────────────────────────────────────────────
# PUREZZA e FORMA: stessa entrata, stessa uscita; ogni pezzo e' una frase chiusa.
# ─────────────────────────────────────────────────────────────────────────────
def test_e_deterministica_e_non_muta_l_ingresso() -> None:
    testo = "Il tecnico ha collaudato l'impianto e ha firmato il verbale."
    copia = str(testo)
    a, b = decomponi(testo), decomponi(testo)
    assert a == b
    assert testo == copia


def test_ogni_pezzo_e_una_frase_chiusa_con_la_maiuscola() -> None:
    for p in decomponi("Il tecnico ha collaudato l'impianto e ha firmato il verbale."):
        assert p[0].isupper(), p
        assert p.endswith("."), p


# ─────────────────────────────────────────────────────────────────────────────
# DUE FORME per due layer. Misurato il 05/09 sui 200 «<vero> + coda»: con il
# soggetto ereditato L1 ferma 101/200 (la carve-out di terzi esenta «Aurelio e'
# verificata»), con la forma NUDA 145/200 (L1.20 riconosce «E' verificata»);
# l'intero 114. Il moat invece vuole il soggetto. Lo stesso claim, due grafie.
# ─────────────────────────────────────────────────────────────────────────────
def test_la_forma_nuda_lascia_la_coda_senza_soggetto() -> None:
    testo = "Il comando warmup e' iniziato alle 14:50 ed e' finito alle 14:53."
    con = decomponi(testo)
    nuda = decomponi(testo, eredita_soggetto=False)
    assert len(con) == len(nuda) == 2, (con, nuda)
    assert con[1].lower().startswith("il comando warmup"), con[1]
    assert nuda[1].lower().startswith("e' finito"), nuda[1]


def test_le_due_forme_hanno_lo_stesso_numero_di_claim() -> None:
    for testo in ("La funzionalita' funziona ed e' verificata.",
                  "L'implementazione e' finita e collaudata.",
                  "Il tecnico ha collaudato l'impianto e ha firmato il verbale, e la funzionalita' e' verificata."):
        assert len(decomponi(testo)) == len(decomponi(testo, eredita_soggetto=False)), testo
