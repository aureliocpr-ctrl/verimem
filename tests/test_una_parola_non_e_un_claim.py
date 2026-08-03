"""«Le stazioni sono distribuite sul territorio» non è un claim di rilascio.

IL DIFETTO, portato da ws5 il 2026-08-04 facendo dogfooding da utente esterno
su domini che il corpus non ha mai visto (sismologia, clinica, agronomia): una
sezione Metodi con `grounding_score` **100.0** finiva quarantinata perché
conteneva la parola «distribuite». `SHIPPED_KEYWORDS` cerca sottostringhe, e
`DISTRIBUIT` sta dentro «distribuite», che in italiano scientifico significa
«collocate nello spazio».

LA MISURA, mia, sul verso largo — perché il caso singolo non dice quanto è
grande la falla:

    frase                                             oggi
    «le stazioni sono distribuite sul territorio»     DISTRIBUIT  ← falso
    «il farmaco viene rilasciato nel sangue»          RILASCIAT   ← falso
    «il permesso è stato rilasciato dalla questura»   RILASCIAT   ← falso
    «i sensori sono cablati al quadro elettrico»      CABLAT      ← falso
    «the package was shipped by courier»              SHIPPED     ← falso
    «the sensors are wired to the electrical panel»   WIRED       ← falso

Sei falsi positivi su sei in italiano, **due su quattro in inglese**. Il
difetto non l'ho introdotto io aggiungendo le radici italiane il 03/08:
`SHIPPED` è anche «spedito» e `WIRED` è anche «collegato via cavo» da sempre.
La mia aggiunta l'ha reso VISIBILE, perché in italiano il senso non-software di
quei verbi è quello dominante — «rilasciare» un documento o una sostanza è più
comune che rilasciare software.

PERCHÉ NON SI VEDEVA. Sul corpus di casa, 573 fatti vivi su 5522 (10,4%)
contengono una di quelle parole, e a leggerli sono quasi tutti claim software
VERI: commit, PR, branch, pipeline. È un corpus di sviluppo software. La lista
è tarata su quel dominio e viene usata su tutti — la stessa classe delle
stoplist monolingue e dei detector L1 solo inglesi, per la terza volta in
quattro giorni.

LA CURA NON È ALLUNGARE LA LISTA, è cambiare la forma del test: da «c'è la
parola» a «c'è la parola **E** si sta parlando di software». Un asse nuovo,
indipendente dal primo. E il vocabolario del dominio software è quasi tutto
inglese anche quando si scrive in italiano — commit, branch, deploy, endpoint,
build — quindi la seconda lista NON eredita il difetto monolingue della prima:
è la stessa in ogni lingua.

MISURATO CONTRO I 573 CASI VERI: ne restano catturati 559 (**97,6%**). I 14
rilasciati letti uno per uno: 8 sono falsi positivi veri — fra cui i referti
che ws5 ha scritto per DESCRIVERE il difetto, che il difetto quarantinava — 3
sono report di conteggi («il tool riporta 861 nella categoria shipped»), che è
giusto rilasciare, e 3 erano claim software veri, recuperati allargando il
vocabolario alle estensioni di file e a «comando»/«doc».

⚠️ COSA QUESTA CURA NON FA, detto qui perché non si perda: resta lessicale. La
domanda giusta sarebbe «chi è il soggetto, e chi scrive?» — «ho distribuito il
modulo» e «le stazioni sono distribuite» hanno lo stesso verbo e statuto
epistemico opposto (l'osservazione è di ws4, sui detector L1). Quella cura
richiede un giudizio semantico, e il 04/08 ho misurato che il CE distillato su
quell'asse non ha segnale. Qui si sposta il tasso di falsi positivi da 6/6 a
0/6 sulla dimensione che si può presidiare oggi.
"""
from __future__ import annotations

import pytest

from verimem.anti_confabulation import detect_unsupported_shipped_claim

