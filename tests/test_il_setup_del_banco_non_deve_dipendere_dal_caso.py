"""La trappola nel setup di `test_due_guardie_si_coprono_e_nessuno_lo_sa`.

⚠️ Il numero del ticket NON è ancora assegnato: «T71» era già stato proposto
per un altro difetto alle 14:09 dello stesso giorno. Quando il numero arriva
va scritto qui e nel nome del ramo.

IL FATTO, con l'output
----------------------
Lo stesso test cade su due PR diverse, su due gambe diverse, e nessuna delle
due tocca quel file::

    #16  run 34689589904  job 103542393169  py3.10  = 1 failed, 12869 passed =
    #27  run 34521726066  job 103020612074  py3.11  = 1 failed, 12853 passed =
    FAILED test_due_guardie_si_coprono_e_nessuno_lo_sa.py
           ::test_una_rettifica_esplicita_aggiorna_ANCHE_se_cita_l_id

La base che le due PR condividono (`32273665`) è **verde in due run interi**
(`34586040059`, `34472649016`), quindi non è ereditato; e nel test non c'è
nulla da cronometrare (`grep` vuoto su sleep/monotonic/cooldown), quindi la
cura di T38 — che tocca **un solo file**, `test_rerank_breaker.py` — non lo
copre.

LA CAUSA — 🔴 QUESTA DIAGNOSI È CADUTA. Si legge, non si applica.
------------------------------------------------------------------
La proposizione del secondo fatto è::

    "La coda ha 540 elementi (rettifica del fatto {fid})."

`{fid}` è l'id del PRIMO fatto: **cambia a ogni esecuzione** e la fonte non lo
contiene. Da qui si concludeva: il moat dà un punteggio più basso, il punteggio
si ferma vicino alla soglia, l'esito oscilla.

🔴 **Falsificata il 2026-09-12 alle 16:29, dai numeri di questo stesso file.**
L'id sposta davvero il punteggio (0,3677 su otto id), ma i punteggi stanno fra
**99,60 e 99,97** mentre il taglio che la scrittura applica è **40,0** — vedi
`test_la_soglia_DICHIARATA_dal_giudice_non_e_quella_APPLICATA_in_scrittura`,
in fondo. **Nessuno di quei fatti può essere fermato dal moat**, e la
dispersione fra id non spiega l'intermittenza.

⇒ **La causa NON è nota.** Il posto da cui ripartire è il campo
`quarantined_by`, che dichiara quale controllo ha fermato un fatto invece di
farlo dedurre; il candidato in cima è `L4.1`, il controllo sui numeri assenti
dalla fonte (un id esadecimale porta corse di cifre) — **ipotesi, non misurata.**

L'autore del banco aveva già incontrato questa trappola su un altro caso e
l'aveva risolta, e sta scritto nel suo docstring: un primo tentativo era stato
«QUARANTINATO a 0,16 perché la source non lo sostiene, e con il fatto fuori
dallo store "ritiri==0" non avrebbe misurato niente». La stessa trappola è
rimasta sul caso qui sopra.

PERCHÉ QUESTO RED NON «RIPRODUCE IL ROSSO»
------------------------------------------
Un rosso che arriva a volte non si riproduce «senza caso»: riprodurlo
vorrebbe dire aspettare che ricapiti. Quello che si può rendere deterministico
è la CAUSA, ed è ciò che misura il test qui sotto — un A/B a una variabile
sola, con input fissi, sullo stesso giudice:

    fonte di oggi        vs   fonte + la riga che nomina l'id
    stessa proposizione, stesso id FISSO (non generato)

Se la fonte arricchita non alza il punteggio, la diagnosi è sbagliata e questo
test lo dice: è la falsificazione, scritta prima della cura.

LA REGOLA DEL MARGINE (decisa in revisione il 2026-09-12, quattro righe)
------------------------------------------------------------------------
1. ⚠️ **CORRETTA alle 16:35, e la versione originale ha fatto danno.** Diceva:
   «la soglia si legge da ``try_local_score`` / ``get_local_threshold()``, mai
   cablata». Applicarla alla lettera porta a confrontare i punteggi con la
   ``config_threshold`` **dichiarata** (99,64) — che il cancello **scarta**
   come artefatto di calibrazione, applicando 40,0. La regola giusta è:
   **la soglia si chiede a chi DECIDE**, cioè
   ``resolve_write_threshold_for(backend_used)``, mai al giudice che la
   riporta e mai a una costante;
2. il margine **si misura e si stampa** a ogni esecuzione;
3. l'asserzione dell'osservatore è ``stato != "quarantined"`` — un fatto, non
   una scelta — più la stampa del margine;
4. un ``MARGINE_MINIMO`` nasce **dopo**, dal primo dato stampato, e quando
   nasce porta accanto il comando che l'ha prodotto.

⇒ IL PRIMO DATO C'È, ed è questo (run 34693325571, job 103552397304 macos
py3.12 e 103552397181 ubuntu py3.10, identici cifra per cifra)::

    punteggio 99.95   config_threshold DICHIARATA 99.64130401611328

🔴 **Quello che qui era scritto come «margine 0,31 punti» NON È UN MARGINE.**
Era la distanza dalla soglia dichiarata, che la scrittura non applica: contro
il taglio in vigore (40,0) il margine vero di quel caso è di **quasi sessanta
punti**. Chiunque volesse fissare un ``MARGINE_MINIMO`` partendo da 0,31
sceglierebbe un numero costruito sul confronto sbagliato.
"""
from __future__ import annotations

