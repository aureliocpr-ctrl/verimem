"""«Rossi pesa 70 kg» ritirato da «Bianchi pesa 95 kg»: stessa fonte, dicevano.

TROVATO da ws5 su un registro pazienti, e qui isolato fino al meccanismo. Il
banco: due scritture, stesso topic, e si cambia una variabile per volta.

    topic DIVERSI, nessuna source        entrambi vivi
    stesso topic, source DIVERSE         NE RESTA UNO — «same-source evolution»
    stesso topic, verified_by diversi    entrambi vivi

La riga di mezzo è il difetto. Chi scrive passa `source=` credendo di dichiarare
da dove viene il fatto — è quello che il prodotto stesso raccomanda, ed è ciò
che accende il moat — e per la supersessione resta «user», perché
`canonical_source_of` legge **solo** `verified_by`:

    canonical_source_of(f) = canonical_source(f.verified_by)   # fallback "user"

Due fatti senza `verified_by` sono entrambi `"user"`, quindi `is_same_source` è
vero, quindi il secondo «evolve» il primo. Sul corpus vivo **500 fatti su 6075
hanno un verified_by**: per gli altri 5575 qualunque coppia nello stesso topic è
un candidato al ritiro, qualunque cosa dicano.

E la source non si può nemmeno recuperare a posteriori: **la tabella `facts` non
ha una colonna `source`**. Il testo passato serve al moat per l'entailment e poi
viene buttato. L'unico campo di provenienza che sopravvive è
`source_signature`, che la CLI non popolava — valorizzato su 26 fatti in tutto
il corpus.

⇒ LA CURA È CONSERVARE CIÒ CHE L'UTENTE HA GIÀ DICHIARATO. Un'impronta della
source finisce in `source_signature`, e la reputazione la guarda prima di
ripiegare su «user». Non si inventa un criterio: si smette di buttare via
l'informazione che chi scrive ha già dato.

⚠️ IL PRESIDIO CHE RENDE LA CURA UNA CORREZIONE E NON UN BLOCCO: due fatti dalla
**stessa** fonte devono continuare ad aggiornarsi. Una memoria che non ritira
più nulla è rotta quanto una che ritira tutto — ed è il difetto che
`ENGRAM_SUPERSEDE_SAME_SOURCE=0` produce già oggi, misurato il 2026-08-03.

⚠️ PERCHÉ È SICURA SUL CORPUS ESISTENTE: `source_signature` è valorizzata su 26
fatti su 6075, tutti con lo stesso valore. La cura cambia il comportamento solo
delle scritture che dichiarano una source — cioè da qui in avanti.
"""
from __future__ import annotations

import pytest

from verimem.supersession_policy import is_same_source


class _F:
    """Un fatto ridotto a ciò che la politica di supersessione guarda."""

    def __init__(self, verified_by=None, source_signature=None):
        self.verified_by = verified_by or []
        self.source_signature = source_signature
        self.created_at = 1.0
        self.asserted_at = None


def test_due_source_diverse_non_sono_la_stessa_fonte():
    """Il cuore: due cartelle cliniche distinte non sono «la stessa fonte», e
    il secondo paziente non è un aggiornamento del primo.

    ✅ ERA `xfail(strict=True)` DAL 2026-08-04, E DAL 2026-09-06 PASSA
    (`6bd8c6ae` + `405ff0cd`). Il marker diceva: «la cura è stata scritta,
    misurata e RITIRATA: colpisce il bersaglio ma rompe il presidio qui sotto,
    e il comportamento cambia in un punto più a valle che non è stato isolato».

    Il punto a valle è stato isolato il 06/09, ed erano DUE cose:
      · il presidio misurava «quanti fatti restano vivi» e fondeva due
        meccanismi diversi — due dei suoi casi erano RITIRI (`L3-supersession`)
        e uno una QUARANTENA (`L4.1`), che con la supersessione non c'entra;
      · il caso che «regrediva» era costruito male: valore NUOVO contro una
        source che ha ancora quello VECCHIO. Non era l'aggiornamento legittimo
        che la cura rompeva, era un claim che la sua fonte non sostiene.

    ⚠️ E LA REGOLA CHE HA RESO LA CURA CONSEGNABILE ERA GIÀ SCRITTA QUI SOTTO,
    nel docstring di `test_il_verified_by_continua_a_comandare_quando_c_e`:
    «la source entra solo dove prima si sarebbe ripiegato sul fallback user».
    Il 06/09 quella riga è stata riderivata da capo, passando per una
    regressione vera (la stessa penna che aggiorna il proprio valore smetteva
    di ritirare) colta da un controllo positivo in un altro file. Leggerla qui
    sarebbe costato trenta secondi.
    """
    rossi = _F(source_signature="sha256:cartella-rossi")
    bianchi = _F(source_signature="sha256:cartella-bianchi")
    assert not is_same_source(rossi, bianchi)


def test_la_stessa_source_resta_la_stessa_fonte():
    """IL PRESIDIO, e la ragione per cui la cura è stata ritirata.

    Se il dato arriva due volte dalla stessa cartella, il secondo aggiorna il
    primo: è il mestiere di una memoria. Una che non ritira più nulla è rotta
    quanto una che ritira tutto — misurato il 2026-08-03 su
    `ENGRAM_SUPERSEDE_SAME_SOURCE=0`, che produce esattamente quel danno.

    Passa oggi (entrambi cadono sul fallback «user») e deve continuare a
    passare quando il difetto sopra sarà curato: è il presidio, non il
    bersaglio."""
    prima = _F(source_signature="sha256:cartella-rossi")
    dopo = _F(source_signature="sha256:cartella-rossi")
    assert is_same_source(prima, dopo)


def test_senza_source_il_comportamento_non_cambia():
    """La compatibilità: due fatti che non dichiarano nulla restano
    indistinguibili, come prima. La cura non inventa provenienza dove non ce
    n'è — sarebbe peggio del difetto."""
    assert is_same_source(_F(), _F())


def test_il_verified_by_continua_a_comandare_quando_c_e():
    """`verified_by` resta la chiave di reputazione dichiarata: la source entra
    solo dove prima si sarebbe ripiegato sul fallback «user»."""
    a = _F(verified_by=["source-doc:relazione2026:pag4"])
    b = _F(verified_by=["source-doc:relazione2026:pag9"])
    c = _F(verified_by=["source-doc:altroarchivio:pag1"])
    assert is_same_source(a, b)
    assert not is_same_source(a, c)


def test_una_source_non_scavalca_un_verified_by_esplicito():
    """Se chi scrive ha dichiarato un `verified_by`, quella è la sua parola
    sulla provenienza e vince: l'impronta della source è il ripiego, non il
    contrario."""
    a = _F(verified_by=["source-doc:archivio:1"], source_signature="sha256:x")
    b = _F(verified_by=["source-doc:archivio:2"], source_signature="sha256:y")
    assert is_same_source(a, b), (
        "il verified_by dichiarato dice che sono lo stesso archivio")
