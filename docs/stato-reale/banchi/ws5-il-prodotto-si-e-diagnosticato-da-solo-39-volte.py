r"""Il watchdog del prodotto ha scritto 39 diagnosi in tre settimane. Nessuno le ha lette.

Stanotte ho passato un'ora a costruire banchi per capire **cosa** aspettasse la prima
scrittura MCP: A/B sul daemon, A/B su `HOME`, CPU e RAM campionate a mano, lettura del
journal. ⇒ **Il prodotto lo sapeva gia'**, e lo aveva scritto **otto volte** mentre
misuravo, in `~/.engram/hang-traces/`.

`_hang_watchdog.py` e' **acceso di default** (`HIPPO_HANG_TRACE_S`, budget **30s**) e il
server lo arma **su ogni chiamata** (`mcp_server.py:7646`). Il suo docstring dice
esattamente a cosa serve — «*dump ALL thread stacks so the exact blocking frame is
captured in the act*» — e nomina perfino le cause tipiche
(`_MODEL_LOCK.acquire` / socket `recv` / sqlite lock).

⇒ Questo banco **non misura il prodotto: legge cio' che il prodotto ha gia' scritto**.

COSA FA::

    ①  legge ogni trace, isola il PRIMO dump (gli altri sono lo stesso stack)
    ②  scarta il thread del watchdog stesso — e' lui che dumpa, non chi si blocca
    ③  prende il thread piu' profondo e il suo primo frame non-`frozen`
    ④  classifica per FAMIGLIA e conta

⚠️ **COSA QUESTO PROVA, e cosa no**::

    prova       che N chiamate a tool hanno superato il budget di 30s, e QUALE frame
                stavano eseguendo quando il dump e' scattato
    NON prova   che ognuna fosse un utente in attesa (possono essere nostre sessioni)
    NON prova   che ogni hang sia durato minuti — 30s bastano a produrre un file
    NON prova   che l'import sia LA CAUSA: e' dove il thread si trovava. Cio' che rende
                la lettura solida e' la **ripetizione**: stanotte 8 hang indipendenti,
                8 volte lo stesso identico frame (`scipy/linalg/blas.py:247`).

🔴 ESITO — **39 trace dal 10/08 al 02/09, e 28 si fermano su un import**::

    per TOOL                                   per FAMIGLIA del frame bloccante
    hippo_remember              30             import di libreria pesante   28 su 39
    hippo_transcript_promote     5             altro                         8
    hippo_validate_claim         2             attesa esplicita (threading)  2
    hippo_ignorance_map          1             codice di verimem             1
    hippo_quarantine_log         1

    i frame che si RIPETONO
    scipy/special/__init__.py:785                       10
    scipy/linalg/blas.py:247                             8   ← i miei di stanotte
    torch/nn/modules/linear.py:134                       2
    transformers/tokenization_utils_tokenizers.py:145    2

⚠️⚠️ **OTTO DEI TRENTANOVE SONO MIEI, di stanotte: senza separarli gonfierei il
fenomeno con le mie stesse misure.** Separati::

    popolazione                      totale   import   di cui scipy
    PRIMA di stanotte (non miei)         31       20             11
    stanotte (miei)                       8        8              8

⇒ **Il fenomeno esiste indipendentemente da me**: **20 hang su 31** fra il **10/08 e il
30/08**, su chiamate che non ho fatto io. Il piu' colpito e' `hippo_remember`.
📌 E il 30/08 fra le **13:03 e le 13:31** ci sono **sette** hang consecutivi, tutti su
`hippo_remember`, tutti sullo stesso frame `scipy/special/__init__.py:785`.

REGIME: sola lettura, macchina di Aurelio, cartella condivisa `~/.engram/hang-traces`
(che il prodotto POTA da solo a 40 file: **il conteggio e' un minimo, non un totale**).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-prodotto-si-e-diagnosticato-da-solo-39-volte.py
"""
import datetime
import glob
import os
import re
import sys

D = os.path.expanduser(os.environ.get("HIPPO_HANG_TRACE_DIR")
                       or "~/.engram/hang-traces")

FAMIGLIE = [
    ("import di libreria pesante", ("scipy/", "torch/", "transformers/", "sympy/",
                                    "pandas/", "sentence_transformers/", "sklearn/",
                                    "numpy/", "botocore/", "importlib_metadata/")),
    ("attesa esplicita (threading)", ("threading.py",)),
    ("codice di verimem", ("encode_service.py", "anti_confab_gate.py", "semantic.py")),
]


def famiglia(frame):
    for nome, chiavi in FAMIGLIE:
        if any(k in frame for k in chiavi):
            return nome
    return "altro"