import pytest

from verimem.local_grounding import try_local_score

#: L'id è FISSO e non generato: se l'input varia, varia il punteggio, e il
#: banco erediterebbe il difetto che sta misurando.
_ID_FISSO = "7c1a9e02"

_SORGENTE_DI_OGGI = ("verbale: la coda aveva 500 elementi\n"
                     "rettifica: la coda aveva 540 elementi\n")

_PROPOSIZIONE = f"La coda ha 540 elementi (rettifica del fatto {_ID_FISSO})."

#: La cura proposta: la fonte si costruisce DOPO il primo fatto, così contiene
#: l'id che la proposizione cita.
_SORGENTE_CURATA = _SORGENTE_DI_OGGI + f"rettifica del fatto {_ID_FISSO}\n"


def _punteggio(sorgente: str, proposizione: str) -> tuple[float, float | None]:
    """Il punteggio del giudice, o salta il test dichiarando perché.

    ``try_local_score`` rende ``None`` quando il modello locale non c'è. Un
    ``None`` letto come «nessun problema» sarebbe il difetto che questo file
    esiste per impedire: qui diventa uno SKIP che dice cosa manca, non un
    verde.
    """
    r = try_local_score(sorgente, proposizione)
    if r is None:
        pytest.skip(
            "CONTROLLO POSITIVO SPENTO: il giudice locale non è disponibile "
            "in questo ambiente, quindi il punteggio non si può misurare. "
            "Questo test NON ha verificato niente — non leggerlo come verde."
        )
    return float(r[0]), r[1]


