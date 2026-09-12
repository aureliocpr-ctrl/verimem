"""Quanto manca perche' i documenti pubblici siano presentabili — per classe.

PERCHE' ESISTE — il 12/09 ho contato a mano i file con un path locale in
`docs/stato-reale/` e mi sono venuti **23**; un'ora dopo, con un regex
leggermente diverso, **24**. Nessuno dei due numeri era sbagliato: era il
righello a muoversi. Una revisione che deve dire *«la pulizia li toglie
TUTTI?»* ha bisogno di un criterio scritto, non di un `grep` riscritto ogni
volta da chi guarda.

🔴 LA DECISIONE DEL 12/09, e perche' cambia il numero di testa:
**le sigle `wsN` RESTANO come sono.** Si tolgono i **nomi umani** (→ ruoli), le
citazioni che li portano, e i **path locali**. Rinominare 447 banchi che hanno
una sigla nel nome costa piu' di quello che rende, e rompe i riferimenti.
⇒ Questo righello tiene le due cose **separate**, perche' un criterio di
accettazione che conti anche cio' che per decisione resta **non puo' mai
arrivare a zero**, e un cancello che non puo' chiudersi viene aggirato.

LE CLASSI:

  🔴 BLOCCANTI — devono arrivare a zero
     ① nome umano nel TESTO      AMBIGUO per costruzione: `tara` e' anche la
                                 tara di un peso, `aldo` sta dentro `caldo`.
                                 Il 12/09 una sostituzione cieca ha scritto
                                 `cDati` al posto di `caldo` in 200+ punti.
                                 ⇒ si stampa il CONTESTO e classifica una
                                 persona; non si sostituisce a occhi chiusi.
     ② nome umano nel PATH       invisibile a una pulizia del TESTO: nessuna
                                 riscrittura della prosa rinomina un file.
     ③ path locale nel TESTO     la home di chi ha lanciato il comando.
     ⑤ nome di SESSIONE          cercato SOLO in forma-nome (`@Nome`, `firma
                                 Nome`, `Agent: Nome`), perche' `varco`,
                                 `paragone` e `lanterna` sono anche parole
                                 italiane: 529 occorrenze di `varco` in un file
                                 sono **486** nomi e 43 parole. Aggiunta il
                                 12/09 dopo che una misura ha mostrato che
                                 l'elenco ① era incompleto — 495 occorrenze in
                                 3 file che questo righello non vedeva, cioe'
                                 uno «zero» che sarebbe stato falso.

  ⚪ DICHIARATA — resta per decisione, si conta per sapere quanto e' grande
     ④ sigla `wsN` (testo e path)

USO
    python scripts/nomi_nei_documenti.py docs/stato-reale
    python scripts/nomi_nei_documenti.py docs/stato-reale --contesto
    python scripts/nomi_nei_documenti.py --autotest

⚠️ Il confronto PRIMA/DOPO si fa su DUE alberi (due worktree, due ref), non su
due momenti dello stesso: il righello stampa la cartella che ha misurato
proprio perche' un banco deve dichiarare quale albero misura.

⚠️ QUESTO FILE E' ESCLUSO DALLA PROPRIA MISURA, e lo dichiara a ogni giro:
contiene l'anagrafica completa perche' **l'elenco E' il criterio**. Spostarlo
fuori dal repo renderebbe il righello muto quando il file manca — e un criterio
assente conta zero e si legge «pulito», che e' il modo piu' efficace di
dichiarare finita una pulizia che non e' partita.
"""
from __future__ import annotations

import pathlib
import re
import sys
import tempfile

#: Il criterio. Va tenuto allineato al board dei ruoli: un nome nuovo che non e'
#: qui non viene contato, e il righello direbbe «pulito» a torto.
SIGLE = ["ws1", "ws2", "ws3", "ws4", "ws5", "ws6", "ws7", "ws8"]
UMANI = ["marie", "tara", "corrado", "galileo", "nadia", "aldo", "giano", "iris", "curie"]

#: 🔴 NOMI DI SESSIONE, aggiunti il 12/09 dopo una misura che ha mostrato che
#: l'elenco sopra era INCOMPLETO: 495 occorrenze in 3 file che questo righello
#: non vedeva, e quindi uno «① a zero» sarebbe stato falso.
#:
#: ⚠️ Vanno cercati SOLO IN FORMA-NOME, e la ragione e' misurata: `varco` in un
#: file solo fa **529** occorrenze totali ma **486** in forma-nome — le altre 43
#: sono la parola italiana. Cercarli come parola nuda rifarebbe, su di noi,
#: l'errore che questo righello esiste per impedire.
#: 📌 E due candidati sono stati SCARTATI dalla stessa misura: `sentinella` (13
#: occorrenze, **0** in forma-nome) e `faro` (1, **0**). Non sono nomi qui, e
#: metterli dentro avrebbe gonfiato ogni numero futuro senza aggiungere un caso.
SESSIONI = ["varco", "paragone", "lanterna"]

