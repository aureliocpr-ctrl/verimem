"""Il README additava le proprie prove con link che sulla pagina pubblica sono 404.

⚠️ IL DIFETTO NON È NEL PACCHETTO, È IN DOVE IL PACCHETTO VIENE LETTO. Il README
è anche la **pagina PyPI**, e lì un link relativo viene risolto rispetto a
`pypi.org`, non al repository::

    [BENCHMARKS.md](./docs/BENCHMARKS.md)
      su GitHub  → funziona
      su PyPI    → https://pypi.org/project/verimem/docs/BENCHMARKS.md  → 404

Erano **sette**: quattro verso `docs/`, tre verso `benchmark/`. E non sono link
qualunque — sono quelli che il README addita come **prova** delle sue
affermazioni («Method and raw numbers: …», «run it yourself», la riga della
tabella che cita il bench). ⇒ Un lettore che volesse verificare i nostri numeri
trovava una pagina che non esiste, proprio nel punto in cui gli dicevamo di
controllare.

═══ E DOPO L'INSTALLAZIONE È PEGGIO, non meglio ═══

Misurato su ciò che il wheel contiene davvero::

    package che arrivano all'utente:   9   (verimem, i due shim, 6 sottopacchetti)
    docs/        163 file nell'albero  ·  nel wheel: NO
    benchmark/   753 file             ·  nel wheel: NO
    tests/      2898 file             ·  nel wheel: NO
    scripts/     157 file             ·  nel wheel: NO

Quelle cartelle **non devono** stare nel pacchetto — un utente non installa i
nostri test. Ma allora un link relativo, dopo `pip install`, non punta a niente
né su PyPI né su disco: **l'unico posto dove quelle prove esistono è il
repository**, e il link deve dirlo.

📌 Questo test nasce dal mandato «la 0.7.5 deve essere perfetta» e dalla frase
che lo accompagna — *«una volta pubblica installiamo la 0.7.5 su di noi»*. Da
quel momento il README che leggeremo sarà quello del pacchetto: un link rotto lì
lo troveremo noi per primi.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_README = Path(__file__).resolve().parents[1] / "README.md"

#: Le cartelle che il README addita come prova e che il pacchetto NON contiene.
#: ⚠️ Non è una scelta da correggere: `tests/`, `docs/` e `benchmark/` fuori dal
#: wheel è giusto — nessuno installa 2898 file di test. È il LINK che deve
#: tenerne conto, non il packaging.
FUORI_DAL_PACCHETTO = ("docs", "benchmark", "tests", "scripts")


def test_nessun_link_relativo_verso_cio_che_il_pacchetto_non_contiene():
    """Il cuore. La regola è condizionale: non vieta di citare le prove —
    pretende che il link porti dove esistono davvero."""
    testo = _README.read_text(encoding="utf-8")
    rotti = re.findall(
        r"\]\(\.?/?(" + "|".join(FUORI_DAL_PACCHETTO) + r")/[^)]+\)", testo)
    assert not rotti, (
        f"{len(rotti)} link relativi puntano a cartelle assenti dal pacchetto "
        f"{sorted(set(rotti))}: su PyPI danno 404 e dopo l'installazione non "
        f"esistono su disco. Vanno resi assoluti verso il repository."
    )


def test_LE_PROVE_SONO_ANCORA_CITATE_e_raggiungibili():
    """⚠️ IL VERSO OPPOSTO, e senza questo il test sopra si «supera» cancellando.

    La cura sbagliata sarebbe togliere i link: il README smetterebbe di additare
    le proprie prove e passerebbe il controllo restando peggiore. Qui si
    pretende che i riferimenti ci siano **e** che siano assoluti.
    """
    testo = _README.read_text(encoding="utf-8")
    assoluti = re.findall(
        r"\]\(https://github\.com/[^)]+/(?:docs|benchmark)/[^)]+\)", testo)
    assert len(assoluti) >= 5, (
        f"il README cita solo {len(assoluti)} prove con link assoluto: se sono "
        f"state tolte invece che corrette, il documento è peggiorato — le "
        f"affermazioni misurate devono restare verificabili"
    )


@pytest.mark.parametrize("frammento,e_rotto", [
    ("[BENCHMARKS.md](./docs/BENCHMARKS.md)", True),
    ("[gov](docs/GOVERNANCE.md)", True),
    ("[bench](/benchmark/trustmem_bench.py)", True),
    # ⚠️ la popolazione opposta: questi NON devono essere segnalati
    ("[BENCHMARKS.md](https://github.com/x/y/blob/main/docs/BENCHMARKS.md)", False),
    ("[licenza](./LICENSING.md)", False),          # sta nella radice, non in una cartella
    ("[sito](https://verimem.com)", False),
])
def test_IL_RICONOSCITORE_prende_i_rotti_e_non_i_buoni(frammento, e_rotto):
    """Il banco del misuratore: un criterio che segnalasse anche i link assoluti
    o quelli alla radice renderebbe il presidio rumoroso, e un presidio rumoroso
    viene spento."""
    trovato = bool(re.search(
        r"\]\(\.?/?(" + "|".join(FUORI_DAL_PACCHETTO) + r")/[^)]+\)", frammento))
    assert trovato is e_rotto, frammento
