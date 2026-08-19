"""Il presidio sulla pubblicazione copre UN FILE. La cartella ne può contenere altri.

═══ IL DIFETTO, trovato da ws8 il 2026-08-18 ═══

I test di `test_la_pubblicazione_ha_un_cancello.py` — otto, e ognuno pretende
qualcosa di sensato — aprono tutti lo stesso file, per **path costante**::

    PUBLISH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish.yml"

⇒ Un secondo workflow che carichi su PyPI **non li rompe: li aggira.** Nasce
senza `needs`, senza `if`, senza i controlli sull'artefatto, e tutta la suite
resta verde — perché nessuno guarda dove non è stato mandato a guardare.

🔑 È la classe che il registro chiama *«un marcatore di provenienza non può
marcare i produttori che non lo conoscono»*: un presidio ancorato a un nome
non vede chi quel nome non ce l'ha. La cura non è aggiungere un altro nome —
è **enumerare**, e leggere l'ASSENZA come un valore.

═══ ⚠️ PERCHÉ COL PARSER E NON COL TESTO ═══

Cercare la stringa `gh-action-pypi-publish` nel testo sbaglia in **entrambe**
le direzioni, ed è il difetto che questo stesso banco rimprovera altrove:

    falso POSITIVO   un commento che nomina l'action senza usarla
    falso NEGATIVO   `twine upload` / `uv publish` pubblicano e non la nominano

⇒ Un file «pubblica» se **esegue** un passo che carica, non se ne parla.

═══ ⚖️ IL LIMITE, dichiarato ═══

Questo banco enumera i workflow **di questo repository**. Non vede: una
pubblicazione fatta a mano da un portatile, un `workflow_call` che vive in un
altro repo, né un file disattivato (`.yml.disabled`) che qualcuno riattiva.
**Copre la porta che si apre da sola, non tutte le porte.**
"""
from __future__ import annotations

from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"

# Il file che `test_la_pubblicazione_ha_un_cancello.py` presidia, per nome.
# Se l'enumerazione trovasse qualcos'altro, quel banco starebbe guardando
# altrove.
PRESIDIATO = "publish.yml"

# Come si carica su PyPI. `uses:` per le action, `run:` per i comandi.
_AZIONI = ("gh-action-pypi-publish",)
_COMANDI = ("twine upload", "uv publish", "flit publish", "poetry publish")


def workflow_che_pubblicano(cartella: Path) -> list[str]:
    """I nomi dei workflow che ESEGUONO un caricamento su un indice.

    Legge col parser: un `uses:` o un `run:` dentro uno step, mai il testo
    nudo — un commento che nomina l'action non pubblica niente.
    """
    import yaml

    trovati: list[str] = []
    for f in sorted(cartella.glob("*.y*ml")):
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception:  # un file illeggibile va segnalato, non saltato
            trovati.append(f"{f.name} (ILLEGGIBILE)")
            continue
        if not isinstance(doc, dict):
            continue
        for job in (doc.get("jobs") or {}).values():
            if not isinstance(job, dict):
                continue
            for step in job.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                uses = str(step.get("uses", "")).lower()
                run = str(step.get("run", "")).lower()
                if any(a in uses for a in _AZIONI) or any(c in run for c in _COMANDI):
                    trovati.append(f.name)
                    break
            else:
                continue
            break
    return trovati


def test_esiste_una_porta_e_una_sola():
    """IL CUORE: la cartella intera, non un file scelto in anticipo.

    Due esiti diversi, e nessuno dei due è «va bene»:

      0 file  -> il presidio dell'altro banco apre un path che non pubblica
                 più; passerebbe a vuoto
      2+ file -> ce n'è uno che il presidio non ha mai guardato
    """
    porte = workflow_che_pubblicano(WORKFLOWS)
    assert porte, (
        f"nessun workflow in {WORKFLOWS.name}/ carica su un indice: o la "
        f"pubblicazione è stata tolta — e allora i banchi sul cancello vanno "
        f"riletti, non cancellati — o il modo di caricare è cambiato e questo "
        f"banco non lo riconosce più. Riconosciuti: {_AZIONI + _COMANDI}")
    assert porte == [PRESIDIATO], (
        f"i workflow che pubblicano sono {porte}, il presidio ne guarda UNO "
        f"solo (`{PRESIDIATO}`, per path costante in "
        f"test_la_pubblicazione_ha_un_cancello.py). Ogni file in più è una "
        f"porta verso PyPI senza cancello, senza controlli sull'artefatto e "
        f"senza avviso — e la suite resterebbe verde")


def test_il_criterio_si_ACCENDE_davvero(tmp_path):
    """⚖️ LA META CHE CONTA: che il test sopra sia rosso quando deve.

    Un presidio che non si è mai visto fallire è indistinguibile da uno
    scollegato — lezione pagata in casa più volte. Qui si costruisce la
    cartella che vogliamo temere e si pretende che venga vista.
    """
    (tmp_path / "publish.yml").write_text(
        "jobs:\n  p:\n    steps:\n      - uses: pypa/gh-action-pypi-publish@v1\n",
        encoding="utf-8")
    (tmp_path / "zz-rilascio-veloce.yml").write_text(
        "jobs:\n  p:\n    steps:\n      - run: twine upload dist/*\n",
        encoding="utf-8")
    assert workflow_che_pubblicano(tmp_path) == [
        "publish.yml", "zz-rilascio-veloce.yml"], (
        "il criterio non vede un secondo workflow che pubblica: sarebbe un "
        "sensore scollegato, verde qualunque cosa accada")


def test_il_criterio_non_grida_su_un_COMMENTO(tmp_path):
    """L'altra popolazione, quella che di solito non si misura.

    Un avviso che si accende su chi nomina l'action senza usarla penalizza il
    file più DOCUMENTATO — e un presidio che grida sul codice sano viene
    spento. Le due celle insieme dicono che il criterio discrimina; una sola
    non lo direbbe.
    """
    (tmp_path / "ci.yml").write_text(
        "# nota: la pubblicazione usa pypa/gh-action-pypi-publish, vedi\n"
        "# publish.yml — qui NON si carica niente\n"
        "jobs:\n  test:\n    steps:\n      - run: pytest -q\n",
        encoding="utf-8")
    assert workflow_che_pubblicano(tmp_path) == [], (
        "un file che si limita a NOMINARE l'action risulta come se "
        "pubblicasse: il criterio legge il testo invece degli step")


def test_il_presidio_vecchio_e_ancorato_a_un_NOME(tmp_path):
    """📌 Perché questo file esiste, scritto in modo che regga da solo.

    Se un giorno l'altro banco imparasse a enumerare, questo test diventa
    rosso e va **cancellato**, non aggirato: vorrebbe dire che il difetto che
    documenta non c'è più.
    """
    altro = Path(__file__).with_name("test_la_pubblicazione_ha_un_cancello.py")
    testo = altro.read_text(encoding="utf-8")
    assert 'workflows" / "publish.yml"' in testo, (
        f"{altro.name} non punta più a un path costante: se ora enumera la "
        f"cartella, questo banco ha finito il suo lavoro e va tolto")
    assert ".glob(" not in testo and ".iterdir(" not in testo, (
        f"{altro.name} ha imparato a enumerare: rileggi questo file, "
        f"probabilmente è diventato ridondante")
