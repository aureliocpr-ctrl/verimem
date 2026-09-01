r"""Chi installa `verimem` oggi riceve `mcp 2.x`: il server MCP parte ancora?

Paga il limite che ho dichiarato alle 00:11 consegnando il reperto sul tetto mancante:
«*NON misurato: **se con `mcp 2.1.1` il prodotto si rompa davvero**. Una major puo'
essere retrocompatibile sull'uso che ne facciamo*».

IL FATTO GIA' MISURATO (`0f47b779` e il post delle 00:11)::

    su PyPI                    verimem 0.7.0, caricata il 22 luglio
    verimem 0.7.0 dichiara     mcp>=1.0.0        ← nessun tetto
    verimem 0.7.1 (branch)     mcp<2,>=1.0.0     ← il tetto c'e'
    mcp su PyPI                2.1.1, ultima upload 2026-08-25

⚠️ **E `mcp 2.0` non e' una major di cortesia**, lo dice la sua stessa pagina: «*This is
**v2** of the MCP Python SDK […] **a major rework of the SDK***» e «*Not ready to
**migrate**? v1.x lives on the `v1.x` branch*».
⚠️ E i tre file di `verimem` che importano `mcp` usano anche
`mcp.server.lowlevel.helper_types` — **API lowlevel**, quella che in un rework cambia
per prima.

L'A/B, stessa macchina, stesso Python, **due venv vergini**::

    venv A   pip install verimem            ← quello che fa un utente OGGI
    venv B   pip install <wheel 0.7.1>      ← il candidato al rilascio, col tetto

⇒ Per ognuno: **quale `mcp` e' arrivato**, e **`import verimem.mcp_server` riesce?**
Quell'import e' il test che @ws1 aveva chiesto per la `C7`, ed e' la porta che
`pyproject.toml` chiama «*MCP server — the HEADLINE use*».

⚠️ **COSA QUESTO BANCO NON DICE**: che il server *funzioni* — misura che **si importi**.
Un import riuscito non prova che una sessione MCP completa vada a buon fine; un import
fallito prova che non ci arriva nemmeno.

SOLA LETTURA sui due venv gia' creati; non installa e non modifica nulla.
⚖️ PUNTI DEBOLI: una macchina, un Python (3.13.12); e i due venv differiscono per **due**
cose insieme (la versione di verimem **e** quella di mcp), quindi un fallimento in A non
si attribuisce da solo a `mcp` — va letto insieme al tetto, che e' l'unica differenza
dichiarata fra i due metadata.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-versione-pubblicata-con-mcp-2.py <venvA> <venvB>
"""
import os
import subprocess
import sys

SONDE = [
    ("mcp installato",
     "import importlib.metadata as m; print(m.version('mcp'))"),
    ("verimem installato",
     "import importlib.metadata as m; print(m.version('verimem'))"),
    ("import mcp.server",
     "import mcp.server; print('ok')"),
    ("import helper_types (lowlevel)",
     "from mcp.server.lowlevel.helper_types import ReadResourceContents; print('ok')"),
    ("import verimem.mcp_server",
     "import verimem.mcp_server; print('ok')"),
]


def prova(venv, codice):
    exe = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(exe):
        return "(venv assente)"
    # ⚠️ ambiente pulito e cwd fuori dal repo: senza, si importerebbe il sorgente
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        r = subprocess.run([exe, "-c", codice], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180, env=env,
                           cwd=os.path.dirname(venv))
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    if r.returncode == 0:
        return (r.stdout or "").strip().splitlines()[-1] if r.stdout.strip() else "ok"
    err = [x for x in (r.stderr or "").splitlines() if x.strip()]
    ultima = err[-1] if err else "(nessun messaggio)"
    return "🔴 " + ultima[:96]


def main():
    if len(sys.argv) < 3:
        print("uso: python %s <venv-pubblicata> <venv-0.7.1>" % sys.argv[0])
        raise SystemExit(2)
    a, b = sys.argv[1], sys.argv[2]
    print("  %-32s %-34s %s" % ("sonda", "A: pip install verimem", "B: wheel 0.7.1"))
    print("  " + "-" * 104)
    esiti = {}
    for nome, codice in SONDE:
        ra, rb = prova(a, codice), prova(b, codice)
        esiti[nome] = (ra, rb)
        print("  %-32s %-34s %s" % (nome, ra[:34], rb[:40]))

    print("\n=== SINTESI ===")
    mcp_a = esiti.get("mcp installato", ("", ""))[0]
    mcp_b = esiti.get("mcp installato", ("", ""))[1]
    imp_a = esiti.get("import verimem.mcp_server", ("", ""))[0]
    imp_b = esiti.get("import verimem.mcp_server", ("", ""))[1]
    low_a = esiti.get("import helper_types (lowlevel)", ("", ""))[0]

    if not mcp_a.startswith("2"):
        print("  ⚠️ nel venv A NON e' arrivata una `mcp 2.x` (%s): il rischio del tetto" % mcp_a)
        print("     mancante NON si manifesta oggi, e il reperto resta latente.")
    elif imp_a.startswith("🔴"):
        print("  🔴🔴 CON mcp %s L'IMPORT DEL SERVER FALLISCE: chi installa verimem oggi" % mcp_a)
        print("       NON puo' usare la porta che il pacchetto chiama «the HEADLINE use».")
        print("       %s" % imp_a)
        if not imp_b.startswith("🔴"):
            print("  ✅ e con mcp %s (wheel 0.7.1, col tetto) l'import RIESCE" % mcp_b)
            print("     ⇒ il tetto e' esattamente cio' che separa i due casi.")
    else:
        print("  🟢 con mcp %s l'import del server RIESCE lo stesso: la major non rompe" % mcp_a)
        print("     l'uso che ne facciamo, e il tetto mancante e' un rischio NON attivo.")
        if low_a.startswith("🔴"):
            print("  ⚠️ ma l'API lowlevel NON si importa (%s):" % low_a[:60])
            print("     il percorso completo va provato, non solo il modulo.")


main()
