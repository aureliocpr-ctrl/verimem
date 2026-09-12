"""Quanto manca perche' i documenti pubblici siano presentabili — per classe
e per POPOLAZIONE.

PERCHE' ESISTE — il 12/09 ho contato a mano i file con un path locale in
`docs/stato-reale/` e mi sono venuti **23**; un'ora dopo, con un regex
leggermente diverso, **24**; col pattern giusto **84**. Nessuno dei tre era
sbagliato: era il righello a muoversi. Una revisione che deve dire *«la pulizia
li toglie TUTTI?»* ha bisogno di un criterio scritto, non di un `grep`
riscritto ogni volta da chi guarda.

🔴 L'ELENCO DEI NOMI NON STA PIU' QUI, e non e' una raffinatezza. Il 12/09 lo
stesso elenco viveva in QUATTRO file con TRE contenuti diversi, e il mio ne
conosceva 9 su 16: mancavano `Varco` (495 occorrenze) e `Vega` (17 file da
solo). **Un elenco incompleto non e' un criterio permissivo: e' un criterio che
MENTE**, perche' porta a zero una misura che zero non e'.
⇒ Il roster unico e' `scripts/nomi_delle_sessioni.py` (adottato 12/09 14:50 da
tutti i righelli). Qui si importa e non si riscrive: **due elenchi sono due
criteri, e divergono il giorno in cui nascono.**

🔴 E LE POPOLAZIONI SONO TRE, non una. Il 12/09 ho scritto «i path locali sono
84 e la pulizia non e' cominciata» misurando su tutti i 775 file, mentre il
perimetro deciso ne conta 169: dentro quello il lavoro era **a zero**, e l'80%
delle occorrenze stava nei banchi, che sono ESCLUSI. Il numero era giusto, il
denominatore no. ⇒ Questo righello stampa **tre numeri**, e un verde su uno
solo non puo' passare per un verde su tutti.

  PERIMETRO       i documenti che la pulizia deve portare a zero
  BANCHI          esclusi: sono codice di misura, e cambiarli falsifica un dato
  DATI DI PROVA   esclusi di diritto (`ESCLUSI_DI_DIRITTO` nel roster):
                  riscriverli falsifica un reperto registrato

LE CLASSI:

  🔴 BLOCCANTI — devono arrivare a zero NEL PERIMETRO
     ① nome di sessione nel TESTO   dal roster: i sicuri senza distinzione di
                                    maiuscole, gli ambigui SOLO maiuscoli
                                    (`tara` e' anche il verbo «tarare»)
     ② nome di sessione nel PATH    invisibile a una pulizia del TESTO: nessuna
                                    riscrittura della prosa rinomina un file
     ③ path locale nel TESTO        la home di chi ha lanciato il comando

  ⚪ DICHIARATA — resta per decisione del 12/09
     ④ sigla `wsN` nei nomi di file: rinominare 447 banchi costa piu' di quel
        che rende e rompe i riferimenti

USO
    python scripts/nomi_nei_documenti.py docs/stato-reale
    python scripts/nomi_nei_documenti.py docs/stato-reale --contesto
    python scripts/nomi_nei_documenti.py --autotest

⚠️ Il confronto PRIMA/DOPO si fa su DUE alberi (due worktree, due ref), non su
due momenti dello stesso: il righello stampa la cartella che ha misurato
proprio perche' un banco deve dichiarare quale albero misura.
"""
from __future__ import annotations

import pathlib
import re
import sys
import tempfile

#: 🔑 SE IL ROSTER NON C'E', QUESTO RIGHELLO NON MISURA — e lo dice uscendo 2.
#: Il ripiego «uso un elenco mio» sarebbe la cosa peggiore: darebbe un numero
#: piu' basso con l'aria di un numero buono, che e' esattamente il modo in cui
#: una pulizia si dichiara finita senza esserlo.
try:
    from nomi_delle_sessioni import ESCLUSI_DI_DIRITTO, trova
except ImportError as _errore:      # pragma: no cover - si prova a mano
    print("NON MISURATO: manca `scripts/nomi_delle_sessioni.py`, che e' il "
          f"roster unico dei nomi ({_errore}).\n"
          "  Non esiste un ripiego: un elenco locale darebbe un numero piu' "
          "basso con l'aria di un numero buono.\n"
          "  Arriva con la PR del cancello sui messaggi; fino ad allora questo "
          "righello non ha un criterio.", file=sys.stderr)
    raise SystemExit(2) from _errore

