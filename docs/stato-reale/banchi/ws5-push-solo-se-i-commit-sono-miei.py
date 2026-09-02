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
      python …/ws5-push-solo-se-i-commit-sono-miei.py TARA [percorsi,separati,da,virgola]

⚠️ **E il trailer da solo NON basta**: il 02/09 alle 01:23 un commit che non avevo
scritto portava `Agent: TARA`, con `VERIMEM_AGENT` **assente** dall'ambiente (shell e
registro). ⇒ Il controllo guarda **anche i file toccati**: se un commit esce dal
perimetro dell'istanza, si ferma comunque.
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
    # il PERIMETRO: i percorsi che questa istanza tocca. Un commit che esce di qui
    # non e' suo, e il trailer non basta a smentirlo (reperto del 02/09 01:23).
    perimetro = sys.argv[2].split(",") if len(sys.argv) > 2 else ["banchi/ws5-", "00-ESAME"]

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
    print("  %-10s %-10s %-40s %s" % ("commit", "agente", "messaggio", "verdetto"))
    print("  " + "-" * 96)
    for r in righe:
        parti = r.split("\t")
        sha = parti[0].strip()
        msg = parti[1].strip() if len(parti) > 1 else ""
        agente = (parti[2] if len(parti) > 2 else "").strip() or "(nessun trailer)"
        # ⚠️ IL TRAILER NON BASTA: il 02/09 alle 01:23 un commit che NON avevo
        # scritto portava `Agent: TARA`, e `VERIMEM_AGENT` non era nell'ambiente.
        # ⇒ il righello solido sono i FILE: se un commit tocca qualcosa fuori dal
        # mio perimetro, non e' mio, qualunque cosa dica il trailer.
        tocca = [f for f in git("show", "--stat=200", "--name-only", "--format=",
                                sha).stdout.splitlines() if f.strip()]
        fuori = [f for f in tocca if not any(p in f for p in perimetro)]
        suo = agente != mio or bool(fuori)
        motivo = ""
        if agente != mio:
            motivo = "🔴 trailer «%s»" % agente[:10]
        elif fuori:
            motivo = "🔴 tocca %s" % fuori[0][-34:]
        if suo:
            altrui.append((sha, agente, motivo))
        print("  %-10s %-10s %-40s %s" % (sha, agente[:10], msg[:40], motivo or "✔ mio"))

    if altrui:                                                    # ③
        print("\n  ⛔ NON PUSHO: %d commit non tuoi davanti a origin." % len(altrui))
        for sha, agente, motivo in altrui:
            print("     %s  %s" % (sha, motivo or ("di " + agente)))
        print("  ⇒ Chi li ha scritti potrebbe volerli amendare o verificare prima.")
        print("     Aspetta che li pushi lui, oppure chiediglielo sul canale.")
        raise SystemExit(1)

    r = git("push", "origin", "main")                             # ④
    # ⚠️ (!) LA PRIMA VERSIONE STAMPAVA «pushato» SENZA GUARDARE L'ESITO: il 02/09 alle
    # 13:20 un push respinto per non-fast-forward («Note about fast-forwards») e' stato
    # annunciato come riuscito. E' esattamente il difetto che questo script esiste per
    # evitare — un controllo che RACCONTA invece di VERIFICARE — commesso qui dentro.
    # ⇒ ora si legge il codice di uscita, e il fallimento dice cosa fare.
    if r.returncode != 0:
        print("\n  🔴 IL PUSH E' FALLITO (exit %d) — NON e' stato pubblicato niente."
              % r.returncode)
        for riga in (r.stderr or r.stdout or "").strip().splitlines()[-4:]:
            print("     %s" % riga[:110])
        if "fast-forward" in (r.stderr or "") or "rejected" in (r.stderr or ""):
            print("  ⇒ origin e' avanti: `git pull --rebase origin main`, poi RIESEGUI")
            print("     questo script (che ricontrollera' l'autore di ogni commit).")
        raise SystemExit(1)
    print("\n  ✅ tutti e %d i commit sono tuoi — pushato (exit 0)." % len(righe))
    for riga in (r.stderr or r.stdout or "").strip().splitlines()[-2:]:
        print("     %s" % riga[:110])


main()
