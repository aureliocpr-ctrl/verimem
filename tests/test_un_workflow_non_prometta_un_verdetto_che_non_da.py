"""Un workflow che PROMETTE «ogni commit merita un verdetto» deve mantenerlo.

Il 10/08 una cura è stata applicata a `ci.yml` **e** a `security.yml`: sulle
pull request cancellare il run superato va bene, sui push su main no. Il 12/08
si è scoperto che non bastava — `cancel-in-progress: false` protegge il run che
GIRA, ma un run **in coda** viene sostituito dal push successivo — e la cura
vera è stata il gruppo per commit::

    group: ci-${{ github.event_name == 'pull_request' && github.ref || github.sha }}

⚠️ **Quella seconda cura è entrata in un file solo.** `security.yml` ha ereditato
il commento del 10/08 — quindici righe, parola per parola le stesse, compresa la
frase «ogni commit merita un verdetto» — ma non la riga che lo mantiene.

Misurato il 15/08 su cento run (13/08 13:28 → 15/08 11:16)::

    ci          2 cancellati su 50
    security   21 cancellati su 50      ← tutti `main` + `push`
    solo il 15/08:   ci 0 su 18   ·   security 7 su 18

═══ PERCHÉ IL CRITERIO NON È «I DUE FILE SIANO UGUALI» ═══

Perché non è detto che la cura vada applicata. Il commento di `ci.yml` dichiara
**il proprio prezzo** e il criterio con cui va ridiscusso: si contano i job in
coda di tutti i run in volo, e «sotto il tetto dei venti il parallelismo è
gratis; sopra, ogni push in più ritarda i verdetti di tutti». Applicando quel
criterio il 15/08 alle 13:24 — 11 run in volo, 20 job in esecuzione, **19 in
coda** — il tetto era saturo: quel giorno la risposta era di non aggiungerne.

⇒ Il difetto da vietare non è «i due file divergono», che è una scelta legittima
di chi ha il perimetro della CI. È che un file **prometta in un commento ciò che
la sua configurazione non fa**. Chi legge quel commento conclude che i suoi
commit hanno un verdetto di sicurezza, e per ventuno run su cinquanta non era
vero.

Restano verdi entrambe le uscite, e la scelta è di chi ha quel perimetro:

    · aggiungere il gruppo per commit anche a `security.yml`;
    · togliere da `security.yml` la promessa che non mantiene.

🔑 È la stessa forma del presidio sulla cache (f4fa6194): vieta il difetto,
non impone la soluzione.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parents[1]
_WORKFLOW = _RADICE / ".github" / "workflows"

# La promessa, nella forma in cui è scritta nei due file. Si cerca la frase, non
# il commento intero: un domani può essere riformulata intorno, ma se questa
# sparisce sparisce anche la promessa, ed è giusto che il presidio taccia.
_PROMESSA = re.compile(r"ogni commit merita un verdetto", re.I)


def _blocco_concurrency(testo: str) -> str:
    """Il blocco `concurrency:` di un workflow, commenti compresi."""
    m = re.search(r"^concurrency:\n((?:[ \t]+.*\n|\n)*)", testo, re.M)
    return m.group(1) if m else ""


def _promette(testo: str) -> bool:
    return bool(_PROMESSA.search(_blocco_concurrency(testo)))


def _mantiene(testo: str) -> bool:
    """La promessa è mantenuta solo se il GRUPPO varia col commit sui push.

    ⚠️ Non basta `cancel-in-progress` condizionato: è la cura del 10/08, e il
    12/08 ha misurato che protegge il run in corso ma non quello in coda — tre
    verdetti persi su sei push con quella riga già in vigore. Ciò che separa i
    push l'uno dall'altro è il `github.sha` dentro il nome del gruppo.
    """
    gruppo = re.search(r"^\s*group:\s*(.+)$", _blocco_concurrency(testo), re.M)
    return bool(gruppo) and "github.sha" in gruppo.group(1)


def _workflow_che_promettono() -> list[Path]:
    return sorted(f for f in _WORKFLOW.glob("*.yml")
                  if _promette(f.read_text(encoding="utf-8", errors="ignore")))


def test_QUALCUNO_FA_ANCORA_QUELLA_PROMESSA():
    """⚠️ Prima di tutto: senza questo, il test sotto è verde su lista vuota.

    Se la frase venisse riformulata in entrambi i file, il presidio smetterebbe
    di misurare **restando verde** — il modo tipico in cui un presidio su un
    testo si disarma senza che nessuno se ne accorga.
    """
    assert _workflow_che_promettono(), (
        "nessun workflow contiene più la promessa «ogni commit merita un "
        "verdetto»: o è stata riformulata e questo presidio va aggiornato, o è "
        "stata tolta ovunque — in entrambi i casi qui non si misura più nulla")


def test_IL_RICONOSCITORE_separa_chi_mantiene_da_chi_no():
    """Il banco del misuratore, sulle DUE popolazioni.

    Un criterio provato solo su chi sbaglia sembra sempre ottimo: `ci.yml`
    promette **e mantiene**, `security.yml` promette e **non** mantiene. Se il
    riconoscitore li dichiarasse uguali — in un verso o nell'altro — il test
    sotto misurerebbe se stesso invece dei workflow.
    """
    ci = (_WORKFLOW / "ci.yml").read_text(encoding="utf-8")
    sec = (_WORKFLOW / "security.yml").read_text(encoding="utf-8")
    assert _promette(ci) and _promette(sec), "entrambi devono fare la promessa"
    assert _mantiene(ci), (
        "ci.yml ha il gruppo per commit dal 12/08: se il riconoscitore non lo "
        "vede, dichiarerebbe rotto un file sano")
    assert not _mantiene(sec), (
        "security.yml non aveva il gruppo per commit: se ora ce l'ha, la cura è "
        "arrivata — togli questo assert e l'xfail sotto")


@pytest.mark.xfail(strict=True, reason=(
    "security.yml ha il commento del 10/08 parola per parola, compresa la frase "
    "«ogni commit merita un verdetto», ma non ha ricevuto la cura del 12/08: "
    "21 run cancellati su 50 fra il 13 e il 15/08, tutti su push a main"))
def test_ogni_workflow_che_promette_un_verdetto_lo_mantiene():
    """Il cuore: la promessa scritta nel file e la riga che la esegue."""
    infedeli = [f.name for f in _workflow_che_promettono()
                if not _mantiene(f.read_text(encoding="utf-8", errors="ignore"))]
    assert not infedeli, (
        f"{infedeli} promettono che ogni commit su main abbia un verdetto, ma "
        f"il loro gruppo di concorrenza non contiene github.sha: due push "
        f"ravvicinati finiscono nello stesso gruppo e il secondo butta il "
        f"primo dalla coda. O si aggiunge il gruppo per commit, o si toglie la "
        f"promessa — ma il file non può dire una cosa e farne un'altra")