#: le sigle restano per decisione: si contano, non si curano
SIGLE = ("ws1", "ws2", "ws3", "ws4", "ws5", "ws6", "ws7", "ws8")
_SIGLA_PATH = re.compile(r"(?:^|[/\-_])(?:" + "|".join(SIGLE) + r")(?:[/\-_.]|$)", re.I)
#: la home di chi ha lanciato il comando, in tutte le forme che usiamo —
#: separatore RIPETUTO compreso (`C:\\Users\\…` nelle stringhe JSON e Python),
#: che il mio primo pattern non prendeva e che valeva 19 occorrenze.
_LOCALE = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+|/c/Users/", re.I)
#: il file che contiene il roster non puo' misurare se stesso
ESCLUSO = "nomi_delle_sessioni.py"

_CONTESTO = 34


def _testo(f: pathlib.Path) -> str:
    return f.read_text(encoding="utf-8", errors="replace")


def _nomi(testo: str) -> list[str]:
    """I nomi BLOCCANTI in un testo: sigle escluse.

    🔴 Il roster mette le SIGLE fra i nomi sicuri, e fa bene: chi misura i
    messaggi le vuole. Ma il criterio di pulizia deciso il 12/09 e' «zero nomi
    umani e zero soprannomi NEL CONTENUTO», e **le sigle restano**. Contarle
    qui gonfiava ① da 3 a 156 su 169 file — cioe' dava per sporco un perimetro
    che e' pulito, e avrei portato un rilievo falso a chi lo aveva ripulito.
    ⇒ Chi importa un roster deve guardare **quali classi ci ha messo dentro**:
    un elenco unico non vuol dire un criterio unico.
    """
    return [n for n, _ in trova(testo) if n.lower() not in SIGLE]


def _nomi_nel_path(rel: str) -> list[str]:
    """I nomi in un PERCORSO, sigle escluse.

    🔴 SERVE `con_identificatori=True`, e l'autotest me l'ha insegnato facendo
    ROSSO: il roster, di suo, scarta un nome attaccato a `-` o `_` dentro un
    token piu' lungo, perche' nella PROSA `iris-ub-jivzor1t` e' una cartella
    temporanea citata come dato e riscriverla falsifica una misura. Ma un NOME
    DI FILE e' fatto esattamente cosi' (`aldo-prova.py`), quindi con la regola
    della prosa la classe ② sarebbe stata **sempre zero**: un criterio spento
    che si legge come «pulito».
    ⇒ Sui percorsi si guarda tutto, e si tolgono le SIGLE, che per decisione
    del 12/09 nei nomi di file restano.
    """
    return [n for n, _ in trova(rel, con_identificatori=True)
            if n.lower() not in SIGLE]


def popolazione(rel: str) -> str:
    """PERIMETRO, BANCHI o DATI-DI-PROVA per un percorso relativo.

    ⚠️ Il filtro dei banchi cerca `banchi` come COMPONENTE, non `"/banchi/"`:
    le cartelle si chiamano anche `banchi-ws2` e `banchi-04`, e un filtro
    troppo stretto non fa rumore — fa entrare nel lavoro roba che era stata
    esclusa, e non se ne accorge nessuno finche' non arriva in revisione.
    """
    p = pathlib.PurePosixPath(rel)
    if p.name in ESCLUSI_DI_DIRITTO:
        return "DATI-DI-PROVA"
    if any(parte.startswith("banchi") for parte in p.parts):
        return "BANCHI"
    return "PERIMETRO"


def misura(radice: pathlib.Path) -> dict:
    """Insiemi di file per classe e per popolazione. Insiemi e non conteggi:
    chi legge deve poter stampare CHI cade, non solo quanti."""
    tutti = sorted(p for p in radice.rglob("*")
                   if p.is_file() and ".git" not in p.parts and p.name != ESCLUSO)
    r: dict = {"tutti": tutti, "nome": [], "path_nome": [], "locale": [],
               "path_sigla": [], "pop": {}}
    for f in tutti:
        rel = f.relative_to(radice).as_posix()
        r["pop"][f] = popolazione(rel)
        if _nomi_nel_path("/" + rel):
            r["path_nome"].append(f)
        if _SIGLA_PATH.search("/" + rel):
            r["path_sigla"].append(f)
        try:
            t = _testo(f)
        except OSError:
            continue
        if _nomi(t):
            r["nome"].append(f)
        if _LOCALE.search(t):
            r["locale"].append(f)
    return r


def _per_pop(r: dict, chiave: str) -> dict:
    conta = {"PERIMETRO": 0, "BANCHI": 0, "DATI-DI-PROVA": 0}
    for f in r[chiave]:
        conta[r["pop"][f]] += 1
    return conta


def _riga(nome: str, conta: dict) -> str:
    return (f"   {nome:<34} {conta['PERIMETRO']:>6} {conta['BANCHI']:>8}"
            f" {conta['DATI-DI-PROVA']:>8}")