#: il file che contiene l'elenco non puo' misurare se stesso
ESCLUSO = "nomi_nei_documenti.py"

_SIGLA = re.compile(r"\b(?:" + "|".join(SIGLE) + r")\b", re.I)
_UMANO = re.compile(r"\b(?:" + "|".join(UMANI) + r")\b", re.I)
#: la FORMA-NOME: `@Varco`, `firma Varco`, `Agent: Varco`, `— Varco`, `di @Varco`.
#: Il criterio e' quello usato nella misura del 12/09 che ha trovato i tre nomi.
_FORMA_NOME = re.compile(
    r"(?:@|\bfirma\s+|\bAgent:\s*|—\s*|\bdi\s+@?)(?:" + "|".join(SESSIONI) + r")\b",
    re.I)
#: nel path il nome sta fra separatori: `banchi-ws2/`, `_ws3_curva.json`, `/ws7-u-c.json`
_SEP = r"(?:^|[/\-_])(?:{})(?:[/\-_.]|$)"
_PATH_UMANO = re.compile(_SEP.format("|".join(UMANI)), re.I)
_PATH_SIGLA = re.compile(_SEP.format("|".join(SIGLE)), re.I)
#: la home di chi ha lanciato il comando, in tutte e tre le forme che usiamo
_LOCALE = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+|/c/Users/", re.I)

_CONTESTO = 34


def _testo(f: pathlib.Path) -> str:
    return f.read_text(encoding="utf-8", errors="replace")


def misura(radice: pathlib.Path) -> dict:
    """Insiemi di file per classe. Insiemi e non conteggi: chi legge deve poter
    stampare CHI cade, non solo quanti."""
    tutti = sorted(p for p in radice.rglob("*")
                   if p.is_file() and ".git" not in p.parts)
    esclusi = [p for p in tutti if p.name == ESCLUSO]
    tutti = [p for p in tutti if p.name != ESCLUSO]
    r: dict[str, list] = {"tutti": tutti, "esclusi": esclusi, "umano": [],
                          "path_umano": [], "locale": [], "sigla": [],
                          "path_sigla": [], "sessione": []}
    for f in tutti:
        rel = "/" + f.relative_to(radice).as_posix()
        if _PATH_UMANO.search(rel):
            r["path_umano"].append(f)
        if _PATH_SIGLA.search(rel):
            r["path_sigla"].append(f)
        try:
            t = _testo(f)
        except OSError:
            continue
        if _UMANO.search(t):
            r["umano"].append(f)
        if _FORMA_NOME.search(t):
            r["sessione"].append(f)
        if _LOCALE.search(t):
            r["locale"].append(f)
        if _SIGLA.search(t):
            r["sigla"].append(f)
    return r


def _elenco(radice: pathlib.Path, files: list, quanti: int = 8) -> None:
    for f in files[:quanti]:
        print(f"      {f.relative_to(radice).as_posix()}")
    if len(files) > quanti:
        print(f"      … e altri {len(files) - quanti}")


def _stampa(radice: pathlib.Path, r: dict, contesto: bool) -> int:
    n = len(r["tutti"])
    bloccanti = sorted(set(r["umano"]) | set(r["path_umano"]) | set(r["locale"])
                       | set(r["sessione"]))
    dichiarati = sorted(set(r["sigla"]) | set(r["path_sigla"]))

    print(f"ALBERO MISURATO: {radice.resolve()}")
    print(f"file: {n}"
          + (f"   (escluso {len(r['esclusi'])}: {ESCLUSO}, contiene l'elenco"
             " per costruzione)" if r["esclusi"] else ""))
    print()
    print("🔴 BLOCCANTI — devono arrivare a zero")
    print(f"   ① nome umano nel TESTO .............. {len(r['umano'])}"
          "   (ambiguo: --contesto per classificarli)")
    print(f"   ② nome umano nel PATH ............... {len(r['path_umano'])}"
          "   (un `git mv`, non una riscrittura)")
    print(f"   ③ path locale nel TESTO ............. {len(r['locale'])}")
    print(f"   ⑤ nome di SESSIONE in forma-nome .... {len(r['sessione'])}"
          f"   ({', '.join(SESSIONI)}; solo `@Nome`/`firma Nome`/`Agent: Nome`)")
    print(f"   ⇒ file da toccare: {len(bloccanti)} su {n}")
    print()
    print("⚪ DICHIARATA — resta per decisione del 12/09, non e' un difetto")
    print(f"   ④ sigla wsN, testo o path ........... {len(dichiarati)}"
          f"   (testo {len(r['sigla'])}, path {len(r['path_sigla'])})")

    if r["path_umano"]:
        print("\n   ② i file che una pulizia del TESTO non tocca:")
        _elenco(radice, r["path_umano"])
    if r["locale"]:
        print("\n   ③ i file con un path locale:")
        _elenco(radice, r["locale"])

    if contesto:
        print("\n=== ① IL CONTESTO DEI NOMI UMANI — classificali a mano ===")
        for f in r["umano"]:
            t = _testo(f)
            for m in _UMANO.finditer(t):
                a = max(0, m.start() - _CONTESTO)
                frammento = t[a:m.end() + _CONTESTO].replace("\n", "⏎")
                print(f"   {f.relative_to(radice).as_posix()}: …{frammento}…")

    return 1 if bloccanti else 0


