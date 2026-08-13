"""Il negatore cinese era riconosciuto da mesi e il conflitto si vedeva 1 volta su 5.

`_NEGATOR_RE` contiene ``没有|不是|不会|不能|不|未|非`` dal 4 agosto. Il negatore
veniva trovato, il suo scope era corretto, e il flip **non usciva lo stesso**::

    系统已签名 / 系统未签名        jaccard 0.286   -> None
    文件已上传 / 文件未上传        jaccard 0.286   -> None
    测试通过了 / 测试没有通过      jaccard 0.500   -> None
    这个功能可以使用 / 这个功能不能使用  jaccard 0.400   -> None
    数据库连接成功 / 数据库连接不成功    jaccard 1.000   -> '成功'   ← l'unico

⇒ **Il pezzo esisteva e non era collegato.** La guardia di somiglianza pretende
un Jaccard ≥ 0.6 fra i token rimasti dopo la rimozione del negatore, e in una
scrittura senza spazi quella rimozione **riscrive i bigrammi che il negatore
attraversava**: due muoiono, uno nasce, il denominatore cresce e il numeratore
no. L'unico caso che passava è quello dove il negatore si AGGIUNGE senza
sostituire nulla (`连接成功` → `连接不成功`), dove la rimozione riporta esatto.

🔑 La stessa soglia 0.6 vuol dire «quasi identiche» per parole separate da spazi
e «quasi impossibile» per bigrammi CJK.

═══ ⚠️ TRE PASSAGGI, E OGNUNO HA RIBALTATO IL PRECEDENTE ═══

**① Misurare la componente non basta.** Sul solo Jaccard la cura dava 5/5; alla
porta dava **0/5**, peggio di prima. `negation_conflict` ha quattro guardie, e
normalizzare i token di contenuto senza normalizzare anche lo scope del negatore
ne spegne una in silenzio: il Jaccard tocca 1.000 mentre ``scope ∩ shared`` è
vuoto. Due lati che normalizzano diversamente.

**② Uno zero del banco negativo non vale, se non sai quale guardia lo produce.**
I casi duri qui sotto sono fermati dalla **terza** guardia — quella che la cura
poteva rompere — e non dal Jaccard, che li avrebbe scartati per la ragione
sbagliata rendendo il banco cieco.

**③ Lo sweep decide DOVE va la cura.** `content_tokens` non appartiene a questo
confronto: la usano `corroboration` e `facts_conflict`, più una ventina di punti
interni. La misura fatta qui autorizza questo confronto, non tutti — perciò la
cura vive in `_token_di_confronto`, locale.

📌 Le frasi sono composte: nel corpus ci sono 7 fatti su 10155 con caratteri
cinesi, e sono tutte misure sul prodotto. Il **criterio** dei casi duri no —
viene dal contratto di `negation_conflict`: «complete, not blocked» non flippa
«complete» perché il negatore scopa una parola che l'altra frase non contiene.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import negation_conflict

#: Affermazione e negazione della STESSA cosa: devono contraddirsi.
OPPOSTI = [
    ("系统已签名", "系统未签名", "签名"),
    ("文件已上传", "文件未上传", "上传"),
    ("测试通过了", "测试没有通过", "通过"),
    ("这个功能可以使用", "这个功能不能使用", "使用"),
    ("数据库连接成功", "数据库连接不成功", "成功"),
]

#: ⚠️ I DURI: contenuto quasi identico, polarità diversa, ma il negatore scopa
#: qualcosa che l'altra frase non dice. NON sono contraddizioni.
NON_OPPOSTI = [
    ("任务完成了", "任务完成了，没有阻塞"),
    ("系统已签名", "系统已签名，未加密"),
    ("测试通过了", "测试通过了，没有警告"),
    ("文件已上传", "文件已上传，未压缩"),
    ("数据库连接成功", "数据库连接成功，没有延迟"),
]


@pytest.mark.parametrize("a,b,atteso", OPPOSTI)
def test_una_frase_cinese_e_la_sua_negazione_si_contraddicono(a, b, atteso):
    """Il cuore. Quattro di questi cinque non uscivano prima della cura."""
    assert negation_conflict(a, b) == atteso, (
        f"«{a}» e «{b}» hanno polarità opposta sullo stesso contenuto: il "
        f"rilevatore non le vede, o restituisce un token diverso da {atteso!r}")


@pytest.mark.parametrize("a,b", NON_OPPOSTI)
def test_IL_NEGATORE_CHE_SCOPA_ALTRO_non_e_una_contraddizione(a, b):
    """⚠️ LA POPOLAZIONE OPPOSTA, e vale più della cura.

    Il confronto a caratteri alza la somiglianza di **tutte** le coppie cinesi,
    comprese quelle che non si contraddicono: è esattamente il modo in cui una
    cura su una metrica normalizzata produce falsi allarmi. Questi cinque casi
    sono la misura di quel rischio, e sono fermati dalla guardia sullo scope.
    """
    assert negation_conflict(a, b) is None, (
        f"«{a}» e «{b}» non si contraddicono — il negatore parla di qualcosa "
        f"che l'altra frase non dice — e vengono segnalate come conflitto: il "
        f"confronto a caratteri ha allargato troppo")


def test_IL_TOKEN_RESTITUITO_RESTA_LEGGIBILE():
    """⚠️ Un verdetto giusto con una diagnosi illeggibile è mezzo difetto.

    Il valore di ritorno è ciò che il chiamante MOSTRA a chi legge. Confrontando
    per caratteri, la scelta ingenua restituiva una sillaba: il giapponese
    passava da «され» a «さ» pur restando un flip corretto. Nessuna delle due
    popolazioni sopra lo avrebbe segnalato — passavano entrambe.
    """
    assert negation_conflict("システムは署名されました",
                             "システムは署名されません") == "され"
    for _a, _b, atteso in OPPOSTI:
        assert len(atteso) > 1


@pytest.mark.parametrize("a,b,atteso", [
    ("the system is signed", "the system is not signed", "signed"),
    ("система подписана", "система не подписана", "подписана"),
    ("il farmaco riduce la mortalita", "il farmaco non riduce la mortalita",
     "mortalita"),
])
def test_LE_LINGUE_CON_GLI_SPAZI_NON_CAMBIANO(a, b, atteso):
    """⚠️ La cura si attiva solo dove serve: se toccasse anche le lingue che
    già funzionavano, sarebbe un cambiamento molto più grande di quello che è
    stato misurato."""
    assert negation_conflict(a, b) == atteso