#: Il mondo, che non parla di software. Sono le frasi vere del referto di ws5
#: piu' quelle che ho aggiunto misurando l'ampiezza.
NON_SOFTWARE = [
    "Le stazioni di misura sono distribuite sul territorio nazionale.",
    "La popolazione e' distribuita in modo non uniforme sulla valle.",
    "Il farmaco viene rilasciato lentamente nel sangue.",
    "Il permesso di soggiorno e' stato rilasciato dalla questura.",
    "Il calore rilasciato dalla reazione e' di 40 kJ per mole.",
    "I sensori sono cablati al quadro elettrico dell'impianto.",
    "The package was shipped by courier on Monday morning.",
    "The sensors are wired to the electrical panel.",
    "The measuring stations are distributed over the whole territory.",
]

#: I claim che la regola esiste per prendere: parlano di software E dichiarano
#: che una cosa e' stata fatta.
SOFTWARE = [
    "Il modulo di autenticazione e' stato rilasciato in produzione.",
    "Il fix e' stato mergiato nel branch principale.",
    "The endpoint was deployed to staging yesterday.",
    "Il nuovo comando e' stato cablato nella CLI.",
    "RERANK LAYER WIRED 2026-06-03: engram/rerank.py con wrapper a due stadi.",
    "Il documento CAPABILITIES.md e' stato shipped stanotte.",
]


@pytest.mark.parametrize("frase", NON_SOFTWARE)
def test_il_mondo_che_non_parla_di_software_passa(frase):
    """Il cuore. Ognuna di queste contiene una parola sorvegliata e nessuna
    afferma di aver rilasciato qualcosa: quarantinarle vuol dire chiedere un
    commit a un sismologo."""
    assert detect_unsupported_shipped_claim(proposition=frase, verified_by=[]) is None, (
        f"«{frase}» non e' un claim di rilascio, e viene trattata come tale")


@pytest.mark.parametrize("frase", SOFTWARE)
def test_i_claim_di_rilascio_veri_restano_presi(frase):
    """IL VERSO OPPOSTO, ed e' quello che rende la cura sicura invece che
    comoda: senza questo, «restringi finche' non si lamenta piu' nessuno»
    sarebbe un modo di spegnere il detector. La regola nasce da 2 confabulazioni
    su 7 nella sessione del 2026-05-17."""
    assert detect_unsupported_shipped_claim(proposition=frase, verified_by=[]) is not None, (
        f"«{frase}» dichiara un rilascio senza prova e non viene piu' vista")


def test_LA_STESSA_FRASE_cambia_natura_col_contesto():
    """Il caso che ha insegnato dove sta davvero il segnale.

    «This was shipped last week» e' il claim che ha fatto nascere la regola
    (2026-05-17, 2 confabulazioni su 7) e non contiene UN SOLO termine
    tecnico: nessuna lista di parole potra' mai riconoscerlo dal testo. Ma il
    prodotto sa gia' sotto quale topic sta scrivendo, e li' la differenza c'e'
    tutta — la stessa identica frase, in un corpus di sismologia, non dichiara
    nessun rilascio.

    E' il motivo per cui questa cura non e' l'ennesimo elenco: il contesto non
    va indovinato dal testo, va LETTO da dove sta gia'."""
    frase = "This was shipped last week."
    assert detect_unsupported_shipped_claim(
        proposition=frase, verified_by=[], topic="project/verimem/cli") is not None, (
        "in un progetto software questo e' esattamente il claim da ancorare")
    assert detect_unsupported_shipped_claim(
        proposition=frase, verified_by=[], topic="ricerca/sismologia") is None, (
        "in un corpus di sismologia si sta chiedendo un commit a un sismologo")


def test_senza_topic_si_decide_solo_col_testo():
    """Il `topic` e' facoltativo: i chiamanti che non lo passano devono
    continuare a funzionare, decidendo sul solo testo. Senza questo la cura
    sarebbe una rottura di contratto travestita da miglioria."""
    assert detect_unsupported_shipped_claim(
        proposition="Il fix e' stato mergiato nel branch principale.",
        verified_by=[]) is not None
    assert detect_unsupported_shipped_claim(
        proposition="Le stazioni sono distribuite sul territorio.",
        verified_by=[]) is None


def test_un_commit_ancora_il_claim_come_prima():
    """La porta d'uscita legittima non si tocca."""
    assert detect_unsupported_shipped_claim(
        proposition="Il fix e' stato mergiato nel branch principale.",
        verified_by=["commit:abc123def"]) is None


