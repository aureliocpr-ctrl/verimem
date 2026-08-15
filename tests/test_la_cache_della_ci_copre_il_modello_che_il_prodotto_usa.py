"""Il percorso dove il prodotto mette il modello dev'essere quello che la CI mette in cache.

Sono **due liste in due file** che devono restare d'accordo, e non si conoscono:
`local_grounding.py` non sa che esiste un workflow, e `ci.yml` non sa che il
percorso può cambiare. Il 15/08 si sono separate senza che niente diventasse
rosso::

    il prodotto scrive in   ~/.cache/verimem/models/local_gate_ce_v2   (dopo 42f03411)
    ci.yml mette in cache   ~/.cache/huggingface
                            ~/.cache/torch/sentence_transformers
                            ~/.engram/models                            ← non più usata in CI

⇒ **La cache salvava una cartella vuota**, e i job continuavano a riscaricare
711 MB di modello a ogni run. È la quarta causa di un guasto che tre sessioni
stavano inseguendo da due giorni, e nessuna delle due modifiche era sbagliata:
erano d'accordo prima e nessuno le teneva insieme.

═══ PERCHÉ IL CRITERIO È NEUTRO RISPETTO ALLA CURA ═══

Questo banco **non dice dove il modello debba stare**, né quali percorsi la CI
debba mettere in cache. Chiede una sola cosa: che il percorso che il prodotto
**usa davvero** sia coperto da una delle voci in cache. Resta verde sia se si
aggiunge `~/.cache/verimem` al workflow, sia se il modello torna sotto un
percorso già coperto — che sono le due cure possibili, e la scelta è di chi ha
il perimetro della CI.

⚠️ `xfail(strict=True)`: oggi il difetto c'è. Quando verrà curato questo test
passerà, l'xpass renderà la suite rossa e chiederà di togliere il marcatore —
così il difetto fa rumore **quando smette di esistere** invece di restare un
marcatore che nessuno rilegge.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parents[1]
_CI = _RADICE / ".github" / "workflows" / "ci.yml"


def _percorsi_in_cache() -> list[str]:
    """Le voci `path:` dei blocchi di cache del workflow, normalizzate.

    ⚠️ Si leggono TUTTI i blocchi: il workflow ne ha più d'uno (il job dei test
    e quello dell'installazione dal wheel), e curarne uno solo lascia l'altro
    a riscaricare — un difetto che si vede solo su una gamba.
    """
    testo = _CI.read_text(encoding="utf-8")
    voci: list[str] = []
    dentro = False
    for riga in testo.splitlines():
        if re.match(r"\s*path:\s*\|\s*$", riga):
            dentro = True
            continue
        if dentro:
            m = re.match(r"\s+(~[^\s#]+|\$\{\{[^}]+\}\}[^\s#]*)\s*$", riga)
            if m:
                voci.append(m.group(1).strip())
            else:
                dentro = False
    return voci


def test_IL_WORKFLOW_DICHIARA_ANCORA_DEI_PERCORSI():
    """⚠️ Prima di tutto: se la lettura fallisse, il test sotto passerebbe a
    vuoto su una lista vuota — un verde che non ha guardato niente."""
    voci = _percorsi_in_cache()
    assert len(voci) >= 3, (
        f"nel workflow trovo solo {len(voci)} percorsi in cache ({voci}): o il "
        f"formato è cambiato e questa funzione va aggiornata, o la cache è "
        f"stata tolta — in entrambi i casi il presidio sotto ha smesso di "
        f"misurare")


# ✅ MARCATORE TOLTO il 15/08 (ws7). Il difetto c'era davvero, e la sua storia
# vale piu' della riga: `~/.cache/verimem` era gia' nel workflow dalle 13:15,
# aggiunto in anticipo su segnalazione di ws3 — ma **undici righe di commento
# stavano DENTRO il blocco `path: |`**, dove `#` non e' un commento: in uno
# scalare letterale YAML e' TESTO, e `actions/cache` le riceveva come pattern.
# Il percorso c'era e non si vedeva. Tolti i commenti da li', questo test e'
# passato a XPASS(strict) al primo colpo.
# 🔑 Il cricchetto ha funzionato come progettato da chi l'ha scritto: non ha
# detto «e' rotto», ha detto «adesso passa, togli il marcatore» — e a togliermelo
# e' toccato senza che nessuno dovesse accorgersene a mano.
def test_il_percorso_del_modello_e_coperto_dalla_cache():
    """Il cuore: ciò che il prodotto scarica dev'essere ciò che la CI conserva.

    Il confronto è per PREFISSO — la cache elenca cartelle, il prodotto usa una
    sottocartella — e su percorsi resi relativi alla home, perché il workflow
    scrive `~/...` e il prodotto restituisce un assoluto che dipende da chi
    esegue.
    """
    from verimem.local_grounding import DEFAULT_MODEL_DIR

    usato = DEFAULT_MODEL_DIR.expanduser()
    try:
        relativo = usato.relative_to(Path.home()).as_posix()
    except ValueError:  # pragma: no cover — modello fuori dalla home
        pytest.skip(f"il modello sta fuori dalla home ({usato}): il confronto "
                    f"con le voci `~/...` del workflow non è applicabile")

    coperti = [v.lstrip("~/") for v in _percorsi_in_cache()]
    assert any(relativo.startswith(c.rstrip("/")) for c in coperti), (
        f"il prodotto mette il modello in ~/{relativo} e la cache del workflow "
        f"copre {coperti}: nessuna voce lo contiene, quindi ogni job lo "
        f"riscarica e il salvataggio conserva una cartella vuota")
