"""T80 — il controllo sui NUMERI non ha bisogno del giudice, ma oggi lo aspetta.

IL DIFETTO, letto nel codice
-----------------------------
`anti_confab_gate`, nel ramo della fonte::

    if gscore is None:
        _emit_l4_skipped()          # <- e basta
    else:
        grounding_val = float(gscore)
        …
        # L4.1 — IL CONTROLLO DETERMINISTICO CHE MANCAVA

`L4.1` confronta i **numeri del claim** con quelli della **fonte**: è lessicale,
non chiama nessun modello, e gli servono soltanto le due stringhe che ha già in
mano. Eppure vive dentro il ramo `else`, cioè **solo quando il giudice ha dato
un punteggio**.

⇒ Mentre il giudice carica — `judge_state()` «warming», il caso di ogni prima
scrittura su una macchina fredda — la scrittura entra con l'avviso onesto
`L4-skipped`, **e nessuno guarda i numeri**. Un valore inventato passa, e passa
proprio nella finestra in cui l'utente è più esposto: la prima volta che usa il
prodotto.

🔑 **Non è il moat che manca: è un controllo che NON dipende dal moat, messo
dietro il moat.** L'avviso dice il vero — «entailment NOT verified» — ma dice
meno di quanto il prodotto potrebbe sapere in quel momento.

LA FORMA DEL BANCO
------------------
Tre celle a **una variabile sola**, il giudice:

* giudice ASSENTE + numero inventato → **oggi ammesso senza `L4.1`** ← il rosso
* giudice PRESENTE + lo stesso numero → `L4.1` c'è  ← prova che il caso è reale
* giudice ASSENTE + numeri che la fonte CONTIENE → nessun `L4.1`  ← prova che la
  cura non è «segnala sempre»

Senza la seconda, il rosso potrebbe essere un claim mal costruito invece di un
buco. Senza la terza, una cura che accendesse `L4.1` a ogni scrittura
passerebbe.

⚠️ Nessuna cella carica un modello: il giudice è reso indisponibile esattamente
come lo rende il prodotto.

LE TRE PORTE, E QUALE QUESTO BANCO COPRE
-----------------------------------------
`L4.1` non gira in **tre** situazioni diverse, non una — contate leggendo il
ramo, e il banco lo dice invece di lasciarlo dedurre::

    1  giudice configurato che NON dà un punteggio      COPERTA (2 celle)
       (`if gscore is None`, il caso del riscaldamento)
    2  NESSUN giudice configurato                        COPERTA (2 celle)
       (`elif source and not _have_judge`, ramo diverso)
    3  giudizio SPENTO ma giudice disponibile            🔴 NON COPERTA
       (né il primo `if` né l'`elif`: non gira il controllo
        e NON esce nemmeno l'avviso `L4-skipped`)

🔴 **PERCHÉ LA TERZA È FUORI, e non è una svista.** Lì il giudizio è spento
**per configurazione**: far girare un controllo che l'operatore ha chiesto di
non avere è una decisione di prodotto, non la cura di questo difetto. E c'è di
peggio — **quel ramo non dice nemmeno «non ho verificato»**: le prime due
almeno lo dichiarano. È un secondo difetto, più grave di questo, e merita un
ticket suo invece di essere assorbito qui in silenzio.

📌 **Ogni porta coperta porta il suo controllo positivo.** Senza, una cura che
accendesse i controlli dappertutto passerebbe su una porta e cadrebbe
sull'altra — e il banco direbbe «metà».
"""
from __future__ import annotations

import verimem.grounding_gate as gg
from verimem.anti_confab_gate import run_validation_gate

#: La fonte parla di 500 e 540. Di megabyte non dice niente.
FONTE = ("verbale: la coda aveva 500 elementi\n"
         "rettifica: la coda aveva 540 elementi\n")

#: La metà verbatim tiene alto il giudice quando c'è; il dettaglio con unità è
#: quello che la fonte TACE, cioè la classe che `L4.1` esiste per prendere.
CLAIM_CON_NUMERO_INVENTATO = "La coda ha 540 elementi e occupa 176 MB."

#: Stessa forma, ma ogni numero è nella fonte.
CLAIM_SENZA_NUMERI_NUOVI = "La coda ha 540 elementi, prima ne aveva 500."