def test_il_referto_che_DESCRIVE_il_difetto_non_ne_e_vittima():
    """Il caso che ha fatto ridere e pensare: fra i 573 fatti catturati sul
    corpus vivo ci sono quelli con cui ws5 denunciava il difetto. Un prodotto
    che quarantina il verbale del proprio guasto rende piu' difficile
    ripararlo."""
    referto = ("La frase sulle stazioni di misura con la parola distribuite "
               "entra quarantined per la keyword DISTRIBUIT.")
    assert detect_unsupported_shipped_claim(proposition=referto, verified_by=[]) is None


@pytest.mark.xfail(reason="il lessicale non ci arriva; la via semantica si', "
                          "misurata — vedi il corpo del test", strict=True)
def test_la_parola_tecnica_di_DUE_mondi():
    """Il residuo del lessicale, e la strada che lo supera — gia' misurata.

    «I sensori sono cablati al quadro elettrico secondo lo schema» resta
    catturata: tolto il trigger `cablat`, il contesto dev viene trovato lo
    stesso da «schema», che e' un termine tecnico in ENTRAMBI i mondi — lo
    schema di un database e lo schema di un impianto elettrico. Lo stesso
    varrebbe per «sistema», «file» (un fascicolo), «test» (un esame clinico),
    «rete» (idrica), «funzione» (matematica). Allargare le esclusioni non
    chiude: e' la trappola da cui nasce tutto questo lavoro.

    ⚠️ NON E' UN MURO, ED E' STATO MISURATO IL 2026-08-04. Una PAROLA non
    discrimina, una FRASE si', e il prodotto ha gia' l'organo giusto: non il
    CE distillato — su quell'asse non ha segnale, i suoi punteggi non
    distinguono `moment magnitude` da `local magnitude` — ma l'EMBEDDER
    multilingue, che fa il salto sinonimico (`Cmax` trova «concentrazione
    plasmatica di picco» a 0.7390, misura di ws4) e regge su dieci lingue
    (ws5). Con due prototipi di dominio e un coseno, su 14 frasi:

        12/14 classificate bene dal SOLO coseno, e in particolare
        «cablati al quadro elettrico secondo lo schema»  -0.0199 -> MONDO  ok
        «lo schema del database e' stato migrato»        +0.0202 -> SW     ok

    cioe' proprio la coppia che il lessicale non puo' separare. Sbagliano
    «il farmaco viene rilasciato nel sangue» (+0.0024) e «il calore rilasciato
    dalla reazione» (+0.0164): il prototipo «mondo» che ho scritto parla di
    misure sul campo e documenti, non di chimica.

    PERCHE' NON E' GIA' IN PRODUZIONE: il margine minimo e' **0.0024**. Il
    segnale c'e' ed e' nella direzione giusta, ma tre millesimi non bastano a
    decidere una quarantena — e' lo stesso ordine di grandezza su cui ws4 ha
    mostrato che il coseno NON ordina gli esiti (`base/premium` perde a 0.9419
    mentre `annuale/mensile` vive a 0.9388). Un decisore tarato li' sarebbe
    instabile per costruzione.

    LA DIREZIONE CHE PROMETTE DI PIU', non ancora provata: i prototipi non
    dovrebbero essere scritti a mano ma PRESI DAL CORPUS — il centroide dei
    fatti di ciascun topic. Cosi' il dominio non si dichiara, si impara, e per
    un sismologo funziona come per uno sviluppatore senza che nessuno scriva
    una lista. Il costo e' quasi nullo: nel percorso di scrittura l'embedding
    del fatto viene gia' calcolato per il recall.

    `strict=True`: quando passera', questo test FALLISCE e va riletto.
    """
    assert detect_unsupported_shipped_claim(
        proposition="I sensori sono cablati al quadro elettrico secondo lo "
                    "schema di impianto.",
        verified_by=[]) is None


def test_un_conteggio_non_e_una_dichiarazione_di_rilascio():
    """«Il tool riporta 861 fatti nella categoria shipped» osserva un numero,
    non afferma di aver rilasciato: e' una frase SUL prodotto, non un claim
    del prodotto."""
    assert detect_unsupported_shipped_claim(
        proposition="Il tool anti_confab_scan riporta 1121 orphan facts con 861 nella "
        "categoria shipped e 250 in diagnosis.", verified_by=[]) is None