def test_la_fonte_che_nomina_l_id_NON_alza_il_punteggio() -> None:
    """La diagnosi di partenza, FALSIFICATA da questo stesso banco.

    Scritto prima come ``ricco > magro``: se la fonte che nomina l'id non
    avesse alzato il punteggio, la diagnosi sarebbe stata sbagliata. **Non
    l'ha alzato.** Misurato il 2026-09-12 su due piattaforme, cifra per
    cifra identico::

        run 34693325571  job 103552397304  macos-latest / py3.12
        run 34693325571  job 103552397181  ubuntu-latest / py3.10
        (99.95 -> 99.71, soglia 99.64130401611328)

    Tre cose che quei numeri dicono e che non sapevamo:

    * l'id nella proposizione **non abbassa** niente: 99,95 è quasi il massimo;
    * la cura proposta **abbassava** il punteggio di 0,24, cioè avvicinava il
      setup alla soglia invece di allontanarlo — sarebbe caduto più spesso;
    * 🔴 **e una terza che qui era scritta ALL'INCONTRARIO**: diceva «la soglia
      che conta è 99,64, non i 40,0 di ``LOCAL_CE_MOAT_THRESHOLD``». È il
      rovescio del vero — il cancello scarta 99,64 e applica **40,0**. La riga
      resta a memoria di come una frase sbagliata sopravviva in un file che per
      il resto misura bene.

    Il test resta, con l'asserzione girata: registra il fatto misurato, così
    se un giorno la relazione si inverte qualcuno se ne accorge.
    """
    magro, soglia = _punteggio(_SORGENTE_DI_OGGI, _PROPOSIZIONE)
    ricco, _ = _punteggio(_SORGENTE_CURATA, _PROPOSIZIONE)

    assert ricco < magro, (
        f"la fonte che nomina l'id ADESSO alza il punteggio "
        f"({magro:.2f} -> {ricco:.2f}, soglia {soglia}): la misura del "
        f"2026-09-12 diceva il contrario (99.95 -> 99.71). Qualcosa nel "
        f"giudice è cambiato, e la cura scartata allora va riesaminata."
    )


#: Otto id della stessa forma di quelli veri (8 hex). Fissi nel file: se li
#: generassi, il banco erediterebbe il difetto che sta misurando.
_ID_DI_PROVA = ("7c1a9e02", "00000000", "ffffffff", "a1b2c3d4",
                "deadbeef", "12345678", "9f8e7d6c", "0a1b2c3d")


def test_id_diversi_SPOSTANO_il_punteggio_del_giudice() -> None:
    """L'id citato muove il punteggio. Quanto, e — importante — di che cosa NO.

    (Si chiamava ``…non_devono_spostare_il_punteggio_piu_del_margine``: il nome
    vecchio è nei messaggi del 2026-09-12 fino alle 16:24.)

    ✅ MISURATO, run 34695954775, job 103559354485 macos py3.12 e 103559354588
    ubuntu py3.11, identici a quattro decimali — stessa fonte, stessa
    proposizione, cambia solo la stringa dell'id::

        deadbeef 99.6069   12345678 99.8257   00000000 99.8477
        9f8e7d6c 99.9418   7c1a9e02 99.9477   a1b2c3d4 99.9548
        ffffffff 99.9559   0a1b2c3d 99.9746
        config_threshold dichiarata 99.6413 · dispersione 0.3677

    L'id sposta il punteggio di **0,3677 punti**, e lo fa in modo
    deterministico: due piattaforme, quattro decimali uguali.

    🔴 QUELLO CHE QUESTA MISURA **NON** DIMOSTRA, e per un'ora ho creduto di sì.
    `deadbeef` sta sotto la `config_threshold` che `try_local_score` dichiara
    (99,6413), e da lì avevo concluso «un id su otto viene quarantinato».
    **Falso**: quel numero non è il taglio in vigore. Il cancello di scrittura
    lo scarta di proposito — «a moat admission cut above ~90/100 is a
    calibration artifact, never a real operating point: ignore it» — e applica
    ``LOCAL_CE_MOAT_THRESHOLD`` = **40,0**. Tutti e otto lo superano di quasi
    sessanta punti: **nessuno di loro può essere fermato dal moat**, `deadbeef`
    compreso. Il presidio qui sotto esiste perché nessun altro rifaccia questa
    strada.

    Cade con lo stesso colpo anche l'ipotesi che `deadbeef` fosse punito perché
    «si legge come parole»: era già debole (n=1, e `ffffffff` è tutto lettere e
    sta in cima), ora è senza quadro.

    ⇒ **La dispersione è vera, la conseguenza no.** Questa cella registra la
    prima e tace sulla seconda. La causa dell'intermittenza di
    `test_due_guardie_si_coprono_e_nessuno_lo_sa.py` **non è nota**, e il posto
    da cui ripartire è il campo `quarantined_by`, che dichiara da solo quale
    controllo ha fermato un fatto — invece di dedurlo.
    """
    misure: dict[str, float] = {}
    soglia: float | None = None
    for ident in _ID_DI_PROVA:
        prop = f"La coda ha 540 elementi (rettifica del fatto {ident})."
        punteggio, s = _punteggio(_SORGENTE_DI_OGGI, prop)
        misure[ident] = punteggio
        soglia = s if s is not None else soglia

    minimo, massimo = min(misure.values()), max(misure.values())
    dispersione = massimo - minimo

    for ident, punteggio in sorted(misure.items(), key=lambda kv: kv[1]):
        print(f"  {ident}  {punteggio:8.4f}")
    print(f"  dispersione {dispersione:.4f} · config_threshold dichiarata "
          f"{soglia if soglia is None else format(soglia, '.4f')}")

    #: Metà della dispersione misurata. Non è una soglia scelta: è il modo di
    #: dire «la relazione non si è ribaltata» senza inchiodare quattro decimali
    #: a un fine-tune che può cambiare.
    assert dispersione > 0.18, (
        f"l'id non sposta più il punteggio del giudice: dispersione "
        f"{dispersione:.4f} contro gli 0.3677 misurati il 2026-09-12 su otto "
        f"id della stessa forma. Se il giudice ha smesso di leggere l'id come "
        f"contenuto, va riletto tutto ciò che questo file dichiara."
    )


