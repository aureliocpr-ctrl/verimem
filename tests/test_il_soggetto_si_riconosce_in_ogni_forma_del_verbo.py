"""T212 — un fatto di terzi resta di terzi in ogni forma del verbo, nelle due lingue.

LA PROMESSA. `is_domain_professional` (subject_extract.py) dichiara: vero se il testo
«reads as a THIRD-PARTY professional/domain fact», e allora il gate tiene L1 come avviso
invece di trattenere (`_domain_precision_fp`, anti_confab_gate.py). E' la carve-out che
evita di mettere in quarantena i fatti dei professionisti per una parola.

COSA VEDEVA L'UTENTE (misurato il 24/09 sul tronco 20aa640d, 120 frasi parallele): il
soggetto si risolveva solo se `_VERB_MARK`, un elenco chiuso, conteneva il verbo. Esito
per forma, esenti/totale: passato composto it 15/15, en 15/15; passato semplice it 0/15,
en 6/15; presente it 0/15, en 3/15; imperfetto/progressivo it 0/15, en 15/15. «Maria ha
descritto la terapia» esente, «Maria descrisse la terapia» no: lo stesso fatto, trattenuto
o no secondo il tempo del verbo.

⚠️ LA LEZIONE NEL FILE (commento di SOFTWARE_HEADS): marcatori di verbo e teste software
sono ACCOPPIATI. Allargare i verbi rende risolvibili soggetti che prima non lo erano, e
se la testa software manca dalla lista, una frase su un proprio lavoro diventa «di terzi».
Per questo la cella tiene i NEGATIVI accanto ai positivi: frasi su un sistema, un software,
un applicativo, in ogni forma, devono restare NON esenti.

La griglia dei 120 casi e' quella misurata il 24/09 (stessi soggetti, verbi, forme);
accanto, verbi che la griglia non conteneva, perche' una lista che copre solo i cinque
verbi misurati passerebbe la prova senza mantenere la promessa.
"""
from __future__ import annotations

import os

import pytest

# encoder in-process, nessun daemon condiviso: come le altre celle della porta
os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.setdefault("VERIMEM_HOSTED", "1")

from verimem import subject_extract as se  # noqa: E402
from verimem.client import Memory  # noqa: E402

SOGGETTI = {"it": ["Maria", "Il medico", "Il dottor Rossi"],
            "en": ["Maria", "The doctor", "Dr. Rossi"]}
COMPLEMENTO = {"it": "la terapia al paziente.", "en": "the treatment to the patient."}
#: la griglia del 24/09: verbo -> {forma: (it, en)}
GRIGLIA = {
    "descrivere": {"composto": ("ha descritto", "has described"),
                   "semplice": ("descrisse", "described"), "presente": ("descrive", "describes"),
                   "imperfetto": ("descriveva", "was describing")},
    "spiegare": {"composto": ("ha spiegato", "has explained"),
                 "semplice": ("spiegò", "explained"), "presente": ("spiega", "explains"),
                 "imperfetto": ("spiegava", "was explaining")},
    "prescrivere": {"composto": ("ha prescritto", "has prescribed"),
                    "semplice": ("prescrisse", "prescribed"),
                    "presente": ("prescrive", "prescribes"),
                    "imperfetto": ("prescriveva", "was prescribing")},
    "confermare": {"composto": ("ha confermato", "has confirmed"),
                   "semplice": ("confermò", "confirmed"), "presente": ("conferma", "confirms"),
                   "imperfetto": ("confermava", "was confirming")},
    "riferire": {"composto": ("ha riferito", "has reported"),
                 "semplice": ("riferì", "reported"), "presente": ("riferisce", "reports"),
                 "imperfetto": ("riferiva", "was reporting")},
}
CASI = [(lingua, f"{s} {forme[forma][0 if lingua == 'it' else 1]} {COMPLEMENTO[lingua]}")
        for forme in GRIGLIA.values() for forma in forme
        for lingua in ("it", "en") for s in SOGGETTI[lingua]]

