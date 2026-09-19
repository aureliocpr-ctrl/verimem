"""T124 — il referto del CHECKPOINT sceglie che cosa dire con una SOGLIA.

La riga (`cli.py:5519`)::

    _passa = (float(_gs) >= float(_cut)) if isinstance(_cut, (int, float)) \\
             else (_adj.get("disposition") != "quarantined")

decide il ramo confrontando il punteggio con il taglio. Ma il moat non e'
l'unico a trattenere: L1 ferma le auto-affermazioni, e quando lo fa il moat puo'
essere PASSATO. Ne escono due bugie di segno opposto, e questo file le inchioda
entrambe:

  · col taglio NELLA ricevuta -> «grounded 95.5» su un fatto QUARANTINATO;
  · col taglio ASSENTE -> «the judge found no support» su una scrittura in cui
    il giudice ha lavorato e ha PASSATO: manda a riscrivere la FONTE mentre la
    cura e' aggiungere una prova a `verified_by`.

⚠️ SOLO IL CHECKPOINT. `verimem remember` — il verbo del FATTO — e' gia'
curato, misurato il 19/09 sulla stessa ricevuta costruita::

    quarantined id=f0f0f0f0f0f0 topic=t
      L1.15 — lacks test evidence
      il giudice era d'accordo — 95.5 sul taglio di 40: la fonte SOSTIENE il
      fatto, e' un controllo di dettaglio ad averlo fermato. Correggi quel
      dettaglio, non la frase

Nomina lo strato, dice che il giudice era d'accordo, e manda a correggere la
cosa giusta. Il difetto e' rimasto su `save`.

🔑 PERCHE' LA RICEVUTA E' COSTRUITA. Il caso da misurare e' «moat passed + L1
trattiene», e il verdetto del moat su quel caso DIPENDE DA CHI RISPONDE (T134,
19/09: sul runner il CE da' 85.15 e `passed`, in locale il cancello sale di
banda a un giudice LLM che da' 0.0 e `failed`). Un banco end-to-end sarebbe
verde o rosso a seconda della macchina — cioe' il difetto che abbiamo appena
classificato. Qui si misura la sola giuntura: che cosa la CLI DICE data una
ricevuta.

⚠️⚠️ E SI PATCHA `save_checkpoint`, NON `Memory`. Il primo tentativo sostituiva
`cli.Memory`: su `remember` funzionava, su `save` NO — quel comando passa da
`_continuity_memory()` + `save_checkpoint()`, il finto non era in mezzo, e il
comando ha fatto DUE SCRITTURE VERE nello store di casa (19/09, ids
`254a195c5ff3` e `a79ffb2669d7`; il contatore dell'arretrato e' salito di uno
fra i due giri). La cartella dati temporanea qui sotto e' una CINTURA: con la
cucitura giusta non si scrive, ma «credevo bastasse» e' esattamente come e'
andata la prima volta.

Ticket T124. Registro: riga nuova, classe «il bug e' la GIUNTURA (verdetto
calcolato e non letto)», la stessa di T56 e T77.
Decisione: nessuna.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

#: Fermata da L1 col moat PASSATO: punteggio alto, verdetto quarantena, e fra i
#: layer nessun `L4-grounding` — il moat non ha bocciato niente.
RICEVUTA = {
    "id": "f0f0f0f0f0f0",
    "stored": True,
    "status": "quarantined",
    "grounding_score": 95.5,
    "moat": "passed",
    "replaced": False,
    "advice": "",
    "warnings": [{"layer": "L1.15",
                  "reason": "Tested/verified claim 'testato' lacks test evidence",
                  "advice": "Add at least one of: pytest:<test>_PASS, ..."}],
    "store": "/tmp/prova/semantic/semantic.db",
    "store_decided_by": "HIPPO_DATA_DIR",
    "judged_by": "daemon",
}


def _referto(monkeypatch, tmp_path, ricevuta: dict) -> str:
    from verimem import cli as _cli

    #: CINTURA, e sono QUATTRO variabili, non tre. Le tre della cartella dati
    #: bastano a un SOTTOPROCESSO, dove l'ambiente e' pronto prima dell'import;
    #: qui il processo e' gia' avviato e `verimem` importato, e il percorso del
    #: giornale si fissa ALL'IMPORT (`event_jsonl_log.py:99`) — senza la quarta
    #: la telemetria di una prova finisce nel corpus di casa. E' la trappola
    #: T91, e me l'ha ricordata il lead dopo che avevo scritto «tre».
    for _v in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(_v, str(tmp_path))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(tmp_path / "events.jsonl"))

    #: ⚠️ ALLA FONTE, non su `cli`: `save_checkpoint` entra con un import
    #: LOCALE dentro la funzione (`cli.py:5453`), quindi l'attributo del modulo
    #: chiamante non esiste ancora quando lo si patcha — e il finto resta fuori.
    #: E' il secondo modo in cui questa sostituzione mi e' sfuggita oggi.
    monkeypatch.setattr(_cli, "_continuity_memory", lambda *a, **k: object())
    monkeypatch.setattr("verimem.continuity.save_checkpoint",
                        lambda *a, **k: dict(ricevuta))
    esito = CliRunner().invoke(
        _cli.app,
        ["save", "Il modulo e stato testato.", "--topic", "t",
         "--source", "Il modulo di pagamento e stato scritto il 3 marzo."])
    return esito.output


def test_CONTROLLO_il_finto_E_DAVVERO_in_mezzo(monkeypatch, tmp_path):
    """La prima cella, e senza di lei le altre non si possono leggere.

    Se il finto non intercetta, il comando SCRIVE per davvero e i due test qui
    sotto misurano una ricevuta prodotta dal giudice della macchina — cioe' un
    altro esperimento. E' gia' successo: due scritture vere nello store di casa.
    """
    out = _referto(monkeypatch, tmp_path, RICEVUTA)
    assert "f0f0f0f0f0f0" in out, (
        "l'id della ricevuta COSTRUITA non compare nel referto: il finto non "
        f"e' in mezzo e questo banco sta misurando una scrittura vera.\n{out}")


def test_non_dice_grounded_su_un_fatto_QUARANTINATO(monkeypatch, tmp_path):
    """Primo verso: col taglio nella ricevuta, il punteggio vince sul verdetto."""
    ric = dict(RICEVUTA,
               adjudication={"threshold": 40.0, "disposition": "quarantined"})
    out = _referto(monkeypatch, tmp_path, ric)
    assert "grounded 95.5" not in out, (
        "la CLI annuncia «grounded 95.5» su un fatto QUARANTINATO: chi legge "
        f"crede che sia entrato. Il verdetto c'e' e non viene letto.\n{out}")


def test_non_accusa_il_giudice_quando_il_moat_e_PASSATO(monkeypatch, tmp_path):
    """Secondo verso, opposto: senza il taglio, la colpa va al giudice sbagliato."""
    ric = dict(RICEVUTA, adjudication={"disposition": "quarantined"})
    out = _referto(monkeypatch, tmp_path, ric)
    assert "the judge found no support" not in out, (
        "la CLI accusa il giudice su una scrittura il cui moat e' PASSATO: "
        f"manda a riscrivere la FONTE mentre a fermare e' stato L1.\n{out}")


def test_CONTROLLO_POSITIVO_un_moat_BOCCIATO_accusa_ancora_il_giudice(
        monkeypatch, tmp_path):
    """Verde PRIMA e DOPO la cura: non si spegne il messaggio del caso vero.

    Qui il moat ha davvero bocciato (`L4-grounding` fra i layer, punteggio
    sotto il taglio): il referto DEVE continuare a dirlo.
    """
    ric = dict(
        RICEVUTA, grounding_score=3.8, moat="failed",
        adjudication={"threshold": 40.0, "disposition": "quarantined"},
        warnings=[{"layer": "L4-grounding",
                   "reason": "the judge found no support for this claim",
                   "advice": ""}])
    out = _referto(monkeypatch, tmp_path, ric)
    assert "3.8" in out, (
        "il referto non porta piu' il punteggio del caso bocciato: una cura "
        f"che spegne questo messaggio e' peggiore del difetto.\n{out}")
