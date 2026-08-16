"""Un check verde chiamato «security» deve dire se è un VERDETTO o un REFERTO.

═══ IL DIFETTO, misurato il 2026-08-16 ═══

`security.yml` ha cinque job e **tre finiscono in ``|| true``**: qualunque cosa
trovino, il job resta verde. È una scelta legittima — le regole S di ruff e
bandit hanno molti falsi positivi, e un veto li renderebbe rumore — ma **due dei
tre non lo dicevano nel nome del JOB**::

    bandit (low+low report)          ->  `|| true`   dice «report»      ✅
    ruff (security rules)            ->  `|| true`   NON lo diceva      🔴
    safety check                     ->  `|| true`   NON lo diceva      🔴
    pip-audit (HIGH/CRITICAL gate)   ->  nessun `|| true`, e' un GATE   ✅
    CodeQL (Python, custom config)   ->  analisi                        —

⇒ Sei run su sei verdi, tutti e cinque i job verdi ogni volta. **Chi legge la
lista dei check vede cinque verdi sotto un workflow chiamato «security» e non
ha modo di sapere che tre sono referti.**

🔑 **Nella lista dei check si leggono i nomi dei JOB, non dei passi.** Il passo
di ruff diceva già «report-only» nel proprio nome, e non serviva a niente: quel
testo non arriva dove qualcuno guarda.

═══ PERCHÉ UN BANCO E NON SOLO UNA RINOMINA ═══

La rinomina è di due righe e regge finché nessuno aggiunge un sesto job. Questo
banco lega le due cose che devono restare insieme — **il ``|| true`` e il
marchio nel nome** — così che aggiungere un report-only muto diventi rosso
invece che invisibile.

⚠️ LIMITE DICHIARATO: questo banco legge il TESTO del workflow, non l'esito sul
runner. Prova che il verde è *etichettato*, non che sia *giusto*. È legittimo
perché l'oggetto misurato è proprio il testo — l'etichetta è ciò che il lettore
vede — ma non sostituisce una misura sull'effetto.

📌 Sul ramo `main` non c'è nessuna protezione (`gh api … /protection` → «Branch
not protected»), quindi nessuno di questi check è obbligatorio: il loro valore è
interamente informativo, il che rende il nome ancora più importante.
"""
from __future__ import annotations

from pathlib import Path

import pytest

SECURITY = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "security.yml"

#: Il marchio che rende onesto un verde non vincolante. Basta la radice:
#: «report-only», «report», «solo referto» passano tutti.
_MARCHIO = "report"


@pytest.fixture()
def wf() -> dict:
    import yaml
    return yaml.safe_load(SECURITY.read_text(encoding="utf-8"))


def test_il_workflow_di_sicurezza_esiste_ancora(wf):
    """CONTROLLO POSITIVO: se il file sparisse, il test sotto passerebbe a
    vuoto invece di fallire."""
    assert wf.get("jobs"), f"nessun job in {SECURITY.name}"


def test_ogni_job_che_NON_PUO_FALLIRE_lo_dice_nel_proprio_nome(wf):
    """IL CUORE: `|| true` e il marchio nel nome viaggiano insieme.

    Un job che non può fallire è un referto. Se il suo nome non lo dice, il
    verde nella lista dei check si legge come un verdetto — ed è il difetto
    che curiamo da giorni sotto un altro nome: *una superficie che promette
    più di quanto misura*.
    """
    muti = []
    for nome_job, job in wf["jobs"].items():
        comandi = " ".join(str(p.get("run", "")) for p in job.get("steps", []))
        if "|| true" not in comandi:
            continue
        etichetta = str(job.get("name") or nome_job)
        if _MARCHIO not in etichetta.lower():
            muti.append(f"{nome_job} (name={etichetta!r})")
    assert not muti, (
        "questi job finiscono in `|| true` — qualunque cosa trovino restano "
        "verdi — e il loro NOME non lo dichiara:\n  " + "\n  ".join(muti)
        + "\n\nNella lista dei check si leggono i nomi dei JOB, non dei passi: "
          "un verde senza marchio si legge come «e' pulito» invece che come "
          "«ho guardato». Aggiungi `report-only` al nome, oppure togli il "
          "`|| true` e assumiti il veto.")


def test_ALMENO_UN_JOB_puo_davvero_fallire(wf):
    """⚖️ L'ALTRA META', e senza di essa la prima passerebbe anche su un
    workflow interamente decorativo.

    Se ogni job fosse un referto ben etichettato, questo file sarebbe onesto e
    inutile: «security» non fermerebbe mai niente. Qui si pretende che almeno
    uno sia un cancello vero — oggi `pip-audit (HIGH/CRITICAL gate)`.
    """
    cancelli = [
        nome_job for nome_job, job in wf["jobs"].items()
        if any(str(p.get("run", "")) for p in job.get("steps", []))
        and "|| true" not in " ".join(
            str(p.get("run", "")) for p in job.get("steps", []))
    ]
    assert cancelli, (
        "NESSUN job di `security` puo' fallire: sono tutti referti. Un "
        "workflow che non ferma mai niente e' un'etichetta, non un presidio — "
        "e il suo verde non significa nulla per nessuno")