def _cancello(claim: str):
    return run_validation_gate(
        proposition=claim, verified_by=None, topic="t/porte", agent=None,
        validate="full", source=FONTE, grounding_llm=object())


def _strati(res) -> list[str]:
    return sorted({str(w.get("layer", "")) for w in (res.warnings or [])})


def _senza_giudice(monkeypatch) -> None:
    """Il giudice non riesce a dare un punteggio: è lo stato «warming».

    Si sostituisce il simbolo che il punto di chiamata risolve — l'import è
    tardivo dentro `run_validation_gate`, quindi conta l'attributo del modulo.
    """
    monkeypatch.setattr(gg, "fact_grounding_score_ex", lambda *a, **k: (None, None))


def _con_giudice(monkeypatch, punteggio: float = 99.9) -> None:
    monkeypatch.setattr(gg, "fact_grounding_score_ex",
                        lambda *a, **k: (punteggio, "local"))


def _nessun_giudice_configurato(monkeypatch) -> None:
    """PORTA 2: nessun giudice, non uno che non sa rispondere.

    `_have_judge` è vero se c'è un llm iniettato, o il backend è locale, o il
    cross-encoder è sul disco, o il daemon si annuncia: si spengono tutte e
    quattro, altrimenti il caso finisce nella porta 1 e questa cella
    misurerebbe due volte la stessa cosa.
    """
    import verimem.local_grounding as lg
    monkeypatch.setattr(gg, "_resolve_backend", lambda *a, **k: "claude")
    monkeypatch.setattr(lg, "local_ce_available", lambda *a, **k: False)
    monkeypatch.setattr(lg, "daemon_del_giudice_annunciato", lambda *a, **k: False)


def _cancello_senza_llm(claim: str):
    return run_validation_gate(
        proposition=claim, verified_by=None, topic="t/porte", agent=None,
        validate="full", source=FONTE, grounding_llm=None)


def test_PORTA2_nessun_giudice_configurato_il_numero_inventato_viene_visto(
        monkeypatch) -> None:
    """La SECONDA porta: ramo diverso, stessa conseguenza.

    Il rilievo del pari che ha allargato questo banco: la cura tocca due rami,
    e prima **il banco ne misurava uno**. Curare una porta che non si misura è
    il modo di scoprire in produzione che la si era curata male.
    """
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    _nessun_giudice_configurato(monkeypatch)
    strati = _strati(_cancello_senza_llm(CLAIM_CON_NUMERO_INVENTATO))

    assert "L4-skipped" in strati, (
        f"questa cella non sta misurando la porta 2 (layer: {strati}): se il "
        f"giudice risulta disponibile il caso è finito nella porta 1 e il "
        f"verdetto qui sotto non dice niente di nuovo")
    assert any(s.startswith("L4.1") for s in strati), (
        f"senza NESSUN giudice configurato il numero assente dalla fonte entra "
        f"non guardato (layer: {strati}): la cura copre l'altro ramo e non "
        f"questo")


def test_CONTROLLO_PORTA2_i_numeri_della_fonte_NON_si_segnalano(
        monkeypatch) -> None:
    """Il controllo positivo della porta 2: non è «segnala sempre» nemmeno qui.

    Ogni porta coperta porta il suo, altrimenti una cura che accende i
    controlli su tutto passerebbe su una porta e cadrebbe sull'altra.
    """
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    _nessun_giudice_configurato(monkeypatch)
    strati = _strati(_cancello_senza_llm(CLAIM_SENZA_NUMERI_NUOVI))
    assert not any(s.startswith("L4.1") for s in strati), (
        f"sulla porta 2 un claim i cui numeri sono TUTTI nella fonte viene "
        f"segnalato lo stesso (layer: {strati})")


def test_CONTROLLO_col_giudice_il_numero_inventato_viene_visto(monkeypatch) -> None:
    """Il caso è reale: con il giudice presente `L4.1` lo prende.

    Se questa cella cade, il rosso qui sotto non dimostra un buco: dimostra che
    il claim è costruito male. Va letta PRIMA dell'altra.
    """
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    _con_giudice(monkeypatch)
    strati = _strati(_cancello(CLAIM_CON_NUMERO_INVENTATO))
    assert any(s.startswith("L4.1") for s in strati), (
        f"con il giudice presente il numero inventato NON viene segnalato "
        f"(layer: {strati}): il claim non serve a misurare il buco, "
        f"riformulalo invece di rilassare l'altra cella")


