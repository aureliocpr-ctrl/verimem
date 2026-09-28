"""Le due classi di scritture di `quantity_match` prendono ESATTAMENTE i blocchi
che il loro commento dichiara.

CodeQL #1310 (py/overly-large-range), letto e misurato il 2026-09-25: la classe
di `_SENZA_PAROLE_RE` dichiarava i CJK compatibili U+F900–U+FAFF, ma nel
sorgente l'estremo era 豈 U+8C48, il carattere unificato in cui la
normalizzazione NFC trasforma U+F900 e che a vista e' identico. L'intervallo
applicato era U+8C48–U+FAFF, 28.344 punti: dentro c'erano Yi, Vai, Cherokee,
Latino esteso D ed E e l'area d'uso privato, dove stanno i glifi Powerline e
Nerd Font dei prompt di terminale. Quei testi ricevevano bigrammi che non
dovevano avere, contro la promessa di `content_tokens`: le altre lingue non
sono toccate.
"""

from __future__ import annotations

from verimem import quantity_match as qm

_CJK = [(0x3040, 0x30FF), (0x31F0, 0x31FF), (0x3400, 0x4DBF),
        (0x4E00, 0x9FFF), (0xF900, 0xFAFF)]
_SENZA_PAROLE = _CJK + [(0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x0E00, 0x0E7F)]


def _presi(regex) -> set[int]:
    """I punti del piano base che la classe prende davvero."""
    return {c for c in range(0x10000) if regex.fullmatch(chr(c) * 2)}


def _dichiarati(intervalli) -> set[int]:
    return {c for a, b in intervalli for c in range(a, b + 1)}


def test_la_classe_senza_parole_prende_solo_i_blocchi_dichiarati():
    presi, dichiarati = _presi(qm._SENZA_PAROLE_RE), _dichiarati(_SENZA_PAROLE)
    in_piu = sorted(presi - dichiarati)
    assert not in_piu, (
        f"{len(in_piu)} punti presi oltre il dichiarato, da U+{in_piu[0]:04X} "
        f"a U+{in_piu[-1]:04X}: un estremo della classe non e' quello scritto "
        "nel commento")
    assert presi == dichiarati, "manca qualcosa di dichiarato"


def test_la_classe_cjk_prende_solo_i_blocchi_dichiarati():
    assert _presi(qm._CJK_RE) == _dichiarati(_CJK)


def test_i_glifi_d_uso_privato_non_diventano_bigrammi():
    """Dal lato di chi scrive: un prompt di terminale copiato in un fatto."""
    token = qm.content_tokens("main  build ready")
    assert "" not in token, (
        "due glifi Powerline sono diventati un bigramma di una scrittura senza "
        f"spazi: {sorted(token)!r}")


def test_il_cinese_resta_a_bigrammi():
    """Controllo positivo: la cura non tocca chi gia' funzionava."""
    assert {"样品", "含有", "毫克"} <= qm.content_tokens("样品-001含有11毫克。")
