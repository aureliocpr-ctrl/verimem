"""Un percorso stampato esce INTERO, su ogni riga che ne stampa uno.

Un percorso serve per essere letto e COPIATO: chi riceve «file not found» o
«cercato in: …» deve poter prendere quella stringa e usarla. La resa a colonne
di `rich` manda a capo dentro la parola quando la riga è più larga del
terminale, e un percorso spezzato non è più un percorso.

⚠️ QUESTO PRESIDIO NASCE DA UNO SWEEP MANCATO — il mio. Il 06/09 la CI ha
fermato la riga che dichiara lo store (`.../semantic/semant\\nic.db`), l'ho
curata con `soft_wrap=True` e ho consegnato. Poi ho contato: altre SETTE righe
di `cli.py` stampavano un percorso, e nessuna era curata. Misurato eseguendo,
prima di toccarle:

    file not found:
    C:/Users/aurel/.../una-cartella-con-un-nome-molto-lungo-per-forz
    are-il-ritorno-a-capo/e-un-altro-livello/file-inesistente.md

⇒ curare UN punto e chiamarla cura è la classe «manca lo SWEEP», la stessa che
avevo appena diagnosticato per T16 (`--db` c'era su due comandi e non sulle
porte). Averla riprodotta il giorno stesso è la ragione per cui questo file
presidia la REGOLA e non i sette casi: un elenco di casi invecchia alla prossima
riga che qualcuno aggiunge, una regola no.

⚠️ E LEGGE IL SORGENTE, il che è un limite dichiarato: non prova che l'uscita
sia intera, prova che nessuno stampi un percorso senza chiederlo. La prova sul
comportamento sta in `test_le_porte_aprono_lo_store_che_indichi.py`
(`test_il_percorso_esce_INTERO_e_non_va_a_capo`), che esegue la porta. Le due
si coprono a vicenda: quella misura un caso davvero, questa impedisce che
nascano casi nuovi.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_CLI = Path(__file__).resolve().parent.parent / "verimem" / "cli.py"

#: Le forme che, dentro una `console.print`, dicono «qui c'è un percorso».
#:
#: ⚠️ SI CERCA UN'INTERPOLAZIONE, NON LA PAROLA. La prima stesura usava
#: `\bpath\b` e ha dato TRE falsi positivi su quattro: `{info.path.name}` è un
#: NOME (corto, non si spezza) e «rerun with the audit path» è prosa inglese.
#: Un presidio che segnala il triplo del vero si smette di leggere, ed è il
#: modo in cui un controllo muore senza che nessuno lo spenga.
_SEGNALI = re.compile(
    r"\{[^}]*(?:db_path|log_path|percorso)[^}]*\}"       # {…db_path…}
    r"|\{[^}]*\.path\b(?!\.name)[^}]*\}"                 # {info.path} ma non .name
    r"|file not found:|data dir\[|cercato in")


def _righe_che_stampano_un_percorso() -> list[tuple[int, str]]:
    """Le `console.print` che interpolano qualcosa che somiglia a un percorso.

    Si guarda l'istruzione INTERA, non la riga: una `print` su più righe ha il
    percorso in cima e `soft_wrap` in fondo, e riga per riga non si vedrebbero
    mai insieme.
    """
    testo = _CLI.read_text(encoding="utf-8")
    righe = testo.splitlines()
    fuori: list[tuple[int, str]] = []
    i = 0
    while i < len(righe):
        if "console.print(" not in righe[i]:
            i += 1
            continue
        pezzi, j, aperte = [righe[i]], i, 0
        while j < len(righe):
            aperte += righe[j].count("(") - righe[j].count(")")
            if j > i:
                pezzi.append(righe[j])
            if aperte <= 0:
                break
            j += 1
        istruzione = "\n".join(pezzi)
        if _SEGNALI.search(istruzione) and "soft_wrap" not in istruzione:
            fuori.append((i + 1, righe[i].strip()[:88]))
        i = j + 1
    return fuori


def test_il_banco_vede_qualcosa(monkeypatch) -> None:
    """CONTROLLO POSITIVO: se il parser non trova nessuna `console.print`, il
    test qui sotto starebbe verde per cecità e non per pulizia."""
    testo = _CLI.read_text(encoding="utf-8")
    assert testo.count("console.print(") > 20, (
        "il parser non riconosce più le stampe: questo file non misura nulla")
    assert "soft_wrap=True" in testo, (
        "nessuna riga usa soft_wrap: o la cura è sparita, o il nome è cambiato")


def test_nessuna_riga_stampa_un_percorso_che_puo_andare_a_capo() -> None:
    fuori = _righe_che_stampano_un_percorso()
    assert not fuori, (
        "queste `console.print` stampano un percorso e possono spezzarlo a "
        "metà su un terminale stretto — un percorso troncato non si copia, ed "
        "è l'unica cosa per cui lo si stampa. Aggiungi `soft_wrap=True`:\n"
        + "\n".join(f"    cli.py:{n}  {r}" for n, r in fuori))
