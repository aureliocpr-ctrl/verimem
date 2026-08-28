"""Cycle 2026-05-27 (round 5) — L1.13 completion claim detector.

Round 5: le due proposte esterne divergevano (f «scalable» contro h
«deployed»); la scelta architetturale è stata (e) complete/done/finished
come L1.13.

Motivazione Claude: (e) ortogonal a tutti i detector esistenti
(L1.9 perf, L1.10 works, L1.11 prod-ready, L1.12 security), non
overlap con L1.0 SHIPPED-family (che copre deploy/merge specific).

Patterns coperti (closing claim):
- English: complete, completed, done, finished, closed, wrapped up,
  task done, all done
- Italian: completo, completato, finito, fatto, chiuso, concluso

Evidence accepted (closing criteria):
- task:<id>_closed or jira:<key>_closed
- acceptance_test:<id>_PASS
- definition_of_done:<id>_met
- review:<id>_approved or pr:<num>_merged
- pytest:<test>_PASS (test coverage)
- bash:<cmd>:exit0 (operational completion)

A1 ANTI-CONFAB closure for completion claims: future "task done" senza
acceptance/review/test evidence = auto downgrade quarantined.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_COMPLETION_PATTERN = re.compile(
    r"\b(?:complete|completed|done|finished|closed|"
    r"wrapped[- ]up|all[- ]done|task[- ]done|"
    # LE QUATTRO FLESSIONI, non solo il maschile singolare. Il gate prendeva
    # «completato» e lasciava passare «completata»: misurato 2026-08-03 sulla
    # self-claim che l'orientamento MCP cita testualmente come esempio di cio'
    # che respinge —
    #     EN  The migration is complete and all tests pass. -> quarantined
    #     IT  La migrazione e completata e tutti i test ...  -> model_claim
    # Non mancava l'italiano: c'era, con una flessione su quattro.
    #
    # Generate dalla REGOLA come fa `l1_tested_detector._TESTED_PATTERN`
    # (testato|testati|testata|testate|verificato|...), che nel banco sui
    # quindici detector era uno di quelli che funzionavano in entrambe le
    # lingue.
    #
    # Rischio misurato prima sul corpus vero (5387 fatti vivi): nessuna forma
    # aggiunta supera il 2% — le piu' frequenti sono `chiusi` 62, `chiusa` 43.
    # E non c'e' asimmetria da valutare: la forma maschile e' gia' qui, quindi
    # se «chiuso» fa scattare il gate «chiusa» deve farlo. Le flessioni non
    # cambiano il criterio, lo applicano.
    r"complet[oaie]|completat[oaie]|finit[oaie]|fatt[oaie]|"
    r"chius[oaie]|conclus[oaie])\b",
    re.IGNORECASE,
)

# Evidence prefixes that count as "closing criteria"
_COMPLETION_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "task:", "jira:", "ticket:",
    "acceptance_test:", "acceptance-test:",
    "definition_of_done:", "dod:",
    "review:", "pr:", "mr:",
    "pytest:", "bash:",
)


# FIX 2026-08-04 — «IL FATTO» E' UN SOSTANTIVO, E IN QUESTO PRODOTTO E' IL NOME
# DELL'UNITA' DI DOMINIO.
#
# Trovato seguendo un numero: se `verimem save` chiamasse il gate L1, 3520 fatti
# vivi su 5781 (60%) avrebbero un warning, e L1.13 da solo ne fa 2082. Contati
# gli hit per parola scatenante, i primi due posti sono `fatto` 437 e `fatti`
# 390 — 855 su 2082, il 41%:
#
#     …updated_at uguale 1785623544 il fatto ha grounding 3.9…
#     …Con i due fatti sul piano annuale entrambi vivi…
#
# LA CAUSA E' UN'OMONIMIA CREATA DALLA TRADUZIONE. In inglese `fact` e `done`
# sono parole diverse e il detector non puo' confonderle; in italiano «fatto» e'
# il participio di *fare* E il sostantivo che questo prodotto usa per i propri
# record. Il pattern e' stato esteso all'italiano parola per parola senza
# accorgersi che una di quelle parole e' il nome della cosa di cui il corpus
# parla in continuazione.
#
# MISURATO SU ENTRAMBE LE POPOLAZIONI (la trappola gia' pagata cinque volte qui:
# un criterio guardato solo dai negativi sembra sempre ottimo). Su 855 hit di
# `fatt*`: 419 con un determinante davanti, 428 senza. Letti nove per parte —
# con determinante 9 su 9 sostantivi; senza, almeno 4 su 9 lo sono comunque.
# Quindi PRECISIONE ALTA e RICHIAMO PARZIALE: questa cura toglie i 419 senza
# perdere claim veri, e non pretende di prenderli tutti.
#
#: Determinanti che rendono «fatto» un sostantivo. Restano FUORI `tutti`/`altri`
#: (precedono volentieri un participio: «sono tutti fatti») e un numero
#: preceduto da `#`, che e' l'id di un task e non un conteggio («P1 #6 FATTO»).
_DETERMINANTE = re.compile(
    r"(?<!#)(?<!#\d)(?<!#\d\d)"
    r"\b(?:il|lo|la|i|gli|le|un|uno|una|del|dei|dello|degli|della|delle|"
    r"nel|nei|nella|nelle|dal|dai|sul|sui|quel|quei|quella|questo|questi|"
    r"questa|ogni|due|tre|quattro|cinque|sei|sette|otto|nove|dieci|dodici|"
    r"\d+)\s+$",
    re.IGNORECASE,
)


def _e_il_sostantivo_fatto(testo: str, m: re.Match) -> bool:
    """La parola trovata e' «fatto/fatti/fatta/fatte» usato come NOME?

    Il confine e' «immediatamente prima»: in «il lavoro fatto in fretta» fra
    l'articolo e la parola c'e' dell'altro, e la parola resta un participio.
    """
    if not m.group(0).lower().startswith("fatt"):
        return False
    return bool(_DETERMINANTE.search(testo[max(0, m.start() - 24):m.start()]))


@dataclass(frozen=True)
class CompletionClaimWarning:
    """Warning emitted when 'complete/done/finished' claim lacks
    closing criteria evidence."""

    matched_text: str
    advice: str


def _has_completion_evidence(verified_by: Iterable[str] | None) -> bool:
    """Return True iff verified_by contains closing criteria evidence."""
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        # FIX 2026-06-03 (sorella red-team, buco L1.13-substring): l'esito di
        # task:/review:/pr:/mr:/pytest:/bash: era confrontato come SUBSTRING
        # ('task:undone_item' conteneva 'done', 'review:disapproved' conteneva
        # 'approved', 'pr:unmerged' conteneva 'merged') → evidenza-spazzatura
        # accettata. Allineato a l1_works_detector.py: confronto PER-TOKEN
        # (split su non-alfanumerico). jira/ticket/acceptance/dod restano
        # accettati col solo prefisso by-design (il ref È il criterio).
        toks = re.split(r"[^a-z0-9]+", lower)
        # task:<id>_closed or task:<id>_resolved or task:<id>_done
        if lower.startswith("task:") and any(
            t in ("closed", "resolved", "done") for t in toks
        ):
            return True
        # jira:<key>_closed
        if lower.startswith("jira:") or lower.startswith("ticket:"):
            return True
        # acceptance_test:_PASS
        if (lower.startswith("acceptance_test:")
                or lower.startswith("acceptance-test:")):
            return True
        # definition_of_done:<id>_met
        if (lower.startswith("definition_of_done:")
                or lower.startswith("dod:")):
            return True
        # review:_approved or pr:_merged or mr:_merged — token di esito
        if lower.startswith("review:") and any(
            t in ("approved", "passed") for t in toks
        ):
            return True
        if (lower.startswith("pr:") or lower.startswith("mr:")) and any(
            t in ("merged", "closed") for t in toks
        ):
            return True
        # pytest:_PASS / bash:exit0 (operational completion) — token di esito
        if lower.startswith("pytest:") and any(
            t in ("pass", "passed", "passing") for t in toks
        ):
            return True
        if lower.startswith("bash:") and "exit0" in toks:
            return True
    return False


def _il_participio_e_nella_fonte(matched_text: str, source: str | None) -> bool:
    """La fonte contiene lo STESSO participio che ha fatto scattare il match?

    Se si', il claim non e' una self-claim: e' un RICALCO della fonte, e questo
    detector — che guarda solo la proposizione — non ha modo di distinguere i
    due casi senza questa domanda.

    ⚖️ IL CRITERIO E' TESTUALE E CONSERVATIVO, ed e' lo stesso gia' adottato in
    `valore_non_nella_fonte._valori_da_token_che_la_fonte_contiene`: «*si perdona
    un valore solo se il TOKEN che l'ha prodotto compare verbatim nella fonte*».
    Qui vale la stessa cosa per la parola di completamento. ⇒ Una self-claim
    SENZA fonte non ha nulla da perdonare e resta fermata: questa non e' una
    disattivazione del layer, e' la domanda che gli mancava.

    Misurato il 2026-08-28 sulle tre popolazioni del banco
    `docs/stato-reale/banchi/L1-13-il-detector-non-vede-la-fonte.py`: su un
    verbale di cantiere 6 frasi su 7 erano fermate da L1.13 con la fonte che le
    sostiene alla lettera, 2 su 4 in una batteria bilingue, e 6 self-claim su 6
    restano fermate.
    """
    if not source or not matched_text:
        return False
    return matched_text.casefold() in source.casefold()


def detect_unsupported_completion_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
    source: str | None = None,
) -> CompletionClaimWarning | None:
    """Return Warning if proposition contains completion claim AND
    verified_by lacks closing criteria evidence. Else None.

    ``source`` e' opzionale e il default ``None`` lascia invariato ogni
    chiamante che non lo passa: senza fonte non c'e' niente da confrontare e il
    comportamento e' quello di prima.
    """
    if not proposition:
        return None
    # Si scorrono TUTTE le occorrenze: la prima puo' essere «il fatto» (il nome
    # di un record) e la seconda un claim vero. Fermarsi alla prima renderebbe
    # la cura una scappatoia — basterebbe aprire il testo con «il fatto».
    for m in _COMPLETION_PATTERN.finditer(proposition):
        if _e_il_sostantivo_fatto(proposition, m):
            continue
        matched_text = m.group(0)
        break
    else:
        return None
    if _has_completion_evidence(verified_by):
        return None
    # LA DOMANDA CHE MANCAVA: la fonte contiene lo stesso participio?
    # Fino al 2026-08-28 questa funzione riceveva solo `proposition` e
    # `verified_by`, quindi non poteva distinguere una self-claim da un fatto
    # che RICALCA la fonte — e su un verbale d'ufficio («la consegna e' stata
    # fatta», «la pratica e' stata chiusa») fermava il secondo credendolo il
    # primo. Reperto dell'esame del 2026-08-28; l'assegnazione sta nel registro.
    if _il_participio_e_nella_fonte(matched_text, source):
        return None
    # Quante affermazioni contiene la frase. Misurato sui 513 quarantinati vivi
    # del corpus (2026-07-30): 1 affermazione 9%, 2-3 16%, 4-9 30%, 10+ 45% —
    # lunghezza mediana 852 char. Non sono fatti respinti ingiustamente, sono
    # NARRAZIONI DI SESSIONE giudicate come un blocco unico, e un blocco con
    # dieci affermazioni chiede dieci evidenze.
    #
    # Il consiglio era gia' su L4 (il moat) e non qui, dove il backlog si ferma
    # davvero: rieseguendo il gate sui 164 che citano evidenza nel testo, 42
    # passano e 122 restano fermi sui detector lessicali, spesso piu' d'uno
    # sullo stesso fatto. Aggiunto solo quando le affermazioni sono piu' di una:
    # dirlo a una frase che ne fa una sola e' rumore, e il rumore e' come la
    # meta' utile di un messaggio smette di essere letta.
    _split = ""
    try:
        from .unsupported_span import split_claim_clauses
        _n = len(split_claim_clauses(proposition))
    except Exception:  # noqa: BLE001 — un consiglio non rompe un detector
        _n = 1
    if _n > 1:
        _split = (f" This proposition makes {_n} separate assertions and the "
                  f"screens judge them together, so one unproven piece holds "
                  f"back the rest — split it and give each part its own "
                  f"evidence.")
    return CompletionClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains completion claim {matched_text!r} but "
            f"no closing criteria evidence in verified_by. Add at least "
            f"one of: task:<id>_closed, acceptance_test:<id>_PASS, "
            f"definition_of_done:<id>_met, review:<id>_approved, "
            f"pr:<n>_merged, pytest:<t>_PASS, bash:<cmd>:exit0." + _split
        ),
    )


__all__ = [
    "CompletionClaimWarning",
    "detect_unsupported_completion_claim",
]
