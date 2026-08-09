"""«NON testato» faceva scattare il detector dei claim di test. E due sorelle.

TROVATO MISURANDO, non leggendo il codice. Il 2026-08-04 ho contato quanti fatti
vivi riceverebbero un warning L1 se `verimem save` chiamasse il gate: **3520 su
5781, il 60%**. Un tasso simile rende il gate inutilizzabile su quel canale — ma
due detector da soli fanno la maggioranza degli hit (**L1.13 2058 · L1.15
1560**), quindi ho letto un campione casuale di otto per ciascuno. Su L1.15
erano falsi positivi quasi tutti, con tre forme distinte:

    «confine anti-correlato NON TESTATO dichiarato»   -> SCATTA 'testato'
    «engram facts add ... --verified-by 'cli:cycle140'» -> SCATTA 'verified'
    «Il fact ha status verified/provisional/legacy»    -> SCATTA 'verified'
    «il modello rustc-verified sul repo»               -> SCATTA 'verified'

**① LA NEGAZIONE.** È la **terza** occorrenza della stessa classe in due giorni:
`unresolved` conteneva `RESOLVED` (curato in `e2d69715`), e ora «non testato» fa
scattare «testato». Un gate anti-confabulazione che blocca la **smentita** di un
claim invece del claim lavora esattamente al contrario: chi documenta «questo
non è stato testato» — cioè chi è onesto — si vede chiedere la prova di averlo
testato.

**② LA PAROLA È SINTASSI, NON ASSERZIONE.** `--verified-by` è il *nome di un
flag*; `status verified/provisional` è un *valore di enum*. Il fatto non
dichiara nulla su sé stesso: cita del codice. È il gemello esatto del caso
`min_status verified` trovato ieri liberando i sei fatti quarantinati a mano.

**③ LA PAROLA COMPOSTA.** `rustc-verified` è il nome di una configurazione.

LA NEGAZIONE NON SI RISCRIVE: `quantity_match._NEGATOR_RE` esiste già ed è stata
estesa a undici lingue il 2026-08-03 (`d06f1521`), proprio dopo aver scoperto
che il prodotto sapeva riconoscere una negazione italiana **in due posti diversi
e mai insieme**. Scriverne una terza qui sarebbe la classe ① — una copia invece
della superficie unica — commessa mentre si cura la ③. Quello che serve in più
non è il *lessico* ma la **portata**: il negatore deve stare vicino alla parola,
e non oltre una virgola o un «ma».

⚠️ I DUE VERSI, perché la cura sia una correzione e non uno spegnimento: i claim
veri devono continuare a scattare, `well-tested` compreso (è nel pattern come
alternativa esplicita, e la regola sul trattino non deve mangiarlo), e una
negazione che riguarda **un'altra** cosa nella stessa frase non deve zittire il
claim.
"""
from __future__ import annotations

import pytest

from verimem.l1_tested_detector import detect_unsupported_tested_claim

#: ① La parola NEGATA: il fatto dichiara che qualcosa NON è stato testato.
NEGATI = [
    "Il confine anti-correlato non e' stato testato.",
    "Questo modulo non e' verificato da nessun test.",
    "This boundary was not tested at all.",
    "Il comportamento al confine non e' mai stato validato.",
]

#: ②③ La parola come SINTASSI: nome di flag, valore di enum, nome composto.
SINTASSI = [
    "Il comando engram facts add -p '...' --verified-by 'cli:cycle140'.",
    "Il fact ha status verified/provisional/legacy.",
    "Chiamare hippo_facts_search con min_status verified restituisce zero item.",
    "Il bench misura il modello rustc-verified sul repo.",
]

#: I claim veri: la prova va chiesta, come prima.
CLAIM_VERI = [
    "Ho testato tutto il modulo.",
    "Il sistema e' stato verificato.",
    "The parser is well-tested.",
    "Tutto validato prima del rilascio.",
]


@pytest.mark.parametrize("prop", NEGATI)
def test_una_dichiarazione_NEGATA_non_e_un_claim(prop):
    """Il cuore: chi documenta di NON aver testato porta l'informazione più
    onesta che ci sia, e il gate gliela quarantina."""
    assert detect_unsupported_tested_claim(proposition=prop, verified_by=[]) is None, (
        f"«{prop}» dice il CONTRARIO di un claim di test e viene trattata come tale")


@pytest.mark.parametrize("prop", SINTASSI)
def test_il_nome_di_un_flag_o_un_valore_di_enum_non_e_un_claim(prop):
    """La parola compare perché il fatto cita del CODICE — un flag, un valore di
    parametro, un identificatore composto — non perché asserisca qualcosa su sé
    stesso."""
    assert detect_unsupported_tested_claim(proposition=prop, verified_by=[]) is None, (
        f"«{prop}» cita sintassi e viene letta come dichiarazione di verifica")


@pytest.mark.parametrize("prop", CLAIM_VERI)
def test_i_claim_VERI_continuano_a_chiedere_la_prova(prop):
    """Il verso che rende la cura una correzione. `well-tested` sta qui apposta:
    è un claim, e la regola sul trattino non deve mangiarlo."""
    assert detect_unsupported_tested_claim(proposition=prop, verified_by=[]) is not None, (
        f"«{prop}» dichiara un test senza prova e non viene piu' vista")


def test_una_negazione_che_riguarda_ALTRO_non_zittisce_il_claim():
    """IL PRESIDIO SULLA PORTATA. Se bastasse un negatore ovunque nella frase,
    qualunque fatto abbastanza lungo conterrebbe un «non» e spegnerebbe il
    detector — la cura diventerebbe un interruttore."""
    prop = "Il modulo non e' stato rilasciato, ma e' stato testato."
    assert detect_unsupported_tested_claim(proposition=prop, verified_by=[]) is not None, (
        "la negazione riguarda il rilascio, non il test: il claim resta un claim")


def test_la_prova_continua_a_zittire_il_detector():
    """La porta d'uscita legittima non si tocca."""
    assert detect_unsupported_tested_claim(
        proposition="Ho testato tutto il modulo.",
        verified_by=["pytest:test_modulo_PASS"]) is None
