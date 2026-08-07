"""«Sul» e «Dopo» venivano contati come nomi propri, e proteggevano ciò che non c'è.

IL DIFETTO, misurato da ws4 sulle 147 coppie vere del corpus e confermato da ws1
su 21151 conflitti (24,2% contro 26,5% — due stime indipendenti che convergono).
``_CAPS_NAME_RE`` e' ``\\b[A-Z][a-zA-Z]{2,}\\b``: una maiuscola e due lettere. In
italiano quella firma la soddisfano tutte le parole che APRONO una frase::

    «Sul corpus reale…»  vs  «Dopo la cura…»     -> soggetti «Sul» e «Dopo»
    «ASSUNTO che…»       vs  «CONFERMATA la…»    -> soggetti urlati
    «TEST verde»         vs  «EMPIRICO il dato»

⇒ Due frasi che cominciano con parole diverse hanno «nomi propri disgiunti», e
la guardia conclude che parlano di due cose diverse. Non e' una protezione: e'
un veto che scatta sulla punteggiatura.

⚠️ E IL DIFETTO E' DOPPIO E OPPOSTO, che e' la ragione per cui va curato prima
di estendere la guardia ad altri rami::

    NON VEDE  S-007, SRV-12, L-45   (cifra e trattino: gli identificatori dei
                                     domini veri — macchine, lotti, ticket)
    VEDE      Sul, Dopo, ASSUNTO    (parole comuni a inizio frase)

Curare solo il primo lato allargherebbe il rumore; curare solo il secondo
lascerebbe scoperti i domini che il prodotto deve servire. Qui si chiude il
SECONDO, che e' quello che ws4 e ws1 hanno misurato.

📌 IL CRITERIO E' DI ws4, e l'ha misurato su ENTRAMBE le popolazioni prima di
proporlo — «un nome proprio non apre la frase e non ha un determinante
davanti»: sulle 147 coppie vere toglie 22 falsi soggetti E AGGIUNGE 5
protezioni su coppie con sovrapposizione mediana 3,9%, cioe' ritiri quasi
certamente sbagliati che oggi passano. I casi protetti scendono da 39 a 22 e
sono piu' puliti. **Migliora le due popolazioni insieme**, che e' raro: quasi
tutti i criteri di oggi ne miglioravano una peggiorando l'altra.

🔑 E LA LISTA DEI DETERMINANTI NON SI SCRIVE: ``composer._ARTICOLI_TUTTI``
esiste gia' con la motivazione scritta per questo uso. I determinanti sono
chiusi dalla lingua (nessuna lingua ne acquisisce di nuovi) quindi l'allowlist
e' legittima secondo il criterio che questa casa applica alle liste. Un import,
zero lista da mantenere — ed e' la classe ②-bis: la cura c'era e mancava il
collegamento.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import _named_subjects_disjoint as disgiunti

#: Frasi che NON nominano soggetti distinti: la parola maiuscola e' una parola
#: comune che apre la frase o segue un determinante.
NON_SONO_SOGGETTI = [
    ("Sul corpus reale la cura regge.", "Con la verifica il dato cambia."),
    ("Nel tracker c'e' l'issue.", "Sul piano c'e' il task."),
    ("Per il gate serve la fonte.", "Non tutti i fatti la hanno."),
    ("Il server ha 300 gigabyte.", "Lo storage ha 500 gigabyte."),
    ("Come misura vale poco.", "Piu' avanti si vedra'."),
]

#: ⚠️ LA POPOLAZIONE OPPOSTA: nomi propri VERI, che devono continuare a
#: proteggere. Senza, il test sopra e' soddisfatto da una funzione che
#: risponde sempre False — cioe' spegnendo la guardia invece di curarla.
SONO_SOGGETTI_VERI = [
    # ⚠️ UN MIO ERRORE CORRETTO DAL BANCO, e vale la pena scriverlo: qui avevo
    # scritto «300 GB di RAM» / «500 GB di RAM», e il test pretendeva che la
    # cura sbagliasse. `RAM` e' maiuscola con tre lettere, quindi la firma del
    # riconoscitore la conta come NOME PROPRIO — in entrambe le frasi. I due
    # insiemi condividevano `RAM` e non erano disgiunti, per una ragione che
    # non c'entra niente con Orion e Zephyr.
    # 🔑 E' il TERZO difetto dello stesso riconoscitore, dopo «non vede S-007» e
    #   «vede Sul»: **conta gli ACRONIMI TECNICI** (RAM, CPU, SQL, API, HTTP).
    #   Qui l'effetto e' benigno — unisce due frasi che parlano della stessa
    #   cosa — ma e' la stessa firma troppo larga, e chi lo curera' deve saperlo.
    ("Orion ha 300 gigabyte di memoria.", "Zephyr ha 500 gigabyte di memoria."),
    ("Il gateway Orion monta la 2.1.", "Il gateway Zephyr monta la 3.4."),
    ("La sede di Milano ha 120 dipendenti.", "La sede di Napoli ha 250 dipendenti."),
    ("Il progetto Helios parte a giugno.", "Il progetto Aurora parte a luglio."),
]


@pytest.mark.parametrize("a,b", NON_SONO_SOGGETTI)
def test_una_parola_comune_a_inizio_frase_non_e_un_soggetto(a, b):
    """IL CUORE: «Sul» e «Dopo» sono maiuscole perche' aprono la frase. Contarle
    come nomi propri fa concludere che due frasi parlano di cose diverse ogni
    volta che cominciano con parole diverse — cioe' quasi sempre."""
    assert not disgiunti(a, b), f"«{a[:24]}…» / «{b[:24]}…» letti come soggetti diversi"


