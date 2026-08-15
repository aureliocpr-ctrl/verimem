"""Un tag non deve poter pubblicare su PyPI da solo.

═══ IL DIFETTO, trovato da ws8 il 2026-08-15 ═══

`publish.yml` non aveva **né `needs`, né `if`, né `environment`**: il job che
carica su PyPI partiva direttamente dal trigger::

    on:
      push:
        tags: ["v*"]

⇒ **Un `git push origin v0.7.5` spediva il pacchetto al mondo in trenta
secondi**, senza che un solo test dovesse passare.

Il contesto in cui l'abbiamo scoperto è ciò che lo rende grave, non la forma:

    · Aurelio, quel giorno alle 14:00:  «NON È PRONTA»
    · `ci` su main: 19 run conclusi quel giorno, 19 failure, ZERO verdi
    · `pyproject` dichiarava 0.7.5, su PyPI c'era la 0.7.0

⇒ Un tag battuto in quel momento avrebbe pubblicato un pacchetto che **la
nostra stessa CI non ha mai approvato**, mentre il mandato diceva di non
rilasciare.

═══ 🔑 PERCHÉ IL CANCELLO È UN JOB E NON UNA RIGA ═══

`needs:` non attraversa i workflow: da `publish.yml` non si può dipendere da
`ci.yml`. Il cancello quindi si costruisce — un job che **chiede a GitHub com'è
andata `ci` sul commit del tag** — e il job di pubblicazione dipende da lui.
Nessuna configurazione fuori dal repository, nessun segreto, solo `gh` in
lettura.

⚖️ **E deve poter essere aperto**: `PUBLISH_ANYWAY=1` come variabile del
repository lo scavalca. Un cancello che non si può aprire viene *tolto*, e
allora non protegge più niente. La differenza che conta è che aprirlo diventa
un **gesto deliberato** invece dell'impostazione predefinita.

═══ ⚠️ IL LIMITE, dichiarato ═══

Questo banco legge il **testo del workflow**, non il comportamento del runner:
prova che il cancello *è dichiarato*, non che *funziona*. Il comando del gate è
stato provato a mano sul commit corrente (esito «nessun run» → fermo), ma la
prova vera arriva al primo tag. **Un presidio sulla forma non sostituisce una
misura sull'effetto** — lezione pagata lo stesso giorno su una cura inerte.
"""
from __future__ import annotations

from pathlib import Path

import pytest

PUBLISH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish.yml"


@pytest.fixture()
def wf() -> dict:
    import yaml
    return yaml.safe_load(PUBLISH.read_text(encoding="utf-8"))


def test_il_workflow_di_pubblicazione_esiste_ancora(wf):
    """CONTROLLO POSITIVO: se il file sparisse o cambiasse forma, i test sotto
    passerebbero a vuoto invece di fallire."""
    assert wf.get("jobs"), f"nessun job in {PUBLISH.name}"


def test_la_pubblicazione_NON_parte_dal_solo_tag(wf):
    """IL CUORE: il job che carica su PyPI deve dipendere da qualcosa."""
    pubblicanti = [
        (nome, d) for nome, d in wf["jobs"].items()
        if any("pypi-publish" in str(s.get("uses", "")).lower()
               or "twine upload" in str(s.get("run", "")).lower()
               for s in d.get("steps", []))
    ]
    assert pubblicanti, (
        "nessun job pubblica piu': se il caricamento su PyPI e' stato tolto "
        "questo banco va riletto, non cancellato")
    for nome, d in pubblicanti:
        assert d.get("needs"), (
            f"il job `{nome}` carica su PyPI e non dipende da nulla: un "
            f"`git push` di un tag lo fa partire da solo, con la CI in "
            f"qualunque stato")
        assert d.get("if"), (
            f"il job `{nome}` dipende da un altro job ma non ne guarda "
            f"l'ESITO: `needs` senza `if` fa partire la pubblicazione anche "
            f"quando il cancello ha detto di no")


