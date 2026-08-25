"""L'advice del moat prometteva ASSERZIONI e mostrava CLAUSOLE.

Su una frase che afferma quattro cose in due proposizioni::

    «Nella cella windows il test_default_is_subprocess e' PASSED mentre
     test_basic_execution, test_cannot_write_outside_mount e
     test_no_network_egress sono SKIPPED.»

l'advice diceva «This proposition makes **2 separate assertions**». Le
affermazioni sono QUATTRO (un PASSED e tre SKIPPED); due è il numero delle
CLAUSOLE, che è ciò che `split_claim_clauses` conta davvero.

⚖️ IL CONTEGGIO NON È IL DIFETTO, ED È IMPORTANTE NON «CURARLO». Contare le
asserzioni semantiche richiede un modello; contare le clausole no, ed è una
scelta dichiarata — `unsupported_span.py:23`: «What survives is what can be
said WITHOUT a model: how many separate assertions the sentence makes». La
spaccatura misurata è corretta in entrambe le lingue::

    IT  -> ['…il test_default_is_subprocess e PASSED',
            'mentre test_basic_execution, … sono SKIPPED']      2 clausole
    EN  -> spaccatura identica                                   2 clausole

⇒ Il difetto è **la parola**: il messaggio nomina una grandezza (asserzioni) e
ne mostra un'altra (clausole). Chi legge conta le proprie affermazioni, trova
un numero più piccolo, e conclude che il gate non ha capito la frase — mentre
il gate ha misurato correttamente un'altra cosa.

🔑 È la stessa forma che il registro chiama «dichiara una proprietà più forte
di quella che misura», qui applicata a un messaggio invece che a un presidio.
"""
from __future__ import annotations

from verimem.anti_confab_gate import run_validation_gate
from verimem.unsupported_span import split_claim_clauses

SOURCE = (
    "   TestFactoryBackendSelection::test_default_is_subprocess PASSED\n"
    "   TestDockerExecutorContract::test_basic_execution SKIPPED\n"
    "   TestDockerExecutorContract::test_cannot_write_outside_mount SKIPPED\n"
    "   TestDockerExecutorContract::test_no_network_egress SKIPPED"
)
CLAIM = (
    "Nella cella windows il test_default_is_subprocess e PASSED mentre "
    "test_basic_execution, test_cannot_write_outside_mount e "
    "test_no_network_egress sono SKIPPED."
)


def _advice_del_moat() -> str:
    r = run_validation_gate(proposition=CLAIM, verified_by=None, topic=None,
                            agent=None, source=SOURCE, grounding_llm=None,
                            ground_write=True)
    for w in (getattr(r, "warnings", None) or []):
        if w.get("layer") == "L4-grounding":
            return str(w.get("advice") or "")
    return ""


def test_presidio_la_spaccatura_in_clausole_e_corretta():
    """La controparte: senza di lei si potrebbe «curare» il conteggio, che è
    sano. Due clausole sono la lettura giusta di quella frase."""
    assert len(split_claim_clauses(CLAIM)) == 2


def test_l_advice_nomina_la_grandezza_che_ha_contato():
    advice = _advice_del_moat()
    assert advice, "il caso non produce piu' l'advice del moat: il banco e' scaduto"
    n = len(split_claim_clauses(CLAIM))
    assert str(n) in advice, f"l'advice non riporta il numero {n}: {advice[:120]!r}"
    assert "separate assertions" not in advice, (
        "l'advice promette ASSERZIONI e mostra CLAUSOLE: la frase ne afferma "
        f"quattro e il numero mostrato e' {n}, cioe' le clausole. Chi legge "
        "conta le proprie affermazioni, trova un numero piu' piccolo e conclude "
        f"che il gate non ha capito la frase. advice: {advice[:160]!r}"
    )
    assert "clause" in advice.lower(), (
        "l'advice deve nominare le CLAUSOLE, che sono cio' che ha contato: "
        f"{advice[:160]!r}"
    )