@pytest.mark.parametrize("a,b", SONO_SOGGETTI_VERI)
def test_CONTROLLO_POSITIVO_due_nomi_propri_restano_disgiunti(a, b):
    """⚠️ IL PRESIDIO CHE IMPEDISCE DI SPEGNERE LA GUARDIA. Orion e Zephyr sono
    due cose diverse, e una versione diversa fra loro non e' un conflitto: se
    questo cadesse, il detector fonderebbe due oggetti distinti."""
    assert disgiunti(a, b), f"«{a[:24]}…» / «{b[:24]}…» non piu' protetti"


def test_il_nome_proprio_a_INIZIO_frase_resta_riconosciuto():
    """⚠️ IL CASO CHE POTEVA ROMPERE LA CURA, e va misurato perche' e' comune:
    un nome proprio PUO' aprire la frase («Orion ha 300 GB»). Scartare la prima
    parola per posizione spegnerebbe la guardia proprio dove serve.

    Regge perche' il criterio non e' posizionale puro: la prima parola cade solo
    se e' anche una parola comune — cioe' se compare in minuscolo altrove nel
    corpus della coppia, o e' un determinante. «Orion» non lo e'.
    """
    assert disgiunti("Orion ha 300 gigabyte.", "Zephyr ha 500 gigabyte.")


def test_LIMITE_DICHIARATO_dopo_e_i_participi_urlati_restano_scoperti():
    """⚠️ IL LIMITE, misurato e scritto invece che allargato per far passare il
    test. «Dopo», «Questo», «ASSUNTO», «CONFERMATA» aprono la frase ma NON sono
    in ``_NON_UNIT_WORDS``, quindi restano contati come nomi propri.

    ⛔ La strada facile era aggiungerli alla lista. Non l'ho presa: sarebbero
    entrati per far passare quattro casi che ho scritto io, non perche' una
    misura lo chiedesse. Sul corpus reale «Dopo» apre 53 proposizioni su 8865 —
    lo 0,6% — mentre «Nel», «Con», «Sul», «Per», «Non», gia' coperti, ne aprono
    794. La lista si estende quando un dato lo chiede.
    """
    assert disgiunti("Dopo la verifica il dato cambia.",
                     "Questo scenario invece fallisce.")


def test_LIMITE_DICHIARATO_le_sigle_restano_invisibili():
    """⚠️ L'ALTRA META' DEL DIFETTO, scritta invece che nascosta: ``S-007`` e
    ``SRV-12`` NON sono ancora riconosciuti come soggetti, perche' la firma
    esige due lettere dopo la maiuscola e loro hanno cifra e trattino.

    Nei domini veri — magazzini, macchine, lotti, ticket, server — quegli
    identificatori sono LA norma, e li' un conflitto falso non degrada un fatto:
    fonde due oggetti fisici distinti. E' aperto e non e' questa la cura:
    allargare alle cifre farebbe entrare versioni e date come soggetti, e
    romperebbe i due rami che la guardia gia' serve (controipotesi di ws4).
    """
    assert not disgiunti("La macchina S-007 monta la 2.1.",
                         "La macchina S-101 monta la 3.4.")
