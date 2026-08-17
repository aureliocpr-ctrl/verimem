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

⚠️ `xfail(strict=True)`: il difetto c'era. Quando è stato curato questo test è
passato, l'xpass ha reso la suite rossa e ha chiesto di togliere il marcatore —
così il difetto fa rumore **quando smette di esistere** invece di restare un
marcatore che nessuno rilegge. È successo il 15/08, e a toglierlo è stato chi
ha curato il workflow, non chi aveva scritto il presidio.

═══ ⚠️ LIMITE DICHIARATO — e un limite dichiarato è un DEBITO ═══

Questo banco è **statico**: confronta due NOMI, quello che il prodotto userà e
quello che la CI elenca. Non tocca il disco — nessuna chiamata al filesystem in
questo file — e resta verde anche dove il modello non è mai stato scaricato:
verificato, in locale `DEFAULT_MODEL_DIR` non esiste e il test passa.

⇒ **Verde qui NON significa «il modello arriva in CI».** Significa «se arriva,
la cache lo conserva». Il difetto trovato lo stesso giorno da ws8 — il passo di
warmup dura 12 secondi contro 2264 MB da scaricare, non scarica, ed esce
`ready` e `success` perché lo step è *best-effort* — **questo banco non lo
vedrebbe mai**, e nessuna sua evoluzione statica potrebbe. Quella domanda
chiede un presidio a runtime, che dopo il warmup verifichi che il modello ci
sia. Non è questo.

L'ipotesi è di ws1 («può essere verde senza provare niente»): la forma esatta
non regge, perché non si confrontano contenuti — ma il livello che indicava è
quello giusto.

📌 Che sia comunque **collegato** è misurato, col criterio che vale per ogni
presidio di casa: togliendo `~/.cache/verimem` dal workflow diventa **rosso**
(8 percorsi letti → 6). Un presidio acceso su una domanda piccola resta acceso;
va detto **quanto** la domanda è piccola.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parents[1]
_CI = _RADICE / ".github" / "workflows" / "ci.yml"


def _righe_dei_blocchi_path() -> list[str]:
    """OGNI riga dentro un blocco `path: |`, così come la riceve `actions/cache`.

    ⚠️⚠️ PRIMA VERSIONE SBAGLIATA, e l'errore vale più della cura. Usciva dal
    blocco alla prima riga che non somigliava a un percorso::

            else:
                dentro = False       # ← si fermava qui

    Ma in uno scalare letterale YAML il blocco finisce dove **cala
    l'indentazione**, non dove una riga smette di piacermi. Con undici righe di
    commento in mezzo al blocco, `~/.cache/verimem` stava DOPO quelle righe e
    questa funzione non lo leggeva mai: il percorso c'era dalle 13:15 e il
    presidio restava rosso. Il verdetto era comunque giusto — il difetto
    esisteva — ma **per una ragione diversa da quella che il messaggio diceva**,
    e un misuratore che azzecca la risposta sbagliando il conto la sbaglierà la
    prossima volta.

    🔑 Diagnosi di ws7, che ha curato il workflow: «the guard could not see it
    either». ⇒ Adesso si legge per INDENTAZIONE, come fa YAML, e si restituisce
    **tutto** ciò che il runner riceve — prosa compresa, perché è quello il
    punto: `actions/cache` la prende come pattern di glob.
    """
    righe: list[str] = []
    indent_blocco: int | None = None
    for riga in _CI.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\s*)path:\s*\|\s*$", riga)
        if m:
            indent_blocco = len(m.group(1))
            continue
        if indent_blocco is None:
            continue
        if not riga.strip():          # una riga vuota non chiude uno scalare
            continue
        if len(riga) - len(riga.lstrip()) <= indent_blocco:
            indent_blocco = None      # l'indentazione è calata: blocco finito
            continue
        righe.append(riga.strip())
    return righe


def _percorsi_in_cache() -> list[str]:
    """Le voci dei blocchi `path:` che sono davvero percorsi.

    ⚠️ Si leggono TUTTI i blocchi: il workflow ne ha più d'uno (il job dei test
    e quello dell'installazione dal wheel), e curarne uno solo lascia l'altro
    a riscaricare — un difetto che si vede solo su una gamba.
    """
    return [r for r in _righe_dei_blocchi_path()
            if re.fullmatch(r"(~[^\s#]+|\$\{\{[^}]+\}\}[^\s#]*)", r)]


