"""RIGA 1 — un fatto ammesso viene servito: nessuna coppia si ritira per un soggetto diverso.

LA PROMESSA. Lista chiusa della 0.7.7, riga 1 (21/09 21:5x). Il README, alla voce
«Cross-fact contradiction + same-source evolution — ON by default», promette che la
stessa fonte che AGGIORNA un valore ritira il vecchio («the plan costs 100 €» →
«…150 €»: recall rende solo il corrente), e subito sotto dichiara come «Known limit»
proprio il caso di questa riga: due fatti sotto lo stesso topic che misurano cose
DIVERSE, e il piu' nuovo ritira quello vero (171 coppie sul nostro store).

COSA VEDE L'UTENTE. Scrive dalla stessa fonte «il capannone 7 misura 300 mq» e «il
capannone 12 misura 400 mq»: tutte e due le scritture tornano ammesse, e la ricerca
gliene restituisce UNA. La ricevuta della seconda elenca la prima fra i `ritirati`.

CONTROLLO POSITIVO. L'esempio del README (100 € → 150 €, stessa fonte) deve ritirare il
vecchio: se non lo fa, l'evoluzione non ha girato e questa riga passerebbe a vuoto.

⚠️ SI GUARDA CIO' CHE LA RICERCA SERVE, non il campo `ritirati` della ricevuta: oggi
l'adattatore lo lascia sempre vuoto («il cancello non li porta ancora con la loro
ragione», `adattatore_ricevuta.py`), e un controllo su quel campo sarebbe rosso per la
ragione sbagliata. `superseded_undo_ops` (la maniglia che il README promette su `add()`)
entra solo nel messaggio, come informazione.

CHI LA CHIUDE: T175 + T211 + T216, una richiesta sola (la decisione numerica, il verbo
come unita', il soggetto dichiarato `about`). Oggi: ROSSA (predizione del 25/09).
"""
from __future__ import annotations

import json

CODICE = r'''
import json
from verimem import Memory
m = Memory()
fuori = {}
fonte_prezzo = ("Pricing page, updated: the plan costs 100 € per month; "
                "from October the plan costs 150 € per month.")
a = m.add("The plan costs 100 € per month.", source=fonte_prezzo, topic="pricing")
b = m.add("The plan costs 150 € per month.", source=fonte_prezzo, topic="pricing")
fuori["prezzo"] = {
    "a": a.get("esito"), "b": b.get("esito"),
    "maniglie_di_b": b.get("superseded_undo_ops"),
    "serviti": [h["text"] for h in m.search("how much does the plan cost", k=10)],
}
fonte = "Nel magazzino il capannone 7 misura 300 mq e il capannone 12 misura 400 mq."
c = m.add("Il capannone 7 misura 300 mq.", source=fonte, topic="magazzino")
d = m.add("Il capannone 12 misura 400 mq.", source=fonte, topic="magazzino")
fuori["capannoni"] = {
    "c": c.get("esito"), "d": d.get("esito"),
    "maniglie_di_d": d.get("superseded_undo_ops"),
    "serviti": [h["text"] for h in m.search("capannone", k=10)],
}
print("ESITO " + json.dumps(fuori, ensure_ascii=False))
'''


def _esito(uscita) -> dict:
    righe = [r for r in uscita.stdout.splitlines() if r.startswith("ESITO ")]
    assert righe, (f"lo script dell'utente non e' arrivato in fondo (exit "
                   f"{uscita.returncode}); stderr: {uscita.stderr[-800:]}")
    return json.loads(righe[-1][len("ESITO "):])


def test_riga_1_due_soggetti_dalla_stessa_fonte_restano_serviti(utente):
    esito = _esito(utente.python(CODICE))

    prezzo = esito["prezzo"]
    assert prezzo["a"] == "ammesso" and prezzo["b"] == "ammesso", prezzo
    assert "The plan costs 150 € per month." in prezzo["serviti"] and \
        "The plan costs 100 € per month." not in prezzo["serviti"], (
        "CONTROLLO POSITIVO SPENTO: l'esempio del README (100 € → 150 €, stessa fonte) "
        f"non serve solo il valore corrente, quindi la riga misurerebbe a vuoto: {prezzo}")

    capannoni = esito["capannoni"]
    assert capannoni["c"] == "ammesso" and capannoni["d"] == "ammesso", capannoni
    assert "Il capannone 7 misura 300 mq." in capannoni["serviti"] and \
        "Il capannone 12 misura 400 mq." in capannoni["serviti"], (
        "due soggetti diversi dalla stessa fonte, tutti e due ammessi, e la ricerca non "
        f"li serve tutti e due: un fatto vero che l'utente non riceve piu'. {capannoni}")
