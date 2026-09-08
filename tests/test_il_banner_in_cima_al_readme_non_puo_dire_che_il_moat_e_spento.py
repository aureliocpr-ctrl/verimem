"""Il PRIMO blocco del README non puo' dire che il moat e' spento: e' misurato falso.

PERCHE' ESISTE QUESTO FILE
==========================
Il 06/09 ho corretto il banner in cima al README — quello che diceva::

    ## ⚠️ BEFORE FIRST USE — RUN THIS ONCE: verimem warmup
    **Until you do, the judge is not installed and the moat is OFF**

Poi ho eseguito i **15 presidi del README** con il banner VECCHIO rimesso, per
vedere quanti si accendevano::

    PRESIDI CHE SI ACCENDONO COL BANNER VECCHIO: 0 su 15

⇒ **Nessuno.** Il blocco piu' visibile del prodotto — il primo che legge chi
arriva da PyPI — **non era presidiato da niente**, ed e' esattamente per questo
che ha potuto restare falso per due release: la cura era entrata (il giudice si
procura da solo) e il testo non l'ha seguita, senza che nulla si accendesse.

I 15 verdi dicevano «non ho rotto il resto». Non dicevano «il banner e' giusto».
Un banco che non discrimina non e' una prova, e qui il banco mancava del tutto.

LA MISURA CHE RENDE FALSA LA FRASE VECCHIA (@ws5 Tara, 06/09) — pacchetto 0.7.6
di PyPI, cartella del giudice VUOTA (0 byte verificati), `warmup` MAI eseguito::

    remember con fonte:  85.7 s  TORNATA
    grounding_score:     99.97052764892578
    moat:                judged 100.0

Il moat era **acceso**: la prima scrittura si e' procurata il giudice da sola.
La frase era vera sulla **0.7.1** (`ensure_gate_model()` raggiungibile solo da
`warmup` — cfr. `tests/test_ws5_giudice_si_procura_da_solo.py`, che conserva la
misura e la cura); la cura e' entrata, la frase e' rimasta.

COSA PRESIDIA, e cosa NON presidia
----------------------------------
Presidia **una affermazione misurata falsa**, non uno stile: che il banner non
torni a dire che il moat e' spento finche' non lanci `warmup`, e che non
ripresenti quel comando come un obbligo.
NON presidia che il testo sia bello, ne' che i numeri siano aggiornati: quelli
hanno gia' i loro presidi (`746 MB`/`711 MB` sono coperti da cinque file
ciascuno).

⚠️ CONTROLLO POSITIVO INTERNO. Se il banner sparisse del tutto, un test che
cerca solo frasi vietate passerebbe **senza presidiare piu' niente** — la forma
«assenza di misura letta come verde» che paghiamo da mesi. Per questo il primo
test qui sotto fallisce se non trova il blocco: il presidio deve poter dire
«il mio bersaglio non c'e' piu'».
"""
from __future__ import annotations

import pathlib
import re

import pytest

README = pathlib.Path(__file__).resolve().parents[1] / "README.md"

#: il banner e' il primo blocco citato del file: le prime righe, prima del corpo
_RIGHE_DEL_BANNER = 40

#: affermazioni MISURATE FALSE il 06/09 (Tara, 0.7.6 con cartella del giudice vuota)
_FRASI_FALSE = [
    re.compile(r"the moat is OFF", re.I),
    re.compile(r"moat is (?:currently |now )?off\b", re.I),
    re.compile(r"judge is not installed and", re.I),
]

#: il comando presentato come OBBLIGO (lo e' stato fino alla 0.7.1, non lo e' piu')
_OBBLIGHI = [
    re.compile(r"BEFORE FIRST USE", re.I),
    re.compile(r"RUN THIS ONCE", re.I),
    re.compile(r"you must run .{0,20}warmup", re.I),
]


def _banner() -> str:
    return "\n".join(
        README.read_text(encoding="utf-8", errors="replace").splitlines()[:_RIGHE_DEL_BANNER]
    )


def test_CONTROLLO_il_banner_esiste_ancora():
    """Senza questo, cancellare il banner farebbe passare tutto il file."""
    testo = _banner()
    assert "warmup" in testo, (
        "il presidio non trova il suo bersaglio: nelle prime "
        f"{_RIGHE_DEL_BANNER} righe del README non si parla piu' di warmup. "
        "Se il banner e' stato spostato o rimosso, aggiorna QUESTO file: "
        "un presidio che non trova cio' che presidia non e' verde, e' cieco."
    )


