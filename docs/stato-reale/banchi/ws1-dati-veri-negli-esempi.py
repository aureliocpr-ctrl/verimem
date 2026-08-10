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


def _sorgenti_wheel(versione: str) -> list[tuple[str, str]]:
    d = json.load(urllib.request.urlopen(
        f"https://pypi.org/pypi/verimem/{versione}/json", timeout=30))
    w = [u for u in d["urls"] if u["packagetype"] == "bdist_wheel"][0]
    z = zipfile.ZipFile(io.BytesIO(
        urllib.request.urlopen(w["url"], timeout=120).read()))
    return [(n, z.read(n).decode("utf-8", "replace"))
            for n in z.namelist() if n.endswith(".py")]


def main(argv: list[str]) -> int:
    if "--wheel" in argv:
        versione = argv[argv.index("--wheel") + 1]
        etichetta = f"WHEEL verimem {versione} (PyPI)"
        sorgenti = _sorgenti_wheel(versione)
    else:
        radice = Path(__file__).resolve().parents[3] / "verimem"
        etichetta = f"ALBERO {radice}"
        sorgenti = _sorgenti_albero(radice)

    print("=" * 78)
    print(f"DATI REALI NEGLI ESEMPI DELLE DOCSTRING — {etichetta}")
    print("=" * 78)

    n_doc = n_esempi = 0
    trovati: list[tuple[str, str, list[str]]] = []
    for nome, testo in sorgenti:
        for qualificato, doc in _docstring_di(testo, nome):
            n_doc += 1
            for riga in _righe_esempio(doc):
                n_esempi += 1
                if (s := _sospetti(riga)):
                    trovati.append((qualificato, riga.strip(), s))

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
    print("\n" + "=" * 78)
    print("Non cerca: chiavi, token, IP, id di ticket, telefoni — un segnale "
          "ciascuno,\ne un banco che li mescola non sa piu' quale sta "
          "misurando.")
    return 1 if trovati else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
