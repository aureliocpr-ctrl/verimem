"""«NON» era il nome proprio piu' frequente del corpus.

`_extract_salients` riconosce i nomi propri con `\\b([A-Z][a-zA-Z]{2,})\\b`:
qualunque parola con l'iniziale maiuscola e almeno tre lettere. Una parola
URLATA per enfasi la soddisfa, quindi entra fra i nomi — e
`_parole_di_contenuto` toglie i nomi dal contenuto, perche' li conta a parte.

Misurato sul corpus di Aurelio il 2026-08-02, sui 5151 fatti vivi:

    nomi distinti estratti: 14102   occorrenze: 86977
    di cui TUTTE MAIUSCOLE:  7833 distinte, 54717 occorrenze

    le piu' frequenti:  1461 NON · 655 MCP · 570 TDD · 531 LLM · 475 CLI
                         414 LOOP · 356 REALE · 355 VERIFICATO · 333 PROSSIMO

Il 63% dei «nomi propri» del corpus sono parole urlate, e la prima e' una
NEGAZIONE. Conseguenza diretta, verificata:

    Il gate NON gira sul canale MCP. -> contenuto ['canale','gate','gira','sul']
    Il gate gira sul canale MCP.     -> contenuto ['canale','gate','gira','sul']
    stesse parole di contenuto: True

Una frase e la sua negazione sono indistinguibili per il criterio che decide
se un fatto e' l'EVOLUZIONE di un altro. La seconda ritira la prima come se
fosse un aggiornamento, mentre dice il contrario.

DUE CURE, E LA PRIMA VERSIONE DELLA SECONDA ERA SBAGLIATA.

(1) Le parole URLATE non sono nomi propri: un nome proprio e' in Title Case,
    TUTTO MAIUSCOLO e' enfasi o sigla. «VERIFICATO», «REALE», «MCP», «TDD»
    tornano fra le parole di contenuto, dove portano il peso che hanno.
    Portata sul pregresso: ZERO — sulle 260 coppie corte gia' superseduta,
    riconosciute evoluzione 228 prima e 228 dopo.

(2) La negazione NON e' una parola in piu' da contare. Il primo tentativo la
    rimetteva fra le parole di contenuto (togliendola da `_PAROLE_VUOTE`, dove
    sta per l'italiano e NON per `not`/`no`/`mai`/`senza`/`never`/`without` —
    incoerenza vera e a se' stante), e MISURATO PEGGIORAVA: 228 -> 229
    evoluzioni, e la coppia in piu' e' un falso positivo, due osservazioni
    diverse unite dal solo fatto di nominare entrambe «non».

    La forma giusta e' la POLARITA': due frasi con polarita' diversa non sono
    l'una l'aggiornamento dell'altra, e il confronto non gonfia nessuna
    intersezione. Il caso peggiore — una frase e la sua negazione, che hanno
    le stesse parole e la stessa testa — si separa; la coppia che nomina «non»
    per caso non si muove.
"""
from __future__ import annotations

from verimem.validate_claim import (
    _extract_salients,
    _parole_di_contenuto,
    _testa_nominale,
)


def test_una_frase_e_la_sua_negazione_non_sono_un_aggiornamento():
    """Il caso peggiore, e la ragione per cui la polarita' esiste.

    Le due frasi hanno le STESSE parole di contenuto e la stessa testa
    nominale — quindi per le due condizioni della guardia sono lo stesso fatto
    aggiornato. E' la polarita' a separarle.
    """
    from verimem.anti_confab_gate import _puo_essere_una_evoluzione

    a = "Il gate NON gira sul canale MCP."
    b = "Il gate gira sul canale MCP."
    assert _parole_di_contenuto(a) == _parole_di_contenuto(b), (
        "presupposto del test: e' proprio perche' sono uguali che serve altro")
    assert _puo_essere_una_evoluzione(b, a) is False, (
        "la negazione non e' un aggiornamento: dice il contrario")


