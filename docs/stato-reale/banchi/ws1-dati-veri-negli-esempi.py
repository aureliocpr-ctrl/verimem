"""Dati REALI dentro gli esempi delle docstring — quelli che escono da `--help`.

    python docs/stato-reale/banchi/ws1-dati-veri-negli-esempi.py [--wheel 0.7.0]

PERCHE' ESISTE. Il 10/08 la caccia agli identificativi interni (`wsN`, nomi di
persona) ha ripulito commenti e docstring in decine di file. Ma cercava CHI e'
nominato, e ha lasciato passare una cosa diversa: nell'esempio del comando
`facts add` c'era il dominio di un asset reale con accanto il topic di un test
di sicurezza svolto su di esso. Nessun `wsN`, nessun nome di persona — e quindi
invisibile a quel criterio.

🔑 UN ESEMPIO E' LA RIGA PIU' ESPOSTA DI UN SORGENTE, per tre ragioni insieme:
  * esce da ``--help`` e dalla pagina PyPI: non serve leggere il codice;
  * e' il posto dove si incolla dalla propria sessione, perche' un esempio
    "vero" e' piu' veloce da scrivere di uno inventato;
  * viene copiato dagli utenti, quindi si propaga.
Le due occorrenze di quel dominio erano nel wheel 0.7.0 pubblicato su PyPI.

⚠️ COSA CERCA, e sono due segnali FALSIFICABILI, non un giudizio di stile:
  ① un percorso con un nome utente che non e' un segnaposto
     (`C:\\Users\\<nome>`, `/home/<nome>`), perche' identifica una macchina;
  ② un dominio che NON e' fra quelli riservati alla documentazione dalla
     RFC 2606 e dalla RFC 6761 (`example.*`, `test`, `invalid`, `localhost`).
Un nome inventato non e' un difetto: `alice@example.com` va benissimo. Il
difetto e' il dato che punta a una persona, una macchina o un'organizzazione
che esistono.

⚠️ COSA NON CERCA, dichiarato perche' NON e' coperto e non deve sembrarlo:
chiavi, token, indirizzi IP, id di ticket, numeri di telefono. Ognuno vuole un
segnale suo e un banco che li mescola non sa piu' quale sta misurando.

📌 La popolazione OPPOSTA e' nel referto: quanti esempi esistono in totale.
Senza, «trovati 3» non dice se sono tre su quattro o tre su duecento — e sui
soli positivi qualunque criterio sembra ottimo.

🪞 PERCHE' SOLO LE RIGHE DI ESEMPIO, misurato e non deciso a tavolino. Cercando
in TUTTE le righe di docstring dell'albero i due segnali danno **14 esiti**, e
sono tutti legittimi::

    arxiv.org · doi.org        citazioni bibliografiche
    github.com · gitlab.com    riferimenti a repository
    claude.ai · x.com          servizi nominati nella prosa
    evil-localhost.attacker.com · 127.0.0.1.evil.com
                               casi di test di SICUREZZA, inventati apposta

Un dominio nella prosa e' quasi sempre una citazione; un dominio dentro un
comando che l'utente copiera' e' quasi sempre un dato di chi l'ha scritto. Il
banco misura il secondo caso, e i 14 sopra sono la prova che allargarlo al
primo lo renderebbe inutilizzabile — inclusi due domini FINTI che verrebbero
segnalati come difetti.

⚠️ QUESTO E' UN CONFINE, NON UNA DISTINZIONE CHE IL CRITERIO SA FARE: i due
segnali non distinguono «pubblico» da «privato». A tenerli fuori e' il filtro
delle righe, non la loro natura. Chi cambiasse `_RIGA_ESEMPIO` deve rileggere
questa nota prima di credere ai numeri.
"""
from __future__ import annotations

import ast
import io
import json
import re
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

#: Riservati alla documentazione: RFC 2606 (example.*, .test, .invalid,
#: .localhost) e RFC 6761. Usarli in un esempio e' la pratica CORRETTA.
_RISERVATI = re.compile(
    r"(?:^|\.)(?:example\.(?:com|org|net)|test|invalid|localhost)$", re.I)

