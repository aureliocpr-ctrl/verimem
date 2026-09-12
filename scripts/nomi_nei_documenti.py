"""Quanti documenti pubblici portano ancora un nome di istanza o un path locale.

PERCHE' ESISTE — il 12/09 ho contato a mano i file con un path locale in
`docs/stato-reale/` e mi sono venuti **23**; un'ora dopo, con un regex leggermente
diverso, **24**. Nessuno dei due numeri era sbagliato: era il righello a muoversi.
Una revisione che deve dire *«la pulizia li toglie TUTTI?»* ha bisogno di un
criterio scritto, non di un `grep` riscritto ogni volta.

LE TRE CLASSI, e perche' stanno separate:

  ① `wsN` nel TESTO — **inequivocabile**: `ws3` non e' una parola italiana.
  ② nome umano nel TESTO — **AMBIGUO**: `tara` e' anche la tara di un peso,
     `iris` anche un fiore, `giano` anche il dio bifronte. Questi NON entrano nel
     numero di testa: si stampano col contesto e li classifica una persona.
     (Misurato sul residuo del 12/09: 8 file su 8 erano nomi veri — zero falsi
     positivi. Ma «zero oggi» non e' «zero per costruzione».)
  ③ nome nel PATH — **invisibile a una pulizia del testo**. Il 12/09:
     **95 file** portavano un nome solo nel nome del file o della cartella
     (`banchi-ws2/`, `ws7-u-c-da-zero-in-dieci-minuti.json`): una PR che riscrive
     il contenuto li lascia tutti, e il nome resta pubblico nell'albero.

🔑 Il numero di testa e' la classe ①. Le altre due si leggono, non si sommano di
nascosto: sommare un ambiguo a un certo produce un numero che nessuno puo'
falsificare.

USO
    python scripts/nomi_nei_documenti.py docs/stato-reale
    python scripts/nomi_nei_documenti.py docs/stato-reale --ambigui   # il contesto
    python scripts/nomi_nei_documenti.py --autotest                   # il righello morde?

⚠️ Il confronto PRIMA/DOPO si fa su DUE alberi (due worktree, due ref), non su
due momenti dello stesso: il righello stampa la cartella che ha misurato proprio
perche' un banco deve dichiarare quale albero misura.
"""
from __future__ import annotations

import pathlib
import re
import sys
import tempfile

#: Il criterio. Va tenuto allineato al ruolo/<ws> del board: un nome nuovo che
#: non e' qui non viene contato, e il righello direbbe «pulito» a torto.
ISTANZE = ["ws1", "ws2", "ws3", "ws4", "ws5", "ws6", "ws7", "ws8"]
UMANI = ["marie", "tara", "corrado", "galileo", "nadia", "aldo", "giano", "iris", "curie"]

_WS = re.compile(r"\b(?:" + "|".join(ISTANZE) + r")\b", re.I)
_UMANO = re.compile(r"\b(?:" + "|".join(UMANI) + r")\b", re.I)
#: nel path il nome sta fra separatori: `banchi-ws2/`, `_ws3_curva.json`, `/ws7-u-c.json`
_PATH = re.compile(r"(?:^|[/\-_])(?:" + "|".join(ISTANZE + UMANI) + r")(?:[/\-_.]|$)", re.I)
#: la home di chi ha lanciato il comando, in tutte e tre le forme che usiamo
_LOCALE = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+|/c/Users/", re.I)

_CONTESTO = 34


def _testo(f: pathlib.Path) -> str:
    return f.read_text(encoding="utf-8", errors="replace")


def misura(radice: pathlib.Path) -> dict:
    """Ritorna gli insiemi di file per classe. Insiemi, non conteggi: chi legge
    deve poter stampare CHI cade, non solo quanti."""
    tutti = sorted(p for p in radice.rglob("*")
                   if p.is_file() and ".git" not in p.parts)
    r: dict[str, list] = {"tutti": tutti, "ws": [], "umano": [], "path": [], "locale": []}
    for f in tutti:
        rel = f.relative_to(radice).as_posix()
        if _PATH.search("/" + rel):
            r["path"].append(f)
        try:
            t = _testo(f)
        except OSError:
            continue
        if _WS.search(t):
            r["ws"].append(f)
        if _UMANO.search(t):
            r["umano"].append(f)
        if _LOCALE.search(t):
            r["locale"].append(f)
    return r


