"""«Quanti giorni per il pagamento?» veniva instradata a un conteggio di FATTI.

IL DIFETTO, trovato da ws5 sul mandato lingue e con una diagnosi che la misura
ha ROVESCIATO. Lui aveva misurato::

    IT  1/3 corrette   <- «Quante…» e «Quanti…» -> intent=count
    DE  3/3            <- tutte find
    FR  2/3            ES  3/3

…e ne aveva concluso «il router sbaglia SOLO in italiano», il che sembrava un
difetto della lingua in cui il prodotto è scritto. Misurando anche l'inglese::

    «Quanti giorni per il pagamento delle fatture?»   -> count  🔴
    «How many days for the payment of invoices?»      -> count  🔴
    «How much does the contract cost?»                -> count  🔴
    «Wie viele Tage fuer die Zahlung?»                -> find   ok
    «Combien de jours pour le paiement?»              -> find   ok

🔑 **L'inglese ha esattamente lo stesso difetto.** Non è la lingua: è il
CRITERIO, e colpisce tutte e sole le lingue che il router *copre*. DE e FR si
salvano **per omissione**, non perché siano trattate meglio.

⚠️ E LA CONSEGUENZA CAMBIA LA CURA: la strada ovvia — «aggiungi *wie viele*,
*combien*, *cuántas* al router» — **propagherebbe il difetto a tre lingue in
più**. Sarebbe la classe ③ al contrario: estendere una lista senza accorgersi
che la lista è sbagliata.

LA DISTINZIONE VERA, e non è linguistica::

    «quante VOLTE ho parlato con Bianchi»   -> conta RECORD    count è giusto
    «quanti FATTI ci sono sul progetto»     -> conta RECORD    count è giusto
    «quanti GIORNI per il pagamento»        -> chiede un VALORE  count è sbagliato
    «quante UNITÀ nel magazzino»            -> chiede un VALORE  count è sbagliato

``count`` scandisce e conta l'insieme dei fatti che corrispondono. Ha senso solo
quando la domanda chiede **quanti record**, non quando chiede **un numero che sta
scritto dentro un record**. Nel secondo caso la risposta giusta è il fatto, e
``count`` restituisce 1 o 0 — un numero che ha la forma della risposta e non lo è.

📌 LA LISTA CHE SERVE QUI È LEGITTIMA, e la distinguo da quelle che rifiuto: non
enumera il mondo (le unità di misura, i sostantivi, le lingue) ma **il vocabolario
del prodotto** — come si chiamano i suoi record. È chiusa e corta per
costruzione: volte, fatti, record, voci, elementi, e i loro equivalenti inglesi.
⛔ CURA RITIRATA, e questo file resta come DOCUMENTAZIONE del difetto con i due
criteri già falsificati — perché il prossimo non li riprovi.

    ① «il sostantivo è un record del prodotto» (volte, fatti, voci…)
       -> CADONO 6 test veri già in repo: «how many MEETINGS», «numero di
          RIUNIONI», «quanti PROGETTI», «number of open TICKETS».
          🔑 In una memoria di lavoro **le cose del mondo SONO i record**: la
          distinzione record-vs-mondo non esiste.
    ② «il sostantivo è un'unità di misura» (usando `_UNIT_SYN`)
       -> non separa: `days` è nel dizionario, `giorni`/`euro`/`unità` no.
          Servirebbe un lessico di unità per ogni lingua — la lista che questa
          casa rifiuta, e che qui non avrebbe nemmeno un bordo chiuso.

🔑 LA RAGIONE È STRUTTURALE, e per questo la cura non sta nel router: «quanti X»
è ambiguo NEL LINGUAGGIO. «Quante riunioni» conta record e «quanti giorni»
chiede un valore, ma la differenza sta in **cosa contiene il corpus**, non nella
domanda — e il router la domanda la vede da sola.

👉 LA DIREZIONE CHE RESTA, senza liste e da misurare: `count` che risponde **1**
a una domanda di quantità è sospetto per costruzione. Invece di decidere PRIMA
quale strada prendere, si può servire il conteggio E il fatto quando l'insieme
ha un elemento solo — chi legge vede «1» e accanto il record che contiene la
risposta vera. È una cura a VALLE, dove l'informazione per decidere esiste.
"""