def frame_bloccante(testo):
    """Il primo frame non-frozen del thread piu' profondo, nel PRIMO dump."""
    parti = testo.split("Timeout (")
    dump = "Timeout (" + parti[1] if len(parti) > 1 else testo
    migliore = []
    for b in re.split(r"\nThread 0x", dump):
        righe = [r for r in b.splitlines() if r.strip().startswith("File ")]
        if any("_hang_watchdog" in r for r in righe):
            continue                      # ② il sorvegliante non e' il sorvegliato
        if len(righe) > len(migliore):
            migliore = righe
    for r in migliore:
        m = re.search(r'File "(.+?)", line (\d+)', r.strip())
        if not m or "frozen" in m.group(1):
            continue
        p = m.group(1)
        p = (p.split("site-packages")[-1].lstrip("\\/").replace("\\", "/")
             if "site-packages" in p else os.path.basename(p))
        return "%s:%s" % (p, m.group(2))
    return "(nessun frame leggibile)"


def main():
    file = sorted(glob.glob(os.path.join(D, "*.txt")), key=os.path.getmtime)
    if not file:
        print("  🔴 nessun trace in %s — il watchdog non ha mai scattato su questa" % D)
        print("     macchina, oppure la cartella e' stata svuotata.")
        return
    print("  cartella: %s" % D)
    print("  trace presenti: %d   (il prodotto ne tiene al massimo 40: e' un MINIMO)\n"
          % len(file))
    print("  %-13s %-30s %s" % ("data", "tool", "frame bloccante"))
    print("  " + "-" * 92)
    per_tool, per_fam, per_frame = {}, {}, {}
    prima, ultima = None, None
    for f in file:
        d = datetime.datetime.fromtimestamp(os.path.getmtime(f))
        prima = prima or d
        ultima = d
        testo = open(f, encoding="utf-8", errors="replace").read()
        m = re.search(r"tool=(\S+)", testo)
        tool = m.group(1) if m else "?"
        fr = frame_bloccante(testo)
        print("  %-13s %-30s %s" % (d.strftime("%d/%m %H:%M"), tool[:30], fr))
        per_tool[tool] = per_tool.get(tool, 0) + 1
        per_fam[famiglia(fr)] = per_fam.get(famiglia(fr), 0) + 1
        per_frame[fr] = per_frame.get(fr, 0) + 1

    print("\n=== SINTESI ===")
    print("  arco: dal %s al %s" % (prima.strftime("%d/%m %H:%M"), ultima.strftime("%d/%m %H:%M")))
    print("\n  per TOOL:")
    for k, v in sorted(per_tool.items(), key=lambda kv: -kv[1]):
        print("    %-40s %3d" % (k, v))
    print("\n  per FAMIGLIA del frame bloccante:")
    for k, v in sorted(per_fam.items(), key=lambda kv: -kv[1]):
        print("    %-40s %3d su %d" % (k, v, len(file)))
    print("\n  i frame che si RIPETONO (la ripetizione e' cio' che rende leggibile un dump):")
    for k, v in sorted(per_frame.items(), key=lambda kv: -kv[1]):
        if v > 1:
            print("    %-52s %3d" % (k, v))

    # ⚠️ separa la popolazione di CHI LEGGE da quella che ha prodotto LEGGENDO: un
    # censimento che include i propri hang misura anche se stesso.
    oggi = datetime.date.today().strftime("%Y-%m-%d")
    pre = [f for f in file
           if datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d") != oggi]
    if pre and len(pre) != len(file):
        imp_pre = 0
        for f in pre:
            if famiglia(frame_bloccante(open(f, encoding="utf-8",
                                             errors="replace").read())) \
                    == "import di libreria pesante":
                imp_pre += 1
        print("\n  ⚠️ SEPARANDO i trace di OGGI (che puoi aver prodotto tu misurando):")
        print("     prima di oggi: %d trace, %d su import" % (len(pre), imp_pre))
        print("     oggi:          %d trace" % (len(file) - len(pre)))
        print("     ⇒ il fenomeno %s indipendentemente da chi legge."
              % ("ESISTE" if imp_pre else "non si vede"))

    imp = per_fam.get("import di libreria pesante", 0)
    print("\n=== VERDETTO ===")
    if imp >= len(file) / 2:
        print("  🔴 %d hang su %d si fermano su un IMPORT di libreria pesante." % (imp, len(file)))
        print("     Non e' un lock ne' la rete: e' il caricamento di una dipendenza")
        print("     scientifica DENTRO la chiamata, invece che all'avvio del processo.")
    else:
        print("  🟡 gli hang non hanno una causa dominante: %d su %d sono import."
              % (imp, len(file)))
    print("  🔑 E il punto che vale piu' del numero: **queste diagnosi il prodotto le ha")
    print("     scritte da solo, e nessuno le ha lette**. La cartella era li' dal 10/08.")


main()
