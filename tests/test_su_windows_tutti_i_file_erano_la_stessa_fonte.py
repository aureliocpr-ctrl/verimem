"""`file:C:/progetto/alfa.py` e `file:C:/altro/beta.py` erano la stessa fonte.

TROVATO leggendo i candidati della mappa `mappa_due_esiti.py` (2026-08-04), sul
percorso che decide CHI PUÒ RITIRARE CHI. `canonical_source` estrae la chiave
di reputazione con:

    _SOURCE_REF_RE = re.compile(r"^(?:source-doc|source|src|doc|file):([^:]+)")

Il `[^:]+` si ferma al primo due punti — che su Windows è quello del **drive**:

    file:C:/Users/aurel/Code/verimem/gate.py   ->  'C'
    file:D:/altro/percorso/b.py                ->  'D'
    file:/home/utente/progetto/c.py            ->  '/home/utente/progetto/c.py'
    file:relativo/d.py                         ->  'relativo/d.py'

I due path POSIX funzionano, i due Windows no. Conseguenza: **tutti i file
dello stesso drive collassano su una chiave sola**, quindi `is_same_source` li
dichiara la stessa fonte e `classify_write_relation` può classificare come
«evolution» — cioè far ritirare l'uno dall'altro — due fatti che vengono da
documenti diversi.

Sul corpus di produzione ci sono già **43 fatti** con `canonical_source = 'C'`.

È la stessa classe pagata più volte in questi giorni: un'espressione tarata su
un mondo — qui POSIX, dove i path non contengono due punti — e usata su tutti.
E si vede solo dove il prodotto gira davvero: su Windows.

⚠️ IL FORMATO STRUTTURATO DEVE RESTARE. `source-doc:X:qualcosa` usa il secondo
due punti come SEPARATORE e deve continuare a dare `X` — il docstring lo
dichiara. La cura riguarda solo il caso in cui ciò che segue è un path con un
drive, riconoscibile perché è **una lettera sola seguita da due punti e da uno
slash** (in avanti o all'indietro). Nessun identificatore di documento ha
quella forma.
"""
from __future__ import annotations

import pytest

from verimem.source_trust import canonical_source
from verimem.supersession_policy import is_same_source


class _F:
    def __init__(self, vb):
        self.verified_by = vb
        self.created_at = 1.0
        self.asserted_at = None


#: Path Windows: il drive NON è l'identità del documento.
WINDOWS = [
    (r"file:C:/Users/aurel/Code/verimem/gate.py", "C:/Users/aurel/Code/verimem/gate.py"),
    ("file:C:" + "\\" + "Users" + "\\" + "aurel" + "\\" + "a.py",
     "C:" + "\\" + "Users" + "\\" + "aurel" + "\\" + "a.py"),
    (r"file:D:/altro/percorso/b.py", "D:/altro/percorso/b.py"),
    (r"doc:E:/archivio/relazione.md", "E:/archivio/relazione.md"),
]


@pytest.mark.parametrize("ref,atteso", WINDOWS)
def test_un_path_windows_non_si_riduce_al_drive(ref, atteso):
    """Il cuore: la chiave deve identificare il DOCUMENTO, non il disco su cui
    sta."""
    assert canonical_source([ref]) == atteso, (
        f"«{ref}» ridotto a «{canonical_source([ref])}»: tutti i file di quel "
        f"drive diventano la stessa fonte")


def test_due_file_sullo_stesso_drive_sono_fonti_DIVERSE():
    """Il danno, end-to-end sul percorso che decide i ritiri: finché la chiave
    è il drive, due documenti scollegati risultano la stessa origine e uno può
    ritirare l'altro."""
    a = _F([r"file:C:/progetto/alfa.py"])
    b = _F([r"file:C:/altro/beta.py"])
    assert not is_same_source(a, b), (
        "due file diversi sullo stesso drive risultano la stessa fonte")


@pytest.mark.parametrize("ref,atteso", [
    (r"file:/home/utente/progetto/c.py", "/home/utente/progetto/c.py"),
    (r"file:relativo/d.py", "relativo/d.py"),
    (r"src:verimem/gate.py", "verimem/gate.py"),
])
def test_i_path_che_gia_funzionavano_non_si_muovono(ref, atteso):
    """POSIX e relativi non hanno mai avuto il problema: la cura non deve
    toccarli."""
    assert canonical_source([ref]) == atteso


def test_il_formato_STRUTTURATO_resta_intatto():
    """`source-doc:X:qualcosa` usa il secondo due punti come SEPARATORE e deve
    continuare a dare `X` — è il contratto dichiarato nel docstring. Senza
    questo presidio la cura del drive romperebbe il formato che la funzione
    esiste per leggere."""
    assert canonical_source(["source-doc:relazione2026:pagina4"]) == "relazione2026"
    assert canonical_source(["source:archivio:sezione2"]) == "archivio"


def test_il_fallback_non_cambia():
    assert canonical_source([]) == "user"
    assert canonical_source(None) == "user"
    assert canonical_source(["commit:abc123"]) == "user"
