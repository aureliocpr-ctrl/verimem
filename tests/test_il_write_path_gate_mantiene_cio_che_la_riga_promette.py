"""«Write-path gate: unsupported claims quarantined» — la riga misurata parola per parola.

✅ **CHIUSO il 2026-08-14.** La riga ora dice «quarantined — **stored, not
served**» e coincide col comportamento; il marcatore ``xfail(strict=True)`` in
fondo e' stato tolto e quel caso e' diventato un guardiano di non-regressione.
Il resto di questa docstring e' la storia del difetto, e resta perche' spiega
perche' il guardiano esiste.

PERCHE' QUESTO FILE E' NATO. La riga 483 del README dichiarava:

    | Write-path gate (unsupported "it works" claims quarantined, not stored) |

Misurato il 2026-08-13 con un claim non sostenuto («Il sistema funziona
perfettamente e tutti i test passano», fonte «Il gatto dorme sul divano»):

    status ............ quarantined   ✅ come promesso
    fuori dal recall .. search() 0 hit ✅ come promesso
    stored ............ **True**       ❌ la riga dice il contrario
    get_all() ......... **lo restituisce**, con status=quarantined

Il comportamento e' quello GIUSTO, ed e' la vetrina a descriverlo male: il
contratto che ogni agente riceve via MCP (``agent_guide.py``, prima riga) lo
scrive correttamente — *«a fact its source does not support is QUARANTINED —
stored, but kept OUT of default recall»*. Due superfici nostre si contraddicono,
e quella sbagliata e' la pubblica.

⚠️ PERCHE' NON E' UNA PIGNOLERIA: «not stored» promette **di piu'** di «stored
ma escluso dalla recall». Suona come *«il dato viene buttato via»*, che per chi
legge pensando a ritenzione e cancellazione e' una garanzia diversa e piu'
forte. E' la terza riga trovata oggi che sbaglia **nella direzione a noi
comoda**, dopo «abstains 2/2» invertito rispetto al proprio bench e i numeri
attribuiti a prodotti altrui.

COME E' COSTRUITO, e perche' NON asserisce semplicemente il comportamento.
La cura di questo difetto sta nel README, non nel codice. Un test che
pretendesse «get_all non restituisce i quarantinati» resterebbe rosso per
sempre, perche' il comportamento e' corretto e non deve cambiare. Il test e'
percio' un'IMPLICAZIONE: *finche' la riga dice «not stored», il prodotto non
deve conservarli*. Si chiude in due modi, entrambi legittimi — correggendo la
riga (che e' la cura giusta: «not served», o «kept out of recall» come gia'
scrive il contratto) oppure cambiando il comportamento. Con ``strict=True``,
appena uno dei due arriva il caso diventa ROSSO e il marcatore va tolto.

⚠️ PERIMETRO, dichiarato: misurato sull'SDK Python. Sulle porte MCP c'e' un
indizio e non una misura — ``facts_list``, ``facts_recent`` e ``get_all`` non
nominano «quarantin» nel proprio corpo, e nel client il filtro
``status != 'quarantined'`` compare in due punti, nessuno dei quali e'
``get_all`` (client.py:2837). Se anche quelle porte li mostrano, «not stored»
e' falso su piu' superfici, non su una: chi lo misura lo aggiunga qui.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem import Memory

README = Path(__file__).resolve().parents[1] / "README.md"

#: Il claim non sostenuto: un'autodichiarazione di successo, che e' esattamente
#: il caso che la riga del README nomina («unsupported "it works" claims»).
_CLAIM = "Il sistema funziona perfettamente e tutti i test passano."
_FONTE_ESTRANEA = "Il gatto dorme sul divano."


@pytest.fixture
def esito(tmp_path_factory):
    """Un archivio nuovo, un claim non sostenuto scritto dentro."""
    m = Memory(str(tmp_path_factory.mktemp("gate") / "g.db"))
    r = m.add(_CLAIM, source=_FONTE_ESTRANEA)
    return m, (r if isinstance(r, dict) else {})


def _riga_del_readme() -> str:
    """La riga della tabella che parla del write-path gate, o stringa vuota."""
    for riga in README.read_text(encoding="utf-8").splitlines():
        if riga.strip().startswith("|") and "Write-path gate" in riga:
            return riga
    return ""


def test_il_claim_non_sostenuto_e_quarantinato(esito) -> None:
    """La meta' della promessa che REGGE, e va detto: il gate fa il suo lavoro."""
    _, r = esito
    assert r.get("status") == "quarantined", (
        f"un'autodichiarazione di successo con una fonte che non la sostiene "
        f"deve essere quarantinata; ottenuto status={r.get('status')!r}, "
        f"grounding_score={r.get('grounding_score')!r}"
    )


