"""Le sonde di rumore contenevano fatti interi: in cinese una frase è un token.

IL DIFETTO, da ws5 il 2026-08-04 alle 02:55 provando il prodotto su lingue che
il corpus non ha mai visto: **12 sonde su 12** contaminate con cinese,
giapponese o thai, **0 su 12** senza (controprova). Il pavimento del rumore
scendeva da 0.8877 a 0.8823, e a quel punto «quanti abitanti ha Roma?» (0.8858)
**attraversa la soglia** — una domanda legittima classificata come rumore.

LA CAUSA, e la parte istruttiva è che la guardia c'era. `_MAX_WORDS_PER_FACT`
= 2 è documentata *esattamente* contro questo caso: senza il cap «a probe can
draw 3-4 words from ONE fact and nearly reconstruct it». Solo che conta parole
separate da SPAZI, e in cinese, giapponese, thai, lao o khmer gli spazi non ci
sono: `text.split()` restituisce **un token solo, la frase intera**. Il cap di
due parole per fatto ne concede quindi due… di cui una è tutto il fatto.

E la seconda rete cede per un motivo indipendente: la sonda viene scartata se
`probe.lower() not in originals`, cioè per **uguaglianza esatta**. Una sonda
che CONTIENE un fatto più qualche parola d'altro non è uguale a niente, e passa.

Due difetti su due assi diversi, e questa è la ragione per cui si curano
entrambi invece di scegliere: la segmentazione è la causa, ma il controllo di
inclusione è la rete che avrebbe dovuto reggere comunque — e che regge anche
per una lingua a cui nessuno ha ancora pensato.

⚠️ COSA RESTA APERTO E NON LO CHIUDE QUESTA CURA (dal referto di ws5): il
pavimento è tarato sul RIFERIMENTO sbagliato. Misurato: rumore alfabetico
0.8468, domande vere di altro dominio 0.8057 — **il rumore batte le domande
legittime**, perché non avendo direzione semantica finisce vicino al centroide,
e il centroide è vicino a tutto. Pulire le sonde alza la qualità della stima ma
non cambia che stimare il rumore sul rumore misuri la cosa sbagliata. Quello è
un cambio di design, non un difetto da riparare.
"""
from __future__ import annotations

import pytest

from verimem.relevance_floor import scrambled_probes_da_testi

#: Tre scritture senza spazi fra le parole. Non è un caso esotico: è come si
#: scrive per una parte grossa del mondo.
SENZA_SPAZI = {
    "cinese": [
        "北京是中国的首都并且拥有超过两千万居民",
        "上海的港口是世界上最繁忙的集装箱港口之一",
        "长江是亚洲最长的河流全长约六千三百公里",
        "黄河流域是中华文明最重要的发源地之一",
        "广州的年平均气温大约是二十二摄氏度",
        "深圳的人口在过去三十年里增长了十倍以上",
    ],
    "giapponese": [
        "東京は日本の首都であり人口は約千四百万人です",
        "富士山は日本で最も高い山で標高は三千七百七十六メートルです",
        "新幹線は時速三百二十キロメートルで走行します",
        "琵琶湖は日本最大の湖で面積は六百七十平方キロメートルです",
        "京都には千六百以上の仏教寺院が存在しています",
        "北海道の冬の平均気温は氷点下六度前後になります",
    ],
    "thai": [
        "กรุงเทพมหานครเป็นเมืองหลวงของประเทศไทยและมีประชากรมากกว่าสิบล้านคน",
        "แม่น้ำเจ้าพระยาไหลผ่านกลางเมืองและมีความยาวสามร้อยเจ็ดสิบกิโลเมตร",
        "ภูเขาดอยอินทนนท์เป็นยอดเขาที่สูงที่สุดในประเทศไทย",
        "จังหวัดเชียงใหม่ตั้งอยู่ทางภาคเหนือของประเทศไทย",
        "อ่าวไทยมีความลึกเฉลี่ยประมาณสี่สิบห้าเมตร",
        "เกาะภูเก็ตเป็นเกาะที่ใหญ่ที่สุดของประเทศไทย",
    ],
}

CON_SPAZI = [
    "Roma e' la capitale d'Italia e ha circa due milioni ottocentomila abitanti.",
    "Il Po e' il fiume piu' lungo d'Italia con seicentocinquantadue chilometri.",
    "Il Monte Bianco raggiunge i quattromilaottocentootto metri di altitudine.",
]


def _contamina(probes, testi) -> list[str]:
    """Le sonde che contengono un fatto INTERO — la definizione del guasto."""
    return [p for p in probes
            if any(t.strip() and t.strip() in p for t in testi)]


@pytest.mark.parametrize("lingua", sorted(SENZA_SPAZI))
def test_nessuna_sonda_contiene_un_fatto_intero(lingua):
    """Il cuore, ed è la misura di ws5 girata come presidio: erano 12 su 12."""
    testi = SENZA_SPAZI[lingua]
    probes = scrambled_probes_da_testi(testi, n=12, seed=7)
    sporche = _contamina(probes, testi)
    assert not sporche, (
        f"{len(sporche)} sonde su {len(probes)} in {lingua} contengono un "
        f"fatto intero: il rumore contiene segnale e il pavimento mangia le "
        f"domande vere.\nprima: «{sporche[0][:70]}…»")


def test_il_controllo_di_inclusione_regge_ANCHE_senza_segmentazione():
    """La seconda rete, presa da sola. Anche se un giorno arrivasse una
    scrittura che la segmentazione non sa spezzare, una sonda che contiene un
    fatto per intero non deve MAI entrare nel campione di rumore: è la
    differenza fra scartare per uguaglianza e scartare per inclusione."""
    testi = ["ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
             "ZYXWVUTSRQPONMLKJIHGFEDCBAzyxwvutsrqponmlkjihgfedcba9876543210"]
    for p in scrambled_probes_da_testi(testi, n=12, seed=3):
        for t in testi:
            assert t not in p, "una sonda ha inglobato un fatto per intero"


def test_le_lingue_con_gli_spazi_non_cambiano_comportamento():
    """Il verso opposto: la cura non deve toccare ciò che già funzionava.
    Senza questo presidio, spezzare i token lunghi potrebbe degradare la
    qualità delle sonde su tutte le lingue che gli spazi ce li hanno."""
    probes = scrambled_probes_da_testi(CON_SPAZI, n=12, seed=1)
    assert probes, "nessuna sonda generata su testo con gli spazi"
    assert not _contamina(probes, CON_SPAZI)
    for p in probes:
        assert len(p.split()) >= 4, (
            f"sonda troppo povera per stimare un pavimento: «{p}»")


@pytest.mark.parametrize("lingua", sorted(SENZA_SPAZI))
def test_le_sonde_si_generano_comunque(lingua):
    """Una cura che azzerasse le sonde spegnerebbe il pavimento invece di
    correggerlo — e un pavimento spento non si vede, come tutti i guasti muti
    di questo modulo."""
    assert scrambled_probes_da_testi(SENZA_SPAZI[lingua], n=12, seed=5), (
        f"nessuna sonda generata in {lingua}: la stima del rumore e' muta")
