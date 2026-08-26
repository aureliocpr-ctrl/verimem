"""`controlla_promesse` contava un debito che non c'era.

Lo script gira nel publish come AVVISO (non veto) e serve a una cosa precisa:
far notare che una promessa scritta in più posti, se la si precisa in uno,
resta vecchia negli altri. Il caso che lo ha motivato è reale.

Ma cerca una STRINGA — lo dice il commento di ``FRASI``, «FORMULAZIONI di
promessa» — e il messaggio diceva «promesse». Misurato sul wheel 0.7.6::

    «never silently» — 12 occorrenze in 8 file · SU PIÙ SUPERFICI
    Queste promesse vivono su più superfici: precisarne una lascia le altre
    com'erano.

Aperte le dodici occorrenze, sono promesse **diverse** che condividono la
formula::

    client.py           a caught hallucination is reported, never silently dropped
    composer.py         never silently admitted
    semantic.py         a hit never silently disappears from the result
    tamper_evidence.py  who ASKED for signing must never silently not get it

Chi legge quell'avviso prima di un rilascio conta otto superfici da
riconciliare e ne trova una vera («exact citation», 1 file). Il conteggio era
esatto; la parola no. E il costo non è il rumore in sé: è che l'avviso sta
esattamente nel punto in cui si vorrebbe segnale.

⚖️ UN PRESIDIO SU UN MESSAGGIO GUARDA IL MESSAGGIO, e va detto perché oggi
ho curato il difetto opposto (`16599716`: un test che asseriva la
formulazione di un advice invece del fatto che l'advice deve portare). La
differenza è che lì il testo era il MEZZO per dire un fatto — il numero di
clausole — e il fatto si poteva asserire direttamente. Qui il testo È il
prodotto: lo script non fa altro che dire una cosa a chi rilascia, e l'unico
modo di presidiare quel che dice è leggerlo. Quindi si asserisce il
COMPORTAMENTO minimo — che l'avviso nomini l'ambiguità quando c'è, e non la
nomini quando non c'è — e non la frase con cui lo fa.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "controlla_promesse.py"
FRASE = "pinco pallino verificato"


def _esegui(percorso: Path) -> str:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(percorso), "--frase", FRASE],
        capture_output=True, text=True, timeout=180,
        encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def _dir_con(tmp_path: Path, quanti: int) -> Path:
    d = tmp_path / f"pacchetto{quanti}"
    (d / "verimem").mkdir(parents=True)
    for i in range(quanti):
        (d / "verimem" / f"modulo{i}.py").write_text(
            f'"""Il modulo {i}: {FRASE} in una promessa sua."""\n',
            encoding="utf-8")
    return d


def test_su_piu_superfici_l_avviso_dice_che_puo_essere_UNA_FORMULA(tmp_path):
    """Il cuore: con la formula in più file, l'avviso non deve affermare che
    sono la stessa promessa — perché lo script non ha modo di saperlo."""
    testo = _esegui(_dir_con(tmp_path, 3))
    assert FRASE in testo, f"lo script non ha trovato la frase di prova:\n{testo}"
    assert "formula" in testo.lower(), (
        "l'avviso su più superfici non nomina il fatto che si tratta di una "
        "FORMULA condivisa: chi legge conclude che è una promessa sola in "
        f"tre posti, e conta un debito che potrebbe non esserci.\n{testo}")


def test_su_piu_superfici_l_avviso_dice_di_APRIRE_le_occorrenze(tmp_path):
    """La parte azionabile: dire che è una formula non basta se non si dice
    cosa fare. Il passo è aprirle prima di contarle."""
    testo = _esegui(_dir_con(tmp_path, 3)).lower()
    assert "diverse" in testo or "aprire" in testo, (
        "l'avviso non dice che le occorrenze vanno aperte prima di contarle "
        "come un debito: senza quel passo resta un numero che spaventa e non "
        f"orienta.\n{testo}")


def test_CONTROLLO_in_un_posto_solo_non_avvisa_di_niente(tmp_path):
    """La difesa, senza la quale il presidio sopra passerebbe anche se lo
    script scrivesse l'avvertenza SEMPRE — che è il modo in cui un avviso
    smette di informare."""
    testo = _esegui(_dir_con(tmp_path, 1))
    assert FRASE in testo, f"lo script non ha trovato la frase di prova:\n{testo}"
    assert "posto solo" in testo, (
        f"una sola occorrenza non è marcata «in un posto solo»:\n{testo}")
    assert "diverse" not in testo.lower(), (
        "l'avvertenza sulle promesse diverse compare anche con UNA sola "
        f"occorrenza: allora non distingue niente.\n{testo}")


def test_CONTROLLO_resta_un_avviso_e_non_un_veto(tmp_path):
    """Il docstring dello script lo promette — «Uscita 0 sempre: questo non è
    un veto» — ed è una scelta argomentata («un controllo che blocca sempre
    viene disattivato»). Se un giorno diventasse un veto, `publish.yml` si
    fermerebbe su ogni formula condivisa e nessuno saprebbe perché."""
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(_dir_con(tmp_path, 3)), "--frase", FRASE],
        capture_output=True, text=True, timeout=180,
        encoding="utf-8", errors="replace")
    assert r.returncode == 0, (
        f"lo script è diventato un veto (EXIT={r.returncode}): fermerebbe il "
        f"publish su ogni formula condivisa.\n{(r.stdout or '') + (r.stderr or '')}")
