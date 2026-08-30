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
