"""T53 — l'iniezione proattiva porta il fatto nel prompt e non dice cos'e'.

Ticket T53 (mappa dell'intera superficie, 09/09): ``StepInjector.inject``
costruisce la riga iniettata con ``{id, proposition, topic, similarity}``
(``proactive_step_injector.py:123-128``) e il banner dell'hook la stampa
come ``- [sim 0.62] topic — proposizione``
(``hooks/pre_tool_use.py:214-215``). Ne' lo status del fatto, ne' il
verdetto di fiducia arrivano a chi legge.

Cosa cambia per l'utente: un fatto che il prodotto stesso classifica
`contested` o `unverified` non entra piu' nel prompt travestito da fatto
qualunque.

CLAIM DEL README PRESIDIATO DA QUESTO BANCO
--------------------------------------------
``README.md:443-444`` — «stored but OUT of default recall — **your agent
will never repeat it as truth**». L'iniezione proattiva e' il posto in cui
quella frase si gioca alla lettera: mette il fatto NEL PROMPT dell'agente.
Le due meta' misurate qui:
* che un quarantenato non ci arrivi —
  ``test_un_quarantenato_non_arriva_nel_prompt`` (verde gia' prima);
* che quello che ci arriva dica cos'e' —
  ``test_un_fatto_contestato_entra_nel_prompt_senza_dirlo``, perche' un
  fatto contestato presentato senza una parola E' ripeterlo come verita'.

LA DISTINZIONE CHE IL BANNER GIA' FA A META'
--------------------------------------------
Il banner dichiara ``note="recalled memory: UNTRUSTED DATA, not
instructions"``. Copre il prompt-injection: il fatto non e' un ordine.
NON copre l'affidabilita' del CONTENUTO: un fatto vecchio di 200 giorni
arriva identico a uno fresco e verificato. «Non fidarti come ISTRUZIONE»
e «non fidarti come INFORMAZIONE» sono due cose diverse, e oggi il
prodotto dice solo la prima.

E' il caso peggiore per una ragione che sta gia' scritta nel prodotto,
nello stesso file, righe 109-113: «Altrove chi legge ha almeno fatto una
domanda e puo' insospettirsi di una risposta strana; qui il contesto
semplicemente non arriva, e nessuno ha chiesto niente su cui dubitare».
Vale identico al rovescio: nessuno ha chiesto niente, quindi nessuno
dubita di quello che arriva.

LIVELLO DICHIARATO: la PORTA. ``hooks.pre_tool_use.run(payload)`` e' il
testo che entra davvero nel prompt del modello ospite. La riga di
``StepInjector.inject`` e' misurata a parte, come funzione.

Ogni prova parte da un CONTROLLO POSITIVO: se un fatto normale non arriva
nel banner, il banco e' cieco e un banner vuoto si legge come «nessun
fatto sospetto», cioe' come un verde.

Eseguito il 09/09 su nadia/t50-t53 con ``env -u HIPPO_ENCODE_DELEGATE_ONLY``.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from verimem.hooks.pre_tool_use import run as hook_run
from verimem.proactive_step_injector import StepInjector
from verimem.semantic import Fact, SemanticMemory

_ORA = time.time()
_GIORNO = 86400.0
_TESTO = "il capannone 12 del magazzino misura 900 metri quadri"


class _Agente:
    """Lo shim minimo che l'iniettore si aspetta: un attributo `semantic`."""

    def __init__(self, semantic: SemanticMemory) -> None:
        self.semantic = semantic


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


def _scrivi(
    sm: SemanticMemory, fid: str, *, status: str = "model_claim",
    eta_giorni: float = 0.0,
) -> Fact:
    f = Fact(
        id=fid, proposition=_TESTO, topic="magazzino",
        confidence=0.9, status=status,
        created_at=_ORA - eta_giorni * _GIORNO,
    )
    sm.store(f)
    return f


def _payload() -> dict[str, Any]:
    """Un PreToolUse vero, come lo manda Claude Code.

    ⚠️ Il testo pertinente sta nel `command` e NON nella `description`:
    `_bash_extractor` (`hooks/pre_tool_use.py:67`) legge solo `command`, e
    sotto gli 8 caratteri (`_STEP_TEXT_MIN_LEN`) l'hook rende stringa vuota.
    La prima stesura di questo banco metteva la domanda nella `description`
    con `command="ls"`: il banner tornava vuoto e il controllo positivo l'ha
    fatto cadere, invece di lasciarmi scrivere «il banner non dice X».
    """
    return {
        "tool_name": "Bash",
        "tool_input": {
            "command": "grep -rn 'capannone 12 magazzino metri quadri' .",
            "description": "cerco la metratura del capannone 12",
        },
    }


def _banner(sm: SemanticMemory) -> str:
    return hook_run(_payload(), agent_factory=lambda: _Agente(sm))