def test_il_claim_quarantinato_non_esce_dalla_recall(esito) -> None:
    """L'altra meta' che regge, ed e' quella che conta per un agente.

    E' la garanzia sostanziale — «so you never get it back as truth» — e questa
    il prodotto la mantiene: cio' che e' quarantinato non torna da una ricerca.
    """
    m, _ = esito
    assert m.search("sistema funziona") == [], (
        "un fatto quarantinato non deve tornare da search: e' la promessa "
        "sostanziale del gate, quella per cui un agente puo' fidarsi di cio' "
        "che riceve"
    )


def test_il_claim_quarantinato_resta_conservato(esito) -> None:
    """La terza meta', ed e' quella che la riga NUOVA promette: «stored».

    ⚠️ PERCHE' ESISTE, e la ragione non e' teorica. Fino al 2026-08-14 la riga
    prometteva «not stored» e l'unico caso che guardava ``stored`` era quello in
    fondo, scritto come IMPLICAZIONE. Curata la riga, quella premessa e' caduta e
    quel caso e' diventato INERTE — corretto, ma inerte. Risultato: per qualche
    ora la promessa nuova «stored, not served» era coperta a meta', «not served»
    dal test sopra e «stored» **da nessuno**. Se qualcuno avesse cambiato il
    comportamento buttando via i quarantinati, nessun banco lo avrebbe preso.

    🔑 E' la classe che un'altra sessione ha nominato oggi — *banchi che si
    spengono da soli quando cade cio' che verificano* — nella sua forma piu'
    insidiosa: **il caso non si e' spento per un difetto, si e' spento perche' la
    cura ha funzionato.** Curare una promessa puo' disarmare il presidio che la
    sorvegliava, e la cura deve portarsi dietro il suo complemento.

    Questo caso e' INCONDIZIONATO apposta: non chiede cosa dica il README, e
    resta rosso se il prodotto smette di conservare i quarantinati — che e'
    esattamente cio' che la riga ora dichiara.
    """
    m, r = esito
    assert r.get("stored") is True, (
        f"la riga del README promette «stored, not served» e la scrittura "
        f"riporta stored={r.get('stored')!r}: se il prodotto ha smesso di "
        f"conservare i quarantinati, e' la riga a essere di nuovo falsa"
    )
    conservati = [f for f in m.get_all() if f.get("status") == "quarantined"]
    assert conservati, (
        "get_all() non restituisce piu' il fatto quarantinato. Il contratto MCP "
        "dice «stored, but kept OUT of default recall» e la tabella del README "
        "dice «stored, not served»: entrambe promettono che il fatto RESTI, "
        "consultabile a chi lo chiede esplicitamente"
    )


def test_la_riga_del_readme_esiste_ancora() -> None:
    """Precondizione: senza la riga, il test sotto misurerebbe il nulla in silenzio."""
    riga = _riga_del_readme()
    assert riga, (
        "nessuna riga della tabella nomina «Write-path gate»: se e' stata "
        "riscritta o tolta, aggiorna questo file invece di lasciarlo verde "
        "per assenza di superficie"
    )


def test_finche_la_riga_promette_not_stored_il_fatto_non_deve_restare(esito) -> None:
    """L'implicazione, non l'asserzione secca — vedi la docstring del modulo.

    ✅ CHIUSO il 2026-08-14: la riga ora dice «quarantined — stored, not
    served», la premessa e' caduta e il marcatore ``xfail(strict=True)`` e'
    stato tolto, come il file stesso prescriveva.

    ⚠️ IL CASO NON VA CANCELLATO CON LA CURA, e questa e' la ragione: da oggi
    e' un GUARDIANO DI NON-REGRESSIONE. Se qualcuno riscrive «not stored» nella
    tabella — per brevita', per copia da una versione vecchia, per traduzione —
    la premessa torna vera, i due assert sotto scattano, e il commit che l'ha
    reintrodotta diventa rosso. Un difetto curato senza un guardiano e' un
    difetto in attesa di tornare.

    📌 La falsificazione, per chi verra' dopo: cambiando SOLO la riga del README
    e lasciando il marcatore, questo caso passava da ``xfailed`` a ``failed``
    (XPASS strict, EXIT 1). E' la prova che la premessa e' agganciata al testo
    vero e non a una costante scritta qui.
    """
    riga = _riga_del_readme()
    if "not stored" not in riga:
        return  # la riga non promette piu' questo: niente da far valere

    m, r = esito
    assert not r.get("stored"), (
        f"la riga del README promette «not stored» e la scrittura riporta "
        f"stored={r.get('stored')!r}"
    )
    conservati = [f for f in m.get_all() if f.get("status") == "quarantined"]
    assert not conservati, (
        f"la riga del README promette «not stored», ma get_all() restituisce "
        f"{len(conservati)} fatto/i quarantinato/i. Il comportamento e' giusto "
        f"— cio' che e' quarantinato resta conservato e fuori dalla recall — "
        f"ed e' la riga a doverlo dire: «not served», o «kept out of recall» "
        f"come gia' scrive agent_guide.py"
    )