from __future__ import annotations

import pytest

from verimem.query_intent import COUNT, classify_query_intent

#: Domande che chiedono un VALORE scritto dentro un fatto: `count` risponderebbe
#: «1», che è il numero di record trovati, non la risposta.
VALORE = [
    "Quanti giorni per il pagamento delle fatture?",
    "Quante unita' ci sono nel magazzino di Verona?",
    "Quanti euro vale il contratto con Ferrero?",
    "How many days for the payment of invoices?",
    "How many units are in the Verona warehouse?",
    "How much does the contract cost?",
]

#: ⚠️ LA POPOLAZIONE OPPOSTA: domande che chiedono davvero QUANTI RECORD.
#: Senza queste, il test sopra è soddisfatto da un router che non instrada mai
#: a `count` — cioè spegnendo la funzione invece di curarla.
CONTEGGIO = [
    "Quante volte ho parlato con Bianchi?",
    "Quanti fatti ci sono sul progetto Ferrero?",
    "Quante voci ci sono nel registro?",
    "How many times did I meet Rossi?",
    "How many facts do you have about the project?",
    "How many records are in the log?",
]


@pytest.mark.xfail(reason="difetto APERTO: due criteri falsificati, vedi il "
                          "docstring del modulo. Non e' una regressione.",
                   strict=True)
@pytest.mark.parametrize("domanda", VALORE)
def test_una_domanda_su_un_VALORE_non_va_al_conteggio(domanda):
    """IL CUORE: «quanti giorni» chiede un numero che sta DENTRO un fatto.
    Instradarla a `count` restituisce il numero di record — 1 — che ha la forma
    di una risposta e non lo è."""
    assert classify_query_intent(domanda) != COUNT, domanda


@pytest.mark.parametrize("domanda", CONTEGGIO)
def test_CONTROLLO_POSITIVO_una_domanda_su_QUANTI_RECORD_resta_un_conteggio(domanda):
    """⚠️ IL PRESIDIO CHE IMPEDISCE DI SPEGNERE LA FUNZIONE. `count` esiste
    perché il recall top-k sottostima gli insiemi (misurato: -58%): se il
    router smettesse di instradarci, tornerebbe il difetto che `count` cura."""
    assert classify_query_intent(domanda) == COUNT, domanda


def test_la_cura_NON_e_una_lista_di_lingue():
    """🔑 Il presidio contro la strada sbagliata. DE e FR oggi finiscono in
    `find` perché il router non le riconosce, e per questo funzionano.
    Aggiungerle al router — la cura ovvia — propagherebbe il difetto a tre
    lingue in più: questo test pretende che, se un giorno verranno
    riconosciute, la distinzione valore/record valga anche per loro.

    Era marcato `xfail(strict=False)` e PASSAVA — cioè il presidio contro la
    strada sbagliata era muto proprio nella direzione che doveva sorvegliare:
    chi avesse aggiunto le lingue al router avrebbe visto un fallimento
    ATTESO e la suite verde. Marcatore tolto il 2026-08-16 dopo tre
    esecuzioni verdi con `--runxfail`. Passa per la ragione dichiarata nel
    docstring — l'assenza dal router — non perché la distinzione sia stata
    estesa: il giorno in cui lo sarà, questo test è il primo a dirlo."""
    for domanda in ("Wie viele Tage fuer die Zahlung der Rechnungen?",
                    "Combien de jours pour le paiement des factures?",
                    "Cuantos dias para el pago de las facturas?"):
        assert classify_query_intent(domanda) != COUNT, domanda