def test_il_margine_si_misura_dal_taglio_che_AMMETTE() -> None:
    """Quanto dista dall'ammissione il setup, misurato sulla scala giusta.

    ⚠️ **QUESTA CELLA CONFRONTAVA CON 99,641 fino al 2026-09-12.** Il numero
    veniva da ``try_local_score``, che lo *dichiara*, e non dal cancello, che
    lo *scarta*. L'asserzione passava lo stesso — il caso curato vale 99,71 —
    ma passava per caso: misurava contro un confine che il prodotto non usa, e
    sarebbe diventata rossa su un punteggio perfettamente ammissibile.

    ⇒ Il margine si misura da ``resolve_write_threshold_for("local")``, cioè
    dal taglio **che decide l'ammissione**. Non da una costante scelta qui e
    non dal numero che il giudice riporta insieme al punteggio.

    Non fissa un margine minimo: continua a non esistere una misura che lo
    sostenga, e inventarlo qui sarebbe un numero senza fonte. Il test pretende
    che il setup **sia ammissibile** — la condizione perché il controllo
    positivo del banco possa accendersi — e stampa i due margini sulla scala
    giusta perché chi vorrà fissare il minimo parta da un dato vero.

    📌 La causa per cui quel fatto viene comunque quarantinato **non è qui**:
    con 99,7 contro un taglio di 40,0 non può essere l'ammissione. Sta a T75,
    e il banco delle due guardie adesso stampa ``quarantined_by`` quando cade.
    """
    from verimem.grounding_gate import resolve_write_threshold_for

    magro, dichiarata = _punteggio(_SORGENTE_DI_OGGI, _PROPOSIZIONE)
    ricco, _ = _punteggio(_SORGENTE_CURATA, _PROPOSIZIONE)
    ammette = resolve_write_threshold_for("local")

    print(f"\n  fonte di oggi   {magro:7.4f}   margine {magro - ammette:+8.4f}")
    print(f"  fonte curata    {ricco:7.4f}   margine {ricco - ammette:+8.4f}")
    print(f"  taglio che AMMETTE      {ammette:7.4f}")
    print(f"  soglia solo DICHIARATA  "
          f"{dichiarata if dichiarata is None else format(dichiarata, '7.4f')}"
          f"   <- non decide")

    assert ricco >= ammette, (
        f"il setup curato ({ricco:.4f}) sta sotto il taglio che ammette "
        f"({ammette:.4f}): il controllo positivo del banco non potrebbe "
        f"accendersi mai, e la sua asserzione misurerebbe il silenzio."
    )
    assert magro >= ammette, (
        f"il setup di oggi ({magro:.4f}) sta sotto il taglio che ammette "
        f"({ammette:.4f}). Il 2026-09-12 ci stava sopra di ~60 punti: se ora "
        f"non ci sta, l'ammissione è cambiata e la causa della quarantena "
        f"intermittente va ricercata QUI prima che a T75."
    )