def test_la_polarita_non_gonfia_l_intersezione():
    """La strada scartata, tenuta ferma da un test.

    Rimettere le negazioni fra le parole CONTATE porta le riconosciute-
    evoluzione da 228 a 229 sulle 260 coppie corte del corpus, e la coppia in
    piu' e' un falso positivo: due osservazioni diverse unite dal solo fatto di
    nominare entrambe «non». Come POLARITA' quel caso non si muove — hanno la
    stessa — e a decidere resta il criterio di prima.
    """
    from verimem.validate_claim import _polarita

    a = "Nel grafo entity_kg l acronimo con piu fatti collegati e NON con 416."
    b = "Nel corpus la parola non compare 2004 volte tutta maiuscola."
    assert _polarita(a) == _polarita(b), "stessa polarita': non le separa"
    assert "non" not in _parole_di_contenuto(a), (
        "la negazione NON deve entrare fra le parole contate")


def test_un_participio_urlato_resta_contenuto():
    """Qui la cura sulle maiuscole vale ed e' senza controindicazioni:
    «VERIFICATO» e «REALE» non sono nomi propri e portano contenuto."""
    a = _parole_di_contenuto("Il commit e VERIFICATO sul corpus REALE.")
    b = _parole_di_contenuto("Il commit e sul corpus.")
    assert a != b, f"«VERIFICATO» e «REALE» spariti: {sorted(a)}"


def test_una_sigla_e_contenuto_non_un_nome_proprio():
    """MCP, TDD, API: portano contenuto e vanno contate come tale."""
    p = _parole_di_contenuto("Il canale MCP giudica come la CLI.")
    assert "mcp" in p and "cli" in p, sorted(p)


def test_un_nome_proprio_VERO_resta_un_nome_proprio():
    """La cura non deve spostare i nomi in Title Case, che sono il caso per
    cui la funzione esiste: «Rex» non e' una parola di contenuto."""
    caps, _ = _extract_salients("Rex is a labrador from Roma.")
    assert "Rex" in caps and "Roma" in caps, caps
    p = _parole_di_contenuto("Rex is a labrador from Roma.")
    assert "rex" not in p and "roma" not in p, sorted(p)


def test_extract_salients_NON_e_stata_toccata_ed_e_una_scelta():
    """La cura sta in `_parole_di_contenuto`, non in `_extract_salients`.

    Quella funzione fa cio' che il suo nome dichiara — estrarre le parole
    CAPITALIZZATE — e «NON» lo e'. Il fatto che non sia un nome proprio e' una
    lettura in piu', e i suoi altri due consumatori la usano per cose diverse:
    `salient_count` decide se una claim ha abbastanza entita' per un giudizio
    non solo lessicale, e `_subj_overlap` misura se claim e fatto parlano dello
    stesso soggetto. Cambiarla muoverebbe il gate che il banco delle 20 claim
    ha gia' misurato (8 confabulazioni su 10 «supported» -> 0), e questo giro
    non ha misurato QUELLO.

    Resta aperto e va guardato: `_subj_overlap` confronta «NON» come se fosse
    un soggetto. Dichiarato, non curato alla cieca.
    """
    caps, _ = _extract_salients("Il gate NON gira: PASS su MASTER.")
    assert "NON" in caps, (
        "se un giorno `_extract_salients` smette di restituire le urlate, "
        "rimisura il banco delle 20 claim prima di lasciarlo entrare")


def test_la_polarita_e_grezza_e_lo_dichiara():
    """Presenza di una negazione, non la sua portata sintattica. Non risolve
    la doppia negazione: dice solo che due frasi hanno polarita' diverse, che
    basta per NON dichiararle un aggiornamento l'una dell'altra."""
    from verimem.validate_claim import _polarita

    assert _polarita("Il daemon NON e' partito.") is True
    assert _polarita("Il daemon e' partito.") is False
    assert _polarita("The daemon did not start.") is True
    assert _polarita("Le daemon n a pas demarre sans erreur.") is True
