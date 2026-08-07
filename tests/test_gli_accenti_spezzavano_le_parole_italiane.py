"""«città» dava il token `citt`, «citta'» dava `citta`: due parole per una.

TROVATO tirando il filo di un referto di ws5. Lei aveva misurato che lo stesso
catalogo sopravvive intatto in giapponese e perde l'80% in italiano, e che la
causa sta in `content_tokens`. Guardando la funzione da vicino, il difetto è più
largo del CJK — `[a-zA-Z]{4,}` è la classe **ASCII**, e taglia fuori:

    cirillico, greco, arabo   ->  ZERO token (sono alfabeti ordinari, con gli
                                  spazi fra le parole: niente li distingue dal
                                  latino se non il blocco Unicode)
    accenti italiani          ->  la parola viene TRONCATA sull'accento

    «La città di Milano ha un'università.»   ->  citt · milano · universit
    «La citta' di Milano ha una universita'» ->  citta · milano · universita

La stessa frase, due grafie, e la funzione che misura la sovrapposizione
lessicale le vede diverse. «però» sparisce del tutto: troncato a `per`, tre
caratteri, sotto la soglia.

**IL CASO È REALE, NON IPOTETICO.** Sul corpus vivo (6068 fatti) ci sono **100
parole scritte in entrambe le grafie**, e non di nicchia: `perché` 88 volte
contro `perche` 322, `entità` 32 contro `entita` 118, `singolarità` 131 contro
`singolarita` 66. Chi scrive da tastiera italiana e chi scrive da una shell che
mangia gli accenti stanno parlando della stessa cosa e il prodotto non lo sa.

MISURATO SULLE DUE POPOLAZIONI, che qui è obbligatorio: la cura gemella —
«conservare token corti e cifre» — fu falsificata proprio così, le coppie sopra
soglia passavano da 848 a 2293 su 3000, cioè PIÙ ritiri.

    BENEFICIO   coppie «stessa frase, due grafie»: 215 su 400 non erano
                riconosciute identiche; dopo la normalizzazione, 0.
                Jaccard mediano 0.984 -> 1.000.
    COSTO       coppie casuali sopra soglia, su 3000: **+0**.

⚠️ IL COSTO NON MISURATO DAI NUMERI, che il test presidia: in italiano l'accento
DISTINGUE parole. `metà` != `meta`, `completò` != `completo`. Normalizzando si
confondono, ed è un prezzo reale — pagato perché sul corpus non produce nemmeno
un ritiro in più, e perché la coppia che unisce (`perché`/`perche`) è molto più
frequente di quella che confonde. Il test lo scrive nero su bianco invece di
lasciarlo scoprire a chi verrà dopo.

⚠️ NON SI TOCCANO la soglia dei 4 caratteri né le cifre: quella strada è già
falsificata sul corpus (`7aa678f57c73`). Qui cambia solo l'ALFABETO.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import content_tokens


@pytest.mark.parametrize("accentata,piatta", [
    ("La città di Milano ha un'università.", "La citta' di Milano ha una universita'."),
    ("La qualità del caffè è superiore.", "La qualita del caffe e superiore."),
    ("L'entità della singolarità è nota.", "L'entita della singolarita e nota."),
    ("La verità sulla parità di trattamento.", "La verita sulla parita di trattamento."),
])
def test_la_stessa_frase_in_due_grafie_da_gli_stessi_token(accentata, piatta):
    """Il cuore: chi scrive «città» e chi scrive «citta'» dice la stessa cosa, e
    una funzione che misura la sovrapposizione lessicale deve saperlo. Sul
    corpus vivo ci sono 100 parole in entrambe le grafie."""
    assert content_tokens(accentata) == content_tokens(piatta), (
        f"«{accentata}» e «{piatta}» danno token diversi")


@pytest.mark.parametrize("frase,parola", [
    ("Il perché non è più chiaro.", "perche"),
    ("Ha superato la metà del percorso.", "meta"),
    ("La città è grande.", "citta"),
])
def test_la_parola_accentata_non_viene_troncata(frase, parola):
    """«perché» diventava `perch`, «città» diventava `citt`: la troncatura
    fabbrica una parola che non esiste in nessuna delle due grafie."""
    assert parola in content_tokens(frase), (
        f"«{parola}» non e' fra i token di «{frase}»: {sorted(content_tokens(frase))}")


@pytest.mark.parametrize("frase,attesi", [
    # cirillico: nessun diacritico, i token restano come si scrivono.
    ("Склад в Ровиго имеет 4200 квадратных метров.", {"склад", "ровиго", "квадратных", "метров"}),
    # greco: i toni cadono con la normalizzazione, esattamente come gli accenti
    # italiani. È lo stesso trattamento, applicato a tutti allo stesso modo —
    # «αποθήκη» -> «αποθηκη» — e vale come presidio: la cura non è ritagliata
    # sull'italiano, è una regola sull'alfabeto.
    ("Η αποθήκη στο Ροβίγκο έχει 4200 τετραγωνικά.", {"αποθηκη", "ροβιγκο", "τετραγωνικα"}),
])
def test_gli_alfabeti_non_latini_producono_token(frase, attesi):
    """Cirillico e greco sono alfabeti ORDINARI, con gli spazi fra le parole:
    nulla li distingue dal latino se non il blocco Unicode. Restituire zero
    token per loro significa che ogni guardia costruita sulla sovrapposizione
    lessicale è cieca in quelle lingue — né supersessione né rilevamento di
    contraddizioni."""
    trovati = content_tokens(frase)
    assert attesi <= trovati, f"mancano {attesi - trovati} in {sorted(trovati)}"


def test_il_prezzo_dichiarato_gli_omografi():
    """IL COSTO, scritto perché non lo si scopra per caso.

    In italiano l'accento distingue parole: `metà` (la parte) e `meta` (il
    fine) diventano lo stesso token. È un prezzo reale, accettato perché
    misurato: sul corpus vivo non produce nemmeno una coppia sopra soglia in
    più (3000 coppie casuali, +0), e la coppia che UNISCE — `perché`/`perche`,
    410 occorrenze — è più frequente di quella che confonde (`metà` 8 contro
    `meta` 537, e quest'ultima è quasi sempre il prefisso «meta-»).

    Se un giorno questa confusione costerà qualcosa di misurabile, la strada è
    un'analisi morfologica, non il ritorno ad ASCII."""
    assert content_tokens("Ha raggiunto la metà.") == content_tokens("Ha raggiunto la meta.")


def test_le_cifre_e_i_token_corti_restano_fuori():
    """La cura gemella è già falsificata sul corpus (`7aa678f57c73`): conservare
    token corti e cifre porta le coppie sopra soglia da 848 a 2293 su 3000, cioè
    PIÙ ritiri. Qui cambia l'alfabeto, non la soglia."""
    t = content_tokens("Il server 42 ha 64 GB e tre CPU.")
    assert "42" not in t and "64" not in t
    assert "tre" not in t and "cpu" not in t
    assert "server" in t
