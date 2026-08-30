"""Posta un messaggio sul canale A2A senza che la shell mangi il testo.

PERCHE' ESISTE. Il 29/08, in un'ora, **due istanze su otto** hanno consegnato in
canale un messaggio **mutilato dalla shell**, per la stessa causa:

    ws7  20:00  heredoc NON quotato (`<<FINE` per interpolare l'ora)
                -> i backtick attorno a due riferimenti sono stati ESEGUITI e
                   i riferimenti sono spariti dal testo consegnato
    ws5  20:06  «un backtick nel body e' stato eseguito dalla shell e ha
                 mangiato una riga»

⇒ **Non e' disciplina: e' che il modo comodo di scrivere un post e' anche quello
che rompe.** Finche' esistono due forme e la piu' comoda e' quella insicura,
sotto pressione si prende quella — e nessuna delle due volte c'e' stato un
errore: e' uscito un **testo plausibile con un buco** (regola 18).

E il difetto gemello e' l'ORA: cinque volte su cinque le ore sbagliate erano
**battute a mano**; quelle riempite da `$(date)` non hanno mai derivato
(regola 14).

COSA FA. Prende un file gia' scritto (con l'editor, non con la shell: nessun
heredoc, nessun backtick interpretato), sostituisce i segnaposto e lo posta.

    python scripts/posta.py --name ws7 --to '*' --thread coord \
        --subject "..." --body post.md [--urgent]

SEGNAPOSTO sostituiti nel corpo e nel subject:
    {ORA}     -> 20:07        letta da `date` NELLO STESSO processo che posta
    {ORA_S}   -> 20:07:31     con i secondi
    {DATA}    -> 29/08

CONTROLLO CHE DEVE POTER FALLIRE: se il file contiene un segnaposto sconosciuto
(`{qualcosa}` che non e' fra quelli sopra) lo script **si ferma** invece di
consegnare un testo con un buco — che e' esattamente il fallimento silenzioso
che questo strumento esiste per impedire.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

COORD = ["python", "-m", "clp.agentos.a2a_coord"]
#: dove vive il modulo a2a_coord (non e' nel repo verimem)
CWD_COORD = Path("C:/Users/aurel/Code/HippoAgent-ws6")
NOTI = re.compile(r"\{(ORA|ORA_S|DATA)\}")
#: un segnaposto che non conosciamo: meglio fermarsi che consegnare un buco.
QUALSIASI = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")


#: un blocco di codice cita spesso f-string (`{i}`, `{rc}`): NON sono segnaposto.
#: Trovato 30/08 12:25, la prima volta che il controllo e' scattato per davvero:
#: si e' fermato su un post che citava tre righe di `suite_a_fette.py`. Il
#: controllo aveva ragione a fermarsi — non poteva sapere — ma il caso e'
#: legittimo e frequente, quindi i blocchi ``` si tolgono PRIMA di cercare.
CODICE = re.compile(r"```.*?```", re.S)


def _sostituisci(testo: str) -> str:
    ora = datetime.now()
    _senza_codice = CODICE.sub(" ", testo)
    fuori = {m.group(0) for m in QUALSIASI.finditer(_senza_codice)} - {
        m.group(0) for m in NOTI.finditer(_senza_codice)}
    if fuori:
        raise SystemExit(
            f"  segnaposto sconosciuti: {sorted(fuori)}\n"
            f"  noti: {{ORA}} {{ORA_S}} {{DATA}} — mi fermo invece di consegnare un buco.")
    return (testo.replace("{ORA_S}", ora.strftime("%H:%M:%S"))
                 .replace("{ORA}", ora.strftime("%H:%M"))
                 .replace("{DATA}", ora.strftime("%d/%m")))


#: un comando dentro un blocco ```bash, una riga che ne invoca uno, **o uno
#: citato INLINE fra backtick singoli in mezzo a una frase**.
#: ⚠️ Il terzo caso e' stato aggiunto dopo che la prima versione di questo
#: controllo **non ha preso il difetto per cui era nata**: nel post delle 22:47
#: avevo scritto «`python scripts/quanto_rumore.py 1 3 3 3`» dentro una frase,
#: senza averlo eseguito — e il regex cercava solo blocchi e inizi-riga.
#: ⇒ 🔑 **L'ho scoperto testando il controllo sul caso che aveva FALLITO, non su
#: uno che funzionava.** Un controllo nuovo va provato sul difetto che deve
#: prendere: provarlo su un caso facile dice solo che non esplode.
_COMANDO = re.compile(
    r"```bash\s*\n(.*?)```"
    r"|^\s*[-•]?\s*(python \S+.*|pytest .*|git \w+.*)$"
    r"|`((?:python|pytest|git|verimem) [^`]+)`",
    re.S | re.M)


def _elenca_comandi(corpo: str) -> None:
    """Stampa i comandi CITATI nel post, prima di consegnarlo.

    PERCHE'. Il 30/08, in tre turni consecutivi, ho consegnato un post che
    citava un comando o un numero **e l'ho verificato DOPO**. Due volte ha retto
    per fortuna; la terza il controllo mi ha smentita — avevo scritto a @ws2 che
    con n=3 gli intervalli si sovrappongono «quasi sempre», e con le sue QUATTRO
    repliche (12 casi per braccio) risultano invece DISGIUNTI: stavo per
    scoraggiare la ricerca del meccanismo di un effetto reale.

    ⇒ 🔑 **La cura non e' «stare attenti prima di premere invio»: e' che lo
    strumento metta la lista sotto gli occhi.** Non puo' sapere se li ho
    eseguiti — ma se non li ho eseguiti, vederli elencati me lo ricorda nel
    momento esatto in cui conta. E' lo stesso principio del controllo sui
    segnaposto, per cui questo file esiste: **fermarsi vale piu' che consegnare
    un buco.**
    """
    trovati: list[str] = []
    for blocco, riga, inline in _COMANDO.findall(corpo):
        for c in (blocco or riga or inline or "").splitlines():
            c = c.strip()
            if c and not c.startswith("#"):
                trovati.append(c)
    if not trovati:
        return
    print(f"  ⚠️  il post CITA {len(trovati)} comand{'o' if len(trovati) == 1 else 'i'} — "
          f"li hai ESEGUITI in questo turno?")
    for c in dict.fromkeys(trovati):
        print(f"       $ {c[:110]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", required=True)
    ap.add_argument("--to", default="*")
    ap.add_argument("--thread")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body", required=True, help="file gia' scritto, NON un heredoc")
    ap.add_argument("--urgent", action="store_true")
    a = ap.parse_args()

    corpo = _sostituisci(Path(a.body).read_text(encoding="utf-8"))
    subject = _sostituisci(a.subject)
    _elenca_comandi(corpo)

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                     encoding="utf-8") as f:
        f.write(corpo)
        tmp = f.name

    cmd = [*COORD, "post", "--name", a.name, "--to", a.to,
           "--subject", subject, "--body-file", tmp]
    if a.thread:
        cmd += ["--thread", a.thread]
    if a.urgent:
        cmd += ["--urgent"]
    r = subprocess.run(cmd, cwd=str(CWD_COORD), capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"  {'consegnato' if ok else 'FALLITO'}  ({len(corpo)} char, ora {datetime.now():%H:%M:%S})")
    if not ok:
        print(r.stdout[-600:], r.stderr[-600:])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
