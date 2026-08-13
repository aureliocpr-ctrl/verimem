"""Ogni capacita' che il README dichiara deve avere un test ancorato alla sua riga.

PERCHE' QUESTO FILE ESISTE, e perche' NON basta avere test sulla funzionalita'.
Il README porta una tabella «Capability» che dichiara, riga per riga, cosa il
prodotto FA. Misurato il 2026-08-13: cercando nei test la stringa esatta di
ciascuna riga, **sei righe su otto danno zero file**. Solo «Bi-temporal history»
(2) e «True forget» (1) sono nominate.

L'obiezione ovvia — *«ma di test sull'astensione e sul gate ne abbiamo a
decine»* — e' vera e non salva la promessa. Il criterio B chiede che ogni
promessa SCRITTA abbia un test che la prova, e la differenza fra le due cose ha
gia' un precedente nostro con nome e cognome:
``test_il_readme_non_puo_invertire_il_bench_che_cita`` esiste perche' il README
dichiarava «abstains 2/2» mentre il file che linkava diceva «abstained 0» —
un'inversione esatta, sulla promessa centrale, nella direzione a noi comoda.
**I test sull'astensione c'erano ed erano verdi.** Non l'hanno vista perche'
provavano l'astensione, non la RIGA.

COME E' COSTRUITO, e perche' cosi':

- la tabella e' letta DAL README a ogni esecuzione, non ricopiata qui. Se
  qualcuno aggiunge una capacita', il caso nuovo compare da solo;
- una riga nuova non elencata in ``SCOPERTE_NOTE`` **fallisce subito**, e cosi'
  dev'essere: una promessa aggiunta senza presidio deve fare rumore nel commit
  che la aggiunge, non sei mesi dopo;
- le sei scoperte di oggi sono marcate xfail **una per una**, non in blocco.
  Con ``strict=True`` il giorno in cui qualcuno scrive il presidio per UNA di
  esse quel caso diventa ROSSO, e chi l'ha scritto toglie la sua voce da
  ``SCOPERTE_NOTE``. **Il presidio si arma una riga alla volta**, che e' l'unico
  modo perche' un debito di sei voci venga pagato da sei persone diverse in sei
  momenti diversi.

⚠️ LIVELLO DELLA MISURA, dichiarato: si cerca la **stringa** della capacita' nei
file di test. Un presidio che citasse la promessa parafrasata non verrebbe
visto, quindi il conto delle scoperte e' un **limite superiore**. E' la stessa
ragione per cui il criterio qui non e' «esiste un test che prova X» — che
nessuno strumento sa decidere — ma «esiste un test che NOMINA la riga»: debole,
ma verificabile, e sufficiente a impedire che la riga e il codice divergano in
silenzio come e' gia' successo.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

README = Path(__file__).resolve().parents[1] / "README.md"
TESTS = Path(__file__).resolve().parent

#: Intestazione della tabella da presidiare, come compare nel README.
_INTESTAZIONE = "| Capability |"

#: Le sei capacita' senza presidio al 2026-08-13, con il file che le ha misurate.
#: Togliere una voce da qui quando il suo presidio esiste — il test lo impone,
#: perche' con xfail(strict=True) il caso curato diventa rosso finche' la voce
#: resta. NON aggiungere voci per far passare una riga nuova: una promessa nuova
#: senza test deve fermare il commit che la introduce.
SCOPERTE_NOTE = frozenset({
    "Conflicting well-grounded memories resolved",
    "Runs fully air-gapped",
})
# Tolta il 2026-08-13: «Provenance on every read» ha ora il suo presidio in
# test_ogni_porta_di_lettura_porta_la_provenienza.py, che nel presidiarla ha
# trovato che la promessa regge su due elementi su tre — chi l'ha scritto e con
# che verdetto escono, il riferimento alla fonte no. Il debito e' passato da
# «nessuno la guarda» a «qualcuno la guarda e il difetto e' scritto», ed e' il
# punto di questo meccanismo: la voce si toglie quando il presidio esiste, non
# quando la promessa e' perfetta.

_CODICE = re.compile(r"`[^`]*`")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _capacita_dichiarate() -> list[str]:
    """I titoli delle righe della tabella «Capability», letti dal README.

    Il titolo e' la prima cella, ripulita di codice e link e troncata al primo
    segno di parentesi: «Trust axes under adversarial pressure ([TrustMem-Bench]
    (...), deterministic)» diventa «Trust axes under adversarial pressure», che
    e' la parte stabile — i link cambiano, la promessa no.
    """
    righe = README.read_text(encoding="utf-8").splitlines()
    fuori: list[str] = []
    dentro = False
    for riga in righe:
        spoglia = riga.strip()
        if _INTESTAZIONE in spoglia:
            dentro = True
            continue
        if not dentro:
            continue
        if not spoglia.startswith("|"):
            break  # la tabella e' finita
        if set(spoglia) <= set("|-: "):
            continue  # riga di separazione
        prima = spoglia.split("|")[1] if "|" in spoglia else spoglia
        titolo = _LINK.sub(r"\1", _CODICE.sub(" ", prima))
        fuori.append(_parte_stabile(titolo))
    return [t for t in fuori if t]


#: Dove finisce la parte STABILE di un titolo: tutto cio' che segue e' glossa.
_GLOSSA = re.compile(r"[(&,:]")


def _parte_stabile(titolo: str) -> str:
    """La chiave di ricerca: la parte del titolo che un presidio citerebbe.

    ⚠️ Serve, e la prima versione di questo file non ce l'aveva: cercando il
    titolo INTERO, «Bi-temporal history & time travel» risultava scoperta pur
    avendo **due** presidi che la nominano come «Bi-temporal history». Il test
    dichiarava un buco dove il buco non c'era — un falso allarme e' peggio del
    silenzio, perche' manda qualcuno a scrivere un presidio che esiste gia'.

    Due tagli, in quest'ordine:
      1. alla prima glossa — parentesi, «&», virgola, due punti: «True forget
         (GDPR): deleted data...» -> «True forget»;
      2. a quattro parole, per i titoli che non hanno glossa: «Abstains instead
         of fabricating when the store can't support an answer» -> «Abstains
         instead of fabricating».
    Il quattro e' una scelta, non una misura: e' il piu' corto che tiene
    distinte tutte le righe della tabella di oggi, e se un domani due righe
    collidessero il primo test di questo file lo direbbe.
    """
    testo = " ".join(_GLOSSA.split(titolo, 1)[0].replace("*", "").split())
    return " ".join(testo.split()[:4])


def _presidi(capacita: str) -> list[str]:
    """I file di test che nominano questa capacita'. Esclude se stesso."""
    fuori = []
    for f in sorted(TESTS.glob("test_*.py")):
        if f.name == Path(__file__).name:
            continue
        try:
            if capacita in f.read_text(encoding="utf-8", errors="ignore"):
                fuori.append(f.name)
        except OSError:
            continue
    return fuori


