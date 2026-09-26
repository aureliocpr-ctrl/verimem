"""Cycle 2026-05-27 (round 6) — L1.14 documentation claim detector.

Claude architectural choice round 6: (g) documented/explained come
ortogonal a tutti detector esistenti. Closes gap "ho documentato" senza
file marker docs.

Patterns coperti:
- English: documented, well-documented, explained, described
- Italian: documentato, spiegato, descritto

Evidence accepted (docs proof):
- docs:<path> or md:<file>
- file:<path>.md or file:<path>/README
- readme:<id>
- changelog:<entry>_added
- comment:<file>:<line>_added
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_DOC_PATTERN = re.compile(
    r"\b(?:documented|well[- ]documented|"
    r"explained|described|"
    # Le quattro flessioni: c'erano maschile e femminile SINGOLARI e non i
    # plurali, quindi «Le API sono documentate» passava mentre «Il modulo e
    # documentato» veniva presa. Stessa cura di `l1_completion_detector`,
    # stesso modello (`l1_tested_detector`), stessa misura sul corpus
    # (`documentati` 24 occorrenze su 5387, `documentate` 2).
    r"documentat[oaie]|spiegat[oaie]|descritt[oaie])\b",
    re.IGNORECASE,
)

#: T206 (24/09) — «explained», «described», «spiegato», «descritto» sono verbi
#: del DIRE prima che della documentazione. «Maria described a view of a
#: waterfall», «John explained that he hopes …», «Maria ha descritto il
#: panorama» sono fatti personali, e lo strato li fermava sulla sola parola: la
#: memoria p025 del pilota LoCoMo, sostenuta dal suo turno e ammessa dal giudice
#: a 98,38, finiva in quarantena. I veri positivi che i test di questo strato
#: proteggono sono tutti PARTICIPI, lo STATO di un artefatto («Behavior
#: described in docs», «Il caso è descritto»). Qui si riconosce l'uso ATTIVO e
#: lo si lascia passare:
#:   - inglese: il verbo seguito SUBITO da un complemento oggetto o da una frase
#:     oggettiva (articolo, dimostrativo, possessivo, pronome, «that», «how»…);
#:   - italiano: il participio retto da AVERE, cioè il passato prossimo attivo,
#:     con al più una parola in mezzo («ha già descritto»).
#: «documented / documentato» NON cambia: «I documented the API» è proprio la
#: dichiarazione di cui lo strato deve chiedere la prova.
#: ⚠️ IL LIMITE, dichiarato e tenuto da una cella: «I explained the new API in
#: the docs» non viene più preso da questo strato. È un verbo del dire con un
#: oggetto, e da solo non si distingue da «I explained my plan to Maria»; se ha
#: una fonte, a giudicarlo resta il moat.
_VERBI_DEL_DIRE_EN = ("explained", "described")
#: Le parole che, SUBITO dopo il verbo, aprono un complemento oggetto o una
#: frase oggettiva. ⚠️ SENZA REGEX, e su una finestra finita: la seconda
#: stesura usava `\s+(?:a|an|the|…)\b` sul testo dopo la parola, e CodeQL
#: l'ha segnalata come la prima (py/polynomial-redos, #1498, riga 89 di
#: 5220080e). Qui si prende la prima parola di una finestra corta dopo il
#: verbo e la si cerca in un insieme: il costo non dipende dal testo.
_APRONO_UN_OGGETTO_EN = frozenset({
    "a", "an", "the", "this", "that", "these", "those", "his", "her", "their",
    "my", "our", "its", "your", "him", "them", "me", "us", "it", "how", "what",
    "why", "where", "when", "who", "whom", "to", "some", "all", "each",
    "every", "several", "many", "one", "two", "three",
})
_FINESTRA_OGGETTO = 40
_PUNTEGGIATURA_AI_BORDI = ".,;:!?\"'()[]«»“”‘’"


def _apre_un_oggetto(proposition: str, fine: int) -> bool:
    """Subito dopo il verbo (spazio, poi una parola) c'è un oggetto o una
    frase oggettiva? Come la regex che sostituisce: serve uno spazio subito
    dopo il verbo, e «described:» o «described.» restano dichiarazioni."""
    dopo = proposition[fine:fine + _FINESTRA_OGGETTO]
    if not dopo[:1].isspace():
        return False
    parti = dopo.split(maxsplit=1)
    return bool(parti) and (
        parti[0].strip(_PUNTEGGIATURA_AI_BORDI).lower() in _APRONO_UN_OGGETTO_EN)
_PARTICIPI_DEL_DIRE_IT = re.compile(r"(?:spiegat|descritt)[oaie]", re.IGNORECASE)
_FORME_DI_AVERE = frozenset({
    "ho", "hai", "ha", "abbiamo", "avete", "hanno", "avevo", "avevi", "aveva",
    "avevamo", "avevate", "avevano", "avrò", "avrai", "avrà", "avremo", "avrete",
    "avranno", "avrei", "avrebbe", "avremmo", "avrebbero", "abbia", "abbiano",
})
#: ⚠️ LINEARE PER COSTRUZIONE. La prima stesura cercava
#: `\s+(?:\w+\s+)?$` su tutto il testo prima della parola, e CodeQL l'ha
#: segnalata (py/polynomial-redos, alto): su una stringa con molti spazi il
#: costo cresce col quadrato della lunghezza. Qui si guarda solo una finestra
#: finita prima della parola, divisa in parole su spazi e apostrofi (così
#: «l'ho spiegato» resta preso), e si chiede se una delle ultime DUE sia una
#: forma di avere («ha descritto», «ha già descritto»).
_FINESTRA_AUSILIARE = 48


def _retto_da_avere(prima: str) -> bool:
    finestra = prima[-_FINESTRA_AUSILIARE:].lower()
    parole = finestra.replace("'", " ").replace("’", " ").split()
    return any(p in _FORME_DI_AVERE for p in parole[-2:])


def _uso_attivo(proposition: str, m: re.Match[str]) -> bool:
    """La parola trovata è un verbo del dire usato in forma ATTIVA (T206)?"""
    parola = m.group(0).lower()
    if parola in _VERBI_DEL_DIRE_EN:
        return _apre_un_oggetto(proposition, m.end())
    if _PARTICIPI_DEL_DIRE_IT.fullmatch(parola):
        return _retto_da_avere(proposition[:m.start()])
    return False


_DOC_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "docs:", "md:", "readme:", "readme.md:",
    "changelog:", "comment:",
)


@dataclass(frozen=True)
class DocClaimWarning:
    matched_text: str
    advice: str


def _has_doc_evidence(verified_by: Iterable[str] | None) -> bool:
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        if any(lower.startswith(p) for p in _DOC_EVIDENCE_PREFIXES):
            return True
        # file:<path>.md or file:<path>/README*
        if lower.startswith("file:") and (
            ".md" in lower or "readme" in lower or "/docs/" in lower
        ):
            return True
    return False


def detect_unsupported_doc_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> DocClaimWarning | None:
    if not proposition:
        return None
    # La prima parola che NON sia un verbo del dire in forma attiva (T206): una
    # frase può contenere tutte e due le cose, e allora resta una dichiarazione.
    m = next((x for x in _DOC_PATTERN.finditer(proposition)
              if not _uso_attivo(proposition, x)), None)
    if m is None:
        return None
    matched_text = m.group(0)
    if _has_doc_evidence(verified_by):
        return None
    return DocClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains documentation claim {matched_text!r} "
            f"but no docs evidence in verified_by. Add at least one of: "
            f"docs:<path>, md:<file>, file:<path>.md, readme:<id>, "
            f"changelog:<entry>_added, comment:<file>:<line>."
        ),
    )


__all__ = ["DocClaimWarning", "detect_unsupported_doc_claim"]