def test_NESSUNA_RIGA_DI_PROSA_DENTRO_UN_BLOCCO_PATH():
    """Blinda la cura di ws7: in `path: |` un `#` NON apre un commento.

    In uno scalare letterale YAML ogni riga è testo, e `actions/cache` la
    riceve come pattern di glob. Il 15/08 undici righe di prosa italiana sono
    finite lì dentro — spiegavano, correttamente, perché quel percorso serviva.

    🔑 **Niente lo avrebbe mostrato.** Il file si legge come se fossero
    commenti, e lo sono ovunque tranne lì: non c'è errore di sintassi, il
    workflow gira, la cache semplicemente non trova nulla. È il caso esatto in
    cui l'occhio non basta e serve un presidio — e la prossima persona che
    vorrà spiegare un percorso avrà la stessa idea, perché è l'idea giusta nel
    posto sbagliato.
    """
    intrusi = [r for r in _righe_dei_blocchi_path() if r.startswith("#")]
    assert not intrusi, (
        f"{len(intrusi)} righe di commento stanno DENTRO un blocco `path: |` di "
        f"{_CI.name}: {intrusi[:3]}… In uno scalare letterale YAML il `#` non è "
        f"un commento ma testo, e actions/cache le riceve come pattern di "
        f"percorso. Sposta il commento SOPRA la riga `path:`, dove `#` "
        f"significa quello che sembra")


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


# ═══ IL GEMELLO: il PERCORSO era coperto, il NOME no ═════════════════════════
# Il test qui sopra chiede che il posto dove il modello finisce sia conservato.
# Non chiede che il modello GIUSTO ci arrivi — e sono due domande diverse, come
# si è visto il 2026-08-17.
#
# `tests/conftest.py` pinna, PRIMA di qualunque import e di proposito, un
# modello DIVERSO da quello del prodotto:
#
#     server  intfloat/multilingual-e5-base                             768 dim
#     test    sentence-transformers/paraphrase-multilingual-MiniLM-L12  384 dim
#
# La separazione è sana: la suite asserisce su 384 e usa lo stub. Ma il workflow
# scaldava e metteva in cache SOLO il modello del server, e i test in-process
# non se ne accorgevano perché lo stub non carica nulla.
# ⇒ I sei test che lanciano un SOTTOPROCESSO (dove lo stub non arriva, e le tre
#   variabili offline sì) chiedevano un modello che nessuno aveva scaricato:
#   `LocalEntryNotFoundError: Cannot find the requested files in the disk cache`.
#   In locale invisibile, perché quel modello è in cache da mesi.
# 🔑 Stessa classe del test sopra — due liste in due file che devono restare
#   d'accordo e non si conoscono — su un attributo diverso.
#
# ⚠️ LIMITE, ed è un debito: questo banco è STATICO. Dice che il workflow NOMINA
# il modello che i test pinnano, non che il download riesca. Un `TEST-MODEL ...`
# fallito nel log resta invisibile qui.
def test_il_modello_che_i_test_pinnano_e_nominato_dal_workflow():
    conftest = (_RADICE / "tests" / "conftest.py").read_text(encoding="utf-8")
    m = re.search(r'HIPPO_EMBEDDING_MODEL"\s*,\s*"([^"]+)"', conftest)
    assert m, ("`conftest.py` non pinna più il modello con quella forma: "
               "aggiorna questo presidio invece di cancellarlo")
    pinnato = m.group(1)
    ci = _CI.read_text(encoding="utf-8")
    # Il nome corto basta: il workflow può nominarlo per intero o per famiglia.
    corto = pinnato.rsplit("/", 1)[-1].rsplit("-L12", 1)[0]
    assert corto in ci, (
        f"i test girano su «{pinnato}» e il workflow non lo nomina mai: chi "
        f"apre un sottoprocesso in CI chiede un modello che nessuno scarica, "
        f"e offline muore con LocalEntryNotFoundError")