def _casi():
    """Un caso per capacita', con xfail individuale su quelle note scoperte."""
    for c in _capacita_dichiarate():
        marchi = []
        if c in SCOPERTE_NOTE:
            marchi.append(pytest.mark.xfail(
                strict=True,
                reason=(
                    f"debito noto al 2026-08-13: nessun test nomina «{c}». "
                    "strict: scritto il presidio, questo caso diventa ROSSO — "
                    "togliere la voce da SCOPERTE_NOTE."
                ),
            ))
        yield pytest.param(c, marks=marchi, id=c[:45].replace(" ", "_"))


def test_la_tabella_delle_capacita_e_ancora_leggibile() -> None:
    """Precondizione: se la tabella sparisce, i casi sotto diventano ZERO e tacciono.

    Senza questo, spostare o rinominare la tabella renderebbe l'intero file
    verde per assenza di casi — la forma piu' silenziosa di sensore scollegato.
    """
    capacita = _capacita_dichiarate()
    assert len(capacita) >= 6, (
        f"la tabella «Capability» del README non e' piu' leggibile: trovate "
        f"{len(capacita)} righe ({capacita}). Se e' stata spostata o riscritta, "
        f"aggiorna _INTESTAZIONE; se e' stata TOLTA, questo file va tolto con lei"
    )
    ignote = set(SCOPERTE_NOTE) - set(capacita)
    assert not ignote, (
        f"SCOPERTE_NOTE elenca capacita' che il README non dichiara piu': "
        f"{sorted(ignote)}. Una voce che non corrisponde a nessuna riga non "
        f"protegge niente — vanno tolte"
    )


@pytest.mark.parametrize("capacita", list(_casi()))
def test_la_capacita_dichiarata_ha_un_test_che_la_nomina(capacita: str) -> None:
    presidi = _presidi(capacita)
    assert presidi, (
        f"il README dichiara «{capacita}» e nessun test nomina quella riga. "
        f"Avere test sulla funzionalita' non basta: «abstains 2/2» era invertito "
        f"rispetto al proprio bench mentre i test sull'astensione erano verdi"
    )
