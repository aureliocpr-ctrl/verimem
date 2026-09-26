"""`decomponi()` on English memories: it must not break a true memory into pieces
that a per-claim judge would then reject.

Measured on 2026-09-24 on a 100-memory pilot extracted from real conversations
(LoCoMo, labelled by three annotators): the splitter broke 5 memories out of 15
splits with the WRONG meaning, two of them TRUE memories. With a judge per claim,
the wrong piece of a true memory becomes a false quarantine. The four causes are
recognisable forms, and each cell below reproduces one of them. The sentences are
paraphrased on purpose: the pilot's text is under a non-commercial licence and
does not enter this repository. The pilot id each form comes from is noted.

  · the nude piece was fused back with a hard-coded Italian « e » («energy e
    support»): the fusion must stitch back the ORIGINAL separator;
  · English irregular past forms (felt, got, found, built, ...) were not finite
    verbs, so «Andrew's dog got» became a subject and «Felt inspired...» a claim
    with no subject;
  · a piece whose first verb sits inside a relative or subordinate clause
    («rest where she goes...», «a source when she started...») is not a clause:
    it is a piece of the previous one;
  · two verbs sharing one complement («inspired and motivated them») are not two
    claims: the left piece ends on its verb.

Two populations, as in the first file: the cells where the split must NOT break a
true memory, and the controls where it must still split correctly.
"""
from __future__ import annotations

import pytest

from verimem.atomic_claims import decomponi


def _nessuna_e_italiana(claims: list[str]) -> bool:
    return not any(" e " in c for c in claims)


# ── the fusion stitches back the original separator (pilot p004, p076) ────────
def test_la_fusione_ricuce_il_separatore_originale() -> None:
    out = decomponi("Lena attended a street festival recently and felt inspired "
                    "by the crowd's energy and support for local artists.")
    assert _nessuna_e_italiana(out), out
    assert out == ["Lena attended a street festival recently.",
                   "Lena felt inspired by the crowd's energy and support for local artists."], out


# ── English irregular past forms are finite verbs (pilot p059, p027, p042) ─────
def test_got_non_entra_nel_soggetto() -> None:
    out = decomponi("Priya's cat got scared and jumped onto the shelf, which was funny.")
    assert out == ["Priya's cat got scared.",
                   "Priya's cat jumped onto the shelf, which was funny."], out


@pytest.mark.parametrize("testo, atteso", [
    ("Leo recently joined a 10K race for a food bank and found it moving to run "
     "with people who shared the goal.",
     "Leo recently found it moving to run with people who shared the goal."),
    ("Kim recently gave a talk at school and felt it was a small but real step.",
     "Kim recently felt it was a small but real step."),
])
def test_il_pezzo_che_comincia_con_un_irregolare_eredita_il_soggetto(testo: str, atteso: str) -> None:
    out = decomponi(testo)
    assert len(out) == 2, out
    assert out[1] == atteso, out


# ── a verb inside a relative or subordinate clause does not make a clause ─────
@pytest.mark.parametrize("testo", [
    # pilot p076: noun coordination followed by a relative clause
    "Omar's garden is his refuge for calm and quiet where he goes to read and unwind after work.",
    # pilot p071: the second piece's verb sits after «when»
    "Tom's father was a loyal supporter and a steady presence when he started running.",
])
def test_una_relativa_non_diventa_un_claim(testo: str) -> None:
    out = decomponi(testo)
    assert out == [testo], out


# ── two verbs sharing one complement are one claim (pilot p086) ───────────────
def test_due_verbi_con_lo_stesso_complemento_restano_uno() -> None:
    testo = "Ravi said that Mia's advice encouraged and reassured him."
    out = decomponi(testo)
    assert out == [testo], out


# ── a nude coordinate with no verb goes back whole (pilot p046) ───────────────
def test_la_coordinata_senza_verbo_torna_intera() -> None:
    # «underserved» is an -ed adjective after «for»: it is not a finite verb
    testo = ("Ana is committed to teaching young musicians and opening doors in "
             "music for underserved schools.")
    out = decomponi(testo)
    assert out == [testo], out


# ── controls: the split that was right stays right (pilot p051, p066) ─────────
@pytest.mark.parametrize("testo, atteso", [
    ("Nora built a bird feeder and joined a club to meet other birdwatchers.",
     ["Nora built a bird feeder.", "Nora joined a club to meet other birdwatchers."]),
    ("Ivan created a new map and shared it with the other players.",
     ["Ivan created a new map.", "Ivan shared it with the other players."]),
])
def test_la_spezzatura_giusta_resta_giusta(testo: str, atteso: list[str]) -> None:
    assert decomponi(testo) == atteso
