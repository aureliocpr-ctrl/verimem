"""RED/GREEN del difetto cp1252 del job `wheel install-from-scratch (windows)`.

Isola LA VARIABILE CHE CAMBIO: il lettore. L'emettitore e' identico nei due
bracci - un processo che stampa su stdout, in UTF-8, la stessa riga JSON che il
server MCP manda in risposta a `initialize`, con dentro la guida vera del
pacchetto (quella che contiene ⚠️, cioe' il byte 0x8f).

Non avvia `verimem mcp`: non serve, e cambierebbe due cose invece di una. Qui la
domanda e' «lo stesso stdout, letto in due modi, da quale dei due si rompe».

    PYTHONUTF8=0 python red_cp1252.py     # riproduce la CI windows
"""
from __future__ import annotations

import json
import locale
import pathlib
import re
import subprocess
import sys

# La guida vera, dal repo: path RELATIVO alla radice, non cablato — un banco
# con un path assoluto gira solo sulla macchina di chi l'ha scritto.
RADICE = pathlib.Path(__file__).resolve().parents[3]
GUIDA_PY = RADICE / "verimem" / "agent_guide.py"
if not GUIDA_PY.exists():  # pragma: no cover
    print(f"  guida non trovata: {GUIDA_PY}"); sys.exit(2)
SRC = GUIDA_PY.read_text(encoding="utf-8")

m = re.search(r'VERIMEM_AGENT_GUIDE\s*=\s*(?:r?"""|\'\'\')(.*?)(?:"""|\'\'\')', SRC, re.S)
GUIDA = m.group(1)

# L'emettitore: stampa la riga JSON in UTF-8 sui BYTE, come fa un server MCP.
EMETTITORE = (
    "import json,sys\n"
    "g = json.loads(sys.stdin.readline())['g']\n"
    "msg = {'jsonrpc':'2.0','id':1,'result':{'instructions': g}}\n"
    # ensure_ascii=False: il server MCP emette i CARATTERI, non le fughe \\uXXXX.
    # Senza questo l'emettitore produce JSON tutto ASCII e il banco non riproduce
    # niente - i due bracci escono OK entrambi e sembrerebbe che la diagnosi cada.
    "sys.stdout.buffer.write((json.dumps(msg, ensure_ascii=False)+chr(10))"
    ".encode('utf-8'))\n"
    "sys.stdout.buffer.flush()\n"
)


def leggi(encoding: str | None) -> tuple[bool, str]:
    """Un giro completo: apro, mando la guida, rileggo la riga. Come il job."""
    kw = {"encoding": encoding} if encoding else {}
    p = subprocess.Popen([sys.executable, "-c", EMETTITORE],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, **kw)
    try:
        p.stdin.write(json.dumps({"g": GUIDA}) + "\n")
        p.stdin.flush()
        line = p.stdout.readline()
        msg = json.loads(line.strip())
        return ("result" in msg), ""
    except Exception as e:  # noqa: BLE001 - e' esattamente cio' che misuro
        return False, f"{type(e).__name__}: {str(e)[:80]}"
    finally:
        p.kill(); p.wait(timeout=30)


def main() -> int:
    print(f"  ambiente: utf8_mode={sys.flags.utf8_mode} "
          f"getpreferredencoding={locale.getpreferredencoding(False)}")
    print(f"  guida: {len(GUIDA)} caratteri, {len(GUIDA.encode('utf-8'))} byte UTF-8")
    print()
    rosso_ok, rosso_err = leggi(None)          # com'e' oggi nel workflow
    verde_ok, verde_err = leggi("utf-8")       # con la cura
    print(f"  SENZA encoding (com'e' oggi) : {'OK' if rosso_ok else 'ROTTO'}  {rosso_err}")
    print(f"  CON encoding='utf-8' (cura)  : {'OK' if verde_ok else 'ROTTO'}  {verde_err}")
    print()
    if locale.getpreferredencoding(False).lower().replace("-", "") == "utf8":
        print("  !!  Questo ambiente e' gia' in UTF-8: NON riproduce la CI windows.")
        print("     Rilancia con PYTHONUTF8=0 - senza, i due bracci sono identici")
        print("     e il confronto non prova niente.")
        return 2
    if not rosso_ok and verde_ok:
        print("  OK  RED->GREEN: il difetto e' nel LETTORE, e l'encoding esplicito lo chiude.")
        return 0
    if rosso_ok:
        print("  KO  il braccio SENZA encoding non si e' rotto: la diagnosi non regge qui.")
    if not verde_ok:
        print("  KO  la cura NON basta: si rompe anche con encoding='utf-8'.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
