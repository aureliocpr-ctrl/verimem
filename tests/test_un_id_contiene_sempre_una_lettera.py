"""T84 — un id di sole cifre si legge come un numero.

Gli id del prodotto sono un uuid tagliato: `uuid.uuid4().hex[:n]`. In
esadecimale ogni carattere è una cifra con probabilità 10/16, quindi un id di
sole cifre esce con probabilità (10/16)^n::

    hex[: 8]    2.3283%   uno ogni 43
    hex[:12]    0.3553%   uno ogni 281
    hex[:16]    0.0542%   uno ogni 1.845

Su un campione di 20.000 il conto dà 71 attesi per la lunghezza 12, e la misura
indipendente ne ha contati 80 — dentro la fluttuazione di un conteggio così.

⚠️ E IL TICKET NE NOMINAVA UNO, MA I PUNTI SONO 19 IN 16 FILE — misurato::

    grep -rn "uuid4().hex\\[:" verimem/*.py   ->  19 occorrenze, 16 file
    per lunghezza: 1 volta hex[:8], 10 volte hex[:12], 8 volte hex[:16]

⇒ Il caso peggiore **non è quello nominato**: `hex[:8]` sbaglia uno ogni 43,
cioè sei volte e mezzo più spesso dell'id dei fatti. Curare il punto del ticket
lascerebbe in piedi il difetto dov'è più probabile.

🔑 LA CURA NON CAMBIA L'ALFABETO. «Almeno una lettera» in esadecimale vuol dire
almeno un carattere fra `a` e `f`: l'id resta un esadecimale valido della
stessa lunghezza, e nessuno che lo legga oggi si accorge della differenza —
tranne chi lo stava scambiando per un numero.

Ticket: T84.
"""

from __future__ import annotations

import pathlib
import re
import uuid

import pytest

from verimem.ids import id_nuovo

RADICE = pathlib.Path(__file__).resolve().parents[1] / "verimem"
#: Il taglio nudo di un uuid: è la forma che questo ticket toglie di mezzo.
TAGLIO_NUDO = re.compile(r"uuid4\(\)\.hex\[:")


def _solo_cifre(s: str) -> bool:
    return s.isdigit()


def test_CONTROLLO_il_caso_temuto_esiste_davvero(monkeypatch):
    """⚠️ SENZA QUESTO le celle sotto potrebbero passare su un caso che non
    capita mai: se il taglio nudo non producesse MAI sole cifre, questo ticket
    curerebbe un'ipotesi. Qui si fabbrica il caso e lo si guarda."""
    monkeypatch.setattr(uuid, "uuid4",
                        lambda: uuid.UUID("12345678901234567890123456789012"))
    assert _solo_cifre(uuid.uuid4().hex[:12]), (
        "il caso temuto non si riproduce nemmeno forzandolo: il difetto "
        "andrebbe ridescritto prima di curarlo")


@pytest.mark.parametrize("lunghezza", (8, 12, 16))
def test_un_id_ha_sempre_una_lettera_anche_quando_il_caso_e_forzato(
        monkeypatch, lunghezza):
    """IL CUORE: con l'orologio truccato perché dia sole cifre, l'id non lo è.

    Il generatore viene forzato a restituire un uuid tutto numerico — il caso
    che in natura esce uno ogni 43 alla lunghezza 8. `id_nuovo` deve renderlo
    lo stesso un id con almeno una lettera.
    """
    monkeypatch.setattr(uuid, "uuid4",
                        lambda: uuid.UUID("12345678901234567890123456789012"))
    ident = id_nuovo(lunghezza)
    assert len(ident) == lunghezza, (
        f"l'id è lungo {len(ident)} invece di {lunghezza}: la cura ha cambiato "
        "la forma degli id, non solo il loro contenuto")
    assert not _solo_cifre(ident), (
        f"l'id {ident!r} è di sole cifre: si legge come un numero")
    assert re.fullmatch(r"[0-9a-f]+", ident), (
        f"l'id {ident!r} non è più un esadecimale valido: la cura ha cambiato "
        "l'alfabeto, e chi lo legge oggi si rompe")


def test_l_id_resta_diverso_a_ogni_chiamata():
    """⚠️ Una cura che garantisse la lettera restituendo sempre lo stesso
    valore passerebbe la cella sopra e distruggerebbe il prodotto. Il negativo
    che serve: mille id, mille valori."""
    visti = {id_nuovo(12) for _ in range(1000)}
    assert len(visti) == 1000, (
        f"su 1000 id ne sono usciti {len(visti)} distinti: la cura ha "
        "introdotto collisioni")


def test_nessun_file_taglia_piu_un_uuid_per_conto_suo():
    """IL CRICCHETTO: 19 punti in 16 file, e il ventesimo nascerebbe uguale.

    Un difetto che sta in diciannove posti non si cura in uno; e un modulo
    nuovo che nessuno chiama è il modo in cui una cura resta scritta e non
    applicata.
    """
    colpevoli = []
    for f in sorted(RADICE.glob("*.py")):
        if f.name == "ids.py":
            continue
        testo = f.read_text(encoding="utf-8", errors="replace")
        codice = chr(10).join(r.split("#", 1)[0] for r in testo.splitlines())
        n = len(TAGLIO_NUDO.findall(codice))
        if n:
            colpevoli.append(f"{f.name}:{n}")
    assert not colpevoli, (
        f"{len(colpevoli)} file tagliano ancora un uuid per conto loro invece "
        f"di chiamare `ids.id_nuovo`: {', '.join(colpevoli)}. Il caso peggiore "
        "è la lunghezza 8, che sbaglia uno ogni 43.")
