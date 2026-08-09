"""«120 l'anno» e «120 l» erano la stessa quantità: 120 LITRI.

IL DIFETTO. Un canone annuo e una cisterna producevano la stessa identica
coppia ``('l', 120.0)``::

    «il canone e' 120 l'anno»      -> [('l', 120.0)]     ← 120 LITRI
    «la tanica contiene 120 l»     -> [('l', 120.0)]     ← 120 litri, vero

🔑 È LA CLASSE ④, LA GIUNTURA — due cose GIUSTE che combinate ingannano.
``l`` è il litro, ed è giusto. Il regex delle quantità si ferma all'apostrofo,
e anche questo è giusto: l'apostrofo non è una lettera. Nessuno dei due
componenti contiene il difetto; **lo contiene la loro combinazione**, che
fabbrica un'unità di misura da un testo che non ne ha nessuna.

⚠️ COSA COSTA, e non è il solito conflitto in più: due fatti che non
condividono nulla diventano CONFRONTABILI. Con lo stesso valore si CONFERMANO
a vicenda («il canone è 120 l'anno» conferma «la cisterna contiene 120 l»); con
valori diversi diventano un conflitto numerico, e il conflitto porta alla
supersessione — cioè al ritiro di un fatto vero. È il danno che questo stesso
modulo documenta a riga 49 («otto fatti veri su nove fuori dal recall»).

E il moncone non è solo ``l``: **nessuna forma elisa era coperta**::

    40 all'ora -> 'all'      120 dell'anno -> 'dell'    30 nell'archivio -> 'nell'
    8 dall'inizio -> 'dall'  12 sull'insieme -> 'sull'

📌 PROVENIENZA: il caso delle elise è di ws4, che l'ha eseguito. La sua
diagnosi diceva «la lista contiene ``dell'`` con apostrofo ma il parser produce
``dell`` senza» — **e la lista non contiene NESSUNA voce apostrofata**: le
elisioni non erano state considerate, non erano state scritte male. Il caso
``l``/litro non era nel suo referto ed è quello che cambia la cura, perché è
l'unico moncone che è anche un'unità VERA.

⛔ PER QUESTO LA CURA NON È LA LISTA. Mettere ``l`` fra le non-unità
spegnerebbe il litro: «la tanica contiene 120 l» perderebbe la sua unità, che
è la popolazione opposta di questo test.

LA CURA È STRUTTURALE E SENZA LISTE, e la regola sta nella grammatica::

    apostrofo + VOCALE      -> elisione (IT/FR)   l'anno, all'ora, d'entre
    apostrofo + «s»/spazio  -> genitivo (EN)      days' notice, day's work

L'elisione italiana **esiste solo davanti a vocale** — è la sua definizione — e
il genitivo sassone non è mai seguito da vocale. Le due popolazioni non si
toccano, e la regola vale per ogni parola elisa senza enumerarne nessuna.

⚠️ CONTROIPOTESI CHE POTEVA UCCIDERLA, misurata prima di scrivere la cura: il
genitivo sassone mette un apostrofo dopo un'unità VERA, e oggi funziona («a 3
days' notice» -> ``day``). Una cura scritta come «apostrofo ⇒ non è un'unità»
avrebbe rotto tre casi veri per curarne sei.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities

#: Le forme ELISE: il moncone prima dell'apostrofo non è un'unità.
ELISIONI = [
    ("il canone e' 120 l'anno", 120.0),
    ("ne consuma 5 l'ora", 5.0),
    ("la macchina fa 40 all'ora", 40.0),
    ("il contratto vale 120 dell'anno", 120.0),
    ("ne restano 30 nell'archivio", 30.0),
    ("parte 8 dall'inizio", 8.0),
    ("sono 12 sull'insieme", 12.0),
    # ⚠️ l'apostrofo TIPOGRAFICO (U+2019) è quello che producono Word, iOS e i
    # modelli di linguaggio: se la cura guardasse solo l'ASCII, coprirebbe il
    # testo scritto a mano e non quello che questo store riceve davvero.
    ("la macchina fa 40 all’ora", 40.0),
    ("il canone e’ 120 l’anno", 120.0),
    # il francese, che di elisioni è fatto
    ("le loyer est 120 l'an", 120.0),
]

#: ⚠️ LA POPOLAZIONE OPPOSTA. Senza, la cura è soddisfatta da un parser che
#: non trova mai un'unità — cioè spegnendo la funzione invece di curarla.
UNITA_VERE = [
    ("la tanica contiene 120 l", "l"),          # ← il litro che la lista avrebbe spento
    ("il serbatoio ha 5 litri", "litro"),
    ("a 3 days' notice is required", "day"),    # ← il genitivo sassone
    ("after 6 months' delay", "month"),
    ("5 years' experience", "year"),
    ("la riunione e' durata 45 minuti", "minuto"),
    ("il magazzino contiene 300 pallet", "pallet"),
]


@pytest.mark.parametrize("frase,valore", ELISIONI)
def test_una_forma_ELISA_non_lascia_una_unita(frase, valore):
    """IL CUORE: «120 l'anno» non contiene litri. Il numero resta — è una
    quantità vera — ma senza unità, che è come il modulo tratta ogni numero
    seguito da una parola funzionale."""
    assert extract_quantities(frase) == {("", valore)}, frase


@pytest.mark.parametrize("frase,attesa", UNITA_VERE)
def test_CONTROLLO_POSITIVO_le_unita_vere_restano(frase, attesa):
    """⚠️ IL PRESIDIO CHE RENDE CONSEGNABILE LA CURA, e contiene i due casi che
    l'hanno decisa: «120 l» è il litro che una cura per liste avrebbe spento, e
    «3 days' notice» è l'unità vera seguita da apostrofo che una cura scritta
    come «apostrofo ⇒ non unità» avrebbe rotto."""
    unita = {u for u, _v in extract_quantities(frase) if u}
    assert attesa in unita, f"«{frase}» ha perso l'unità: {unita}"


def test_il_canone_e_la_cisterna_non_si_confondono_piu():
    """🔑 IL CASO CHE DÀ IL NOME AL FILE, ed è quello che costa: prima della
    cura le due frasi producevano la STESSA quantità, quindi si confermavano a
    vicenda pur non avendo nulla in comune."""
    canone = extract_quantities("il canone e' 120 l'anno")
    cisterna = extract_quantities("la tanica contiene 120 l")
    assert canone != cisterna, (
        f"un canone annuo e una cisterna producono la stessa quantita': {canone}")
    assert cisterna == {("l", 120.0)}    # la cisterna misura litri
    assert canone == {("", 120.0)}       # il canone misura 120 di niente