#: I TLD ammessi. ⚠️ UNA LISTA CHIUSA, e la scelta va motivata perche' in questa
#: casa le liste cadono spesso: la prima versione chiedeva solo «due o piu'
#: etichette con un TLD alfabetico», e su quella definizione `os.environ.get`,
#: `subprocess.run` e `flow.write` SONO DOMINI. Misurato: **466 finti domini**
#: nelle docstring dell'albero, tutti chiamate Python.
#: 🔑 Il banco dava comunque il numero giusto — perche' guarda solo le righe di
#: esempio, dove le chiamate non compaiono. Cioe' funzionava per una ragione
#: diversa da quella dichiarata, e un banco cosi' regge finche' nessuno tocca
#: l'altro filtro.
#: Qui la lista NON e' la trappola delle liste linguistiche: i TLD sono uno
#: standard chiuso (IANA), non le parole di una lingua. ⚠️ Ma e' PARZIALE — un
#: dominio `.museum` o `.中国` non verrebbe visto, ed e' un falso NEGATIVO
#: dichiarato, non un buco scoperto dopo.
_TLD = (r"com|org|net|edu|gov|mil|int|io|dev|app|ai|co|me|tv|cc|xyz|info|biz"
        r"|online|site|cloud|tech|it|uk|de|fr|es|nl|eu|ru|cn|jp|br|ca|au|ch")
_DOMINIO = re.compile(
    rf"\b((?:[a-z0-9](?:[a-z0-9-]{{0,61}}[a-z0-9])?\.)+(?:{_TLD}))\b", re.I)

#: `C:\Users\<nome>` e `/home/<nome>` — la cartella di un utente REALE.
_UTENTE = re.compile(
    r"(?:[A-Za-z]:[\\/]+Users[\\/]+|/home/|/Users/)([A-Za-z0-9._-]+)")

#: Segnaposti che un autore mette APPOSTA: non sono un utente reale.
_SEGNAPOSTO = frozenset({
    "user", "username", "utente", "you", "youruser", "your-user", "me",
    "nome", "name", "someone", "public", "default", "all", "administrator",
})

#: Righe che SONO un esempio: il prompt di una shell o un blocco di codice
#: dentro una docstring. Un esempio vive qui, non nella prosa attorno.
_RIGA_ESEMPIO = re.compile(
    r"^\s*(?:[$>#]\s|\.\.\.\s|>>>\s|\S+\s+(?:add|save|search|recall|index|"
    r"mcp|serve|warmup|forget|doctor|facts|flow)\b|\{|\"[a-z_]+\":)")


def _docstring_di(testo: str, dove: str) -> list[tuple[str, str]]:
    """``(nome qualificato, docstring)`` per modulo, classi e funzioni.

    Con ``ast`` e non con una regex sulle triple virgolette: una regex qui
    sbaglia su ogni stringa che ne contenga una, e il punto del banco e'
    misurare il prodotto, non la mia regex.
    """
    try:
        albero = ast.parse(testo)
    except SyntaxError:
        return []
    fuori: list[tuple[str, str]] = []
    if (d := ast.get_docstring(albero)):
        fuori.append((f"{dove}::<modulo>", d))
    for n in ast.walk(albero):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (d := ast.get_docstring(n)):
                fuori.append((f"{dove}::{n.name}", d))
    return fuori


def _righe_esempio(doc: str) -> list[str]:
    return [r for r in doc.splitlines() if _RIGA_ESEMPIO.match(r)]


def _sospetti(riga: str) -> list[str]:
    """I dati REALI nella riga. Vuoto quando sono segnaposti o riservati."""
    fuori = []
    for m in _UTENTE.finditer(riga):
        if m.group(1).lower() not in _SEGNAPOSTO:
            fuori.append(f"utente:{m.group(1)}")
    for m in _DOMINIO.finditer(riga):
        d = m.group(1)
        if not _RISERVATI.search(d) and not d.lower().endswith((".py", ".md",
                                                                ".txt", ".db",
                                                                ".json",
                                                                ".jsonl",
                                                                ".toml",
                                                                ".yml")):
            fuori.append(f"dominio:{d}")
    return fuori


def _sorgenti_albero(radice: Path) -> list[tuple[str, str]]:
    return [(str(p.relative_to(radice.parent)), p.read_text("utf-8", "replace"))
            for p in sorted(radice.rglob("*.py"))]


