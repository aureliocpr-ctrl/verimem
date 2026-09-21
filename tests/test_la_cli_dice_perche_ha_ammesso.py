"""Un fatto ammesso deve dire PERCHE', non solo che e' entrato.

MISURATO il 2026-09-20 sul tronco a5a9ac0a, stesso claim, stesse due uscite:

    testo    admitted id=0217fdf427bd topic=prova/t174
    --json   esito ammesso · punteggio 99.77965545654297 · soglia 40.0 ·
             scala moat-0-100 · margine 59.77965545654297 · giudice local ·
             modello local_gate_ce_v2 · moat passed

Nove parole contro ventidue chiavi. E per un NO la stessa CLI stampa ventidue
righe: layer, advice, «il giudice era d'accordo», il suggerimento su
writer_role. ⇒ Il prodotto argomenta i suoi no e non i suoi si'.

⚠️ QUESTO NON E' UN CALCOLO, E' UNA STAMPA: punteggio, soglia e giudice sono
gia' nella ricevuta che la CLI ha in mano mentre stampa quella riga. La cella
lo fissa nel modo piu' duro possibile — i numeri della riga di testo devono
essere gli STESSI del json, carattere per carattere dove sono stringhe e senza
ricalcoli dove sono numeri. Se un giorno qualcuno li riformattasse a mano, qui
si vedrebbe.

⚠️ Il NO non si tocca: una cella lo tiene fermo.

⚖️ DUE REGIMI, ed entrambi sono esercitati qui:
  · sul runner non c'e' un giudice raggiungibile, la ricevuta torna
    `moat: not_run:no_judge` e gira il ramo «non giudicato»;
  · in locale, con il cross-encoder in casa, gira il ramo dei numeri.
La cella non sceglie: legge cosa dice la ricevuta e pretende che la riga dica
la stessa cosa. Cosi' misura il prodotto in tutt'e due i mondi invece di
misurare quale dei due le e' capitato.

⚠️ E LO STESSO INGRESSO, non uno simile. La prima stesura chiedeva il json di
`CLAIM + " (a)"` e il testo di `CLAIM + " (b)"`: due stringhe diverse, due
punteggi diversi — 99.98 contro 99.95 — e l'assert cadeva in CI dicendo «la
riga non dice punteggio=99.98» mentre la riga era giusta. In locale passava
per fortuna, perche' i due numeri si somigliavano. E' la lezione di T147
(«una variabile per volta presuppone lo stesso INGRESSO») rifatta in forma
nuova: non due fonti, due claim. Ora la stringa e' UNA e cambiano solo gli
store, cosi' il giudice — che e' deterministico — deve dare lo stesso numero
a TUTTE le cifre.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

from tests._esito import esito

CLAIM = "Il collaudo della linea 3 e' stato ultimato il 12 marzo."
FONTE = ("Il collaudo della linea 3 si e' ultimato il 12 marzo con esito "
         "positivo e la linea e' stata approvata dalla commissione.")


def _cli(tmp_path, *argomenti: str) -> str:
    """La CLI in un processo pulito, con uno store tutto suo.

    ⚠️ L'AMBIENTE SI RIPULISCE, non si eredita. Ereditando `os.environ` da
    pytest il sottoprocesso si porta dietro le variabili che il conftest
    impone, e con quelle il giudice e' uno stub: la ricevuta torna con
    `punteggio: None` e questa cella misurerebbe l'ambiente di test invece
    del prodotto. Misurato il 2026-09-20: stesso claim, stesso store nuovo —
    dalla shell `punteggio 99.86578369140625`, ereditando da pytest `None`.
    Qui si simula un UTENTE, quindi si tengono solo le variabili di sistema
    piu' quelle dello store.
    """
    import os
    # ⚠️ `USERNAME` SERVE, e non e' una variabile qualunque: torch costruisce
    # il nome della cartella della sua cache dal nome utente, e senza quella
    # due processi scrivono sotto lo STESSO nome e il secondo muore con
    # «Artifact of type=precompile already registered in mega-cache artifact
    # factory» (T182). Trovata per bisezione il 2026-09-21: stesso comando,
    # stesso albero, stesso torch 2.12.0.dev+cu128 — env intero EXIT=0, le
    # dodici minime EXIT=1, minime + USERNAME EXIT=0, e come controllo
    # negativo minime + NUMBER_OF_PROCESSORS di nuovo EXIT=1.
    # ⚠️ Sembrava intermittente: non lo era: dipendeva da quali altri processi
    # stessero scrivendo in quella cartella condivisa nello stesso momento.
    env = {k: v for k, v in os.environ.items()
           if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE",
                    "HOMEDRIVE", "HOMEPATH", "PYTHONPATH", "APPDATA",
                    "LOCALAPPDATA", "PATHEXT", "COMSPEC", "USERNAME")}
    for v in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        env[v] = str(tmp_path)
    env["ENGRAM_EVENT_LOG"] = str(tmp_path / "eventi.jsonl")
    r = subprocess.run([sys.executable, "-m", "verimem.cli", *argomenti],
                       capture_output=True, text=True, timeout=900, env=env)
    # ⚠️ L'ESITO SI GUARDA, e da oggi si pretende ZERO: T182 e' chiusa —
    # era `USERNAME` assente dall'ambiente ridotto qui sopra, che faceva
    # scrivere due processi sotto lo stesso nome di cache. Un comando che
    # stampa la ricevuta e POI muore non deve piu' passare di qui: chi lo
    # chiama da uno script si ferma lo stesso.
    return esito(r, atteso=0)


def _estrai(testo: str) -> str:
    """Il json dentro un'uscita che porta anche avvisi, telemetria e — quando
    puo' presentarsi, un traceback con graffe sue.

    ⚠️ Non si prende «dalla prima graffa all'ultima»: con il traceback in
    mezzo quel taglio produce un pezzo che non e' json, e l'errore che si
    legge e' `JSONDecodeError` invece della causa vera. Si prova a decodificare
    da OGNI graffa e si tiene il primo oggetto valido.
    """
    d = json.JSONDecoder()
    for i, c in enumerate(testo):
        if c != "{":
            continue
        try:
            oggetto, fine = d.raw_decode(testo[i:])
        except ValueError:
            continue
        if isinstance(oggetto, dict) and "esito" in oggetto:
            return testo[i:i + fine]
    raise AssertionError(f"nessuna ricevuta json nell'uscita: {testo[-400:]}")


def test_la_riga_dice_cio_che_la_ricevuta_sa(tmp_path):
    """Stessa identica stringa, due store: la riga deve dire cio' che il json
    dice, e nel regime senza giudice deve DIRE che nessuno ha giudicato."""
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    d = json.loads(_estrai(_cli(a, "remember", CLAIM, "--source", FONTE,
                                "--topic", "prova/t174", "--json")))
    assert d.get("esito") == "ammesso", d

    tutto = " ".join(_cli(b, "remember", CLAIM, "--source", FONTE,
                          "--topic", "prova/t174").splitlines())
    assert "admitted" in tutto, f"non c'e' piu' la riga di ammissione: {tutto[-300:]}"

    if d.get("punteggio") is None:
        assert ("non giudicat" in tutto.lower() or "not_run" in tutto
                or "no_judge" in tutto), (
            "il fatto e' entrato SENZA giudizio e la riga non lo dice: chi "
            f"legge crede che qualcuno abbia controllato. {tutto[-300:]}")
    else:
        for campo, atteso in (("punteggio", f"{d['punteggio']:.2f}"),
                              ("soglia", f"{d['soglia']:.0f}"),
                              ("giudice", str(d["giudice"])),
                              ("modello", str(d["modello"])),
                              ("margine", f"{d['margine']:.2f}")):
            assert atteso in tutto, (
                f"la riga non dice {campo}={atteso}: {tutto[-300:]}")


def test_i_numeri_della_riga_sono_quelli_della_ricevuta(tmp_path):
    """Non ricalcolati: gli STESSI, a tutte le cifre stampate.

    Due store e UNA stringa: il giudice e' deterministico, quindi se i numeri
    divergessero sarebbe perche' qualcuno li ha riformattati per conto suo.
    """
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    d = json.loads(_estrai(_cli(a, "remember", CLAIM, "--source", FONTE,
                                "--topic", "prova/t174", "--json")))
    tutto = " ".join(_cli(b, "remember", CLAIM, "--source", FONTE,
                          "--topic", "prova/t174").splitlines())
    if d.get("punteggio") is None:
        assert not re.search(r"\d+\.\d+/100", tutto), (
            f"la riga inventa un punteggio che la ricevuta non ha: {tutto[-300:]}")
    else:
        assert f"{d['punteggio']:.2f}" in tutto, (
            f"punteggio stampato diverso da quello della ricevuta "
            f"({d['punteggio']:.2f}): {tutto[-300:]}")
        assert f"{d['margine']:.2f}" in tutto, (
            f"margine stampato diverso da quello della ricevuta "
            f"({d['margine']:.2f}): {tutto[-300:]}")


def test_il_no_resta_com_e(tmp_path):
    """NON-REGRESSIONE: la spiegazione dei rifiuti non si tocca."""
    testo = _cli(tmp_path, "remember",
                 "Ho verificato che il sistema funziona correttamente.",
                 "--topic", "prova/t174no")
    assert "advice" in testo.lower() or "quarantined" in testo.lower(), (
        f"il NO ha perso la sua spiegazione: {testo[-400:]}")