def test_senza_giudice_il_numero_inventato_passa_SENZA_essere_guardato(
        monkeypatch) -> None:
    """IL ROSSO. Stesso claim, stessa fonte: cambia solo che il giudice carica.

    Oggi la scrittura entra con `L4-skipped` e **nessun `L4.1`**: il controllo
    sui numeri non è stato saltato perché non poteva decidere — è stato saltato
    perché sta dietro a chi non poteva decidere.
    """
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    _senza_giudice(monkeypatch)
    strati = _strati(_cancello(CLAIM_CON_NUMERO_INVENTATO))

    assert "L4-skipped" in strati, (
        f"il giudice non risulta assente (layer: {strati}): il banco non sta "
        f"misurando la finestra del riscaldamento, e il verdetto qui sotto non "
        f"vale")
    assert any(s.startswith("L4.1") for s in strati), (
        f"IL BUCO: senza giudice il numero che la fonte non contiene entra "
        f"SENZA che nessuno lo guardi (layer: {strati}). `L4.1` e' lessicale e "
        f"in quel momento ha gia' in mano tutto cio' che gli serve — la fonte "
        f"e la proposizione. Sta dietro al moat solo per come e' scritto il "
        f"ramo, non perche' dipenda dal moat.")


def test_CONTROLLO_senza_FONTE_non_cambia_niente(monkeypatch) -> None:
    """🔴 IL CONFINE VERO DELLA CURA, e nel banco mancava (rilievo del pari).

    `L4.1` confronta i numeri del claim con quelli della **fonte**. Se la cura
    venisse scritta come «fai girare i controlli lessicali comunque» invece di
    «falli girare ogni volta che c'e' una FONTE», una scrittura senza fonte
    confronterebbe i suoi numeri con il nulla — e da lì **ogni numero risulta
    assente**.

    ⚠️ E non e' un timore teorico: dentro quella testa lessicale c'e' anche
    `L4.1-ambiguo`, che guarda **solo la proposizione** (`numeri_ambigui`) e non
    ha nessuna fonte da consultare. Su una scrittura senza fonte si
    accenderebbe da sola.

    ⇒ Sarebbe **l'unico modo in cui questa cura puo' fare un danno grosso**:
    quarantinare in massa le scritture ordinarie che oggi entrano
    legittimamente come non verificate. Questa cella lo rende impossibile, e
    deve passare **prima e dopo** la cura.
    """
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    _senza_giudice(monkeypatch)
    res = run_validation_gate(
        proposition=CLAIM_CON_NUMERO_INVENTATO, verified_by=None,
        topic="t/porte", agent=None, validate="full", source=None,
        grounding_llm=object())
    strati = _strati(res)
    assert not any(s.startswith("L4.1") for s in strati), (
        f"una scrittura SENZA FONTE viene segnalata dai controlli lessicali "
        f"(layer: {strati}): non c'e' nessuna fonte con cui confrontare i "
        f"numeri, quindi «assente dalla fonte» non vuol dire niente. Una cura "
        f"che accende quei controlli fuori dal ramo della fonte quarantina in "
        f"massa le scritture ordinarie.")


def test_CONTROLLO_senza_giudice_i_numeri_della_fonte_NON_si_segnalano(
        monkeypatch) -> None:
    """L'altra faccia: la cura non deve diventare «segnala sempre».

    Un claim i cui numeri stanno tutti nella fonte non deve produrre `L4.1`
    nemmeno a giudice spento. Senza questa cella, accendere il layer su ogni
    scrittura passerebbe per cura.
    """
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    _senza_giudice(monkeypatch)
    strati = _strati(_cancello(CLAIM_SENZA_NUMERI_NUOVI))
    assert not any(s.startswith("L4.1") for s in strati), (
        f"un claim i cui numeri sono TUTTI nella fonte viene segnalato lo "
        f"stesso (layer: {strati}): il controllo non distingue piu' le due "
        f"popolazioni, e un avviso che si accende sempre non informa nessuno")