def _stringhe_di(testo: str, dove: str) -> list[tuple[str, str]]:
    """Le stringhe LETTERALI del codice — dove i percorsi fanno danno davvero.

    ⚠️ PERCHE' ESISTE, e nasce da un mio errore misurabile. La prima versione di
    questo banco guardava SOLO le docstring di ``verimem/``, e non ha visto la
    riga che stava rompendo la CI da giorni::

        tests/test_il_giornale_non_rispettava_l_isolamento.py:42
        _REPO = r"C:\\Users\\<utente>\\Code\\HippoAgent"

    Un percorso di una macchina, usato come percorso REALE: su Linux e macOS
    non esiste, e quattro test non potevano passare su NESSUN commit.
    🔑 Il segnale era gia' quello giusto — il banco cerca esattamente
    ``C:\\Users\\<nome>``. **A mancare era il PERIMETRO**: cercavo dove la
    riga imbarazza (la pagina pubblica) e non dove ROMPE (il codice eseguito).

    ⚠️ QUI IL BANCO NON DISTINGUE uso da dato di prova, e non finge di farlo:
    ``test_su_windows_tutti_i_file_erano_la_stessa_fonte.py`` contiene lo stesso
    percorso come STRINGA DA PARSARE, ed e' legittimo. La lista e' corta
    abbastanza da leggerla a mano — e un classificatore che non so validare
    farebbe piu' danno del conteggio grezzo.

    📊 QUANTO E' CORTA, e cosa c'e' dentro (misurato su ``verimem/`` + ``tests/``
    il 2026-08-10): **21 esiti su 117.401 stringhe letterali**. Raggruppati per
    nome trovato::

        utente:dev (8) · utente:agent (3)     nomi generici, scritti apposta
        utente:important · utente:X           dentro comandi DISTRUTTIVI di prova
                                              (`del /q /s C:\\Users\\important`),
                                              scritti per collaudare la sandbox
        utente:aurel (il resto)               il nome vero

    🔑 IL CRITERIO CHE LA MISURA HA RIVELATO, e che non avevo previsto: cio che
    conta non e' «un nome che non e' un segnaposto» — ``dev``, ``agent``, ``X``
    e ``important`` non sono nella lista dei segnaposti eppure sono tutti
    inventati. Cio' che conta e' **IL nome di chi lavora qui**, e quello non si
    ricava da una lista.
    ⚠️ Non lo si ricava nemmeno dall'utente corrente: un banco che leggesse
    ``$USER`` darebbe esiti diversi su macchine diverse, e in CI non troverebbe
    nulla. Percio' il banco resta grezzo E DICHIARA di esserlo: 21 righe si
    leggono, 21 righe non si contano.
    """
    try:
        albero = ast.parse(testo)
    except SyntaxError:
        return []
    fuori = []
    for n in ast.walk(albero):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            fuori.append((f"{dove}:{n.lineno}", n.value))
    return fuori


def _sorgenti_pubblicate(versione: str, tipo: str) -> list[tuple[str, str]]:
    """I `.py` dell'artefatto PUBBLICATO — ``wheel`` oppure ``sdist``.

    ⚠️ QUI SI GUARDAVA SOLO IL WHEEL, e per due giorni ho creduto di misurare
    «il pacchetto». `twine upload` ne pubblica DUE, e il secondo non lo apriva
    nessuno: sulla 0.7.0 l'sdist porta 1457 voci contro le 440 del wheel, di cui
    **997 sotto `tests/`** — cioe' un'intera superficie di sorgenti che finisce
    su PyPI e che questo banco non vedeva.
    🔑 Il difetto non era un criterio sbagliato: era il PERIMETRO. Lo stesso
    banco, sullo stesso indice, con la stessa regola — e mezza risposta.
    ⚠️ I due archivi si aprono in due modi: il wheel e' uno `.zip`, l'sdist un
    `.tar.gz`. Il tipo si CHIEDE al metadato `packagetype`, non si assume dal
    nome del file.
    """
    d = json.load(urllib.request.urlopen(
        f"https://pypi.org/pypi/verimem/{versione}/json", timeout=30))
    voluto = "bdist_wheel" if tipo == "wheel" else "sdist"
    urls = [u for u in d["urls"] if u["packagetype"] == voluto]
    if not urls:
        return []
    raw = urllib.request.urlopen(urls[0]["url"], timeout=120).read()
    if voluto == "bdist_wheel":
        z = zipfile.ZipFile(io.BytesIO(raw))
        return [(n, z.read(n).decode("utf-8", "replace"))
                for n in z.namelist() if n.endswith(".py")]
    fuori: list[tuple[str, str]] = []
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as t:
        for m in t.getmembers():
            if not (m.isfile() and m.name.endswith(".py")):
                continue
            f = t.extractfile(m)
            if f is not None:
                fuori.append((m.name, f.read().decode("utf-8", "replace")))
    return fuori