def test_il_cancello_GUARDA_la_ci_e_non_qualcos_altro(wf):
    """⚠️ `needs` + `if` non bastano: contano su COSA sono.

    Un cancello che dipendesse da un job che non misura niente sarebbe
    verde per costruzione — la forma esatta del difetto che curiamo da due
    giorni (un presidio che c'e' e non guarda).
    """
    testo = PUBLISH.read_text(encoding="utf-8")
    assert "actions/runs" in testo and "conclusion" in testo, (
        "il cancello non interroga l'esito dei run della CI: senza quello "
        "e' un job che dice sempre di si'")
    assert "head_sha" in testo, (
        "il cancello non filtra per il COMMIT del tag: guarderebbe l'ultimo "
        "run qualunque, che puo' essere di un altro commit")


def test_cio_che_si_spedisce_viene_GUARDATO_prima_di_partire(wf):
    """⚠️ IL CANCELLO SULLA CI NON BASTA, e questo e' il pezzo che aggiunge.

    Il cancello chiede «la CI e' verde?» — la qualita' del CODICE. Non guarda
    **cosa c'e' dentro il pacchetto**: con la CI verde si aprirebbe e un
    artefatto sporco passerebbe. Misurato da ws2 il 2026-08-15 sugli artefatti
    ricostruiti da `0dc18f24`::

        controlla_registro  WHEEL   EXIT=0   pulito
        controlla_promesse  WHEEL   EXIT=0
        controlla_registro  SDIST   EXIT=1   321 identificativi in 129 file

    ⇒ **Solo il wheel**, ed e' la separazione che ha reso la scelta decidibile:
    il wheel e' cio' che l'utente installa ed e' gia' verde, quindi accenderlo
    costa zero; l'sdist e' un debito con un numero, e un blocco secco li'
    fermerebbe qualunque rilascio senza curare niente.
    📌 I due controlli sono di ws2 e stanno qui col suo assenso esplicito.
    """
    passi = wf["jobs"]["build-and-publish"]["steps"]
    testo = " ".join(str(s.get("run", "")) for s in passi)
    for script in ("controlla_registro", "controlla_promesse"):
        assert script in testo, (
            f"`{script}` non gira piu' prima della pubblicazione: il cancello "
            f"guarda la CI, non cosa c'e' dentro il pacchetto. Senza questo, "
            f"un artefatto sporco parte con la CI verde")
    # ⚠️ `name` E `uses` insieme, non l'uno o l'altro: lo step di pubblicazione
    # ha un `name` in italiano e la stringa che lo identifica sta in `uses`
    # (`pypa/gh-action-pypi-publish`). La prima versione di questa riga guardava
    # `name or uses` e non trovava nulla — il test falliva sul workflow CORRETTO,
    # cioe' era un falso allarme, la forma di presidio che poi viene spento.
    righe = [f"{s.get('name', '')} {s.get('uses', '')}" for s in passi]
    i_ctrl = next(i for i, n in enumerate(righe) if "identificativi" in n)
    i_pub = next(i for i, n in enumerate(righe) if "pypi-publish" in n.lower())
    assert i_ctrl < i_pub, (
        f"il controllo sull'artefatto (passo {i_ctrl}) viene DOPO la "
        f"pubblicazione (passo {i_pub}): guarderebbe una cosa gia' spedita")


def test_il_cancello_SI_PUO_APRIRE_di_proposito(wf):
    """⚖️ L'altra meta', e non e' un vezzo: un cancello che non si puo' aprire
    viene TOLTO, e allora non protegge piu' niente.

    Qui si pretende che esista una via d'uscita esplicita — cosi' chi ha una
    ragione per pubblicare comunque non debba cancellare il presidio per
    farlo.
    """
    testo = PUBLISH.read_text(encoding="utf-8")
    assert "PUBLISH_ANYWAY" in testo, (
        "non c'e' modo di scavalcare il cancello di proposito: la prima volta "
        "che qualcuno avra' una ragione legittima per pubblicare con la CI "
        "rossa, toglera' il cancello invece di aprirlo")
