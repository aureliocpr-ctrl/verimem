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
    # ⚠️ E NON BASTA IL COMMIT: serve anche il RAMO. Fessura trovata da ws8 il
    # 2026-08-15 e misurata qui su entrambe le popolazioni — `ci` gira anche
    # sui `pull_request`, quindi un commit di un ramo di lavoro ha un run col
    # suo SHA::
    #
    #     44d47c6f (ramo ws3/gate-precision)  senza filtro=failure  con=(nulla)
    #     ae210e47 dcc41bc8 0e158cbb 6747ad54 (main)  identici in entrambi
    #
    # ⇒ Senza il filtro, un run VERDE su un ramo mai integrato aprirebbe il
    # cancello. Col filtro, i quattro commit di main danno lo stesso esito di
    # prima: la cura chiude la fessura e non il caso buono.
    assert "head_branch" in testo, (
        "il cancello non chiede se lo SHA sta su MAIN: `ci` gira anche sui "
        "pull request, quindi un commit di un ramo di lavoro ha un suo run — "
        "e se fosse verde si pubblicherebbe codice mai integrato. "
        "Misurato: senza il filtro, 44d47c6f (ramo ws3/gate-precision) "
        "restituisce un run; con il filtro, nessuno")


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


def test_anche_l_ARTEFATTO_NON_PRESIDIATO_viene_nominato_prima_di_partire(wf):
    """⚠️⚠️ GLI ARTEFATTI SONO DUE, E IL PASSO SOPRA NE GUARDA UNO.

    Il fatto che mancava, portato da ws8 il 2026-08-15 e riverificato leggendo
    il file: `pypa/gh-action-pypi-publish` senza `with:` carica `dist/` INTERO.
    Le uniche righe non-commento che nominano `dist/` sono `twine check dist/*`
    (solo i metadata) e `ls dist/*.whl` — **il .tar.gz parte senza guardia**::

        controlla_registro  WHEEL   EXIT=0   pulito          <- presidiato
        controlla_registro  SDIST   EXIT=1   330 identificativi, tutti in tests/

    🔑 Il criterio con cui i controlli furono accesi sul solo wheel era «chi
    INSTALLA», ed era sbagliato: **l'sdist non ha bisogno di essere installato,
    basta che qualcuno lo APRA**, e su PyPI sta in «Download files».

    ⛔ ⇒ Il percorso non verifica cio' che spedisce, e questo non e' un limite
    che accompagna la promessa: la SOSPENDE. Il minimo che questo file puo'
    pretendere e' che **il numero venga detto nel momento in cui si pubblica**,
    invece di vivere in una conversazione.
    """
    passi = wf["jobs"]["build-and-publish"]["steps"]
    testo = [str(s.get("run", "")) for s in passi]
    guarda_sdist = [i for i, t in enumerate(testo)
                    if "tar.gz" in t and "controlla_registro" in t]
    assert guarda_sdist, (
        "nessun passo guarda l'sdist prima della pubblicazione: il controllo "
        "sul wheel non copre l'altro artefatto, e `dist/` viene caricato "
        "intero. Chi legge questo workflow conclude che l'artefatto sia "
        "verificato, e gli artefatti sono due")
    righe = [f"{s.get('name', '')} {s.get('uses', '')}" for s in passi]
    i_pub = next(i for i, n in enumerate(righe) if "pypi-publish" in n.lower())
    assert guarda_sdist[0] < i_pub, (
        f"l'sdist viene guardato al passo {guarda_sdist[0]}, dopo la "
        f"pubblicazione al passo {i_pub}: guarderebbe una cosa gia' spedita")
    # ⚖️ E DEVE RESTARE UN AVVISO finche' nessuno ha deciso: un avviso puo'
    # stare da solo, un veto no. Togliere l'sdist da PyPI e' una scelta di
    # DISTRIBUZIONE (senza sdist non si compila da sorgente, e Debian,
    # conda-forge e Nix lo pretendono) e non la si prende dentro un file di CI.
    assert "::warning::" in testo[guarda_sdist[0]], (
        "il passo sull'sdist non avvisa: o non dice niente, o e' diventato un "
        "veto. Se il veto e' stato acceso DI PROPOSITO, cambia questa riga e "
        "scrivi nel banco CHI ha deciso e quando — la domanda aperta e' "
        "«il sorgente non esce finche' e' sporco, o esce sporco perche' serve "
        "a chi impacchetta?» e la risposta non sta in un workflow")


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
