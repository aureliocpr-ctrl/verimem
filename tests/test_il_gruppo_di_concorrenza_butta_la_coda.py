"""Il gruppo di concorrenza per REF fa cadere i run IN CODA, e cancel-in-progress
non li protegge.

`cancel-in-progress: false` protegge il run **che gira**. Un run **pendente** nello
stesso gruppo viene invece **sostituito** dal piu' recente: e' comportamento
documentato di GitHub, non un difetto dell'espressione.

=== MISURATO il 2026-08-12 su origin/main ===
Tre run di `ci` cancellati nella stessa giornata, tutti con la stessa firma::

    15:30  0f496502  cancelled  vita  8,2 min  job partiti 0/0
    16:52  a0fbe104  cancelled  vita 10,8 min  job partiti 0/0
    17:03  a184694b  cancelled  vita  4,2 min  job partiti 0/0

**Zero job partiti** su tutti e tre ⇒ erano in coda, non in esecuzione. E il primo
si e' concluso **+1 secondo** dopo il push successivo: e' la sostituzione, non una
mano umana.

I run che sopravvivono durano **45-46 minuti** (il tetto e' windows), quindi
qualunque push dentro quella finestra mette in coda — e la coda viene buttata dal
push dopo. **Oggi tre verdetti persi su sei push.**

=== LA CURA E IL SUO PREZZO ===
Gruppo **per COMMIT** sui push (ogni sha ha il suo gruppo, non c'e' niente da
sostituire) e **per ref** sulle pull request, dove cancellare il superato resta
giusto.

⚠️ **Toglie il tetto naturale** al numero di run contemporanei. Misurato prima di
applicarla: **11 run in due giorni, al massimo 2 contemporanei, ~0,2 run/ora** — il
tetto di concorrenza non e' in vista con questo traffico. Se un giorno si pushasse
otto volte in un'ora si avrebbero otto run per sei gambe, e allora questa riga va
ridiscussa.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

CI = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


@pytest.fixture
def concorrenza() -> dict:
    """Il blocco `concurrency:` **parsato**, non il testo.

    ⚠️ La prima versione di questo banco leggeva le RIGHE e cercava la prima
    che contenesse `cancel-in-progress:`. Trovava il COMMENTO che spiega la
    cura — che quella chiave la nomina — invece della chiave vera, e diventava
    rosso su un file corretto. Il difetto era nel misuratore, e si vedeva solo
    perche' e' diventato rosso dove non doveva.
    🔑 Leggere lo YAML parsato toglie la classe: e' anche il livello a cui
    GitHub legge il file, quindi il banco misura dove il prodotto misura.
    """
    import yaml
    return yaml.safe_load(CI.read_text(encoding="utf-8"))["concurrency"]


class TestIlGruppoNonButtaLaCoda:

    def test_il_blocco_esiste(self, concorrenza):
        """CONTROLLO POSITIVO: se qualcuno togliesse `concurrency:`, i test
        sotto fallirebbero con un KeyError invece di passare a vuoto."""
        assert "group" in concorrenza
        assert "cancel-in-progress" in concorrenza

    def test_il_gruppo_dipende_dal_COMMIT_non_solo_dal_ref(self, concorrenza):
        """IL ROSSO: con `group: ci-${{ github.ref }}` ogni push finisce nello
        stesso gruppo, quindi il pendente viene sostituito. Il gruppo deve
        distinguere i commit."""
        assert "github.sha" in concorrenza["group"], (
            "il gruppo non distingue i commit: un run in coda viene sostituito "
            f"dal push successivo — group = {concorrenza['group']}"
        )

    def test_le_pull_request_continuano_a_cancellare(self, concorrenza):
        """L'altra meta': sulle PR cancellare il superato e' giusto, e non
        deve essere stato buttato via insieme al difetto."""
        assert "pull_request" in concorrenza["group"], (
            "la distinzione fra push e pull request e' sparita dal gruppo: "
            "sulle PR il run superato non serve a nessuno e va cancellato"
        )

    def test_cancel_in_progress_resta_condizionale(self, concorrenza):
        """Se qualcuno lo rimettesse a `true` fisso, i push tornerebbero a
        cancellarsi fra loro — il difetto curato il 10/08."""
        valore = str(concorrenza["cancel-in-progress"])
        assert re.search(r"\$\{\{.*\}\}", valore), (
            f"cancel-in-progress non e' piu' condizionale: {valore}"
        )
