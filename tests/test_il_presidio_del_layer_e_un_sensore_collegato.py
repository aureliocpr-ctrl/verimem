"""Il presidio della porta cade DAVVERO se si toglie la cura: la prova.

DA DOVE VIENE. Il punto del mattino del 31/08 (`lead-audit`, 05:15) dichiara
apertamente, su F3-①: *«il fix `agito` (la porta MCP nominava `gate` invece del
layer) ha due firme … Al presidio-porta manca il test che cade senza la cura:
firma finale in sospeso, dichiarata.»*

⚠️ E' la differenza fra un test ROSSO VERO e un GUARDIANO CHE MENTE:
`test_la_porta_degli_agenti_nomina_il_layer` asserisce
`quarantined_by != "gate"` **alla porta**, ma finche' nessuno mostra che
TOGLIENDO la cura quell'asserzione cade, non si sa se stia presidiando qualcosa
o se sia verde per un'altra ragione. La prova che un criterio funziona e' che
togliendolo il numero CAMBI.

🔑 PERCHE' LA FALSIFICAZIONE E' SULLA FUNZIONE E NON SUL CHIAMANTE. Il modo
ovvio sarebbe togliere `agito=...` da `mcp_server.py`, eseguire, rimettere.
⛔ Non si fa: questo albero e' condiviso da otto istanze che committano nello
stesso momento, e un A/B nel repo condiviso e' gia' costato una volta (memoria
`gate-non-legge-i-numeri-italiani`, 18-19/08). L'A/B qui sta dentro UNA
esecuzione e non tocca nessun file — che e' anche la forma piu' pulita, perche'
isola il parametro invece del diff.

MISURATO (2026-08-31, ore 05:20, una sola esecuzione, nessuna scrittura)::

    warnings = [{"layer": "L4.1", ...}]

    chi_ha_quarantinato("ok", warnings, agito=["L4.1"])   ->  'L4.1'
    chi_ha_quarantinato("ok", warnings)                   ->  'gate'   ← senza la cura

⇒ **Il parametro e' portante**: senza, i due cicli finali non hanno niente su
cui girare e la funzione cade sull'ultima riga, `return "gate"`. Il presidio
alla porta ha quindi qualcosa da presidiare, e diventa rosso se la chiamata
perde `agito`.

⚖️ COSA QUESTO FILE NON FA: non duplica il test della porta — quello misura
l'uscita del tool, questo misura che la sua asserzione sia *falsificabile*.
Sono due cose diverse e servono entrambe.
"""

from __future__ import annotations

import inspect

from verimem.client import _blocking_layers, chi_ha_quarantinato


def test_senza_agito_la_funzione_cade_sull_etichetta_generica() -> None:
    """IL CUORE — l'A/B che rende il presidio della porta un sensore collegato."""
    warnings = [{"layer": "L4.1", "message": "il numero non compare nella fonte"}]
    agito = _blocking_layers(warnings)
    assert agito == ["L4.1"], agito

    con_cura = chi_ha_quarantinato("ok", warnings, agito=agito)
    senza_cura = chi_ha_quarantinato("ok", warnings)

    assert con_cura == "L4.1", con_cura
    assert senza_cura == "gate", (
        f"senza `agito` la funzione risponde {senza_cura!r} invece di 'gate': "
        "il presidio alla porta non sta piu' presidiando questo difetto, e la "
        "cura andrebbe rimotivata prima di fidarsi del suo verde.")


def test_la_porta_MCP_passa_davvero_quel_parametro() -> None:
    """⚠️ L'ALTRA META': la cella sopra prova che il parametro CONTA, questa che
    la porta lo PASSA. Separate apposta: se qualcuno lo togliesse dalla
    chiamata, questo test dice DOVE, mentre quello della porta direbbe solo che
    l'uscita e' sbagliata."""
    sorgente = inspect.getsource(
        __import__("verimem.mcp_server", fromlist=["mcp_server"]))
    assert "agito=_bl(_gate_warnings)" in sorgente, (
        "la porta MCP non passa piu' i layer che hanno bloccato a "
        "`chi_ha_quarantinato`: `quarantined_by` tornera' 'gate' e la "
        "ricevuta smettera' di nominare il decisore.")


def test_CONTROLLO_un_avviso_non_viene_nominato_come_decisore() -> None:
    """⚠️ LA POPOLAZIONE OPPOSTA, e senza di essa la cura sarebbe peggiore del
    difetto: un layer `*-observe` NON ha deciso nulla: nominarlo come decisore
    accrediterebbe di un blocco chi si e' limitato ad avvisare. Qui `gate` e' la
    risposta GIUSTA — la stessa stringa che nella prima cella e' il difetto."""
    solo_avvisi = [{"layer": "L4.1-observe", "message": "avviso, non blocca"}]
    agito = _blocking_layers(solo_avvisi)
    assert agito == [], agito
    assert chi_ha_quarantinato("ok", solo_avvisi, agito=agito) == "gate"