#: verbi FUORI dalla griglia: la lista deve valere per il registro, non per cinque verbi
FUORI_GRIGLIA = [
    "Il medico raccomandò una dieta leggera.",
    "La paziente riferiva un dolore al fianco.",
    "Il notaio firmò il contratto di vendita.",
    "L'avvocato sostiene che la clausola è nulla.",
    "La commissione decise di rinviare la gara.",
    "The nurse recommended a lighter diet.",
    "The lawyer argues that the clause is void.",
    "The committee decided to postpone the tender.",
    "Dr. Bianchi diagnosed a mild fracture.",
    "The patient describes a sharp pain.",
]

#: frasi su un PROPRIO lavoro: devono restare non esenti in ogni forma
NEGATIVI = [
    "Il sistema descrive lo stato del deploy.",
    "L'applicativo confermò il salvataggio.",
    "Il software spiegava l'errore nel log.",
    "Il deploy riferisce il risultato del test.",
    "The system describes the deploy state.",
    "The application confirmed the save.",
    "The new tests describe the regression.",
    "Io ho descritto la terapia al paziente.",
    "I described the treatment to the patient.",
    "We confirmed the fix.",
]


@pytest.mark.parametrize("lingua,frase", CASI, ids=[f"{c[0]}-{i:03d}" for i, c in enumerate(CASI)])
def test_la_griglia_misurata_e_tutta_di_terzi(lingua, frase):
    assert se.is_domain_professional(frase), (
        f"{frase!r}: soggetto {se.subject_of(frase)!r}, testa {se.subject_head(frase)!r}")


@pytest.mark.parametrize("frase", FUORI_GRIGLIA)
def test_anche_i_verbi_fuori_dalla_griglia(frase):
    assert se.is_domain_professional(frase), (
        f"{frase!r}: soggetto {se.subject_of(frase)!r}, testa {se.subject_head(frase)!r}")


@pytest.mark.parametrize("frase", NEGATIVI)
def test_NEGATIVO_il_proprio_lavoro_resta_trattenuto(frase):
    assert not se.is_domain_professional(frase), (
        f"{frase!r} letto come fatto di TERZI: soggetto {se.subject_of(frase)!r}, "
        f"testa {se.subject_head(frase)!r}")


def test_il_conteggio_della_griglia_e_quello_misurato():
    """La griglia non si ritaglia: sono i 120 casi del 24/09."""
    assert len(CASI) == 120


# --- LA SUBORDINATA IN TESTA (25/09, dalla CI di questa stessa richiesta) -----------
# «as you correctly said, the whole pipeline is perfect and bug-free» era trattenuta da
# L1; con le forme finite e' diventata esente (macOS, test_gate_redteam_fixes:
# 'model_claim' == 'quarantined'). Il confine cadeva su «said», il verbo della
# SUBORDINATA, e il soggetto della subordinata («as you correctly», testa «correctly»)
# passava per quello della frase. La stessa forma c'era gia' prima delle forme finite con
# i marcatori di `_VERB_MARK`: «Since the auditor confirmed, the pipeline is flawless»
# aveva il soggetto «auditor». Il soggetto di una frase che comincia con una subordinante
# e' quello della principale, dopo la prima virgola; senza virgola non si sa: vuoto.
SUBORDINATA_IN_TESTA_NON_ESENTE = [
    "as you correctly said, the whole pipeline is perfect and bug-free",
    "As you said, the deploy is flawless.",
    "Since the auditor confirmed, the pipeline is flawless.",
    "Because the reviewer approved, the code is bug-free.",
    "Come hai detto giustamente, la pipeline è perfetta e senza bug.",
    "Siccome il revisore ha approvato, la pipeline è perfetta.",
    "Mentre il medico descriveva la terapia, il sistema funzionava perfettamente.",
    "As you correctly said the release is rock-solid",
]

#: la popolazione opposta: la principale ha un soggetto di terzi, e resta di terzi
SUBORDINATA_IN_TESTA_DI_TERZI = [
    "As the surveyor said, the damage is repaired and verified.",
    "Come ha detto il perito, il danno è riparato e verificato.",
    "Secondo il notaio, il contratto è valido.",
    "According to the notary, the contract is valid.",
]


