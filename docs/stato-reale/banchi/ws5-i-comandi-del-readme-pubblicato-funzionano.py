r"""I comandi che il README PUBBLICATO dice di eseguire funzionano davvero?

E' il dogfooding che nessuno ha ancora fatto: non «il README dice il vero» (lo stanno
misurando @ws4 e @ws7 sui numeri), ma **«se un utente fa quello che c'e' scritto,
succede quello che dice?»**.

⚠️ La vetrina che conta e' quella **pubblicata**: chi arriva su PyPI legge il README
della **0.7.0 del 22 luglio**, non quello di `main`. Quindi i comandi li estraggo dal
`METADATA` del wheel scaricato da PyPI, non dal repo.

COME: estraggo dal README le righe che invocano `verimem`, le eseguo nel venv vergine
con `pip install verimem`, e guardo **exit code e prime righe di output**.

🔴 **FILTRO DI SICUREZZA, e non e' una formalita'**: il README puo' citare comandi
**distruttivi** (`reset` cancella episodi, skill e fatti; `forget` rimuove). Quelli si
**elencano e non si eseguono** — su uno store temporaneo il danno sarebbe nullo, ma un
banco che esegue alla cieca cio' che trova in un testo e' un banco che prima o poi lo
esegue altrove.

🔴 ESITO — **due comandi su otto crashano, e il README non dice cosa manca**::

    comando (dal README PUBBLICATO)             exit   cosa vede l'utente
    verimem index contract.pdf                    1    file not found: contract.pdf
    verimem search-docs "termination clause"      0    no results (index empty)
    verimem trust "the deploy is green" …         0    il pannello trust
    verimem airgap                                1    il pannello airgap (avvisi)
    verimem airgap --live                         0    ok
    verimem console                               1    🔴 TRACEBACK
    verimem gateway keys create --tenant acme …   0    key created for tenant acme
    verimem gateway serve                         1    🔴 TRACEBACK

    (2 comandi `verimem import …` ELENCATI e non eseguiti: distruttivi)

🔑 **L'errore in fondo al traceback e' OTTIMO**::

    ImportError: the gateway needs fastapi — pip install 'verimem[server]'

Dice **cosa manca** e **come si risolve**. ⇒ Il difetto non e' il messaggio: e' che
arriva dentro **venti righe di traceback Python**, quando potrebbe essere una riga.

🔴 **MA IL REPERTO VERO E' NEL README**: quegli extra **non sono MAI menzionati** —
`grep` su tutto il README pubblicato: **zero occorrenze** di `[server]`. E il commento
accanto al comando dice::

    verimem console        # your OWN local store: browser opens, no keys, no config

⇒ **Il browser non si apre.** Un utente che installa come dice il README
(`pip install verimem`) e lancia cio' che il README mostra, ottiene un traceback — e
**nel testo non c'e' nulla che glielo faccia prevedere**. Gli extra esistono e sono
dichiarati nel `METADATA` (`ann, audit, byok, dev, documents, full, mcp-only, server,
tui, vision`): manca **una riga nel README**, non una funzionalita'.

✅ **E LA CURA E' DIMENSIONATA, non ipotizzata**: eseguito
`pip install 'verimem[server]'` — **8.3 secondi, quattro pacchetti** (fastapi, httptools,
watchfiles, websockets) — i due comandi **funzionano**::

    verimem console        exit 124 (= il timeout del banco: ERA IN ESECUZIONE), 0 traceback
                           «(personal mode, loopback only)»
    verimem gateway serve  exit 124, 0 traceback
                           «Uvicorn running on http://127.0.0.1:8377»

⇒ Sono **server**: restano attivi, e il mio `timeout` li ha interrotti — che e' la prova
che partivano. ⇒ **La cura e' una riga nel README** (`pip install 'verimem[server]'`
accanto a quei comandi), e costa all'utente **otto secondi**. Non e' una funzionalita'
mancante: e' una riga di testo.

🪞 **E questo banco ha sbagliato TRE volte prima di dire il vero**, ogni volta in modo
che sarebbe passato inosservato::

    ① `cmd.split()` spezzava «"termination clause"» in due argomenti ⇒ due comandi
       risultavano rotti (exit 2, «Usage:») e il difetto era MIO
    ② `exit 1` trattato come «va bene» ⇒ la sintesi stampava «tutti i comandi
       partono» SOPRA due traceback
    ③ senza il filtro sui distruttivi avrei eseguito `verimem import …`

⇒ **Due volte su tre il misuratore sbagliava a FAVORE del prodotto**, e la terza
sarebbe stata un'azione, non una misura.

REGIME: venv vergine su Windows (`pip install verimem` → 0.7.0) · ambiente **pulito**
(le 9 variabili nostre tolte) · CWD **fuori dal repo** · store **temporaneo**.
⚖️ PUNTI DEBOLI: l'estrazione e' una regex sul README — prende i comandi che *sembrano*
tali e puo' mancarne o inventarne; per ognuno riporto **cosa ho eseguito**, cosi' chi
legge vede se la sonda era sensata. E un comando che «esce a zero» non e' un comando che
fa quello che il README promette: qui misuro **che non fallisca**.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-i-comandi-del-readme-pubblicato-funzionano.py <wheel> <venv> <store>
"""
import os
import re
import shlex
import subprocess
import sys
import zipfile

