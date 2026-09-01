r"""Pusha SOLO se ogni commit davanti a origin e' tuo. Altrimenti si ferma e te li mostra.

Nasce da un errore che ho fatto **due volte in otto minuti**, la seconda **con il
controllo davanti agli occhi**::

    01:17   push → porta su origin `2af0eb47`, dell'agente **Aldo**
    01:18   scrivo sul canale la lezione: «prima di pushare, LEGGI l'autore»
    01:26   stampo `in attesa: … [Curie] …`  e **pusho lo stesso**

⇒ Il difetto non era non sapere: era che **il controllo mostrava e non fermava**. E' la
stessa forma che sto misurando nel prodotto da due giorni — *un campo stampato e non
letto e' un campo assente* — applicata a me.

🔑 **La differenza fra un avviso e un presidio**: un avviso lo puoi ignorare senza
accorgertene; un presidio ti obbliga a decidere. Questo script e' il presidio.

COSA FA::

    ①  git fetch (per non leggere un `origin/main` stantio)
    ②  elenca i commit davanti a origin con AUTORE (trailer `Agent:`)
    ③  se ce n'e' anche uno solo non tuo → ESCE 1 e NON pusha
    ④  altrimenti → pusha

⚠️ **Perche' il trailer e non `%an`**: su questa macchina l'autore git e' sempre
«Aurelio Capriello» per tutte le istanze — e' il trailer `Agent:` a dire chi ha scritto.
Chi si affida a `%an` vede otto istanze come una sola persona.

USO:  python docs/stato-reale/banchi/ws5-push-solo-se-i-commit-sono-miei.py <TuoAgente>
      python …/ws5-push-solo-se-i-commit-sono-miei.py TARA
"""
import subprocess
import sys


def git(*args, check=False):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=check)


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <NomeAgente>   (es. TARA)" % sys.argv[0])
        raise SystemExit(2)
    mio = sys.argv[1].strip()

    git("fetch", "-q", "origin")                                  # ①
    # ⚠️ `%(trailers:…,valueonly)` porta con se' un A CAPO: dentro una riga
    # tab-separata spezza il record, e il commit dopo sembra «di un altro».
    # La prima versione bloccava un commit MIO per questo — un presidio che
    # sbaglia FERMANDO e' il difetto giusto da avere, ma resta un difetto.
    # ⇒ record separati da NUL, e il trailer ripulito a mano.
    out = git("log", "origin/main..HEAD",
              "--format=%x00%h\t%s\t%(trailers:key=Agent,valueonly)").stdout   # ②
    righe = [r.replace("\n", " ").strip() for r in out.split("\x00") if r.strip()]
    if not righe:
        print("  niente da pushare: HEAD == origin/main")
        return

    altrui = []
    print("  %-10s %-12s %s" % ("commit", "agente", "messaggio"))
    print("  " + "-" * 88)
    for r in righe:
        parti = r.split("\t")
        sha = parti[0].strip()
        msg = parti[1].strip() if len(parti) > 1 else ""
        agente = (parti[2] if len(parti) > 2 else "").strip() or "(nessun trailer)"
        suo = agente != mio
        if suo:
            altrui.append((sha, agente))
        print("  %-10s %-12s %s %s" % (sha, agente[:12], msg[:56],
                                       "🔴 NON TUO" if suo else ""))

    if altrui:                                                    # ③
        print("\n  ⛔ NON PUSHO: %d commit non tuoi davanti a origin." % len(altrui))
        for sha, agente in altrui:
            print("     %s di %s" % (sha, agente))
        print("  ⇒ Chi li ha scritti potrebbe volerli amendare o verificare prima.")
        print("     Aspetta che li pushi lui, oppure chiediglielo sul canale.")
        raise SystemExit(1)

    r = git("push", "origin", "main")                             # ④
    print("\n  ✅ tutti e %d i commit sono tuoi — pushato." % len(righe))
    print("  %s" % (r.stdout or r.stderr or "").strip().splitlines()[-1:] or "")


main()