def test_la_soglia_DICHIARATA_dal_giudice_non_e_quella_APPLICATA_in_scrittura() -> None:
    """Il presidio che nasce da un mio errore, perché non lo rifaccia nessuno.

    `try_local_score` rende ``(punteggio, config_threshold)``. Quel secondo
    numero **sembra** il taglio di ammissione, ed è quello che il modello
    fine-tuned porta nel suo `gate_config.json`: il 2026-09-12 valeva
    ``99.64130401611328``.

    **Non è il taglio in vigore.** `resolve_write_threshold_for("local")` lo
    scarta di proposito quando supera 90 — il commento nel cancello lo chiama
    «a calibration artifact, never a real operating point» — e rende
    ``LOCAL_CE_MOAT_THRESHOLD``, cioè **40,0**, che è il valore usato al punto
    di decisione della scrittura.

    Fra i due numeri ci sono quasi sessanta punti. Chi confronta un punteggio
    con quello dichiarato invece che con quello applicato conclude che fatti
    ammessi sono respinti — è successo, ed è costato due annunci sbagliati in
    un'ora.

    ⚠️ Questa cella NON pretende che il modello dichiari 99,64: quel numero è
    del fine-tune e può cambiare. Pretende che, **finché il dichiarato è un
    artefatto (>90), l'applicato sia un altro numero** e che i due non vengano
    confusi.
    """
    from verimem.grounding_gate import (
        LOCAL_CE_MOAT_THRESHOLD,
        resolve_write_threshold_for,
    )

    r = try_local_score(_SORGENTE_DI_OGGI, _PROPOSIZIONE)
    if r is None or r[1] is None:
        pytest.skip(
            "il giudice locale non dichiara una config_threshold in questo "
            "ambiente: non c'è il confronto da fare, e questo test NON ha "
            "verificato niente."
        )

    dichiarata = float(r[1])
    applicata = resolve_write_threshold_for("local")
    print(f"\n  dichiarata da try_local_score  {dichiarata:.4f}")
    print(f"  applicata in scrittura         {applicata:.4f}")
    print(f"  punteggio di questo caso       {r[0]:.4f}")

    if dichiarata <= 90.0:
        assert applicata == dichiarata, (
            f"la soglia dichiarata ({dichiarata:.4f}) è sanamente calibrata "
            f"(<=90) e allora deve essere ANCHE quella applicata, mentre in "
            f"scrittura vale {applicata:.4f}."
        )
        return

    assert applicata != dichiarata, (
        f"il cancello applica {applicata:.4f}, cioè la soglia dichiarata dal "
        f"modello ({dichiarata:.4f}), che è sopra 90 e che il codice stesso "
        f"chiama un artefatto di calibrazione. Se la decisione è cambiata, il "
        f"commento in grounding_gate va riscritto lì, non aggirato qui."
    )
    assert applicata == LOCAL_CE_MOAT_THRESHOLD, (
        f"con una soglia dichiarata inutilizzabile ({dichiarata:.4f} > 90) il "
        f"cancello dovrebbe ripiegare sul taglio validato "
        f"{LOCAL_CE_MOAT_THRESHOLD:.1f} e invece applica {applicata:.4f}."
    )
