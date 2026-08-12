"""«480パレット**あります**» contro «320パレット**です**»: nessun conflitto visto.

Due frasi giapponesi che dicono quanti pallet ci sono nello stesso magazzino,
con due valori diversi. Misurato prima della cura::

    ヴェローナの倉庫には480パレットあります  ->  ('パレットあります', 480.0)
    ヴェローナの倉庫は320パレットです      ->  ('パレットです',   320.0)
    numeric_conflict                    ->  None

Due unità diverse ⇒ due grandezze diverse ⇒ nessuna contraddizione. Ma la
grandezza è la stessa: cambia il verbo, non il pallet.

═══ 🔑 LA CAUSA NON È LA LINGUA, È LA POSIZIONE DEL VERBO ═══

Si vede solo mettendo le due lingue senza spazi una accanto all'altra, ed è il
motivo per cui vale la pena scriverlo qui::

    ZH   有480个托盘  /  存放320个托盘   ->  ('个托盘', 480) e ('个托盘', 320)  ✅
    JA   480パレットあります / 320パレットです                                ❌

Verbi diversi in entrambe. In cinese il verbo **precede** il numero e resta
fuori dall'unità; in giapponese lo **segue** e ci finisce dentro. Stesso
parser, stesso difetto potenziale, esito opposto per l'ordine delle parole —
e per mesi la lettura era «il CJK è rotto», che avrebbe portato a curare anche
il cinese, dove non c'è niente da curare.

═══ ⚖️ UN CRITERIO, NON UNA LISTA DI VERBI ═══

Le desinenze giapponesi si scrivono in **hiragana** (okurigana) e le unità in
katakana o kanji: è ortografia, non vocabolario, quindi copre anche i verbi che
nessuno ha elencato. Stessa scelta di `_DATA_CJK` (`8月10日` copre due lingue
senza dizionario) e di `norm_unit` sui diacritici.

═══ ⚠️⚠️ IL PRESIDIO, e perché senza la cura è SBAGLIATA ═══

Misurato prima di scegliere, sulla popolazione opposta: diversi contatori
giapponesi **sono** hiragana, e la versione ingenua li cancella::

    つ   こ   ひとつ   まい   ほん   ぴき     ->  stringa VUOTA

`つ` è il contatore generico, `まい` conta i fogli, `ぴき` gli animali piccoli.
Se dopo il taglio non resta nulla, la parola ERA l'unità e si tiene intera.
Con il presidio: **11 casi su 11** — cinque code verbali tolte, sei unità
hiragana conservate.

📌 RESTA SCOPERTO il verbo in KANJI: «ミリグラム含まれています» -> «ミリグラム含»,
dove 含 è la radice di 含まれる. Dichiarato, non taciuto.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import norm_unit, numeric_conflict


def test_due_verbi_diversi_non_fanno_due_grandezze_diverse():
    """Il cuore: cambia il verbo, non il pallet."""
    a = "ヴェローナの倉庫には480パレットあります。"
    b = "ヴェローナの倉庫は320パレットです。"
    r = numeric_conflict(a, b)
    assert r is not None, "il conflitto giapponese resta invisibile"
    assert {r[1], r[2]} == {480.0, 320.0}, f"valori sbagliati: {r}"


@pytest.mark.parametrize("unita", ["つ", "こ", "ひとつ", "まい", "ほん"])
def test_LA_POPOLAZIONE_OPPOSTA_le_unita_hiragana_sopravvivono(unita):
    """⚠️ IL PRESIDIO. Senza, la cura cancella i contatori giapponesi.

    Sono unità legittime e frequenti: un taglio che le svuota non estende la
    copertura, la distrugge — e in modo silenzioso, perché un'unità vuota non
    dà errore, fa solo sparire il confronto.
    """
    assert norm_unit(unita), f"«{unita}» è stata svuotata dal taglio"


@pytest.mark.parametrize("frase_a,frase_b", [
    ("倉庫には480パレットあります。", "キャッシュは30分後に期限切れです。"),
    ("りんごが5つあります。", "本が3まいあります。"),
])
def test_LA_POPOLAZIONE_OPPOSTA_soggetti_diversi_non_vanno_in_conflitto(
        frase_a, frase_b):
    """Togliere la coda verbale rende più unità confrontabili fra loro: il
    rischio speculare è che diventino confrontabili anche cose che non lo sono.
    Il secondo caso è quello stretto — due unità hiragana **diverse** (`つ` e
    `まい`), che dopo il taglio restano diverse e non devono contendersi."""
    assert numeric_conflict(frase_a, frase_b) is None


@pytest.mark.parametrize("unita,atteso", [
    ("pallet", "pallet"),
    ("unità", "unita"),
    ("Stück", "stuck"),
    ("个托盘", "个托盘"),
])
def test_le_altre_lingue_non_sono_toccate(unita, atteso):
    """Il criterio è ancorato all'hiragana, che nelle altre lingue non esiste —
    cinese compreso, ed è la ragione per cui questa cura non poteva essere «una
    cura per il CJK»."""
    assert norm_unit(unita) == atteso