def autotest() -> int:
    """Ogni classe deve ACCENDERSI su un caso costruito e SPEGNERSI quando il
    token se ne va: un criterio vale solo se togliendolo il numero cambia."""
    esiti = []
    with tempfile.TemporaryDirectory(prefix="nomi-autotest-") as d:
        radice = pathlib.Path(d)

        def scrivi(rel: str, testo: str) -> pathlib.Path:
            p = radice / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(testo, encoding="utf-8")
            return p

        umano = scrivi("testo/nota.md", "reperto di Tara, 6,8 misurati")
        locale = scrivi("loc/nota.md", r"C:\Users\qualcuno\AppData\Local\Temp\x")
        sigla = scrivi("sig/nota.md", "il difetto e' di @ws6, non mio")
        scrivi("banchi/aldo-prova.py", "print(1)")          # ② nome nel PATH
        scrivi("banchi-ws2/prova.py", "print(1)")           # ④ sigla nel path
        # controllo NEGATIVO: parole che CONTENGONO un nome senza esserlo. Se
        # questo si accende, il confine di parola non tiene e OGNI numero sale.
        neg = scrivi("negativo.md", "tarare la bilancia, il caldo, Marielle, ws9")
        # ⚠️ IL LIMITE, scritto come test e non come nota: l'omonimo CADE dentro.
        omonimo = scrivi("omonimo.md", "il peso al netto della tara")
        # ⑤ i nomi di sessione: forma-nome SI', parola comune NO. La seconda
        # gamba e' la piu' importante: senza, questo righello rifarebbe su di
        # se' l'errore che esiste per impedire.
        sessione = scrivi("sess/nota.md", "il rilievo e' di @Varco, non mio")
        parola = scrivi("sess/parola.md",
                        "hanno aperto un varco nel muro, e il paragone regge")
        # il righello non deve misurare se stesso
        scrivi(ESCLUSO, "UMANI = marie tara corrado aldo giano iris")

        r = misura(radice)
        esiti.append(("① nome umano nel testo si accende", umano in set(r["umano"])))
        esiti.append(("③ path locale si accende", locale in set(r["locale"])))
        esiti.append(("④ sigla nel testo si accende", sigla in set(r["sigla"])))
        esiti.append(("② nome umano nel PATH si accende",
                      any("aldo-prova" in f.as_posix() for f in r["path_umano"])))
        esiti.append(("② e NON e' visto dal testo",
                      not any("aldo-prova" in f.as_posix() for f in r["umano"])))
        esiti.append(("④ sigla nel path NON entra fra i nomi umani",
                      not any("banchi-ws2" in f.as_posix() for f in r["path_umano"])))
        esiti.append(("controllo NEGATIVO resta spento (`caldo` non e' `aldo`)",
                      neg not in set(r["umano"]) | set(r["path_umano"])
                      | set(r["locale"]) | set(r["sigla"])))
        esiti.append(("① l'OMONIMO cade in ①, ed e' per questo che si stampa"
                      " il contesto", omonimo in set(r["umano"])))
        esiti.append(("⑤ `@Varco` (forma-nome) si accende",
                      sessione in set(r["sessione"])))
        esiti.append(("⑤ «un varco nel muro» (parola) resta SPENTO",
                      parola not in set(r["sessione"])))
        esiti.append((f"il righello ESCLUDE se stesso ({ESCLUSO})",
                      len(r["esclusi"]) == 1
                      and not any(f.name == ESCLUSO for f in r["umano"])))

        umano.write_text("reperto del Product Owner", encoding="utf-8")
        esiti.append(("① si SPEGNE tolto il nome",
                      umano not in set(misura(radice)["umano"])))

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
    sys.exit(_stampa(cartella, misura(cartella), "--contesto" in argomenti))
