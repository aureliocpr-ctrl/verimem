"""«Il farmaco riduce la mortalità» e «non riduce» restavano vivi entrambi.

IL DIFETTO, misurato da ws4 il 2026-08-04 e confermato da me con un banco mio
(un processo per caso, store vergine, i due versi):

    IT  «Il farmaco riduce la mortalita» / «...NON riduce»      -> VIVI 2/2
    EN  «The drug reduces mortality»     / «...does NOT reduce» -> VIVI 1/2
    IT  «La differenza e significativa»  / «...NON e»           -> VIVI 2/2

Per una memoria verificata è il guasto peggiore che ci sia, e va detto perché:
finora avevamo misurato che il prodotto ritira TROPPO — due entità distinte
scambiate per una. Qui **non ritira quando deve**, e il risultato è che la
smentita di un fatto convive col fatto, senza che nessuno dei due porti traccia
dell'altro. La domanda successiva pesca l'uno o l'altro, e la risposta è
un'incognita.

LA CAUSA — e non è quella che sembrava. Non è il `non` in stoplist: quella è
`content_tokens`, che il `non` lo toglie di proposito perché serve al matching
delle quantità, e toccarla sarebbe la trappola della metrica normalizzata già
pagata il 2026-08-02. Isolato passo per passo, tutto il resto del percorso
funzionava già:

    _has_negator(A)=False  _has_negator(B)=False   <<< qui
    content_tokens identici, jaccard 4/4 = 1.00
    contrasting_attrs = False

`quantity_match._NEGATOR_RE` — il rilevatore che sta NEL percorso di scrittura —
elencava solo negatori inglesi: not, never, cannot, isn't, doesn't, nor. In
italiano non vedeva niente, quindi le due polarità risultavano uguali e la
funzione usciva alla prima riga.

DUE RILEVATORI, DIFETTI COMPLEMENTARI, ed è la ragione per cui la cura
unifica invece di rattoppare:

    contradiction._has_negation        multilingue (aveva già «non»)  MA
                                       chiamato solo da scan_corpus, mai in
                                       scrittura
    quantity_match._negation_conflict  in scrittura  MA solo inglese

Il prodotto sapeva riconoscere una negazione italiana e sapeva usarla — in due
posti diversi, e mai insieme. Ora la definizione di «cos'è un negatore» è una
sola, in `quantity_match`, e `contradiction` la importa: due liste non possono
più divergere perché non ci sono più due liste.

⚠️ LE LINGUE A NEGAZIONE MORFOLOGICA restano il pezzo difficile e sono dentro
per pattern, non per parola: il giapponese nega col suffisso verbale
(ない/ません), il cinese con 不 e 没有, l'arabo con لا/لم/ليس. Sono riconoscibili
lessicalmente e quindi coperti; una lingua che negasse con un'inflessione
interna alla radice (turco -me-) non lo sarebbe, e quello richiede morfologia
vera.
"""
from __future__ import annotations

import logging
import pathlib
import tempfile

import pytest

from verimem import Memory
from verimem.quantity_match import negation_conflict

logging.disable(logging.INFO)

#: Le coppie del referto clinico, nelle lingue in cui il prodotto viene usato.
#: Ognuna è la STESSA affermazione con la polarità girata.
OPPOSTI = {
    "it": ("Il farmaco riduce la mortalita dei pazienti.",
           "Il farmaco non riduce la mortalita dei pazienti."),
    "it-2": ("La differenza fra i gruppi e statisticamente significativa.",
             "La differenza fra i gruppi non e statisticamente significativa."),
    "en": ("The drug reduces patient mortality.",
           "The drug does not reduce patient mortality."),
    "de": ("Das Medikament senkt die Sterblichkeit der Patienten.",
           "Das Medikament senkt nicht die Sterblichkeit der Patienten."),
    "es": ("El farmaco reduce la mortalidad de los pacientes.",
           "El farmaco no reduce la mortalidad de los pacientes."),
    "fr": ("Le medicament reduit la mortalite des patients.",
           "Le medicament ne reduit pas la mortalite des patients."),
    "pt": ("O medicamento reduz a mortalidade dos pacientes.",
           "O medicamento nao reduz a mortalidade dos pacientes."),
    "nl": ("Het medicijn verlaagt de sterfte van de patienten.",
           "Het medicijn verlaagt niet de sterfte van de patienten."),
}