@pytest.mark.parametrize("rx", _FRASI_FALSE, ids=lambda r: r.pattern[:28])
def test_il_banner_non_dice_che_il_moat_e_spento(rx):
    m = rx.search(_banner())
    assert m is None, (
        f"il banner dice di nuovo {m.group(0)!r}, che e' MISURATO FALSO: sul "
        "pacchetto 0.7.6, con la cartella del giudice vuota e warmup mai "
        "eseguito, la prima scrittura con fonte e' tornata dopo 85.7 s con "
        "moat judged 100.0 (misura @ws5, 06/09). Il moat era acceso."
    )


@pytest.mark.parametrize("rx", _OBBLIGHI, ids=lambda r: r.pattern[:24])
def test_il_banner_non_presenta_warmup_come_obbligo(rx):
    m = rx.search(_banner())
    assert m is None, (
        f"il banner ripresenta warmup come un obbligo ({m.group(0)!r}). Non lo "
        "e': il prodotto si procura il giudice da solo alla prima scrittura "
        "gated. warmup sposta QUANDO paghi il download, non se il moat e' "
        "acceso."
    )


# ─────────────────────────────────────────────────────────────────────────
# 08/09 — IL PRESIDIO GUARDAVA IL POSTO IN CUI LA FRASE ERA STATA CURATA,
# NON IL POSTO IN CUI ERA RIMASTA.
#
# Il 06/09 il banner e' stato corretto e questo file l'ha presidiato: 7 passed,
# EXIT=0 sul tip 0ffd5ef7 — il candidato al tag. Ma `_banner()` legge solo le
# prime 40 righe, e la stessa frase vietata viveva alla riga 344, dentro
# `## Install`:
#
#     > ⚠️ After `pip install`, run `verimem warmup` before the first write —
#     > see the banner at the top: without it the judge is missing and the
#     > moat is OFF.
#
# ⚠️ E CITAVA IL BANNER COME FONTE di cio' che il banner smentisce
# esplicitamente («This box used to say the moat was OFF … Corrected here»).
# ⇒ Presidio verde, difetto presente, sul commit che si tagga.
#
# 🪞 La stessa riga era stata letta il 04/09 (`docs/stato-reale/00-ESAME.md`,
# cella W7-142) come una VIRTU' — «il README sa dire che una cosa e' OFF, e lo
# fa due volte». Era vero quel giorno: il banner diceva la stessa cosa. E'
# diventata una contraddizione due giorni dopo, quando il banner e' cambiato e
# l'Install no. **Una citazione interna invecchia quando cambia cio' che cita.**
def test_la_frase_falsa_non_vive_in_NESSUN_punto_del_readme():
    testo = README.read_text(encoding="utf-8", errors="replace")
    colpevoli = []
    for n, riga in enumerate(testo.splitlines(), 1):
        if n <= _RIGHE_DEL_BANNER:
            continue  # il banner ha gia' i suoi test, sopra
        for rx in _FRASI_FALSE:
            if rx.search(riga):
                colpevoli.append(f"  README.md:{n}: {riga.strip()[:100]}")
                break  # una riga si conta UNA volta, anche se due regex la prendono
    assert not colpevoli, (
        "il README dice che il moat e' spento finche' non esegui `warmup`, "
        "FUORI dal banner — e il banner dichiara quella frase falsa e misurata "
        "tale (06/09, 0.7.6 con la cartella del giudice vuota: la scrittura e' "
        "stata giudicata lo stesso). Righe:\n" + "\n".join(colpevoli)
    )


def test_CONTROLLO_il_corpo_del_readme_e_stato_letto_davvero():
    """Il gemello del controllo positivo di sopra, per QUESTO test.

    Se il README fosse vuoto o troncato, il test qui sopra passerebbe senza
    aver guardato niente: un verde che non ha letto nulla non e' un verde.
    """
    righe = README.read_text(encoding="utf-8", errors="replace").splitlines()
    assert len(righe) > _RIGHE_DEL_BANNER + 100, (
        f"il README ha {len(righe)} righe: il corpo oltre il banner non c'e', "
        "quindi il test sulla frase falsa non sta guardando nulla."
    )
    corpo = "\n".join(righe[_RIGHE_DEL_BANNER:])
    assert "warmup" in corpo, (
        "nel corpo del README non si parla piu' di `warmup`: se la sezione "
        "Install e' stata spostata, aggiorna QUESTO file invece di fidarti "
        "del verde."
    )
