"""Due popolazioni datate: il registro di eventi e l'appuntamento che si sposta.

IL RAMO `DATE` di ``_entita_diverse`` diceva una cosa sola — «date disgiunte ⇒
due eventi ⇒ coesistono» — e aveva TRE presidi verdi su quella popolazione e
ZERO sull'altra. Messo in matrice il 20/08::

                        devono COESISTERE            devono RITIRARE
    senza data          everyday (10 casi) ✅         everyday (3) ✅
    stessa data         —                            una_STESSA_data_ripetuta ✅
    date DISGIUNTE      it-iso, it-mese, en ✅✅✅      ← nessun presidio

Su un banco a due popolazioni, prima della cura: **COESISTONO 4/4 · RITIRANO 0/4.**
Non era un criterio che sbagliava qualche caso: era un COSTANTE.

⚠️⚠️ PERCHÉ QUESTO FILE ESISTE, e non basta il test che la cura fa passare.
La prima forma della guardia — «fondi se NON sono entrambe al passato» — chiude
la cella vuota **e apre un buco peggiore**, perché ``not(passato ∧ passato)`` è
vero anche quando NON SAPPIAMO. Misurato alla porta del prodotto::

    polarità «non passato»     ES «tuvo lugar el <data>»   2 scritti -> VIVI 1
                               DE «fand am <data> statt»   2 scritti -> VIVI 1
    polarità «prova positiva»  le stesse due               2 scritti -> VIVI 2

Cioè: un registro spagnolo o tedesco veniva **fuso**, e si perdono fatti — il
nodo più caro che abbiamo. Il danno non è simmetrico: senza cura un utente si
tiene un fatto obsoleto ACCANTO al nuovo, con quella polarità ne perde uno vero.

🔑 E il presidio che avrebbe dovuto vederlo NON lo vedeva:
``test_un_registro_datato_in_quattro_lingue`` interroga ``date_menzionate``, che
nessuna delle due polarità tocca ⇒ sarebbe rimasto **verde** mentre lo spagnolo
si rompeva. Un presidio a quattro lingue cieco al livello dove il danno accade.
Questo file misura alla PORTA: quanti fatti restano vivi dopo ``mem.add``.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.client import Memory


def _vivi(mem, topic: str) -> int:
    """⚠️ Non basta ``superseded_by IS NULL``: un quarantinato è
    non-superseduto e invisibile."""
    c = sqlite3.connect(str(mem.semantic.db_path))
    try:
        return c.execute(
            "SELECT COUNT(*) FROM facts WHERE topic=? AND superseded_by IS NULL "
            "AND status NOT IN ('quarantined','user_belief')", (topic,)
        ).fetchone()[0]
    finally:
        c.close()


def _scrivi(mem, topic, frasi):
    fonte = " ".join(frasi)
    for f in frasi:
        mem.add(f, topic=topic, source=fonte)
    return _vivi(mem, topic)


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


#: ⚠️ LA POPOLAZIONE CHE LA CURA NON DEVE TOCCARE, e le ultime due sono il
#: motivo per cui la polarità è «prova positiva»: sono lingue che gli elenchi
#: NON conoscono, e devono restare com'erano.
@pytest.mark.parametrize("lingua,frasi", [
    ("it", ["La consegna a Prato e' avvenuta il 2026-03-12.",
            "La consegna a Prato e' avvenuta il 2026-04-20."]),
    ("en", ["The audit in Turin took place on 2026-03-12.",
            "The audit in Turin took place on 2026-04-20."]),
    ("es", ["La entrega en Prato tuvo lugar el 2026-03-12.",
            "La entrega en Prato tuvo lugar el 2026-04-20."]),
    ("de", ["Die Lieferung in Prato fand am 2026-03-12 statt.",
            "Die Lieferung in Prato fand am 2026-04-20 statt."]),
])
def test_un_registro_di_eventi_datati_resta_intero(mem, lingua, frasi):
    """Due eventi accaduti in due date sono due fatti, in OGNI lingua."""
    vivi = _scrivi(mem, f"reg/{lingua}", frasi)
    assert vivi == 2, (
        f"[{lingua}] scritti 2, vivi {vivi}: il registro e' stato fuso")


#: La cella che era vuota: la data è un ATTRIBUTO che si sposta.
@pytest.mark.parametrize("lingua,frasi", [
    ("en", ["The compliance audit is on 2025-03-06.",
            "The compliance audit is on 2025-09-20."]),
    ("it", ["L'audit di conformita' e' il 6 marzo 2025.",
            "L'audit di conformita' e' il 20 settembre 2025."]),
])
def test_un_appuntamento_spostato_aggiorna_il_vecchio(mem, lingua, frasi):
    """Lo stesso audit riprogrammato non e' due audit."""
    vivi = _scrivi(mem, f"app/{lingua}", frasi)
    assert vivi == 1, (
        f"[{lingua}] scritti 2, vivi {vivi}: il vecchio non e' stato ritirato")


@pytest.mark.xfail(strict=True, reason=(
    "APERTO e DICHIARATO 2026-08-20: `stessa_frase_altra_data` chiede il testo "
    "IDENTICO tranne le date, quindi una RIFORMULAZIONE non la attiva. E' il "
    "prezzo scelto per non allargare un criterio sintattico su un fenomeno "
    "semantico. strict=True: il giorno che si copre, questo test FALLISCE e va "
    "tolto il marker — non resta un difetto silenzioso."))
def test_un_appuntamento_spostato_con_ALTRE_PAROLE_ancora_non_si_aggiorna(mem):
    frasi = ["The compliance audit is on 2025-03-06.",
             "The compliance audit has been moved to 2025-09-20."]
    assert _scrivi(mem, "app/riform", frasi) == 1
