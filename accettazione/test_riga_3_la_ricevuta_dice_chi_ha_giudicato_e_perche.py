"""RIGA 3 — la ricevuta dice chi ha giudicato e perché.

LA PROMESSA. Lista chiusa della 0.7.7, riga 3 (21/09 21:5x). Il README, quickstart
Python: «THE MOAT, live … the local CE is the judge», con l'esempio Postgres ammesso e
MongoDB in quarantena; e alla voce Install: «`admitted` on its own does not mean judged.
Read that field.» Le invarianti I1 (nessun fatto servito come verificato senza un
punteggio del giudice su una fonte) e I5 (la ricevuta nomina ogni livello consultato e
ogni livello saltato). La RICERCA del 21/09 §2: il giudice è un artefatto VERSIONATO.

COSA VEDE L'UTENTE. Sulla scrittura ammessa, la ricevuta gli dice QUALE giudice (chi e
quale modello, in quale versione) e con che punteggio contro quale soglia. Sulla scrittura
trattenuta, gli dice QUALE livello l'ha fermata e PERCHE'. E se ha chiesto il servizio
condiviso (`HIPPO_ENCODE_DELEGATE_ONLY=1`) e il giudizio e' avvenuto altrove, la
ricevuta gli dice perche' (T179, #124): altrimenti crede di avere un'installazione che
non ha. Il 23/09 su c524fa07 la ricevuta portava `'version': None`.

CHI LA CHIUDE: T179 (#124), T177 (la versione del giudice). Oggi: ROSSA (predizione).
"""
from __future__ import annotations

import json

NON_DICHIARATO = "non dichiarato dal cancello"

CODICE = r'''
import json
from verimem import Memory
m = Memory()
src = "We migrated the analytics store to Postgres last quarter."
r1 = m.add("Analytics runs on Postgres.", source=src)
r2 = m.add("Analytics runs on MongoDB.", source=src)
chiavi = ("esito", "giudice", "modello", "scala", "punteggio", "soglia", "fermato_da",
          "livelli", "judged_by")
print("ESITO " + json.dumps({
    "ammessa": {k: r1.get(k) for k in chiavi},
    "versione": ((r1.get("adjudication") or {}).get("judge") or {}).get("version"),
    "trattenuta": {k: r2.get(k) for k in chiavi},
}, ensure_ascii=False, default=str))
'''


def _esito(uscita) -> dict:
    righe = [r for r in uscita.stdout.splitlines() if r.startswith("ESITO ")]
    assert righe, (f"lo script dell'utente non e' arrivato in fondo (exit "
                   f"{uscita.returncode}); stderr: {uscita.stderr[-800:]}")
    return json.loads(righe[-1][len("ESITO "):])


def _dichiarato(valore) -> bool:
    return bool(valore) and str(valore) != NON_DICHIARATO


def test_riga_3_la_ricevuta_nomina_il_giudice_la_sua_versione_e_il_perche(utente):
    esito = _esito(utente.python(CODICE))
    ammessa, trattenuta = esito["ammessa"], esito["trattenuta"]

    # chi: la scrittura sostenuta dalla fonte e' ammessa E giudicata
    assert ammessa["esito"] == "ammesso", ammessa
    assert ammessa["punteggio"] is not None and ammessa["soglia"] is not None, (
        f"ammessa senza punteggio o senza soglia: non e' stata giudicata (I1). {ammessa}")
    assert _dichiarato(ammessa["giudice"]) and _dichiarato(ammessa["modello"]), (
        f"la ricevuta non nomina chi ha giudicato: {ammessa}")
    assert esito["versione"], (
        "la ricevuta nomina il modello ma non la sua VERSIONE: l'utente non puo' sapere "
        f"quale giudice ha deciso. adjudication.judge.version = {esito['versione']!r}")

    # perche': la scrittura che la fonte non sostiene e' trattenuta e dice da chi
    assert trattenuta["esito"] == "fermato", trattenuta
    assert trattenuta["fermato_da"], f"trattenuta senza il livello che l'ha fermata: {trattenuta}"
    livello = [liv for liv in trattenuta["livelli"] or []
               if liv.get("nome") == trattenuta["fermato_da"]]
    assert livello and livello[0].get("ragione"), (
        f"il livello {trattenuta['fermato_da']!r} ha fermato la scrittura senza dire "
        f"perche': {trattenuta['livelli']}")


def test_riga_3_chi_ha_chiesto_il_servizio_condiviso_sa_perche_non_l_ha_avuto(utente):
    esito = _esito(utente.python(CODICE, HIPPO_ENCODE_DELEGATE_ONLY="1"))
    ammessa = esito["ammessa"]
    servita_dal_servizio = "daemon" in str(ammessa.get("judged_by") or "").lower()
    if servita_dal_servizio:
        return  # la delega chiesta e' avvenuta: non c'e' un perche' da dire
    ragioni = " ".join(str(liv.get("ragione") or "") for liv in ammessa.get("livelli") or [])
    assert "daemon" in ragioni.lower(), (
        "l'utente ha chiesto il servizio condiviso (HIPPO_ENCODE_DELEGATE_ONLY=1), il "
        f"giudizio non e' venuto da li' (judged_by={ammessa.get('judged_by')!r}), e la "
        f"ricevuta non dice perche': livelli = {ammessa.get('livelli')}")