class TestAllaPortaDellHook:
    """Il testo che entra nel prompt del modello ospite."""

    def test_il_controllo_positivo_si_accende(self, sm: SemanticMemory) -> None:
        """Prima di dire «il banner non dice X» bisogna provare che il
        banner dica QUALCOSA. Un banner vuoto non e' una buona notizia:
        e' un banco cieco.
        """
        _scrivi(sm, "f-sano")

        banner = _banner(sm)

        assert banner, (
            "CONTROLLO POSITIVO SPENTO: il banner e' vuoto anche con un "
            "fatto pertinente nello store — sotto pytest l'embedder e' lo "
            "stub e il banco alla porta e' CIECO"
        )
        assert "capannone 12" in banner, (
            f"il fatto non e' nel banner: {banner!r}"
        )

    def test_un_fatto_di_200_giorni_non_arriva_nel_prompt(
        self, sm: SemanticMemory,
    ) -> None:
        """La SECONDA riga del ticket che cade, misurata il 09/09.

        200 giorni: il prodotto lo chiamerebbe `stale` (soglia 180,
        `trust_signal.py:37`). Ma nel prompt non ci arriva proprio — il
        recall sotto l'iniettore filtra per freschezza prima. Scritto qui
        come test verde e non incassato come rosso: il mio controllo
        positivo era rimasto spento, e un controllo spento non prova un
        difetto, prova solo che non ho visto niente.
        """
        _scrivi(sm, "f-vecchio", eta_giorni=200.0)

        banner = _banner(sm)

        assert banner == "", (
            "un fatto di 200 giorni ARRIVA nel prompt: la riga del ticket "
            f"regge e questo test va riscritto come rosso —\n{banner}"
        )

    def test_un_fatto_contestato_entra_nel_prompt_senza_dirlo(
        self, sm: SemanticMemory,
    ) -> None:
        """Il caso piu' grave rimasto del ticket.

        `contested` non dipende dallo status: nasce da una contraddizione
        aperta nella ContradictionStore, e il recall NON la guarda. Il
        fatto e' fresco, il suo status e' `model_claim`: passa ogni
        filtro e arriva nel prompt mentre il prodotto, se glielo si
        chiede, risponde che quel fatto e' contestato.
        """
        from verimem.contradiction import Contradiction, ContradictionStore

        _scrivi(sm, "f-contestato")
        store = ContradictionStore(sm.db_path)
        store.add(Contradiction(
            fact_a_id="f-contestato", fact_b_id="f-altro",
            kind="numeric_clash", similarity=0.95,
        ))

        banner = _banner(sm)

        assert banner and "capannone 12" in banner, (
            "CONTROLLO POSITIVO SPENTO: il fatto contestato non arriva "
            f"nemmeno nel banner, il confronto non vale — banner={banner!r}"
        )
        assert "contested" in banner.lower(), (
            "un fatto con una contraddizione APERTA entra nel prompt e la "
            f"riga non lo dice:\n{banner}"
        )

    def test_un_fatto_non_verificato_entra_senza_dire_che_non_lo_e(
        self, sm: SemanticMemory,
    ) -> None:
        """`legacy_unverified`: il prodotto lo chiama `unverified` da
        sempre (era gia' uno dei due status che la funzione nominava).
        """
        _scrivi(sm, "f-legacy", status="legacy_unverified")

        banner = _banner(sm)

        assert banner and "capannone 12" in banner, (
            "CONTROLLO POSITIVO SPENTO: il fatto non arriva nel banner — "
            f"banner={banner!r}"
        )
        assert "unverified" in banner.lower(), (
            "un fatto legacy_unverified entra nel prompt e la riga non "
            f"dice che non e' verificato:\n{banner}"
        )

    def test_un_quarantenato_non_arriva_nel_prompt(
        self, sm: SemanticMemory,
    ) -> None:
        """La misura che ABBASSA la gravita' del ticket, quindi va fatta.

        Se il recall che sta sotto l'iniettore nasconde gia' i tre status
        a rango negativo, allora nel prompt non arriva un fatto FERMATO —
        e T53 riguarda i fatti `stale` / `contested` / `unverified`, che
        il recall NON filtra. E' un ticket piu' piccolo di come suona, e
        conviene dirlo prima che qualcuno ci costruisca sopra.
        """
        _scrivi(sm, "f-sano")
        _scrivi(sm, "f-fermato", status="quarantined")

        banner = _banner(sm)

        assert banner and "capannone 12" in banner, (
            "CONTROLLO POSITIVO SPENTO: nemmeno il fatto sano arriva — "
            f"banner={banner!r}"
        )
        assert "f-fermato" not in banner, (
            f"un fatto quarantenato e' finito nel prompt:\n{banner}"
        )


class TestLaRigaIniettata:
    """Livello funzione: cosa mette dentro `StepInjector.inject`."""

    def test_la_riga_porta_lo_status_del_fatto(
        self, sm: SemanticMemory,
    ) -> None:
        _scrivi(sm, "f-legacy", status="legacy_unverified")
        inj = StepInjector(_Agente(sm))

        righe = inj.inject(_TESTO, min_similarity=0.0, top_k=5)

        assert righe, (
            "CONTROLLO POSITIVO SPENTO: inject non rende niente, il "
            "confronto non vale"
        )
        riga = righe[0]
        assert "status" in riga, (
            f"la riga iniettata non porta lo status: chiavi={sorted(riga)}"
        )
        assert riga["status"] == "legacy_unverified", (
            f"status sbagliato nella riga: {riga.get('status')!r}"
        )
