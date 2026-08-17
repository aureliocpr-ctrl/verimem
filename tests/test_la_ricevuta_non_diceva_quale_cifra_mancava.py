"""«quarantined id=f014eeafa03a topic=t» — e basta. Fermato, senza sapere perché.

IL DIFETTO, isolato da ws1 con la formulazione che lo rende curabile: *«non è un
gate severo — moat e L4.1 chiedono cose DIVERSE (la fonte sostiene il fatto? /
ogni cifra sta nella fonte?) e chi scrive MISURE li attiva entrambi. Cura più
piccola: dire QUALE cifra non ha trovato»*. Verificato da lui su 16 casi su 16.

MISURATO DALLA PORTA, prima di scrivere::

    il layer SA quale valore manca:   [(40.0, …)]
    l'SDK lo DICE:  reason «il claim afferma un valore che la fonte non
                    contiene: 40 pezzo», matched_text '40 pezzo', più un advice
    la CLI stampava: «quarantined id=f014eeafa03a topic=t»    ← e nient'altro

⇒ Il motivo esisteva già nel verdetto e non arrivava alla porta dell'umano.
Nulla da inventare: si stampa.

🔑 E LA RAGIONE PER CUI IL CASO SFUGGIVA sta nel come la ricevuta decideva cosa
dire: **guardava solo il punteggio**. Con moat 95,5 e taglio 40 il ramo «bocciato
dal giudice» non scatta — ma il fatto è quarantinato da ``L4.1``, che la ricevuta
non guardava affatto. Decidere in base al solo punteggio nasconde proprio il caso
in cui le due voci si contraddicono, cioè quello in cui l'utente ha più bisogno
di sapere chi ha parlato.

⚠️ UNDICESIMA VOLTA CHE IL BANCO MISURA SÉ STESSO, e vale la pena scriverlo: la
mia prima misura cercava ``getattr(r, "warnings")`` su un valore che è un
**dict**, e concludeva che il prodotto non dicesse niente. Il prodotto lo diceva.
Se avessi «curato» quella conclusione avrei aggiunto un messaggio che c'era già.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

from tests._real_model import real_ce_cached

# Questo banco interroga il MOAT: senza il giudice locale non c'e' un verdetto
# da leggere, e la ricevuta non puo' dire quale cifra manca perche' nessuno l'ha
# cercata. La disciplina e' gia' dichiarata in tests/_real_model.py — «CE-moat
# tests must skip there», perche' la CI scalda con `--no-gate` e il modello del
# giudice non viene scaricato.
#
# ⚠️ QUESTO NON CURA NIENTE e non va letto come un miglioramento: i sei test di
# questo file risultavano FAILED in CI e ora risulteranno SKIPPED. E' una
# RICLASSIFICAZIONE — da «il banco ha misurato e il prodotto ha sbagliato» a
# «il banco non ha potuto misurare» — e la seconda e' l'unica delle due vera.
# Un rosso che nessuno puo' curare smette di essere letto: dopo qualche giorno
# non distingue piu' un guasto nuovo dal rumore di fondo.
# Misurato con un A/B sulla stessa macchina, stesso test, stesso commit:
#   giudice presente -> EXIT=0 · giudice assente -> EXIT=1 FAILED
# Se un giorno la CI scaldera' senza `--no-gate`, questi test ripartiranno da
# soli: la guardia interroga la disponibilita' del gate, non un interruttore.
#
# 📌 2026-08-13 16:23 — E' SUCCESSO, e la previsione qui sopra ha retto: il
# commit `8669b5e3` ha tolto `--no-gate` dal warmup e messo `~/.engram/models`
# in cache. La riga «la CI scalda con --no-gate» sopra descrive quindi il
# passato: da quel commit il giudice in CI C'E', `real_ce_cached()` rende vero
# e questi test NON vengono saltati. Misurato, non dedotto: nel run
# 31718419381 (commit `cbdf7cc2`, dopo quello) i sei test risultano FAILED e
# non SKIPPED.
# ⚠️ Il paragrafo resta perche' il suo ragionamento e' giusto e la guardia
# serve ancora a chi non ha il modello in locale. Va letto con la sua data:
# una premessa scaduta non e' innocua, autorizza a credere gia' risolto cio'
# che e' ancora rosso.
pytestmark = pytest.mark.skipif(
    not real_ce_cached(),
    reason="il giudice del moat non e' in cache (la CI scalda con --no-gate): "
           "questo banco misura cosa dice la ricevuta di un verdetto, e senza "
           "verdetto non c'e' niente da misurare",
)

CLAIM = "L'ordine 77 conteneva 40 pezzi."
FONTE = "Verbale: e' stato consegnato l'ordine 77. Ha partecipato Bianchi."
VERO = "Il magazzino di Verona contiene 480 pallet."
FONTE_VERA = "Inventario: magazzino Verona, 480 pallet a scaffale."


# ── Il banco leggeva l'output sbagliato, in due modi ────────────────────────
# Le due funzioni stanno qui ma i loro guardiani stanno in
# `test_il_banco_della_ricevuta_legge_la_superficie_giusta.py`: misurano il
# BANCO, non il prodotto, e non devono tacere quando tace il giudice — che e'
# quello che farebbero, ereditando il `pytestmark` di questo modulo.
_LOG_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[.\d]* \[\w+\s*\]")


def solo_la_ricevuta(testo: str) -> str:
    """Cio' che il prodotto DICE a chi salva, senza cio' che scrive per se'.

    ⚠️ Serve perche' i log strutturati finiscono nello stesso testo e portano
    `layers=['L4.1']`: l'assert che pretende dalla RICEVUTA il nome del
    controllo che ha bocciato si accontentava della RIGA DI LOG. Due superfici
    diverse, una sola stringa cercata — il banco poteva restare verde con la
    ricevuta muta. E' il difetto che questo file rimprovera al prodotto,
    ripetuto dentro il banco che lo misura.
    """
    return "\n".join(
        r for r in testo.splitlines()
        if not _LOG_RE.match(r) and "it/s]" not in r
        and "Loading weights" not in r)


def cosa_non_ha_trovato(grezzo: str) -> str:
    """Il NOME di cio' che manca, che la coda dell'errore non contiene.

    Misurato il 2026-08-16 sul run 31971326291: la coda dice «couldn't find
    them in the cached files. Check your internet connection…» e non nomina
    NIENTE — il soggetto sta molte righe piu' su, e con 42241 byte di stderr
    nessuna coda ragionevole lo raggiunge. Sei rossi hanno percio' detto per
    ore «manca un modello» senza dire quale, e la caccia e' andata avanti per
    ipotesi.

    🔑 E' il rimprovero che questo file fa al prodotto — *«la ricevuta non
    diceva QUALE cifra mancava»* — ripetuto dentro il banco che lo misura.
    """
    marcatori = (
        "does not appear to have",      # transformers: nomina file e repo
        "is not a local folder",        # transformers: nomina la CARTELLA
        "is not a valid model identifier",
        "Can't load",
        "LocalEntryNotFound",
        "OSError",
        "cached files",
    )
    righe = [r.strip() for r in grezzo.splitlines()
             if any(m in r for m in marcatori)]
    return " | ".join(righe[:4])[:400] if righe else "(nessuna riga nota)"


def leggi(returncode: int, stdout, stderr) -> str:
    """Il verdetto del processo PRIMA del suo output.

    Un CLI che muore lascia un output TRONCO, e ogni assert riferisce allora
    una stringa mancante invece di un processo morto. In CI lo nasconde due
    volte, perche' la piattaforma TRONCA le righe lunghe: i log riempiono il
    messaggio e la coda — dove starebbe la causa — viene tagliata via.
    """
    grezzo = (stdout or "") + (stderr or "")
    if returncode != 0:
        # ⚠️ l'informazione decisiva PRIMA, la coda DOPO: se il messaggio viene
        # tagliato si perde la coda, non il verdetto.
        raise AssertionError(
            f"CLI-MORTO exit={returncode} len_stdout={len(stdout or '')} "
            f"len_stderr={len(stderr or '')} "
            f"cosa_manca={cosa_non_ha_trovato(grezzo)!r} "
            f"coda={grezzo[-200:]!r}")
    return solo_la_ricevuta(grezzo)


def _remember(tmp_path, claim, source):
    # ⚠️ TUTTI E TRE gli alias, non due: il terzo verrebbe EREDITATO da
    # os.environ (la fixture autouse lo pinna a un'altra tmp) e i tre
    # disaccorderebbero. Il prodotto allora emette `RuntimeWarning: DATA_DIR
    # aliases disagree` proprio dentro l'output che gli assert qui sotto
    # leggono — rumore che maschera il motivo vero di un rosso.
    env = dict(os.environ, HIPPO_DATA_DIR=str(tmp_path),
               ENGRAM_DATA_DIR=str(tmp_path),
               VERIMEM_DATA_DIR=str(tmp_path))
    r = subprocess.run(
        [sys.executable, "-m", "verimem.cli", "remember", claim,
         "--topic", "t", "--source", source],
        capture_output=True, text=True, env=env, timeout=900)
    # 🔑 L'AMBIENTE, quando il comando muore. In CI la stessa CLI eseguita in un
    # passo del workflow — stesso runner, stesso job, stessa cache, stesse tre
    # variabili offline — RIESCE (stdout 1468 B), e qui muore con 42241 B e
    # `LocalEntryNotFoundError`. Misurato sul run 32015210026.
    # Il modello non e' la differenza (`CONFIG.embedding_model` e' lo stesso che
    # la sonda carica) e nemmeno il tempo (prima e dopo la suite i numeri sono
    # identici). Resta cio' che le fixture mettono in `os.environ` e che questo
    # sottoprocesso EREDITA — e finora nessun referto lo nominava.
    # ⇒ Si stampa solo in caso di morte, e solo le variabili che riguardano il
    #   caricamento: un elenco completo sarebbe di nuovo illeggibile.
    if r.returncode != 0:
        _prefissi = ("HIPPO", "ENGRAM", "VERIMEM", "HF_", "HUGGINGFACE",
                     "TRANSFORMERS", "SENTENCE", "TORCH", "XDG_CACHE")
        _amb = {k: v for k, v in sorted(env.items())
                if k.startswith(_prefissi)}
        raise AssertionError(
            f"CLI-MORTO(env) {len(_amb)} variabili rilevanti ereditate: "
            f"{_amb} || {leggi(r.returncode, r.stdout, r.stderr)}")
    # ⚠️ `subprocess` puo' rendere `None` invece di stringa vuota su uno dei due
    # canali, e la somma esplode PRIMA di arrivare all'assert: in CI si legge
    # `TypeError: can only concatenate str (not "NoneType") to str` al posto del
    # motivo per cui il test e' rosso. Il difetto vero resta nascosto sotto.
    # 🔑 NON e' cosmesi difensiva: qui il fallimento del banco MASCHERA il
    # fallimento che il banco esiste per mostrare.
    return leggi(r.returncode, r.stdout, r.stderr)


def test_la_ricevuta_dice_QUALE_valore_non_ha_trovato(tmp_path):
    """IL CUORE: chi viene fermato deve sapere perché. «quarantined id=…» da solo
    manda a indovinare, e il motivo era già calcolato."""
    out = _remember(tmp_path, CLAIM, FONTE)
    assert "quarantined" in out
    assert "40" in out, f"la cifra mancante non compare nella ricevuta:\n{out}"
    assert "L4.1" in out, "non si sa QUALE voce del gate ha parlato"


def test_la_ricevuta_dice_anche_COSA_FARE(tmp_path):
    """Un rifiuto senza rimedio è un muro. Il consiglio esisteva già nel
    verdetto: «correggi il valore, oppure passa la fonte che lo contiene»."""
    out = _remember(tmp_path, CLAIM, FONTE)
    assert "correggi" in out.lower() or "fonte che lo contiene" in out.lower()


def test_CONTROLLO_POSITIVO_un_fatto_ammesso_non_riceve_rumore(tmp_path):
    """⚠️ LA POPOLAZIONE OPPOSTA. Un avviso che compare anche quando tutto va
    bene è rumore: chi salva cento fatti veri leggerebbe cento spiegazioni di
    niente, e smetterebbe di leggerle proprio quando servono."""
    out = _remember(tmp_path, VERO, FONTE_VERA)
    assert "admitted" in out
    assert "L4.1" not in out
    assert "non contiene" not in out


def test_il_caso_che_sfuggiva_moat_a_favore_e_layer_contrario(tmp_path):
    """🔑 IL CASO CHE DÀ SENSO ALLA CURA: il giudice approva (95,5 su un taglio
    di 40) e il fatto è quarantinato lo stesso, da un controllo diverso.

    È il caso in cui le due voci del gate si contraddicono — quello che ws1 ha
    trovato in 16 casi su 16 fra i suoi quarantinati — e la ricevuta, decidendo
    cosa dire in base al solo punteggio, era proprio lì che taceva.
    """
    out = _remember(tmp_path, CLAIM, FONTE)
    assert "quarantined" in out
    # il punteggio del giudice è ALTO e il fatto è fermato lo stesso:
    # entrambe le informazioni devono raggiungere chi legge
    assert "L4.1" in out and "40" in out


# ── L'ALTRA VOCE: quella che era d'accordo ──────────────────────────────────
# Il gate ha DUE voci e chiedono cose diverse. La cura sopra fa dire quale ha
# bocciato; questa fa dire che l'altra aveva approvato.
#
# Un fatto respinto 1-a-1 non è un fatto respinto 2-a-0, e per chi scrive è la
# differenza fra «riformula la frase» e «hai sbagliato UN numero».

def test_la_ricevuta_dice_che_il_giudice_era_D_ACCORDO(tmp_path):
    """IL CUORE: il claim è fermato da un controllo di dettaglio, ma la fonte lo
    sostiene — grounding 94,6 su un taglio di 40. Chi legge deve saperlo,
    altrimenti riscrive tutta la frase quando bastava correggere una cifra."""
    out = _remember(tmp_path, CLAIM, FONTE)
    assert "quarantined" in out
    assert "giudice era d'accordo" in out or "giudice era d" in out
    assert "taglio" in out


def test_CONTROLLO_POSITIVO_il_fatto_ammesso_non_riceve_la_seconda_voce(tmp_path):
    """⚠️ LA POPOLAZIONE OPPOSTA: se il fatto passa, non c'è nessun disaccordo da
    spiegare. Due righe in più su ogni salvataggio riuscito sono rumore, e il
    rumore fa smettere di leggere proprio quando conta."""
    out = _remember(tmp_path, VERO, FONTE_VERA)
    assert "admitted" in out
    assert "giudice era d" not in out


# ═══ E LO STESSO METRO APPLICATO A QUESTO BANCO ═══════════════════════════
# I sei test qui sopra, quando l'ambiente non regge, dicevano «CLI-MORTO … non
# trova i file in cache» senza nominare cosa mancasse: la stessa ricevuta muta
# che questo file rimprovera al prodotto. Il criterio di un presidio e' che
# TOGLIENDOLO il messaggio cambi, quindi si misura sul messaggio, non sull'idea.

_STDERR_VERO = (
    "2026-08-16T21:02:44Z [info] flow.warmup phase=start\n"
    "Loading weights:  37%|###   | 74/199 [00:03<00:05, 22.51it/s]\n"
    "OSError: /home/runner/.cache/verimem/models/local_gate_ce_v2 is not a "
    "local folder and is not a valid model identifier listed on "
    "'https://huggingface.co/models'\n"
    "If this is a private repository, make sure to pass a token.\n"
    "We couldn't connect to 'https://huggingface.co' to load the files, and "
    "couldn't find them in the cached files.\n"
    "Check your internet connection or see how to run the library in offline "
    "mode at 'https://huggingface.co/docs/transformers/installation'.\n")


def test_il_verdetto_di_questo_banco_NOMINA_cio_che_manca():
    """La coda da sola non basta: e' il pezzo che NON contiene il nome."""
    with pytest.raises(AssertionError) as e:
        leggi(1, "", _STDERR_VERO)
    messaggio = str(e.value)
    assert "local_gate_ce_v2" in messaggio, (
        f"il verdetto non nomina cio' che manca: {messaggio}")
    assert "cosa_manca=" in messaggio


def test_CONTROLLO_NEGATIVO_la_sola_coda_non_lo_direbbe():
    """Se questa passasse con la coda soltanto, il presidio sopra sarebbe
    decorativo: il nome sta 4 righe piu' su di quante ne prenda `coda`."""
    assert "local_gate_ce_v2" not in _STDERR_VERO[-200:]


def test_un_output_senza_righe_note_non_inventa_un_nome():
    assert cosa_non_ha_trovato("tutto bene\nnessun errore\n") == (
        "(nessuna riga nota)")
