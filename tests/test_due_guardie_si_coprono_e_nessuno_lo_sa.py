"""Il caso protetto da DUE guardie insieme, e da nessuna delle due da sola.

2026-08-22. Censendo il loop di `run_validation_gate` una guardia alla volta —
spegnerla, guardare se il numero si muove — tre guardie su cinque risultavano
INERTI. Il numero e' giusto e la conclusione che invitava a trarre e' falsa::

    references_fact ON  + `if ea or eb` ON    ritirati=0   protetto
    references_fact OFF + `if ea or eb` ON    ritirati=0   l'ALTRA copre
    `if ea or eb` OFF   + references_fact ON  ritirati=0   l'ALTRA copre
    ENTRAMBE OFF                              ritirati=1   il fatto vero si perde

Sono mutuamente ridondanti: provata da sola ognuna sembra morta, perche' l'altra
raccoglie il caso. Un censimento a variabile singola non puo' vederlo, e chi lo
leggesse come «se ne possono togliere tre» produrrebbe esattamente il difetto che
quelle guardie esistono per impedire — un fatto vero cancellato in silenzio.

PERCHE' QUESTO PRESIDIO NON NOMINA NESSUNA GUARDIA. Presidiare «la guardia X e'
accesa» lega il test a un'implementazione: oggi ne bastano due, domani una terza
puo' sostituirle entrambe e il test direbbe rosso su un prodotto sano. E il verso
opposto e' peggio — un presidio scritto sul NOME di una funzione interna muore
quando qualcun altro cura lo stesso difetto in un altro modo (misurato oggi: un
mio file di test e' caduto con `ImportError` perche' la cura era entrata in una
forma diversa dalla mia). Qui si inchioda il COMPORTAMENTO, dalla porta: chiunque
lo garantisca, deve continuare a garantirlo.

═══════════════════════════════════════════════════════════════════════════════
2026-09-07 — IL CASO ERA SBAGLIATO, E L'INVARIANTE NO.

Il presidio nasceva con UN solo caso: «La coda ha 540 elementi (rettifica del
fatto {fid})» contro «La coda ha 500 elementi», stessa fonte, e pretendeva
ritiri==0. Quel caso e' un clash NUMERICO deterministico, ed e' precisamente
quello che `anti_confab_gate.py:749` esclude per iscritto dal 2026-07-25, dopo
una revisione avversariale convergente 2/2::

    "CORREZIONE del fatto X: il valore e' 200" against a stored "il valore e'
    100" names X, so the guard kept the stale 100 alive beside its own correction

Sono la STESSA forma di frase. Il presidio chiedeva al prodotto di tenere vivo
un valore che l'utente aveva appena rettificato **dicendo che lo stava
rettificando** — cioe' il contrario di cio' che quell'utente paga.

Chi ha scritto il presidio non ha letto quel commento; chi ha scritto quel
commento non ha lasciato un test. Il rosso e' arrivato con `9827aed4`, che ha
ristretto `_entita_diverse` per un'altra ragione e ha fatto cadere l'unica
guardia rimasta su questa rotta: A/B del 06/09 — con i 4 commit 1 failed, senza
il solo `9827aed4` 2 passed. **Quel commit ha curato un difetto vero senza
saperlo**, e ha spento un presidio scritto sul difetto.

MISURATO OGGI, `scratchpad/probe_citazione_senza_clash.py`, build 0b70c071::

    A. rettifica SENZA citazione            model_claim  ritiri=1  same-source evolution
    B. rettifica CON citazione              model_claim  ritiri=1  same-source evolution
    C. cita l'id e CONCORDA (500 = 500)     model_claim  ritiri=0  —

Il gate ritira dove c'e' un clash concreto e sta fermo dove non c'e'. Il caso C
misura davvero: il suo controllo positivo e' acceso — il fatto e' ENTRATO con
grounding 99,93. Un primo tentativo («Il fatto {fid} e' stato registrato durante
il collaudo») era stato QUARANTINATO a 0,16 perche' la source non lo sostiene, e
con il fatto fuori dallo store «ritiri==0» non avrebbe misurato niente.

FALSIFICATO NELLO STESSO GIRO — il presidio nuovo e' ACCESO. Rimettendo
`references_fact` a guardia di quel ciclo, cioe' la cosa che il commento
esclude, il secondo test diventa rosso e gli altri due restano verdi::

    guardia rimessa   1 failed, 2 passed   assert 0 == 1
    come in main      3 passed

⚠️ IL PRIMO TENTATIVO DI QUELL'A/B HA MISURATO UN `NameError`, non la guardia:
in `anti_confab_gate.py` l'import di `references_fact` e' locale a un'altra
funzione (riga 2232), non globale. Vale la pena tenerne il risultato, perche'
dice una cosa su questo file: con la rotta ROTTA il primo test passava lo
stesso, e a diventare rosso e' stato il CONTROLLO in fondo. Il primo presidio,
da solo, non distingue «non ha ritirato» da «non ha potuto»: e' il controllo che
gli da' significato, ed e' per questo che i tre test vivono insieme.

Da qui i DUE presidi qui sotto, uno per meta' della decisione: prima ne esisteva
uno solo, e stava sulla meta' sbagliata.
═══════════════════════════════════════════════════════════════════════════════

⚠️ REGIME: rotta lessicale `same-source`, ENGRAM_SUPERSEDE_SAME_SOURCE=enforce.
Sotto pytest l'embedder e' uno stub su SHA-256 (`conftest`), quindi la rotta
semantica non riconosce i due fatti come contraddittori e nessuna supersessione
avverrebbe: un presidio scritto su quella rotta passerebbe anche a difetto
presente. Il CONTROLLO POSITIVO qui sotto e' cio' che lo dimostra ogni volta.
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from verimem.client import Memory

FONTE = ["source-doc:coda:1"]
SORGENTE = ("verbale: la coda aveva 500 elementi\n"
            "rettifica: la coda aveva 540 elementi\n")


def _ritiri(seconda: str) -> tuple[int, str, str]:
    """Scrive due fatti sulla stessa source e conta i ritiri.

    `seconda` puo' contenere `{fid}`: viene sostituito con l'id del PRIMO fatto,
    che e' il modo in cui un chiamante cita esplicitamente cio' che sta
    rettificando.

    Torna anche lo STATUS con cui il secondo fatto e' entrato: senza, un
    «ritiri == 0» ottenuto perche' il moat ha quarantinato il secondo fatto
    sarebbe indistinguibile da uno ottenuto perche' il prodotto ha deciso di non
    ritirare. E' il controllo positivo, e va guardato in ogni test che pretende 0.

    L'INTERMITTENZA: DUE CURE PROPOSTE, DUE RITIRATE (2026-09-12)
    --------------------------------------------------------------
    La causa ha un nome dalle 17:40 (`L4.1`, sotto), ma tutte e tre le cure
    proposte prima di saperlo sono cadute: questo blocco esiste per impedire
    che vengano riproposte.

    ① ARRICCHIRE LA FONTE con l'id che la proposizione cita. Ritirata: misurato
       su due piattaforme, la fonte arricchita ABBASSA il punteggio (99,95 ->
       99,71) e avvicinerebbe il setup al confine invece di allontanarlo.

    ② FISSARE L'ID citato, per togliere la variabilita'. Ritirata, e per una
       ragione che vale a prescindere da tutto il resto:
       `supersession_policy.references_fact(new_text, old_id)` cerca l'id
       **dello store** dentro il testo nuovo. Con un id inventato la ricerca
       non trova nulla, la guardia non si arma e i due presidi qui sotto
       resterebbero VERDI misurando un caso che non esiste piu' — il peggiore
       dei quattro stati di un test, quello che mente.

    ③ RIPESCARE quando il punteggio del giudice sta sotto la soglia. Scritta e
       ritirata nella stessa ora, e la ragione e' la piu' istruttiva:
       **filtrava contro un numero che il prodotto butta.**

    IL NUMERO CHE IL CODICE NOMINA NON E' QUELLO CHE USA
    -----------------------------------------------------
    `try_local_score` rende ``(punteggio, config_threshold)`` e il secondo vale
    **99,64**. Ma `grounding_gate.resolve_write_threshold_for("local")` lo
    SCARTA di proposito — «a moat admission cut above ~90/100 is a calibration
    artifact, never a real operating point: ignore it» — e rende
    ``LOCAL_CE_MOAT_THRESHOLD`` = **40,0**, che e' il valore usato al punto di
    decisione (`anti_confab_gate.py`, `_threshold_of_record`).

    ⇒ Gli otto id misurati stanno fra **99,6069 e 99,9746**: superano il taglio
    in vigore di quasi sessanta punti. **Nessuno di loro puo' essere fermato
    dal moat**, e la dispersione fra id — reale, 0,3677 — non spiega niente di
    questa intermittenza::

        deadbeef 99.6069   12345678 99.8257   00000000 99.8477
        9f8e7d6c 99.9418   7c1a9e02 99.9477   a1b2c3d4 99.9548
        ffffffff 99.9559   0a1b2c3d 99.9746        (run 34695954775,
        job 103559354485 macos py3.12 · 103559354588 ubuntu py3.11)

    LA CAUSA ERA GIA' SCRITTA NEL PRODOTTO — e non nel punteggio
    -------------------------------------------------------------
    `client.py` registra un caso riprodotto della STESSA forma: il moat
    **APPROVA a 99.89** e a fermare la scrittura e' **`L4.1`**, il controllo
    lessicale sui valori che la fonte non contiene. Le due cose convivono per
    disegno.

    ⇒ **Un grounding alto non dice che la scrittura sia passata.** Il
    ragionamento «99,6 contro un taglio di 40, quindi non puo' essere la
    soglia, quindi la causa e' ignota» e' sbagliato nell'ultimo passo, ed e'
    quello che ha fatto perdere tre ore a piu' di uno.

    ⚠️ E `quarantined_by` **NON basta**: in quel caso registrato scriveva il
    generico `'gate'` mentre a decidere era `L4.1` — tanto che il giorno dopo
    una lettura in buona fede concluse «non e' L4». **Un'etichetta generica si
    legge come un'assenza e fa dedurre il contrario del vero.** Chi decide sta
    nei WARNING della ricevuta, che portano il `layer`.

    🔬 Resta APERTO, e va falsificato invece che creduto: **come L4.1 estragga
    i valori.** Nel caso registrato erano «6 mb, 176», cioe' numeri con
    un'unita' accanto; un id esadecimale nudo potrebbe non entrarci affatto.
    Se ci entra, gli id con CIFRE sono i pericolosi e `deadbeef` il piu'
    sicuro — l'opposto di quel che prediceva il punteggio. La prova e' una
    riga: stampare i warning per ciascuno degli otto id.

    ⇒ **E questo banco adesso quel campo LO LEGGE E LO STAMPA quando cade.**
    Il campo c'era a tutte e tre le cadute e veniva buttato: la ricevuta di
    ``add()`` lo porta, e la colonna nel DB pure. Tre run spesi per un rosso
    che aveva la risposta dentro.

    ⚠️ IL PRESIDIO RESTA ACCESO — decisione del 2026-09-12 alle 17:00, contro
    due proposte, una delle quali mia. Erano ``xfail(strict=False)`` e uno
    SKIP, per smettere di far cadere PR estranee. **Sono le due forme dello
    stesso silenzio**, e la regola e' che un test o misura qualcosa e resta
    acceso, o si TOGLIE con la ragione scritta e il ticket che dice cosa lo
    sostituisce. Questo misura — sette esecuzioni su otto arriva in fondo e
    copre un caso che nessun'altra misura vede — quindi resta.

    🔑 Quello che cambia non e' il verdetto: e' che adesso **ogni caduta paga
    il proprio costo**, perche' consegna il nome dello schermo che ha fermato
    il fatto invece di lasciare aperta la domanda per la quarta volta.
    """
    db = Path(tempfile.mkdtemp()) / "coppia.db"
    mem = Memory(str(db))
    prima = mem.add("La coda ha 500 elementi.", topic="t/coppia",
                    verified_by=FONTE, source=SORGENTE, validate="full")
    fid = prima.get("id") or prima.get("fact_id") or ""
    ricevuta = mem.add(seconda.format(fid=fid), topic="t/coppia",
                       verified_by=FONTE, source=SORGENTE, validate="full")
    sid = ricevuta.get("id") or ricevuta.get("fact_id") or ""
    vivo = mem.semantic.get(sid) if sid else None
    stato = str(getattr(vivo, "status", None)) if vivo is not None else "ASSENTE"
    conn = sqlite3.connect(f"file:{mem.semantic.db_path}?mode=ro", uri=True)
    try:
        riga = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL").fetchone()
        ritiri = int(riga[0]) if riga else 0
        nel_db = ""
        if sid:
            q = conn.execute(
                "SELECT quarantined_by FROM facts WHERE id = ?", (sid,)).fetchone()
            nel_db = (q[0] if q and q[0] else "") or ""
    finally:
        conn.close()

    # ⚠️ `quarantined_by` NON BASTA, ed e' il campo che ha gia' ingannato
    # qualcuno: nel caso riprodotto in `client.py` il moat APPROVA a 99.89, a
    # fermare e' `L4.1`, e la colonna scrive il generico `'gate'` — tanto che
    # il giorno dopo una lettura in buona fede concluse «non e' L4». Chi decide
    # sta nei WARNING della stessa ricevuta, che portano il `layer`. Si
    # stampano tutti e tre: se l'etichetta generica e il layer non coincidono,
    # la differenza e' essa stessa il reperto.
    strati = [str(w.get("layer", "?"))
              for w in (ricevuta.get("warnings") or []) if isinstance(w, dict)]
    assert stato in ("model_claim", "user_manual"), (
        f"CONTROLLO POSITIVO SPENTO: il secondo fatto e' entrato come "
        f"{stato!r}, quindi non c'era niente che potesse ritirare il primo.\n"
        f"    layer dei warning         = {strati!r}   <- CHI DECIDE\n"
        f"    quarantined_by (ricevuta) = "
        f"{(ricevuta.get('quarantined_by') or '')!r}   <- etichetta generica\n"
        f"    quarantined_by (nel DB)   = {nel_db!r}\n"
        f"    grounding_score           = "
        f"{ricevuta.get('grounding_score')!r}   <- puo' essere ALTO e la "
        f"scrittura fermata lo stesso\n"
        f"    ^^^ LEGGI IL LAYER, NON L'ETICHETTA. Al 2026-09-12 questa caduta "
        f"e' arrivata TRE volte su PR che non toccano questo file, e per tre "
        f"ore la causa e' stata attribuita al punteggio del giudice: a torto, "
        f"perche' il taglio ammette a 40,0 e il punteggio vale ~99,6. **Un "
        f"grounding alto NON dice che la scrittura sia passata**: il moat puo' "
        f"approvare e un controllo lessicale fermare, per disegno.\n"
        f"    Riporta le righe qui sopra: sono cio' che chiude il ticket.\n"
        f"    NON ammorbidire questa asserzione e NON silenziare la cella: un "
        f"test o misura e resta acceso, o si toglie con la ragione.")

    return ritiri, fid, stato


def test_un_fatto_che_cita_l_id_di_un_altro_SENZA_contraddirlo_non_lo_ritira():
    """L'invariante vera: citare non e' contraddire.

    Diventa rossa solo se cadono TUTTE le guardie che coprono questo caso — che
    e' esattamente l'evento che nessun'altra misura vede.
    """
    ritiri, fid, stato = _ritiri(
        "Nel verbale la coda aveva 500 elementi, come nel fatto {fid}.")
    assert stato in ("model_claim", "user_manual"), (
        f"CONTROLLO POSITIVO SPENTO: il secondo fatto e' entrato come {stato!r}, "
        f"quindi non c'era niente che potesse ritirare il primo e lo 0 qui sotto "
        f"non misurerebbe il prodotto. Riformula la proposizione in modo che la "
        f"source la sostenga, invece di rilassare l'assert.")
    assert ritiri == 0, (
        f"un fatto che cita {fid[:8]} SENZA contraddirne il valore lo ha "
        f"comunque ritirato: sono cadute tutte le guardie che coprivano questo "
        f"caso, non una. Provale a COPPIE, non una alla volta: da sola ognuna "
        f"sembra inerte.")


def test_una_rettifica_esplicita_aggiorna_ANCHE_se_cita_l_id():
    """L'altra meta' della decisione, che fino al 07/09 non presidiava nessuno.

    `anti_confab_gate.py:749` esclude deliberatamente `references_fact` dalla
    rotta deterministica: li' il conflitto e' stato TROVATO da un rilevatore
    concreto (numerico, anno, versione, data, negazione), e citare un id non lo
    scusa — altrimenti il valore vecchio resterebbe vivo accanto alla sua stessa
    correzione. Era una decisione scritta solo in un commento; un commento non
    diventa rosso quando qualcuno lo contraddice.
    """
    ritiri, fid, stato = _ritiri(
        "La coda ha 540 elementi (rettifica del fatto {fid}).")
    assert stato in ("model_claim", "user_manual"), (
        f"CONTROLLO POSITIVO SPENTO: la rettifica e' entrata come {stato!r}.")
    assert ritiri == 1, (
        f"una rettifica esplicita che cita {fid[:8]} non aggiorna piu' il valore "
        f"precedente: il 500 resta vivo accanto al 540 che lo corregge. Se e' "
        f"stato voluto, la decisione del 2026-07-25 in anti_confab_gate.py:749 "
        f"va riscritta li', non aggirata qui.")


def test_CONTROLLO_senza_la_citazione_il_ritiro_avviene_ancora():
    """Impedisce alle invarianti di essere soddisfatte dal silenzio.

    Se il prodotto smettesse di superseder in generale — o se il banco finisse
    su una rotta che sotto pytest non vede nulla — il primo test passerebbe per
    la ragione sbagliata. Questo lo rende impossibile: senza la citazione quel
    ritiro DEVE avvenire.
    """
    ritiri, _, _ = _ritiri("La coda ha 540 elementi.")
    assert ritiri == 1, (
        "la rettifica di uno stesso valore non aggiorna piu' il precedente: il "
        "presidio qui accanto non sta piu' misurando niente")
