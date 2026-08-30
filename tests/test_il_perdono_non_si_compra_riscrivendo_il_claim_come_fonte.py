"""Il perdono di `L1.13` non si compra passando il claim come fonte.

LA CURA CHE QUESTO TEST PRESIDIA (28/08, `e3ecd7f1`) era giusta e resta: il
detector non riceveva la fonte e fermava fatti VERI — un verbale d'ufficio
(«la pratica e' stata chiusa») con la fonte al 99,9. La cura passa `source` e
perdona quando il participio che ha fatto scattare il match **e' scritto nella
fonte**.

CIO' CHE LA CURA NON NOMINAVA, e che un banco indipendente ha misurato
(`docs/stato-reale/banchi/ws3-il-perdono-si-compra-riscrivendo-il-claim-come-fonte.py`,
**5 su 5**): **chi scrive la fonte puo' essere chi scrive il claim.** Passando la
stessa frase come `source`, il match e' verbatim **per costruzione** e il perdono
diventa una scelta del chiamante invece di una proprieta' della fonte.

IL CRITERIO DELLA GUARDIA — dichiarato, perche' il DoD lo chiede e perche' la
forma del criterio conta piu' del suo esito:

    Il perdono si applica SOLO se la PROVENIENZA del write non e' `agent_claim`.

**Non e' una somiglianza di testo, ed e' deliberato.** Un confronto testuale —
verbatim o per soglia — ripeterebbe a un livello piu' in la' il difetto che sta
curando: e' aggirabile **per riformulazione**, come un banco terzo ha gia'
mostrato sul fail-closed anti-auto-sorgente (3 su 3). La provenienza non cambia
riscrivendo la frase, quindi la guardia regge alla riformulazione **per
costruzione**, non per fortuna — ed e' il vincolo posto in sede di voto: *«il
criterio sia sulla PROVENIENZA, non sulla SOMIGLIANZA»*.

⚠️ IL LIMITE, dichiarato qui perche' non sia scoperto dopo: `writer_role` e' una
**dichiarazione di chi chiama** (`gate_router.classify_provenance` lo dice nei
suoi commenti, ed e' una scelta di sicurezza gia' presa altrove nel prodotto).
Chi ingerisce davvero un documento ha la strada esplicita — `writer_role`
`external_content` o `user` — e la riottiene dichiarandola. ⇒ **La guardia alza
il costo dell'aggiramento da «riformula una frase» a «dichiara il falso su un
campo di provenienza». Non lo rende impossibile, e non lo pretende.**

I casi sono quelli del banco, appaiati (nessuno porta parole da collaudo:
«verified»/«tested» sveglierebbero `L1.15`, un detector diverso, e un banco che
varia due cose insieme non puo' attribuire l'effetto a una).
"""

from __future__ import annotations

import pytest

from verimem.gate_router import AGENT_CLAIM, EXTERNAL_CONTENT, USER_INPUT
from verimem.l1_completion_detector import (
    detect_unsupported_completion_claim as detect,
)

#: le cinque frasi del banco terzo, due lingue, nessuna parola da collaudo.
CLAIMS = [
    "The due-diligence review was completed before the acquisition closed.",
    "La pratica e' stata chiusa prima della scadenza.",
    "The compliance audit was completed by the external firm.",
    "The database migration was completed in production.",
    "Il deploy in produzione e' stato completato.",
]


@pytest.mark.parametrize("claim", CLAIMS)
def test_senza_fonte_resta_fermato(claim: str) -> None:
    """CONTROLLO CHE DEVE POTER FALLIRE: senza fonte il detector prende questi
    claim. Se ne lasciasse passare uno, le celle sotto misurerebbero un
    detector che non vede quel claim, non l'effetto della fonte."""
    assert detect(proposition=claim, verified_by=None, source=None) is not None


@pytest.mark.parametrize("claim", CLAIMS)
def test_la_fonte_eco_non_compra_il_perdono(claim: str) -> None:
    """Il claim ripassato come fonte, con la provenienza dell'agente."""
    assert detect(proposition=claim, verified_by=None, source=claim,
                  provenance=AGENT_CLAIM) is not None


def test_regge_alla_riformulazione_e_non_solo_alla_copia() -> None:
    """La condizione posta in sede di voto: una fonte RIFORMULATA — stesso
    contenuto, parole diverse — resta fermata. Una guardia testuale cadrebbe
    qui; una guardia sulla provenienza no, perche' non guarda il testo."""
    claim = "The database migration was completed in production."
    riformulata = ("We finished moving the database over to the production "
                   "environment earlier today, with no issues.")
    assert detect(proposition=claim, verified_by=None, source=riformulata,
                  provenance=AGENT_CLAIM) is not None


def test_il_verbale_di_terzi_resta_perdonato() -> None:
    """LA CURA DEL 28/08 NON DEVE TORNARE INDIETRO: il caso per cui e' nata —
    un fatto VERO la cui fonte porta lo stesso participio — continua a passare
    quando la provenienza non e' quella dell'agente."""
    claim = "L'istruttoria e' stata chiusa dal responsabile del procedimento."
    fonte = ("Verbale del 12 marzo: l'istruttoria relativa alla pratica 2214 "
             "e' stata chiusa dal responsabile del procedimento, che ne ha "
             "firmato gli atti.")
    for prov in (USER_INPUT, EXTERNAL_CONTENT):
        assert detect(proposition=claim, verified_by=None, source=fonte,
                      provenance=prov) is None


def test_senza_provenienza_dichiarata_il_perdono_resta_come_prima() -> None:
    """COMPATIBILITA' ALL'INDIETRO, ed e' una scelta esplicita: chi chiama il
    detector senza dire la provenienza ottiene il comportamento del 28/08.
    La guardia vive nel gate, che la provenienza ce l'ha; un chiamante che non
    la passa non viene silenziosamente irrigidito."""
    claim = "The database migration was completed in production."
    assert detect(proposition=claim, verified_by=None, source=claim) is None


# ── ALLA PORTA, che e' il livello a cui il verdetto conta. Un detector verde
#    non e' un prodotto curato: la stessa famiglia di celle ha gia' mostrato che
#    il layer puo' parlare e il sistema decidere altro, e viceversa.

def _layers(**kw: object) -> list[str]:
    from verimem.anti_confab_gate import run_validation_gate
    g = run_validation_gate(proposition=kw.pop("proposition"),  # type: ignore[arg-type]
                            verified_by=[], topic=None, agent=None, **kw)  # type: ignore[arg-type]
    return sorted({str((w or {}).get("layer") or "?")
                   for w in (getattr(g, "warnings", None) or [])})


@pytest.mark.parametrize("claim", CLAIMS)
def test_alla_porta_la_fonte_eco_non_compra_il_perdono(claim: str) -> None:
    """Senza `writer_role` la provenienza e' quella dell'agente: e' il regime
    del banco terzo, ed e' il default di chi non dichiara niente."""
    assert "L1.13" in _layers(proposition=claim, source=claim)


def test_alla_porta_il_verbale_dichiarato_resta_perdonato() -> None:
    """Chi ingerisce davvero un documento ha la strada esplicita, e la cura del
    28/08 continua a valere su quella strada."""
    claim = "L'istruttoria e' stata chiusa dal responsabile del procedimento."
    fonte = ("Verbale del 12 marzo: l'istruttoria relativa alla pratica 2214 "
             "e' stata chiusa dal responsabile del procedimento.")
    assert "L1.13" not in _layers(proposition=claim, source=fonte,
                                  writer_role="external_content")
