"""`С-001`, `样品-001`, `試料-001`: il codice era invisibile fuori dal latino.

La cura dell'11/08 toglieva i codici di record dalle quantità con
`[A-Za-z]{1,6}-\\d{1,6}`. Misurato il giorno dopo sul perimetro delle sette
lingue::

    S-001    (latino)     visto ✅
    С-001    (cirillico)  NON visto
    样品-001  (cinese)     NON visto
    試料-001  (giapponese) NON visto

⚠️ E il caso russo è quello cattivo: la **С** cirillica è **visivamente
identica** alla `C` latina. Un umano che rilegge il codice non vede nessuna
differenza — la regex sì. È un difetto che non si trova guardando, solo
misurando.

Il danno concreto, misurato con un A/B nella stessa esecuzione prima e dopo::

    «样品-001含有11毫克»   PRIMA -> [('含', 1.0), ('毫克', 11.0)]
                          DOPO  -> [('毫克', 11.0)]

Il `-001` produceva un valore fantasma con unità «含» (un pezzo del verbo
«contenere»), che è esattamente la forma di rumore per cui la cura esiste.

═══ ⚠️ IL LIMITE, DICHIARATO E MISURATO — perché il confronto NON è stato
allargato ═══

`_senza_identificatori` usa il pattern Unicode; `_identificatori_disgiunti`
— che decide se due fatti parlano di **record diversi** — resta sul pattern
latino. Non è una dimenticanza: allargarlo **peggiorerebbe**, e l'ho misurato
prima di scegliere::

    «这个样品-001…»  ->  这个样品-001      (questo campione)
    «那个样品-001…»  ->  那个样品-001      (quel campione)
      ⇒ codici DIVERSI ⇒ disgiunti ⇒ il conflitto vero verrebbe PERSO

In cinese e giapponese non ci sono spazi, quindi `{1,6}` si porta dentro anche
le parole prima del codice. Per **cancellare** il codice dal testo è innocuo —
si tolgono caratteri che non erano una quantità. Per **decidere** se due record
sono diversi sarebbe un difetto nuovo, e oggi quel caso funziona proprio perché
i codici CJK non vengono visti affatto.

🔑 **Allargare una vista non è sempre un miglioramento: dipende da chi la
usa.** Stessa regex, due consumatori, due verdetti opposti.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities, numeric_conflict


@pytest.mark.parametrize("lingua,frase,vero", [
    ("EN", "Sample S-001 contains 11 milligrams.", 11.0),
    ("IT", "Il campione S-001 contiene 11 milligrammi.", 11.0),
    ("RU", "Образец С-001 содержит 11 миллиграммов.", 11.0),
    ("ZH", "样品-001含有11毫克。", 11.0),
    ("JA", "試料-001には11ミリグラム含まれています。", 11.0),
])
def test_il_codice_non_produce_un_valore_in_nessun_alfabeto(lingua, frase, vero):
    """Il cuore: il codice sparisce, la misura vera resta.

    Le due asserzioni insieme: se cadesse solo la prima avremmo un codice
    ancora letto come numero, se cadesse solo la seconda avremmo una cura che
    si è mangiata il dato — e quel secondo modo di sbagliare è già costato il
    ritiro della cura del 2026-08-04.
    """
    valori = {v for _u, v in extract_quantities(frase)}
    assert vero in valori, f"[{lingua}] ha perso la misura vera: {valori}"
    assert 1.0 not in valori and 0.0 not in valori, (
        f"[{lingua}] il codice produce ancora un valore fantasma: {valori}")


def test_due_schede_latine_con_codici_diversi_restano_non_in_conflitto():
    """Il discriminante di soggetto continua a funzionare dove è definito."""
    assert numeric_conflict(
        "Il campione S-001 contiene 11 milligrammi.",
        "Il campione S-002 contiene 12 milligrammi.") is None


def test_IL_LIMITE_il_confronto_CJK_resta_fuori_ed_e_una_scelta():
    """⚠️ QUESTO TEST DOCUMENTA UN LIMITE, NON UNA CAPACITÀ.

    In cinese il discriminante di soggetto non vede i codici, quindi due schede
    diverse non vengono separate da lì. È lo stato di oggi ed è **voluto**:
    allargare il pattern al confronto farebbe risultare «questo campione-001» e
    «quel campione-001» due record diversi, perdendo un conflitto vero.

    Se un giorno questa asserzione cadesse, vuol dire che qualcuno ha allargato
    il confronto — e allora deve prima aver risolto la segmentazione, non solo
    la regex.
    """
    from verimem.quantity_match import _identificatori_disgiunti
    assert not _identificatori_disgiunti("样品-001含有11毫克。", "样品-002含有12毫克。")
    # ma in latino il discriminante li separa eccome
    assert _identificatori_disgiunti("Il campione S-001 …", "Il campione S-002 …")
