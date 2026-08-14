#!/usr/bin/env python
"""Verifica che un artefatto non porti registro privato fuori dal progetto.

Il codice sorgente distribuito contiene commenti e docstring scritti durante lo
sviluppo. Alcuni nominano le sessioni di lavoro che li hanno prodotti, o il
committente. Quel testo esce con il pacchetto: finisce su PyPI, e nel caso delle
``description`` dei tool MCP viene letto a runtime dall'agente dell'utente.

Questo controllo si esegue **sull'artefatto che verrà pubblicato**, non
sull'albero di lavoro: si punta a un ``.whl`` (letto senza estrarlo), a un
``.tar.gz``, o a una directory. La ripulitura verificata a mano sul sorgente non
dice nulla su cosa finisce nel pacchetto — l'unico modo per saperlo è misurare
il pacchetto.

    python scripts/controlla_registro.py dist/verimem-0.7.5-py3-none-any.whl
    python scripts/controlla_registro.py .

Uscita 0 se non trova identificativi di sessione, 1 altrimenti: è pensato per
essere eseguito come ultimo passo prima di ``twine upload``.

Le classi sono separate perché non hanno lo stesso peso. Gli identificativi di
sessione non sono mai stati distribuiti: farli uscire è una prima volta, e il
controllo la blocca. Il nome del committente è nel sorgente pubblicato da
luglio: segnalarlo come errore bloccherebbe ogni rilascio senza che nessuno
possa più richiamare quanto è già uscito, quindi viene contato e riportato ma
non fa fallire il controllo.
"""

from __future__ import annotations

import ast
import io
import pathlib
import re
import sys
import tarfile
import tokenize
import zipfile
from collections import Counter, defaultdict

#: I nomi propri assegnati alle sessioni di lavoro. Elencati per esteso perché
#: un'euristica su «parola capitalizzata vicino a wsN» non li prenderebbe dove
#: compaiono da soli, che è il caso più difficile da notare rileggendo.
NOMI_SESSIONE = (
    "Vega|Varco|Saggiatore|Paragone|Riscontro|Vedetta|Mnemo|Tara|Lanterna|"
    "Ester|Archivista|Censore"
)

#: Escluse quando il controllo punta a una directory: copie del sorgente
#: (``build``, ``dist``), ambienti e dipendenze di terzi, cache.
ESCLUSE = frozenset({
    "build", "dist", ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".tox", ".mypy_cache", ".pytest_cache", "site-packages",
})

CLASSI: dict[str, tuple[re.Pattern[str], bool]] = {
    # nome della classe: (pattern, blocca il rilascio)
    "identificativo di sessione": (re.compile(r"\bws[1-8]\b"), True),
    "nome proprio di sessione": (re.compile(rf"\b({NOMI_SESSIONE})\b"), True),
    "nome del committente": (re.compile(r"\bAurelio\b"), False),
}