def _stampa(radice: pathlib.Path, r: dict, ambigui: bool) -> None:
    n = len(r["tutti"])
    testo = sorted(set(r["ws"]) | set(r["umano"]))
    solo_path = sorted(set(r["path"]) - set(testo))
    ovunque = sorted(set(testo) | set(r["path"]))
    #: ⚠️ tutte le componenti, non solo la prima: una cartella annidata che porta
    #: un nome costa un `git mv` come quella in cima, e la v1 non la vedeva.
    cartelle = sorted({parte for f in r["path"]
                       for parte in f.relative_to(radice).parts[:-1]
                       if _PATH.search("/" + parte + "/")})

    print(f"ALBERO MISURATO: {radice.resolve()}")
    print(f"file: {n}\n")
    print("① NOME DI ISTANZA NEL TESTO — inequivocabile")
    print(f"   wsN ................................. {len(r['ws'])}")
    print("② NOME UMANO NEL TESTO — AMBIGUO, da classificare a mano")
    print(f"   un nome della lista ................. {len(r['umano'])}"
          f"   (--ambigui per il contesto)")
    print(f"   ①∪② ................................ {len(testo)}")
    print("③ NOME NEL PATH — invisibile a una pulizia del TESTO")
    print(f"   file ................................ {len(r['path'])}")
    print(f"   di cui il nome sta SOLO nel path .... {len(solo_path)}")
    print(f"   cartelle ............................ {len(cartelle)}"
          + (f"   {', '.join(cartelle)}" if cartelle else ""))
    print("④ PATH LOCALE NEL TESTO")
    print(f"   file ................................ {len(r['locale'])}")
    pct = f"{100 * len(ovunque) / n:.1f}%" if n else "n/d"
    print(f"\n⇒ con un nome DA QUALCHE PARTE: {len(ovunque)} su {n} ({pct})")

    if solo_path:
        print("\n   i primi che una pulizia del testo NON tocca:")
        for f in solo_path[:10]:
            print(f"      {f.relative_to(radice).as_posix()}")
        if len(solo_path) > 10:
            print(f"      … e altri {len(solo_path) - 10}")

    if ambigui:
        print("\n=== ② IL CONTESTO DEI NOMI AMBIGUI — classificali ===")
        for f in r["umano"]:
            t = _testo(f)          # una lettura per file, non una per match
            for m in _UMANO.finditer(t):
                a = max(0, m.start() - _CONTESTO)
                frammento = t[a:m.end() + _CONTESTO].replace("\n", "⏎")
                print(f"   {f.relative_to(radice).as_posix()}: …{frammento}…")


def autotest() -> int:
    """Ogni classe deve ACCENDERSI su un caso costruito, e SPEGNERSI quando il
    token se ne va: un criterio vale solo se togliendolo il numero cambia."""
    casi = [
        ("① wsN nel testo", "ws/nota.md", "il difetto e' di @ws6, non mio", "ws"),
        ("② nome umano nel testo", "umano/nota.md", "reperto di Tara, 6,8 misurati", "umano"),
        ("④ path locale", "loc/nota.md", r"C:\Users\qualcuno\AppData\Local\Temp\x", "locale"),
    ]
    esiti = []
    with tempfile.TemporaryDirectory(prefix="nomi-autotest-") as d:
        radice = pathlib.Path(d)
        for _, rel, contenuto, _chiave in casi:
            p = radice / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(contenuto, encoding="utf-8")
        # ③ il nome sta SOLO nel path: il contenuto non deve nominare nessuno
        (radice / "banchi-ws2").mkdir(parents=True, exist_ok=True)
        (radice / "banchi-ws2" / "prova.py").write_text("print(1)", encoding="utf-8")
        # controllo NEGATIVO: parole che CONTENGONO un nome senza esserlo — se
        # questo si accende, il confine di parola non tiene e OGNI numero sale.
        (radice / "negativo.md").write_text(
            "tarare la bilancia, Marielle, workstation, ws9", encoding="utf-8")
        # ⚠️ IL LIMITE, scritto come test e non come nota: l'omonimo CADE dentro.
        # E' esattamente per questo che ② non entra nel numero di testa.
        (radice / "omonimo.md").write_text(
            "il peso al netto della tara", encoding="utf-8")

        r = misura(radice)
        for nome, rel, _c, chiave in casi:
            acceso = any(f.name == pathlib.Path(rel).name for f in r[chiave])
            esiti.append((nome + " si accende", acceso))
        esiti.append(("③ nome SOLO nel path si accende",
                      any("banchi-ws2" in f.as_posix() for f in r["path"])))
        esiti.append(("③ e NON e' visto dal testo",
                      not any("banchi-ws2" in f.as_posix()
                              for f in set(r["ws"]) | set(r["umano"]))))
        neg = radice / "negativo.md"
        esiti.append(("controllo NEGATIVO resta spento",
                      neg not in set(r["ws"]) | set(r["umano"]) | set(r["path"])))
        esiti.append(("② l'OMONIMO cade in ②, non in ①",
                      (radice / "omonimo.md") in set(r["umano"])
                      and (radice / "omonimo.md") not in set(r["ws"])))

        # e il criterio si spegne se il token se ne va
        (radice / "ws" / "nota.md").write_text("il difetto non e' mio", encoding="utf-8")
        esiti.append(("① si SPEGNE tolto il token", not misura(radice)["ws"]))

    for nome, ok in esiti:
        print(f"   {'✅' if ok else '🔴'} {nome}")
    caduti = [n for n, ok in esiti if not ok]
    print(f"\n   autotest: {len(esiti) - len(caduti)}/{len(esiti)}")
    return 1 if caduti else 0


if __name__ == "__main__":
    argomenti = sys.argv[1:]
    if "--autotest" in argomenti:
        sys.exit(autotest())
    if not argomenti:
        print(__doc__)
        sys.exit(2)
    cartella = pathlib.Path(argomenti[0])
    if not cartella.is_dir():
        print(f"non e' una cartella: {cartella}")
        sys.exit(2)
    _stampa(cartella, misura(cartella), "--ambigui" in argomenti)
