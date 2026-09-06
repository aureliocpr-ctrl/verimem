"""UN lock di processo per gli import pesanti, perche' non si incrocino.

⚠️ PERCHE' ESISTE — due difetti misurati il 06/09, stessa famiglia:

  T1b (bloccante).  Il warm delle librerie del giudice girava su un thread di
  sfondo mentre la richiesta importava ``numpy.random``: due ``create_module``
  in parallelo, entrambi FERMI. Banco end-to-end su origin/main pulito:
  **0 giri su 3**; col caricamento sincrono **3 su 3**.

  Il P0 del giudice (fallimentare).  Il warm del modello del giudice importa
  ``transformers`` su un thread di sfondo mentre il modulo si sta
  inizializzando altrove, e **fallisce**:

      mcp_preload_moat_judge_failed
        error="cannot import name 'AutoModelForSequenceClassification'
               from 'transformers'"

  Lo stesso import, provato DA SOLO nello stesso venv, riesce (misurato in
  QA il 06/09, sul commit di release installato). A/B a una variabile, stesso
  fatto:
  con il warm su thread ``judged=False``; col warm sincrono ``grounding 98.37``,
  ``judged=True``.

⇒ Non sono due bug: e' lo stesso, in due forme. Un import pesante eseguito su un
thread mentre lo stesso pacchetto si inizializza altrove o si blocca o fallisce.

🔑 LA REGOLA DI QUESTO MODULO, e va rispettata da chi lo usa:

    IL LOCK SI TIENE SOLO ATTORNO ALL'IMPORT, MAI ATTORNO AL LAVORO.

I pesi del giudice sono 746 MB e il loro caricamento dura 19,1 s (misurato).
Se quel tratto stesse dentro il lock, una richiesta che arriva nel frattempo
aspetterebbe 19 s — cioe' avrei rimesso al suo posto il difetto tolto con
``a562e232`` (il build che teneva ``_agent_lock``). Il lock serializza gli
``import``, non il caricamento.

Uso:

    from ._import_lock import lock_import

    with lock_import():                 # <- solo l'import
        from transformers import AutoModelForSequenceClassification
    modello = AutoModelForSequenceClassification.from_pretrained(...)   # <- fuori

⚠️ RIENTRANTE di proposito (``RLock``): un import ne innesca altri, e con un
lock semplice il primo import annidato dentro lo stesso thread si
autobloccherebbe — un deadlock introdotto dalla cura, che e' il modo peggiore
di curare.
"""
from __future__ import annotations

import threading

#: Uno solo per processo. Rientrante: vedi la nota in coda al docstring.
_LOCK = threading.RLock()


def lock_import() -> threading.RLock:
    """Il lock degli import pesanti. Da usare come context manager.

    Torna sempre lo STESSO oggetto: se ne tornasse uno nuovo a ogni chiamata,
    due chiamanti si serializzerebbero ognuno con se' stesso e con nessun altro
    — un lock che non protegge niente e non lo dice.
    """
    return _LOCK


def e_tenuto_da_un_altro_thread() -> bool:
    """True se il lock e' preso da un THREAD DIVERSO da chi chiama.

    ⚠️ IL NOME DICE IL LIMITE, e il limite e' reale: il lock e' rientrante,
    quindi ``acquire(blocking=False)`` chiamata dal thread che GIA' lo tiene
    RIESCE, e questa funzione risponderebbe False su un lock tenuto. Chiamata
    dal proprio detentore mente. Si chiama cosi' perche' un misuratore che
    risponde a una domanda diversa da quella che sembra e' peggio di nessun
    misuratore — ed e' la trappola in cui questo file esiste per non cadere.

    Solo per i banchi: un thread verifica che UN ALTRO tenga il lock. Non usarla
    per decidere — fra la risposta e l'azione lo stato puo' cambiare.
    """
    preso = _LOCK.acquire(blocking=False)
    if preso:
        _LOCK.release()
        return False
    return True