def _sorgenti(percorso: pathlib.Path):
    """Restituisce (nome, testo) per ogni ``.py`` dell'artefatto.

    Un wheel è uno zip e un sdist un tar: si leggono senza scrivere su disco,
    perché estrarre un pacchetto per controllarlo introduce il rischio di
    controllare la copia sbagliata.
    """
    #: Questo file elenca i pattern per esteso, quindi contiene ciò che cerca:
    #: puntato alla radice del repository si accuserebbe da solo.
    io_stesso = pathlib.Path(__file__).resolve()

    if percorso.is_dir():
        for p in sorted(percorso.rglob("*.py")):
            #: Directory che contengono copie del sorgente o codice di terzi. Senza
            #: questo filtro, puntare il controllo alla radice del progetto esamina
            #: decine di migliaia di file e — peggio — legge ``build/lib/verimem``,
            #: una copia che può essere vecchia di giorni: ``build`` precede
            #: ``verimem`` in ordine alfabetico, quindi in un elenco troncato la
            #: copia morta compare per prima. Il verdetto va dato sull'artefatto
            #: (``.whl``/``.tar.gz``), che di queste directory non ne ha nessuna.
            if ESCLUSE & set(p.parts):
                continue
            if p.name.startswith("."):
                continue
            if p.resolve() == io_stesso:
                continue
            yield str(p.relative_to(percorso)).replace("\\", "/"), p.read_text(
                encoding="utf-8", errors="replace"
            )
    elif percorso.suffix == ".whl" or percorso.suffix == ".zip":
        with zipfile.ZipFile(percorso) as z:
            for nome in sorted(z.namelist()):
                if nome.endswith(".py"):
                    yield nome, z.read(nome).decode("utf-8", errors="replace")
    elif ".tar" in percorso.suffixes or percorso.suffix == ".gz":
        with tarfile.open(percorso) as t:
            for m in sorted(t.getmembers(), key=lambda x: x.name):
                if m.name.endswith(".py") and m.isfile():
                    f = t.extractfile(m)
                    if f is not None:
                        yield m.name, f.read().decode("utf-8", errors="replace")
    else:
        raise SystemExit(f"formato non riconosciuto: {percorso}")


def _righe_di_prosa(testo: str) -> set[int]:
    """Le righe che stanno in un commento o in un docstring.

    È lì che vivono le attribuzioni — «misurato da …», «isolato da …». Fuori,
    un nome che somiglia a un identificativo è quasi sempre un identificatore:
    ``ws = tmp_path / "ws1"`` usa ``ws`` per *workspace*. Il controllo blocca
    sulla prosa e conta il resto a parte, perché un veto su un'omonimia insegna
    a ignorare il controllo — e un controllo ignorato non presidia niente.

    I docstring si trovano con ``ast`` (sono espressioni-stringa in testa a
    modulo, classe o funzione); i commenti con ``tokenize``. Se il file non si
    analizza — sintassi di una versione diversa, o troncato — si considera
    tutto prosa: meglio un falso allarme che un'assenza silenziosa.
    """
    prosa: set[int] = set()
    try:
        albero = ast.parse(testo)
    except SyntaxError:
        return set(range(1, testo.count("\n") + 2))

    for nodo in ast.walk(albero):
        if not isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        corpo = getattr(nodo, "body", None)
        if not corpo:
            continue
        primo = corpo[0]
        if (isinstance(primo, ast.Expr) and isinstance(primo.value, ast.Constant)
                and isinstance(primo.value.value, str)):
            fine = getattr(primo, "end_lineno", primo.lineno)
            prosa.update(range(primo.lineno, fine + 1))

    try:
        for tok in tokenize.generate_tokens(io.StringIO(testo).readline):
            if tok.type == tokenize.COMMENT:
                prosa.add(tok.start[0])
    except (tokenize.TokenError, IndentationError):
        pass
    return prosa


#: Un collaudo di questo controllo deve **contenere** gli identificativi che il
#: controllo cerca: sono i suoi dati di prova. Senza un'uscita, il controllo
#: boccia il file che dimostra che funziona, e l'unico modo di far passare il
#: rilascio diventa cancellare quella prova — un veto che punisce il proprio
#: collaudo si fa disattivare, non correggere.
#:
#: L'uscita ha tre limiti, e sono la ragione per cui è accettabile:
#:   - vale **solo** per i file di collaudo: un modulo del prodotto non può
#:     esentarsi, ed è la parte che l'artefatto installato porta davvero;
#:   - chiede una **ragione scritta** sulla stessa riga, che finisce nel referto:
#:     chi la mette deve dire perché, e chi legge lo vede;
#:   - le righe esentate **restano contate** e vengono dichiarate. Un'esenzione
#:     silenziosa fa apparire pulito ciò che non lo è, che è esattamente il
#:     difetto contro cui questo controllo esiste.
MARCATORE = re.compile(r"registro-esente:\s*(?P<ragione>\S.*)")