#: comandi che NON si eseguono mai, nemmeno su uno store temporaneo
DISTRUTTIVI = ("reset", "forget", "import", "requalify", "prune", "consolidate")
#: il README ne cita molti: ne provo un numero fisso, i primi in ordine di apparizione
QUANTI = 8


def comandi_dal_readme(wheel):
    z = zipfile.ZipFile(wheel)
    md = [n for n in z.namelist() if n.endswith("METADATA")][0]
    testo = z.read(md).decode("utf-8", "replace")
    trovati, visti = [], set()
    for riga in testo.splitlines():
        r = riga.strip().lstrip("$").strip()
        if not r.startswith("verimem "):
            continue
        r = r.split("#")[0].strip().rstrip("\\").strip()
        # niente placeholder: un comando con <...> non e' eseguibile come sta
        if "<" in r or ">" in r or "|" in r:
            continue
        if r not in visti:
            visti.add(r)
            trovati.append(r)
    return trovati


def main():
    if len(sys.argv) < 4:
        print("uso: python %s <wheel> <venv> <store>" % sys.argv[0])
        raise SystemExit(2)
    wheel, venv, store = sys.argv[1], sys.argv[2], sys.argv[3]
    exe = os.path.join(venv, "Scripts", "verimem.exe")
    if not os.path.exists(exe):
        print("  🔴 verimem non installato in %s" % venv)
        return

    tutti = comandi_dal_readme(wheel)
    print("  comandi `verimem …` eseguibili trovati nel README PUBBLICATO: %d" % len(tutti))
    saltati = [c for c in tutti if any(c.split()[1:2] == [d] for d in DISTRUTTIVI)]
    sicuri = [c for c in tutti if c not in saltati]
    if saltati:
        print("  ⛔ NON eseguiti (distruttivi): %s" % ", ".join(saltati))
    print()

    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["HIPPO_DATA_DIR"] = store
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    print("  %-46s %-6s %s" % ("comando eseguito (dal README)", "exit", "prima riga utile"))
    print("  " + "-" * 104)
    esiti = []
    for cmd in sicuri[:QUANTI]:
        # ⚠️ `cmd.split()` spezza «"termination clause"» in DUE argomenti e il
        # comando esce 2 con «Usage:» — che sembra un difetto del README ed e' un
        # difetto del banco. `shlex` rispetta le virgolette come farebbe una shell.
        args = shlex.split(cmd, posix=False)[1:]
        args = [a.strip('"') for a in args]
        try:
            r = subprocess.run([exe] + args, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=300,
                               env=env, cwd=os.path.dirname(venv))
            code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            code, out = "TIMEOUT", ""
        utili = [x.strip() for x in out.splitlines()
                 if x.strip() and "RuntimeWarning" not in x and not x.startswith("W0")
                 and "_threshold_of_record" not in x and "triton" not in x]
        prima = " ".join(" ".join(utili[:2]).split())[:52] if utili else "(nessun output)"
        # ⚠️ `exit 1` NON basta a dire «e' andata bene»: `doctor` esce 1 per due
        # AVVISI documentati, e `console` esce 1 con un TRACEBACK. Trattarli uguali
        # nasconde i crash — e la prima versione di questo banco lo faceva, stampando
        # «tutti i comandi partono» sopra due traceback.
        crash = "Traceback" in out
        esiti.append((cmd, code, crash))
        print("  %-46s %-6s %s" % (cmd[:46], code, prima))

    print("\n=== SINTESI ===")
    if not esiti:
        print("  ⚠️ nessun comando eseguibile estratto: la regex non ha trovato nulla di")
        print("     utilizzabile, e questo banco non dice niente sul README.")
        return
    crashati = [(c, e) for c, e, k in esiti if k]
    altri = [(c, e) for c, e, k in esiti if not k and e not in (0, 1)]
    ok = [c for c, e, k in esiti if not k and e in (0, 1)]
    print("  eseguiti %d · senza traceback: %d · CON TRACEBACK: %d · altri errori: %d"
          % (len(esiti), len(ok), len(crashati), len(altri)))
    if crashati:
        print("  🔴 COMANDI DEL README CHE CRASHANO con un traceback:")
        for c, e in crashati:
            print("     %-44s exit %s" % (c, e))
        print("  ⇒ un utente che segue il README vede un traceback Python, non un errore")
        print("    del prodotto. E' la differenza fra «non posso farlo» e «si e' rotto».")
    if altri:
        print("  ⚠️ altri exit inattesi: %s" % ", ".join("%s(%s)" % (c[:30], e) for c, e in altri))
    if not crashati and not altri:
        print("  🟢 nessun comando provato crasha.")
    print("  ⚠️ E «non crasha» non e' «fa quello che il README promette»: qui misuro")
    print("     che non si rompa, non che mantenga.")


main()