def main(argv: list[str]) -> int:
    codice = "--anche-il-codice" in argv
    if "--wheel" in argv or "--sdist" in argv:
        # ⚠️ DUE ARTEFATTI, NON UNO. `twine upload` ne pubblica due dallo stesso
        # comando e finora questo banco apriva solo il primo: chi leggeva il suo
        # referto credeva di sapere cosa c'e' «nel pacchetto» e ne conosceva
        # meta'. Le due porte restano SEPARATE di proposito — un solo numero che
        # somma i due archivi nasconderebbe proprio la differenza che conta.
        tipo = "sdist" if "--sdist" in argv else "wheel"
        versione = argv[argv.index(f"--{tipo}") + 1]
        etichetta = f"{tipo.upper()} verimem {versione} (PyPI)"
        sorgenti = _sorgenti_pubblicate(versione, tipo)
        if not sorgenti:
            print(f"⛔ nessun {tipo} pubblicato per la {versione}.")
            return 2
    else:
        base = Path(__file__).resolve().parents[3]
        cartelle = [base / "verimem"]
        if codice:
            cartelle.append(base / "tests")
        etichetta = " + ".join(str(c) for c in cartelle)
        sorgenti = [s for c in cartelle if c.is_dir()
                    for s in _sorgenti_albero(c)]

    print("=" * 78)
    print(f"DATI REALI NEGLI ESEMPI — {etichetta}")
    if codice:
        print("  con --anche-il-codice: anche le STRINGHE LETTERALI e tests/")
    print("=" * 78)

    n_doc = n_esempi = n_str = 0
    trovati: list[tuple[str, str, list[str]]] = []
    nel_codice: list[tuple[str, str, list[str]]] = []
    for nome, testo in sorgenti:
        for qualificato, doc in _docstring_di(testo, nome):
            n_doc += 1
            for riga in _righe_esempio(doc):
                n_esempi += 1
                if (s := _sospetti(riga)):
                    trovati.append((qualificato, riga.strip(), s))
        if codice:
            for dove, valore in _stringhe_di(testo, nome):
                n_str += 1
                if (s := [x for x in _sospetti(valore)
                          if x.startswith("utente:")]):
                    nel_codice.append((dove, valore, s))

    print(f"\n  docstring lette          {n_doc}")
    print(f"  righe che sono un esempio {n_esempi}   <- la popolazione OPPOSTA")
    print(f"  con un dato REALE         {len(trovati)}")
    if n_esempi:
        print(f"  quota                     {100 * len(trovati) / n_esempi:.1f}%")
    print()
    for qualificato, riga, s in trovati:
        print(f"  🔴 {qualificato}")
        print(f"     {riga[:96]}")
        print(f"     -> {', '.join(s)}")
    if not trovati:
        print("  nessun dato reale negli esempi.")

    if codice:
        # ⚠️ Solo `utente:` — un DOMINIO dentro una stringa di codice e' quasi
        # sempre un valore di prova o una costante legittima, e segnalarlo qui
        # annegherebbe l'unico segnale che rompe davvero.
        print(f"\n  stringhe letterali lette {n_str}   <- la popolazione OPPOSTA")
        print(f"  con un percorso di una MACCHINA {len(nel_codice)}")
        print("  ⚠️ il banco NON distingue un percorso USATO da un DATO DI "
              "PROVA:\n     la lista va letta, non contata.\n")
        for dove, valore, s in nel_codice:
            print(f"  🔴 {dove}  -> {', '.join(s)}")
            print(f"     {valore.splitlines()[0][:88] if valore else ''}")
    print("\n" + "=" * 78)
    print("Non cerca: chiavi, token, IP, id di ticket, telefoni — un segnale "
          "ciascuno,\ne un banco che li mescola non sa piu' quale sta "
          "misurando.")
    return 1 if trovati else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
