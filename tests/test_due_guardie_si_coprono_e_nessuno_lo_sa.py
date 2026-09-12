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
    """
    db = Path(tempfile.mkdtemp()) / "coppia.db"
    mem = Memory(str(db))
    prima = mem.add("La coda ha 500 elementi.", topic="t/coppia",
                    verified_by=FONTE, source=SORGENTE, validate="full")
    fid = prima.get("id") or prima.get("fact_id") or ""
    #: ⚠️ LA FONTE RESTA QUELLA ORIGINALE, E NON PER DIMENTICANZA.
    #:
    #: Questi due presidi sono deterministici solo se la fonte contiene
    #: anche l'id che la proposizione cita. La cura c'era su questo ramo ed
    #: e' stata CEDUTA alla PR che porta anche il banco che la spiega: due
    #: rami non possono portare la stessa cura sullo stesso file, e chi
    #: porta la spiegazione deve portare la cura.
    #:
    #: ⇒ QUESTO RAMO VA MERGIATO DOPO QUELLO: da solo lascia i due presidi
    #: qui sopra intermittenti, com'erano prima.
    ricevuta = mem.add(seconda.format(fid=fid), topic="t/coppia",
                       verified_by=FONTE, source=SORGENTE,
                       validate="full")
    sid = ricevuta.get("id") or ricevuta.get("fact_id") or ""
    vivo = mem.semantic.get(sid) if sid else None
    stato = str(getattr(vivo, "status", None)) if vivo is not None else "ASSENTE"
    conn = sqlite3.connect(f"file:{mem.semantic.db_path}?mode=ro", uri=True)
    try:
        riga = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL").fetchone()
        return (int(riga[0]) if riga else 0), fid, stato
    finally:
        conn.close()


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


# ═══════════════════════════════════════════════════════════════════════════
# T69 — L'OSSERVATORE CHE LA CURA DEL 2026-09-12 AVEVA TOLTO
#
# Mettendo l'id nella fonte, i due presidi qui sopra sono tornati
# deterministici — e insieme al rumore se n'e' andato l'unico posto da cui si
# vedeva un comportamento del PRODOTTO: lo stesso ingresso, quattordici gambe
# verdi e una rossa. Quel dato non era il difetto del banco: era il sintomo di
# un giudizio che si ferma vicino al taglio, e la cura l'ha reso invisibile.
#
# E' la stessa forma gia' pagata su T49 e scritta trenta righe piu' su in
# questo file: «curare una promessa puo' disarmare il presidio che la
# sorvegliava, e la cura deve portarsi dietro il suo complemento». Stavolta il
# presidio l'ho disarmato io, e il complemento e' questo caso.
#
# COSA OSSERVA, e perche' puo' fallire davvero: scrive la proposizione COME
# ERA — con l'id che la fonte non contiene — e guarda QUANTO il giudizio disti
# dalla soglia. Non pretende un verdetto: pretende un MARGINE. Un ingresso
# legittimo che passa per due punti non e' un ingresso promosso, e' un
# ingresso che la prossima esecuzione boccia.
# ═══════════════════════════════════════════════════════════════════════════

#: Il taglio del moat, LETTO DAL PRODOTTO e non copiato qui. Era `40.0`
#: scritto a mano: una soglia duplicata e' la classe ① delle nostre cinque —
#: una copia invece della superficie unica — e l'avevo commessa dentro un
#: banco che parla di presidi disarmati. Se il nome sparisce, questo file
#: muore con un ImportError, che e' il segnale giusto: la soglia si e' mossa.
from verimem.grounding_gate import LOCAL_CE_MOAT_THRESHOLD  # noqa: E402


def test_OSSERVATORE_registra_il_margine_ma_NON_lo_giudica_ancora():
    """Il difetto del PRODOTTO che la cura del banco aveva smesso di mostrare.

    ⚠️ IL NOME DICE COSA FA, e cioe' MENO di quanto T69 chiedeva. Vale la pena
    spiegare perche', invece di lasciare un nome che promette un presidio.

    T69 chiedeva «un osservatore che possa fallire» su un difetto vero: un
    ingresso legittimo che passa per pochi punti oggi e viene bocciato domani
    (misurato in CI il 2026-09-12: 14 gambe verdi e 1 rossa sullo stesso
    ingresso). Per farlo fallire servirebbe un MARGINE MINIMO — e la prima
    versione di questo file ne aveva uno, `MARGINE_MINIMO = 10.0`, dichiarato
    nel commento come «una scelta, non una misura».

    L'ho tolto, per due ragioni che tirano dalla stessa parte:
      · un limite scelto e' un debito che paga chi lo trova rosso fra un mese;
      · un altro banco sullo stesso giudice ha deciso di NON fissarne uno
        perche' nessuno l'ha misurato, e due file dello stesso repo non
        possono rispondere il contrario alla stessa domanda.

    E l'assert che restava — «lo stato non e' quarantined» — e' PROPRIO quello
    che oscilla: metterlo qui significherebbe armare nella suite la stessa
    trappola intermittente che un'altra PR sta togliendo da questo file. Un
    osservatore che puo' fallire a caso non e' un osservatore, e' un rumore
    che qualcuno dovra' spegnere.

    ⇒ QUESTO TEST REGISTRA E NON GIUDICA. Fallisce solo se il numero non e'
    piu' ottenibile — che e' una regressione vera: senza `grounding_score`
    sulla ricevuta, il margine non lo puo' misurare piu' nessuno, e il difetto
    tornerebbe invisibile per sempre invece che per una cura. Il margine sta
    nel messaggio, cosi' chi legge un rosso qui trova il numero davanti.

    🔑 COSA LO ARMA: la distribuzione del punteggio sullo STESSO ingresso,
    ripetuto. Se i valori stanno a cavallo del taglio, il margine minimo
    esiste e vale quel che dice la misura; se sono stabili e lontani, la
    diagnosi del 2026-09-12 e' sbagliata e va ritirata — compresa la mia.
    Fino ad allora questo file NON dichiara chiuso T69.
    """
    db = Path(tempfile.mkdtemp()) / "margine.db"
    mem = Memory(str(db))
    prima = mem.add("La coda ha 500 elementi.", topic="t/margine",
                    verified_by=FONTE, source=SORGENTE, validate="full")
    fid = prima.get("id") or prima.get("fact_id") or ""

    #: La fonte e' quella ORIGINALE, senza l'id: e' il caso che la CI ha visto.
    ricevuta = mem.add(
        f"La coda ha 540 elementi (rettifica del fatto {fid}).",
        topic="t/margine", verified_by=FONTE, source=SORGENTE, validate="full")

    punteggio = ricevuta.get("grounding_score")
    stato = ricevuta.get("status")
    assert punteggio is not None, (
        "la ricevuta non porta piu' `grounding_score`: senza quel numero il "
        "margine fra un ingresso e il taglio del moat non e' misurabile da "
        "nessuna porta, e il difetto del 2026-09-12 — un ingresso legittimo "
        "ammesso per un soffio — torna invisibile. Non abbassare questo "
        f"assert: rimetti il campo sulla ricevuta. ricevuta={ricevuta}")

    margine = float(punteggio) - LOCAL_CE_MOAT_THRESHOLD
    print(f"[T69] grounding={punteggio} soglia={LOCAL_CE_MOAT_THRESHOLD} "
          f"margine={margine:+.2f} stato={stato!r}")