def _vivi(a: str, b: str) -> list[str]:
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    m.add(a, topic="neg/prova")
    m.add(b, topic="neg/prova")
    return [f.proposition for f in m.semantic.all()
            if not getattr(f, "superseded_by", None)
            and getattr(f, "status", "") != "quarantined"]


@pytest.mark.parametrize("lingua", sorted(OPPOSTI))
def test_il_rilevatore_vede_la_polarita_girata(lingua):
    """Il livello basso, così si vede subito se a rompersi è il rilevatore o
    il percorso che lo usa."""
    a, b = OPPOSTI[lingua]
    assert negation_conflict(a, b) is not None, (
        f"[{lingua}] «{a}» e «{b}» hanno polarità opposta e il rilevatore "
        f"non la vede")


@pytest.mark.parametrize("lingua", ["it", "it-2", "de", "es"])
def test_due_opposti_non_restano_entrambi_vivi(lingua):
    """La misura end-to-end, che è quella che conta per chi usa il prodotto:
    scritte le due frasi, non devono sopravvivere tutte e due."""
    a, b = OPPOSTI[lingua]
    vivi = _vivi(a, b)
    assert len(vivi) < 2, (
        f"[{lingua}] la smentita convive col fatto: {len(vivi)} vivi.\n"
        f"Una domanda successiva pescherà l'uno o l'altro senza criterio")


def test_la_stessa_polarita_NON_e_un_conflitto():
    """Il verso opposto, e senza questo la cura sarebbe un modo di far
    ritirare tutto: due frasi entrambe affermative, o entrambe negative, non
    si contraddicono per il fatto di parlare della stessa cosa."""
    assert negation_conflict(
        "Il farmaco riduce la mortalita dei pazienti.",
        "Il farmaco riduce la mortalita dei pazienti anziani.") is None
    assert negation_conflict(
        "Il farmaco non riduce la mortalita dei pazienti.",
        "Il farmaco non riduce la mortalita dei pazienti anziani.") is None


def test_il_negatore_inglese_non_scatta_su_un_prefisso():
    """`non` è una parola in italiano e un PREFISSO in inglese. Senza questa
    guardia, «the non-blocking call completes» verrebbe letto come una
    negazione di «blocking» — e in un corpus tecnico inglese sarebbe un falso
    positivo continuo."""
    assert negation_conflict(
        "The non-blocking call completes in 5 ms.",
        "The blocking call completes in 5 ms.") is None


@pytest.mark.parametrize("a,b", [
    ("この薬は患者の死亡率を下げます。", "この薬は患者の死亡率を下げません。"),
    ("该药物降低患者死亡率。", "该药物不降低患者死亡率。"),
])
def test_anche_dove_la_negazione_non_e_una_parola_separata(a, b):
    """Giapponese e cinese negano col suffisso verbale (ません) e con una
    particella attaccata (不). Sono riconoscibili lessicalmente, quindi non
    c'è ragione di lasciarli fuori — ed è la differenza fra «copriamo le
    lingue con gli spazi» e «copriamo le lingue»."""
    from verimem.quantity_match import _has_negator
    assert _has_negator(a) != _has_negator(b), (
        f"polarità non distinta fra «{a}» e «{b}»")


def test_le_due_definizioni_di_negatore_sono_UNA_SOLA():
    """La classe che questo progetto paga più spesso: una copia invece della
    superficie unica. `contradiction` aveva la sua lista (che l'italiano ce
    l'aveva) e `quantity_match` la sua (che non ce l'aveva). Finché restano
    due, divergono — è già successo. Questo test lo impedisce."""
    from verimem.contradiction import _has_negation
    from verimem.quantity_match import _has_negator
    for testo in ("Il farmaco non riduce la mortalita.",
                  "Das Medikament senkt nicht die Sterblichkeit.",
                  "The drug does not reduce mortality.",
                  "Il farmaco riduce la mortalita."):
        assert _has_negation(testo) == _has_negator(testo), (
            f"i due rilevatori dissentono su «{testo}»: sono tornati due")
