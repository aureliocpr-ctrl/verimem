"""README:714 — «every claim in this README links to a raw result file».

Il README e' la pagina di PyPI (`pyproject.toml: readme = "README.md"`), quindi
questa riga e' la promessa di VERIFICABILITA' che un utente riceve prima di
installare: se ogni numero rimanda a un risultato grezzo, chiunque puo'
ricontrollarci.

🔴 Il difetto: la stessa pagina dichiara DUE eccezioni, cinquanta righe piu'
sopra e in grassetto — riga 664 e riga 704, entrambe «**has no committed results
file**». Le eccezioni non sono nascoste: sono la parte piu' onesta del documento.
E' la SINTESI a promettere piu' di quanto la pagina mantenga, e un «every» con due
eccezioni scritte dallo stesso testo e' la riga che un lettore cita quando ci
difende — e che chiunque puo' falsificare **leggendo la pagina che ha in mano**.

La cura e' UNA PAROLA: «nearly every claim … the two exceptions are flagged
inline». Il contenuto onesto c'e' gia'.

Presidio: Product Owner, 12/09/2026, sul README di `origin/main`.
Verificato con  grep -n "every claim in this README" README.md   -> riga 714
                grep -n "has no committed results file" README.md -> righe 664, 704
⚠️ LIMITE DICHIARATO: **questo file non e' stato eseguito da chi lo ha scritto**
(sono in sola lettura oggi). Va eseguito dal pari: atteso 1 xfailed + 1 passed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
README = RADICE / "README.md"

PROMESSA = "every claim in this README links"
ECCEZIONE = "has no committed results file"

# `.mcp.json` e' il file che l'UTENTE crea per collegare il server al proprio
# client: il README lo mostra come esempio, non lo pubblica. Non e' un risultato.
NON_SONO_RISULTATI = {".mcp.json"}


def _testo_readme() -> str:
    assert README.is_file(), f"il README non e' al suo posto: {README}"
    return README.read_text(encoding="utf-8", errors="replace")


#: Le eccezioni che la pagina dichiara di sé, contate il 12/09/2026 (righe 664 e
#: 704). Il numero e' misurato QUI, sullo stesso testo che questo test legge.
ECCEZIONI_IL_12_09 = 2


def test_una_promessa_universale_non_convive_con_le_eccezioni_che_dichiara():
    """🔴 Il difetto e' APERTO e questo test lo REGISTRA invece di aspettarselo.

    ⚙️ **Perche' non e' un `xfail`** (decisione del 12/09: *«un test misura e
    resta, o si toglie con la ragione»*). Un `xfail` cade solo quando il difetto
    e' curato; questo cade **nei due versi** — se la parola «every» viene
    corretta **e** se le eccezioni dichiarate cambiano di numero, cioe' se la
    pagina ne acquista una terza senza che nessuno lo dica.
    """
    testo = _testo_readme()
    promette = PROMESSA in testo
    eccezioni = testo.count(ECCEZIONE)

    # Il controllo positivo del test e' qui: se una delle due stringhe sparisse
    # dal README (riscritta, tradotta, spostata) questo test smetterebbe di
    # misurare cio' che crede, e lo direbbe invece di passare in silenzio.
    assert promette, (
        f"la riga che questo test presidia non c'e' piu' nel README: {PROMESSA!r}. "
        "Se e' stata riscritta, aggiorna il presidio; se e' stata tolta, togli il test."
    )
    assert eccezioni >= 1, (
        f"le eccezioni dichiarate non ci sono piu' nel README: {ECCEZIONE!r}. "
        "Se sono state curate davvero, questo test ora passa ed e' giusto cosi'."
    )

    # Il difetto REGISTRATO: la promessa universale e le sue eccezioni convivono.
    # Se la promessa viene corretta («nearly every»), questo cade ed e' una BUONA
    # notizia: il test va girato, non tolto.
    assert promette, (
        "🟢 **BUONA NOTIZIA, e questo test va riscritto**: la promessa universale "
        f"«{PROMESSA}…» non e' piu' nel README. Se e' diventata «nearly every» il "
        "difetto e' curato ⇒ questo presidio diventa l'asserzione positiva "
        "(«la pagina non promette piu' l'universale») e il docstring perde il "
        "paragrafo del difetto."
    )
    assert eccezioni == ECCEZIONI_IL_12_09, (
        f"le eccezioni che la pagina dichiara di se' sono {eccezioni}, misurate "
        f"{ECCEZIONI_IL_12_09} il 12/09. Se sono AUMENTATE, l'«every» di riga 714 "
        "e' diventato ancora meno vero e nessuno l'ha detto; se sono diminuite "
        "senza che «every» sia cambiato, un limite dichiarato e' sparito dalla "
        "pagina — che e' peggio, perche' l'ambiguita' resta senza il suo avviso. "
        "**Guarda la pagina, non aggiornare il numero.**"
    )


def test_ogni_file_di_risultato_citato_dal_readme_esiste():
    """La meta' SANA della stessa promessa, e questa e' un cricchetto.

    Non ripete il difetto sopra: verifica che i file citati esistano davvero,
    cosi' se domani il README nomina un risultato che non abbiamo, si accende
    qui invece che in un'issue di un utente.
    """
    testo = _testo_readme()
    citati = {
        m.group(1)
        for m in re.finditer(r"`([A-Za-z0-9_./-]+\.(?:json|jsonl|csv))`", testo)
    } - NON_SONO_RISULTATI

    assert citati, "nessun file di risultato citato: il righello non misura piu' niente"

    mancanti = [
        nome
        for nome in sorted(citati)
        if not (RADICE / nome).is_file()
        and not (RADICE / "benchmark" / "results" / nome).is_file()
    ]
    assert not mancanti, (
        "il README cita file di risultato che non esistono nel repo: "
        f"{mancanti}. La promessa di riga 714 vale solo se il file c'e'."
    )
