"""Una scrittura con fonte ASPETTA il giudice che sta caricando, invece di uscire.

⚠️ IL P0 CHE QUESTO FILE PRESIDIA — misurato il 06/09 da @ws1 Marie sul commit di
release installato, A/B a UNA variabile, porta MCP, configurazione di DEFAULT:

    warm su thread   moat_judge failed (import)   grounding None    judged False
    warm sincrono    moat_judge complete 19,1 s   grounding 98.37   judged True

Lo stesso identico fatto, con la stessa fonte. L'errore del braccio rotto:

    cannot import name 'AutoModelForSequenceClassification' from 'transformers'

e lo stesso import, provato DA SOLO nello stesso venv, riesce.

⇒ Un utente che passa una `source` — cioe' chiede il controllo forte — riceveva
`stored=True · grounding_score=None · judged=False · layers=['L4-skipped']`: il
prodotto **dichiara** di non aver giudicato (non mente), ma **non fa il lavoro**
proprio a chi lo ha chiesto. Aurelio: «ci apriamo al mondo solo quando tutto
funziona davvero» — il tag 0.7.7 e' stato fermato per questo.

LA CURA, in due pezzi:
  (a) `verimem/_import_lock.py` — gli import pesanti si mettono in fila sotto UN
      lock, cosi' non si incrociano (e' anche la famiglia di T1b);
  (b) QUI: se il giudice sta CARICANDO, la scrittura lo aspetta con un budget
      dichiarato (`VERIMEM_JUDGE_WAIT_S`, default 60 s) invece di uscire subito.

⚠️ NESSUN MODELLO IN QUESTO FILE: `judge_state` e `local_ce_available` sono
sostituiti da finti. Il banco misura il CONTRATTO — «aspetta», «non aspetta chi
non deve», «il budget morde» — non il giudice vero. Il verdetto sul giudice vero
e' l'A/B di @ws1 Marie sul commit installato: questo file non lo sostituisce.
"""
import time

from verimem import anti_confab_gate as gate
from verimem import local_grounding as lg

#: Il giudizio finto non deve mai partire: qui si misura solo l'ATTESA.
_FONTE = "the config sets the cache TTL to 30 minutes"
_FRASE = "The cache TTL is 30 minutes."


def _layers(risultato) -> list[str]:
    return [str((w or {}).get("layer") or "")
            for w in (getattr(risultato, "warnings", None) or [])]


def _chiama() -> object:
    return gate.run_validation_gate(
        proposition=_FRASE, verified_by=["source-doc:x:1"], topic="t",
        agent=None, validate="fast", source=_FONTE, ground_write=True,
    )


def test_se_il_giudice_sta_caricando_la_scrittura_lo_aspetta(monkeypatch):
    """Il caso del P0: `warming` non deve produrre un'uscita immediata."""
    partenza = time.time()
    #: warming per 1,5 s, poi pronto. Il gate deve accorgersene e proseguire.
    monkeypatch.setattr(
        lg, "judge_state",
        lambda: "warming" if time.time() - partenza < 1.5 else "ready")
    monkeypatch.setattr(
        lg, "local_ce_available",
        lambda: time.time() - partenza >= 1.5)
    monkeypatch.setenv("VERIMEM_JUDGE_WAIT_S", "20")

    t0 = time.time()
    _chiama()
    atteso = time.time() - t0

    assert atteso >= 1.4, (
        f"la scrittura non ha aspettato il giudice (durata {atteso:.2f}s). "
        "Con `warming` deve attendere: uscire subito fa entrare NON VERIFICATO "
        "un fatto che sarebbe stato giudicato — misurato 98,37 col warm "
        "sincrono contro judged=False col warm su thread."
    )


def test_se_il_giudice_non_e_su_disco_la_scrittura_NON_aspetta(monkeypatch):
    """Il controllo che impedisce alla cura di diventare un'attesa cieca.

    `absent` significa «il modello non c'e'»: aspettarlo sarebbe peggio del
    difetto, perche' il budget scadrebbe a ogni singola scrittura.
    """
    monkeypatch.setattr(lg, "judge_state", lambda: "absent")
    monkeypatch.setattr(lg, "local_ce_available", lambda: False)
    monkeypatch.setenv("VERIMEM_JUDGE_WAIT_S", "20")

    t0 = time.time()
    risultato = _chiama()
    durata = time.time() - t0

    assert durata < 2.0, (
        f"ha aspettato {durata:.2f}s un giudice ASSENTE: con un budget di 20 s "
        "ogni scrittura pagherebbe l'attesa per un modello che non arrivera'."
    )
    assert "L4-skipped" in _layers(risultato), (
        "senza giudice sul disco la scrittura deve restare dichiarata "
        f"L4-skipped; visti: {_layers(risultato)!r}"
    )


def test_il_budget_dell_attesa_morde(monkeypatch):
    """Se il giudice non arriva mai, si esce al budget — mai appesi.

    Esercita il RAMO DELL'USCITA: senza questa cella un budget rotto (mai letto,
    o letto male) non lo scoprirebbe nessuno, perche' le altre due passano sia
    con l'attesa breve sia con quella infinita.
    """
    monkeypatch.setattr(lg, "judge_state", lambda: "warming")
    monkeypatch.setattr(lg, "local_ce_available", lambda: False)
    monkeypatch.setenv("VERIMEM_JUDGE_WAIT_S", "1")

    t0 = time.time()
    risultato = _chiama()
    durata = time.time() - t0

    assert durata < 8.0, (
        f"il budget non morde: {durata:.2f}s con VERIMEM_JUDGE_WAIT_S=1. "
        "Una scrittura non deve restare appesa al caricamento del giudice."
    )
    assert durata >= 0.9, (
        f"non ha aspettato affatto ({durata:.2f}s): il budget e' letto ma "
        "l'attesa non avviene, e la cella sopra passerebbe per il motivo "
        "sbagliato."
    )
    assert "L4-skipped" in _layers(risultato), (
        "scaduto il budget la scrittura resta ammessa e DICHIARATA non "
        f"verificata; visti: {_layers(risultato)!r}"
    )