def _stampa(radice: pathlib.Path, r: dict, contesto: bool) -> int:
    n = len(r["tutti"])
    tot = {"PERIMETRO": 0, "BANCHI": 0, "DATI-DI-PROVA": 0}
    for f in r["tutti"]:
        tot[r["pop"][f]] += 1

    print(f"ALBERO MISURATO: {radice.resolve()}")
    print(f"file: {n}   (roster: scripts/nomi_delle_sessioni.py)\n")
    print(f"   {'':<34} {'PERIM.':>6} {'BANCHI':>8} {'PROVA':>8}")
    print(_riga("file totali", tot))
    print("   " + "─" * 58)
    print("🔴 BLOCCANTI (solo la colonna PERIMETRO deve andare a zero)")
    print(_riga("① nome di sessione nel TESTO", _per_pop(r, "nome")))
    print(_riga("② nome di sessione nel PATH", _per_pop(r, "path_nome")))
    print(_riga("③ path locale nel TESTO", _per_pop(r, "locale")))
    print("⚪ DICHIARATA — resta per decisione del 12/09")
    print(_riga("④ sigla wsN nel PATH", _per_pop(r, "path_sigla")))

    bloccanti = [f for f in set(r["nome"]) | set(r["path_nome"]) | set(r["locale"])
                 if r["pop"][f] == "PERIMETRO"]
    print(f"\n   ⇒ DA TOCCARE nel perimetro: {len(bloccanti)} su {tot['PERIMETRO']}")
    if bloccanti:
        for f in sorted(bloccanti)[:10]:
            print(f"      {f.relative_to(radice).as_posix()}")
        if len(bloccanti) > 10:
            print(f"      … e altri {len(bloccanti) - 10}")

    if contesto:
        print("\n=== ① IL CONTESTO DEI NOMI — classificali a mano ===")
        for f in r["nome"]:
            if r["pop"][f] != "PERIMETRO":
                continue
            t = _testo(f)
            for nome, pos in [(n, p) for n, p in trova(t) if n.lower() not in SIGLE]:
                a = max(0, pos - _CONTESTO)
                frammento = t[a:pos + len(nome) + _CONTESTO].replace("\n", "⏎")
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

        nome = scrivi("testo/nota.md", "reperto di Tara, 6,8 misurati")
        locale = scrivi("loc/nota.md", r"C:\Users\qualcuno\AppData\Local\Temp\x")
        doppio = scrivi("loc/doppio.md", r"path in JSON: C:\\Users\\qualcuno\\x")
        scrivi("banchi/aldo-prova.py", "print(1)")
        scrivi("banchi-ws2/prova.py", "print(1)")
        scrivi("banchi-04/dentro.md", "reperto di Vega")
        prova = scrivi("00-ESAME.md", "Corrado Ferri - job title is giardiniere")
        # controllo NEGATIVO: parole che CONTENGONO un nome senza esserlo, e la
        # forma minuscola di un ambiguo. Se questo si accende, OGNI numero sale.
        neg = scrivi("negativo.md",
                     "tarare la bilancia, il caldo, Marielle, ws9, "
                     "hanno aperto un varco nel muro")

        r = misura(radice)
        pop = r["pop"]
        esiti.append(("① nome nel testo si accende", nome in set(r["nome"])))
        esiti.append(("③ path locale si accende", locale in set(r["locale"])))
        esiti.append(("③ separatore DOPPIO si accende (valeva 19 occorrenze)",
                      doppio in set(r["locale"])))
        esiti.append(("② nome nel PATH si accende",
                      any("aldo-prova" in f.as_posix() for f in r["path_nome"])))
        esiti.append(("② e NON e' visto dal testo",
                      not any("aldo-prova" in f.as_posix() for f in r["nome"])))
        esiti.append(("controllo NEGATIVO resta spento (`caldo`, `tarare`, "
                      "`varco` minuscolo)", neg not in set(r["nome"])))
        esiti.append(("`banchi-ws2` e' BANCHI (non `/banchi/`)",
                      pop[radice / "banchi-ws2" / "prova.py"] == "BANCHI"))
        esiti.append(("`banchi-04` e' BANCHI",
                      pop[radice / "banchi-04" / "dentro.md"] == "BANCHI"))
        esiti.append(("`00-ESAME.md` e' DATI-DI-PROVA", pop[prova] == "DATI-DI-PROVA"))
        esiti.append(("un nome nei BANCHI non entra nel bloccante del perimetro",
                      _per_pop(r, "nome")["PERIMETRO"] == 1))
        esiti.append(("`Vega` (roster) si accende",
                      any("dentro" in f.as_posix() for f in r["nome"])))

        nome.write_text("reperto del Product Owner", encoding="utf-8")
        esiti.append(("① si SPEGNE tolto il nome",
                      nome not in set(misura(radice)["nome"])))

    for testo_esito, ok in esiti:
        print(f"   {'✅' if ok else '🔴'} {testo_esito}")
    caduti = [t for t, ok in esiti if not ok]
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
