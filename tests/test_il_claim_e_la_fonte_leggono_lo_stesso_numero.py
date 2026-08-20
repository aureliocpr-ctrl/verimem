"""La stessa stringa, letta come claim e come fonte, dava due numeri diversi.

`valori_non_nella_fonte` legge i due lati con DUE modalità: il claim con
``extract_quantities(prop)``, la fonte con ``extract_quantities(src,
come_fonte=True)``. Sulle versioni attaccate a un nome le due letture non
coincidono, e la differenza va nel verso peggiore — il claim FABBRICA un valore
che la fonte non può produrre::

    stringa                    come CLAIM     come FONTE
    "… click-8.4.2."           ('', 4.2)      —              il claim inventa
    "… pytest-8.4.1."          ('', 4.1)      —              il claim inventa
    "… python-3.12."           ('', 12.0)     ('', 3.12)     due numeri diversi
    "cli.py-354-"              —              ('', 354.0)    verso innocuo

⇒ Con `click-8.4.2` su ENTRAMBI i lati, L4.1 dichiarava assente un valore che
nella fonte c'è alla lettera, e il fatto usciva `quarantined` col giudice a
99,98. Misurato il 20/08 alla porta del prodotto (quattro scritture, tutte
`layers=['L4.1']`) e alla funzione.

📏 PORTATA, misurata e piccola — si dichiara perché non gonfi il risultato: sui
12.763 fatti del corpus 219 hanno quella forma, ma dei 197 quarantinati col
giudice sopra 99 solo CINQUE, e tre erano scritture dell'esperimento stesso.
Non è la causa del fronte quarantena: è la forma di ogni riga `Successfully
installed`, quindi colpisce le misure di dipendenza che scriviamo di continuo.

⚖️ LA CURA STA IN `valori_non_nella_fonte` E NON IN `extract_quantities`, ed è
la scelta che il modulo dichiara già per «nessun X vale 0»: toccare l'estrattore
alimenterebbe i sei moduli del gate che lo leggono, mentre qui l'equivalenza
vive solo nel confronto fra claim e fonte.
"""
from __future__ import annotations

import pytest

from verimem.valore_non_nella_fonte import valori_non_nella_fonte


def _assenti(claim: str, fonte: str) -> list[str]:
    return [f"{v.come_scritto()}" for v in valori_non_nella_fonte(claim, fonte)]


@pytest.mark.parametrize("token", [
    "click-8.4.2", "pytest-8.4.1", "numpy-1.26.4", "torch-2.3.1",
    "python-3.12", "node-20.11.1", "foo-1.2.3",
])
def test_la_stessa_stringa_sui_due_lati_non_e_un_valore_assente(token):
    """IL CUORE: se il testo è IDENTICO nel claim e nella fonte, nessun valore
    del claim può essere «non nella fonte»."""
    frase = f"Il pacchetto installato e' {token}."
    assenti = _assenti(frase, frase)
    assert not assenti, (
        f"{token}: la stessa stringa sui due lati dichiara assente {assenti}")


def test_il_caso_reale_di_una_riga_successfully_installed():
    """Il caso che l'ha fatto vedere: un fatto che cita la versione letta da un
    log di installazione."""
    fonte = ("click 8.1.8\n"
             "Successfully installed click-8.4.2 pytest-8.4.1 iniconfig-2.1.0\n")
    claim = ("In locale click e' alla versione 8.1.8 mentre in CI risulta "
             "installato click-8.4.2.")
    assert not _assenti(claim, fonte), _assenti(claim, fonte)


# ── I CONTROLLI OPPOSTI: senza questi la cura potrebbe essere «non vetare mai» ──

def test_CONTROLLO_una_versione_INVENTATA_resta_fermata():
    """⚠️⚠️ IL PRESIDIO CHE VALE PIÙ DELLA CURA. Un `nome-X.Y.Z` che nella fonte
    NON c'è deve continuare a essere dichiarato assente, altrimenti la cura ha
    spento il layer invece di renderlo simmetrico."""
    fonte = "Successfully installed click-8.4.2 pytest-8.4.1\n"
    claim = "In CI risulta installato click-9.9.9."
    assert _assenti(claim, fonte), (
        "una versione che la fonte non contiene non e' piu' segnalata: "
        "il veto e' stato spento")


def test_CONTROLLO_un_numero_ordinario_assente_resta_fermato():
    """Secondo controllo, fuori dalla forma delle versioni: il layer deve
    continuare a fare il suo mestiere sui numeri normali."""
    assert _assenti("Il file pesa 12 MB.", "Il file pesa 10 MB.")