@pytest.mark.parametrize("frase", SUBORDINATA_IN_TESTA_NON_ESENTE)
def test_NEGATIVO_la_subordinata_in_testa_non_presta_il_suo_soggetto(frase):
    assert not se.is_domain_professional(frase), (
        f"{frase!r} letto come fatto di TERZI: soggetto {se.subject_of(frase)!r}, "
        f"testa {se.subject_head(frase)!r}")


def test_la_virgola_dei_decimali_non_chiude_la_subordinata():
    """Dal raggio sullo store vero (25/09): un fatto che cominciava con «Secondo» e
    aveva un numero con la virgola («99,52») prendeva il soggetto da dentro il numero."""
    frase = "Secondo il perito il danno vale 12,50 euro, e la riparazione è conclusa."
    assert "50" not in se.subject_of(frase), se.subject_of(frase)
    assert se.subject_head(frase) == "riparazione", se.subject_of(frase)


@pytest.mark.parametrize("frase", SUBORDINATA_IN_TESTA_DI_TERZI)
def test_con_la_subordinata_in_testa_conta_il_soggetto_della_principale(frase):
    assert se.is_domain_professional(frase), (
        f"{frase!r}: soggetto {se.subject_of(frase)!r}, testa {se.subject_head(frase)!r}")
    assert se.subject_head(frase) in {"damage", "danno", "contratto", "contract"}, (
        f"{frase!r}: di terzi per il soggetto della subordinata, non della principale: "
        f"{se.subject_of(frase)!r}")


# --- ALLA PORTA: cio' che l'utente vede nella ricevuta ------------------------------
# Un fatto di un professionista con una parola che fa scattare L1 (L1.15, «verificato»):
# col passato composto entrava con l'avviso, col passato semplice veniva TRATTENUTO.
# Il giudice e' iniettato a un punteggio alto e fisso: l'unica cosa che puo' trattenere
# e' uno strato lessicale. Nessun modello (sotto pytest l'embedder e' lo stub).

class _GiudiceFinto:
    """Giudice iniettato: punteggio fisso e alto, nessuna rete, nessun modello."""

    def complete(self, system, messages, **kw):  # noqa: ANN001
        return type("R", (), {"text": "Score: 98"})()


@pytest.fixture
def porta(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")
    return Memory(str(tmp_path / "porta.db"), grounding_llm=_GiudiceFinto())


def _strati(r: dict) -> list[str]:
    return [str(w.get("layer")) for w in (r.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


@pytest.mark.parametrize("fatto, fonte", [
    pytest.param("Il perito descrisse il danno come riparato e verificato.",
                 "Perizia: il perito ha trovato il danno riparato e verificato.",
                 id="perito-descrisse"),
    pytest.param("The notary verified the identity of the parties.",
                 "Deed: the notary verified the identity of the parties.",
                 id="notary-verified"),
])
def test_alla_porta_il_fatto_di_terzi_entra_con_l_avviso(porta, fatto, fonte):
    r = porta.add(fatto, source=fonte)
    disp = (r.get("adjudication") or {}).get("disposition")
    strati = _strati(r)
    assert disp == "admitted", (
        f"fatto di un professionista, sostenuto dalla fonte, giudice a 98: "
        f"disposizione {disp!r}, strati {strati}")
    assert "L1-domain-precision-observe" in strati, (
        f"ammesso senza dire che L1 aveva parlato ed e' stato tenuto come avviso: {strati}")


def test_NEGATIVO_alla_porta_la_stessa_frase_su_un_sistema_resta_trattenuta(porta):
    r = porta.add("Il sistema descrisse il danno come riparato e verificato.",
                  source="Log: il sistema segnala il danno riparato e verificato.")
    disp = (r.get("adjudication") or {}).get("disposition")
    assert disp != "admitted", (
        f"una frase sul proprio sistema e' entrata come fatto di terzi: {disp!r}, "
        f"strati {_strati(r)}")
