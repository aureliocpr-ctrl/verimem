"""Cycle 2026-05-27 (round 7) — L1.15 tested/verified detector.

Ortogonal a L1.10 (works/funziona) — L1.15 cattura claim su TESTING
process completion, non runtime behavior. Esempio:
- L1.10 fires: "Il sistema funziona" (runtime claim)
- L1.15 fires: "Tutto testato" (process claim sin pytest ref)

Patterns coperti (testing claim):
- English: tested, well-tested, verified, validated
- Italian: testato, testati, verificato, verificata, validato

Evidence accepted:
- pytest:<test>_PASS
- test_coverage:<percent>
- ci:<pipeline>:green
- review:<id>_approved
- qa:<scenario>_PASS
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# La portata della negazione sta in UN modulo solo — vedi `negation_scope`, che
# spiega perche' non se ne scrive una copia qui dentro.
from .negation_scope import governata_da_negazione

_TESTED_PATTERN = re.compile(
    r"\b(?:well[- ]tested|tested|"
    r"verified|validated|"
    r"testato|testati|testata|testate|"
    r"verificato|verificata|verificati|verificate|"
    r"validato|validata|validati|validate)\b",
    re.IGNORECASE,
)

# FIX 2026-08-04 — LA PAROLA C'E' MA NON E' UNA DICHIARAZIONE. Trovato
# misurando: se `verimem save` chiamasse il gate, 3520 fatti vivi su 5781 (il
# 60%) riceverebbero un warning L1, e questo detector da solo ne fa 1560.
# Letto un campione casuale, quasi tutti erano falsi positivi di due forme.
#
# ① LA NEGAZIONE. «Il confine anti-correlato NON e' stato testato» faceva
#    scattare 'testato'. E' la TERZA occorrenza della stessa classe in due
#    giorni (`unresolved` conteneva `RESOLVED`, curato in e2d69715): il gate
#    anti-confabulazione blocca la SMENTITA invece del claim, cioe' punisce
#    chi documenta di non aver verificato — l'informazione piu' onesta che un
#    fatto possa portare.
#
#    Il lessico NON si riscrive: `quantity_match._NEGATOR_RE` esiste ed e'
#    stata estesa a undici lingue il 2026-08-03 (d06f1521), proprio dopo aver
#    scoperto che il prodotto riconosceva la negazione italiana in due posti
#    diversi e mai insieme. Quello che manca qui non e' il vocabolario ma la
#    PORTATA: il negatore deve stare vicino alla parola e non oltre una virgola
#    o un'avversativa, altrimenti qualunque fatto lungo conterrebbe un «non» e
#    il detector sarebbe spento invece che corretto.
#
# ② LA PAROLA E' SINTASSI. `--verified-by` e' il nome di un FLAG,
#    `status verified/provisional` e `min_status verified` sono VALORI di
#    parametro, `rustc-verified` e' un identificatore composto. Il fatto cita
#    del codice, non asserisce nulla su se stesso. E' il gemello del caso
#    trovato il 2026-08-04 liberando a mano i fatti quarantinati.

#: Un carattere ATTACCATO alla parola che la rende sintassi e non prosa.
#: Attaccato e' il punto: «Nota: verificato tutto» ha uno spazio in mezzo ed
#: e' un claim, `--verified-by` no.
_ADIACENTE_DI_CODICE = frozenset("-=:/_")
#: La parola come valore di un parametro di stato, dove il nome precede.
_NOME_DI_PARAMETRO = re.compile(r"(?:\w*status|\w*state|--?\w+)\s+$",
                                re.IGNORECASE)


def _e_sintassi(testo: str, inizio: int, fine: int) -> bool:
    """La parola e' un pezzo di codice citato, non un'asserzione?"""
    prima = testo[inizio - 1] if inizio > 0 else ""
    dopo = testo[fine] if fine < len(testo) else ""
    if prima in _ADIACENTE_DI_CODICE or dopo in _ADIACENTE_DI_CODICE:
        return True
    return bool(_NOME_DI_PARAMETRO.search(testo[max(0, inizio - 40):inizio]))

# FIX 2026-06-03 (sorella red-team, buco L1-tested-bypass): i prefissi che
# implicano un test/processo eseguito NON bastano da soli — un ref-spazzatura
# tipo ``test:foo`` / ``pytest:run_42`` / ``ci:main`` / ``qa:x`` / ``review:y``
# passava come evidenza valida (substring ``startswith``), bypassando L1.15.
# Allineato al fix gemello di l1_works_detector (SCAN-68/NONNA): si esige un
# TOKEN di ESITO confrontato PER-TOKEN (split su non-alfanumerico), non
# substring. La metrica ``coverage`` esige invece un valore NUMERICO.
_OUTCOME_TOKENS: frozenset[str] = frozenset(
    {"pass", "passed", "passing", "green", "approved", "ok", "exit0"}
)
#: Prefissi "processo eseguito": richiedono un token di esito verificabile.
_OUTCOME_REQUIRED_PREFIXES: tuple[str, ...] = (
    "pytest:", "test:", "ci:", "qa:", "review:", "validation:",
)
#: Prefissi metrica: richiedono almeno un token numerico (es. coverage 85%).
_COVERAGE_PREFIXES: tuple[str, ...] = ("test_coverage:", "coverage:")

#: Prefissi "comando eseguito": da soli NON provano un test — vedi
#: ``_RUNNER_TOKENS`` sotto.
_ESECUZIONE_PREFIXES: tuple[str, ...] = ("bash:", "cmd:")
#: I runner di test, riconosciuti DENTRO il comando.
#:
#: PERCHE' (misurato il 2026-08-04): `bash:pytest tests/test_parsing.py:exit0`
#: E' pytest eseguito, con l'esito, e veniva rifiutato — perche' il prefisso
#: diceva `bash:` invece di `pytest:`. L'utente porta la prova che il detector
#: chiede, scritta in un altro formato, e si vede quarantinare il fatto.
#:
#: E' un caso della forma che il 04/08 e' uscita quattro volte in punti
#: indipendenti: una domanda con DUE esiti dove ne servono TRE. Qui la domanda
#: e' «c'e' la prova?» e le risposte vere sono *del tipo giusto* / **di un
#: altro tipo** / *nessuna*, con quella di mezzo schiacciata su «nessuna». Le
#: cinque famiglie di prefissi L1 sono quasi disgiunte (tested∩security = 0,
#: works∩security = 0), quindi una prova vale per una famiglia sola.
#:
#: ⚠️ SI CURA SOLO IL CASO INEQUIVOCABILE, e la differenza e' il punto: un
#: `bandit:clean` per «il modulo funziona» va rifiutato davvero — uno scanner
#: statico non prova il comportamento a runtime — e unire le liste renderebbe
#: ogni prova buona per ogni claim, cioe' spegnerebbe il detector fingendo di
#: ripararlo. Qui il comando NOMINA un runner di test: e' il comando a dirlo,
#: non il prefisso.
_RUNNER_TOKENS: frozenset[str] = frozenset({
    "pytest", "unittest", "tox", "nox",          # python
    "jest", "mocha", "vitest", "jasmine",        # javascript
    "rspec", "minitest",                         # ruby
    "phpunit",                                   # php
    "junit", "testng",                           # java
})
#: `npm test`, `cargo test`, `go test`, `mvn test`, `dotnet test`: qui il
#: token `test` e' il SOTTOCOMANDO, quindi va accettato solo accanto al suo
#: strumento — `bash:ls test` non e' un test.
_RUNNER_COPPIE: tuple[tuple[str, str], ...] = (
    ("npm", "test"), ("yarn", "test"), ("pnpm", "test"),
    ("cargo", "test"), ("go", "test"), ("mvn", "test"),
    ("gradle", "test"), ("dotnet", "test"), ("swift", "test"),
)


@dataclass(frozen=True)
class VerificationClaimWarning:
    matched_text: str
    advice: str


def _has_tested_evidence(verified_by: Iterable[str] | None) -> bool:
    """True solo se ``verified_by`` contiene un ref di test VERIFICABILE.

    Un prefisso nudo (``test:foo``) non basta: per i prefissi "processo
    eseguito" serve un token di esito (pass/green/approved/...); per i
    prefissi metrica serve un valore numerico. Confronto PER-TOKEN (non
    substring), cosi' ``test:greenfield`` / ``review:approvable_pending``
    non contano per via di una sottostringa accidentale.
    """
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        tokens = re.split(r"[^a-z0-9]+", lower)
        # Metrica coverage: serve un valore numerico (es. '85').
        if lower.startswith(_COVERAGE_PREFIXES):
            if any(t.isdigit() for t in tokens):
                return True
            continue
        # Processo eseguito: serve un token di esito verificabile.
        if lower.startswith(_OUTCOME_REQUIRED_PREFIXES):
            if any(t in _OUTCOME_TOKENS for t in tokens):
                return True
            continue
        # Comando eseguito che INVOCA un runner di test: e' una prova di test
        # comunque sia stato scritto il prefisso. Servono entrambe le cose —
        # il runner e l'esito — perche' `bash:pytest ...` senza exit code non
        # dice come e' andata, e `bash:ls:exit0` non e' un test.
        if lower.startswith(_ESECUZIONE_PREFIXES):
            if not any(t in _OUTCOME_TOKENS for t in tokens):
                continue
            visti = set(tokens)
            if visti & _RUNNER_TOKENS:
                return True
            if any(a in visti and b in visti for a, b in _RUNNER_COPPIE):
                return True
            continue
    return False


def detect_unsupported_tested_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> VerificationClaimWarning | None:
    if not proposition:
        return None
    # Si scorrono TUTTE le occorrenze: la prima puo' essere un `--verified-by`
    # e la seconda un claim vero. Fermarsi alla prima renderebbe la cura una
    # scappatoia — basterebbe nominare un flag all'inizio del fatto.
    for m in _TESTED_PATTERN.finditer(proposition):
        if governata_da_negazione(proposition, m.start()):
            continue
        if _e_sintassi(proposition, m.start(), m.end()):
            continue
        matched_text = m.group(0)
        break
    else:
        return None
    if _has_tested_evidence(verified_by):
        return None
    return VerificationClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains tested/verified claim {matched_text!r} "
            f"but no test evidence in verified_by. Add at least one of: "
            f"pytest:<test>_PASS, test_coverage:<N>%, ci:<id>:green, "
            f"review:<id>_approved, qa:<scenario>_PASS."
        ),
    )


__all__ = ["VerificationClaimWarning", "detect_unsupported_tested_claim"]