def _esenzione(nome: str, testo: str) -> str | None:
    """La ragione dichiarata, se il file è un collaudo e la dichiara."""
    if not pathlib.PurePath(nome).name.startswith("test_"):
        return None
    trovato = MARCATORE.search(testo)
    return trovato.group("ragione").strip()[:90] if trovato else None


def controlla(percorso: pathlib.Path) -> int:
    conteggi: Counter[str] = Counter()
    file_per_classe: defaultdict[str, set[str]] = defaultdict(set)
    esempi: defaultdict[str, list[str]] = defaultdict(list)
    totale_file = 0

    in_codice: Counter[str] = Counter()
    esempi_codice: defaultdict[str, list[str]] = defaultdict(list)
    esentate: Counter[str] = Counter()
    ragioni: dict[str, str] = {}

    for nome, testo in _sorgenti(percorso):
        totale_file += 1
        prosa = _righe_di_prosa(testo)
        ragione = _esenzione(nome, testo)
        for riga_n, riga in enumerate(testo.splitlines(), 1):
            for classe, (pattern, _) in CLASSI.items():
                for trovato in pattern.finditer(riga):
                    voce = f"{nome}:{riga_n}  [{trovato.group(0)}]  {riga.strip()[:70]}"
                    if riga_n not in prosa:
                        #: Fuori da commenti e docstring il nome è quasi sempre un
                        #: identificatore che gli somiglia — `ws = tmp_path / "ws1"`
                        #: dove `ws` sta per *workspace*. Contato a parte: bloccare
                        #: su un'omonimia insegna a ignorare il controllo.
                        in_codice[classe] += 1
                        if len(esempi_codice[classe]) < 3:
                            esempi_codice[classe].append(voce)
                        continue
                    if ragione is not None:
                        esentate[nome] += 1
                        ragioni[nome] = ragione
                        continue
                    conteggi[classe] += 1
                    file_per_classe[classe].add(nome)
                    if len(esempi[classe]) < 5:
                        esempi[classe].append(voce)

    print(f"artefatto: {percorso}")
    print(f"file .py esaminati: {totale_file}\n")
    blocca = False
    for classe, (_, bloccante) in CLASSI.items():
        n = conteggi[classe]
        marchio = "BLOCCA" if (n and bloccante) else ("     " if n else "  ok ")
        print(f"  {marchio}  {classe:30s} {n:>5d} in {len(file_per_classe[classe]):>3d} file")
        if n and bloccante:
            blocca = True

    if esentate:
        #: Dichiarate sempre, col nome del file e la ragione: un'esenzione che
        #: non compare nel referto è indistinguibile da un'assenza di difetti.
        print(f"\n  esentate perché dati di prova di un collaudo "
              f"({sum(esentate.values())} righe in {len(esentate)} file):")
        for nome in sorted(esentate):
            print(f"     {esentate[nome]:>4d}  {nome}  — {ragioni[nome]}")

    if sum(in_codice.values()):
        print("\n  fuori da commenti e docstring, NON bloccanti "
              "(un nome che somiglia, non un'attribuzione):")
        for classe, n in in_codice.items():
            if n:
                print(f"     {classe:30s} {n:>5d}")
        for classe in CLASSI:
            for riga in esempi_codice[classe][:2]:
                print(f"       {riga}")

    for classe in CLASSI:
        if esempi[classe]:
            print(f"\n-- {classe}, primi {len(esempi[classe])} --")
            for riga in esempi[classe]:
                print(f"   {riga}")

    if blocca:
        print(
            "\nIl pacchetto porterebbe fuori dal progetto identificativi interni.\n"
            "Le righe vanno riscritte a mano: spiegano il perché di una scelta, e\n"
            "una sostituzione automatica lascia una frase grammaticalmente rotta o\n"
            "vuota di significato."
        )
        return 1
    print("\nNessun identificativo di sessione nell'artefatto.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    sys.exit(controlla(pathlib.Path(sys.argv[1])))
