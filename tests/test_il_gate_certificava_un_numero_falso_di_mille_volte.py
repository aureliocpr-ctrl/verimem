"""«Lo stipendio è 45.000 euro» contro una fonte che dice «45 euro»: AMMESSO.

IL DIFETTO, ed è il peggiore che questo prodotto possa avere: il gate non tace e
non accusa a torto — **certifica come vero un fatto che la fonte contraddice di
mille volte**. Trovato la notte del 09→10/08 in tre, e nessuno leggendo il codice.

LA MECCANICA, misurata::

    _QUANT_RE.finditer("45.000 euro")  ->  [('45.000', 'euro')]
    float("45.000")                    ->  45.0        ← non 45000
    la fonte «45 euro»                 ->  45.0
    45.0 == 45.0  ⇒  nessuna obiezione ⇒  **admitted**

Il punto è ANCHE il separatore decimale inglese, quindi la regex lo accetta
volentieri e ``float`` restituisce un numero credibile. È la ragione per cui
questa classe è la più pericolosa delle quattro: **somiglia a una notazione
valida**. Le altre tre (virgola migliaia, virgola decimale, spazio) SPEZZANO il
numero, uno dei pezzi non sta nella fonte, e il layer protesta — con messaggi
assurdi, ma il fatto non entra come verificato.

📊 QUANTO È GRANDE, misurato da ws8 sul corpus reale (`semantic.db` in mode=ro,
9365 proposizioni, ore 00:06 del 10/08)::

    PERICOLOSA  un solo gruppo   «1.500» letto 1.5     100 · 1,07%
    INVISIBILE  due o più gruppi «1.500.000» -> []       2 · 0,02%
                                                  ⇒ CINQUANTA A UNO

E le righe sono NOSTRE: «102.913 LOC» letto 102.9 · «16.300+ test pytest verdi»
letto 16.3 (in tre fatti diversi) · «145.000» letto 145.0. Un fatto che dice
16.300 test viene confrontato come se dicesse 16,3: se una fonte qualsiasi
contenesse «16.3», quel claim risulterebbe CONFERMATO.

⚠️ LIMITE DICHIARATO DA ws8: ha letto 6 righe su 100, non tutte.

🔑 IL CRITERIO, misurato 9/9 su un banco di plausibilità: un numero è AMBIGUO se
ha tre cifre dopo il punto, la parte intera non è ``0`` e non supera tre cifre.
Le due osservazioni che lo rendono preciso:

  · ``0.250`` NON può essere migliaia — «zero mila duecentocinquanta» non esiste
    in nessuna convenzione ⇒ i millesimi e le tolleranze si salvano
  · un gruppo di migliaia ha ESATTAMENTE tre cifre ⇒ ``3.1416`` è decimale certo

Sui veri ambigui la regola NON è indovinare: è **non emettere un valore**. Non
«vale 45000», non «vale 45»: tacere sul VALORE, che è l'unica cosa che oggi si sa
per certo essere sbagliata.

⛔ E QUESTO FILE È IL RED, non la cura. La cura tocca ``extract_quantities``, che
serve a quantity_match, facts_conflict, valore_non_nella_fonte e
vicinato_del_valore: va fatta con la suite verde davanti, non all'una di notte su
un perimetro raddoppiato in un'ora.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

FONTE_45 = "Contratto: lo stipendio annuo e' 45 euro."


@pytest.mark.xfail(strict=True, reason=(
    "IL DIFETTO, non ancora curato: il gate certifica come vero un claim che la "
    "fonte contraddice di mille volte. Xfail STRICT apposta — il giorno che la "
    "cura entra, questo test diventa XPASS e la suite lo segnala: e' il modo di "
    "non dimenticarsene."))
def test_IL_DIFETTO_un_numero_mille_volte_piu_grande_viene_ammesso():
    """IL CUORE. «45.000 euro» (quarantacinquemila) contro «45 euro»
    (quarantacinque) deve essere FERMATO. Oggi passa."""
    assenti = valori_non_nella_fonte("Lo stipendio annuo e' 45.000 euro.", FONTE_45)
    assert assenti, (
        "il gate ha AMMESSO un claim che la fonte contraddice di 1000x: "
        "45.000 e 45 vengono letti entrambi 45.0")


def test_CONTROLLO_NEGATIVO_lo_stesso_confronto_senza_separatore_e_preso():
    """⚠️ LA POPOLAZIONE OPPOSTA, ed è quella che dimostra che il layer FUNZIONA:
    tolto il punto, lo stesso identico confronto viene preso.

    Senza questo controllo il test sopra si leggerebbe come «il layer è rotto»,
    mentre il layer è sano e il difetto sta in COME viene letto il numero."""
    assenti = valori_non_nella_fonte("Lo stipendio annuo e' 45000 euro.", FONTE_45)
    assert assenti, "senza separatore il layer deve prendere la differenza"
    assert "45000" in [a.come_scritto() for a in assenti]


def test_la_lettura_sbagliata_e_dimostrabile_sul_numero_nudo():
    """La causa, isolata: non è il confronto, è il valore che entra nel confronto."""
    (unita, valore), = extract_quantities("45.000 euro")
    assert unita == "euro"
    assert valore == 45.0, "oggi 45.000 viene letto 45.0 — questo è il difetto"
    assert valore != 45000.0


@pytest.mark.parametrize("testo,letto", [
    ("102.913 LOC", 102.913),      # «OMNEX v6.3.0: 170 Python files, 102.913 LOC»
    ("16.300 test", 16.3),         # «16.300+ test pytest verdi» — in TRE fatti diversi
    ("145.000 righe", 145.0),
    ("15.000 file", 15.0),
])
def test_I_CASI_REALI_dal_corpus_sono_letti_come_decimali(testo, letto):
    """⚠️ NON sono casi inventati: sono righe del corpus di casa, trovate da ws8
    su `semantic.db` in sola lettura (9365 proposizioni, 100 nella classe
    pericolosa = 1,07%).

    Un fatto che dice «16.300 test» viene confrontato come se dicesse 16,3.
    """
    (_u, v), = extract_quantities(testo)
    assert v == pytest.approx(letto), f"«{testo}» oggi vale {v}"


def test_LA_CLASSE_INVISIBILE_due_gruppi_spariscono_del_tutto():
    """L'altra metà, cinquanta volte più rara ma non innocua: con due o più
    gruppi la regex non matcha affatto e il numero non esiste per il layer.

    Il caso è reale: «Il wheel torch 2.13.0 per Windows pesa 122.057.313 byte»,
    un fatto salvato da ws8, di cui il gate non ha visto il numero."""
    assert extract_quantities("Il wheel pesa 122.057.313 byte.") == set()


@pytest.mark.parametrize("numero,decimale_certo", [
    ("0.250", True),    # «zero mila duecentocinquanta» non esiste
    ("0.125", True),
    ("3.1416", True),   # quattro cifre: non è un gruppo di migliaia
    ("12.34", True),
    ("99.9", True),
    ("45.000", False),  # ambiguo — ed è il caso che certifica il falso
    ("1.500", False),
    ("250.000", False),
    ("3.141", False),   # ambiguo davvero: in italiano è 3141
])
def test_IL_CRITERIO_separa_i_decimali_certi_dagli_ambigui(numero, decimale_certo):
    """Il criterio che la cura dovrà applicare, misurato PRIMA di scriverla:
    9 casi su 9 concordi col giudizio umano.

    ⚠️ È un banco di PLAUSIBILITA', non un campione del corpus: i casi li ho
    scelti io. Il campione vero è quello di ws8 (6 righe lette su 100, nessuna
    delle quali un decimale legittimo).
    """
    import re
    ambiguo = re.compile(r"^(?!0\.)\d{1,3}\.\d{3}$")
    assert bool(ambiguo.match(numero)) is not decimale_certo
