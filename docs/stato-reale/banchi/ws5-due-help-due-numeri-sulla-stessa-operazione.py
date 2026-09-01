r"""`recall` si presenta come «the 2-second read» e la telemetria ne misura 61.

Nasce leggendo `verimem telemetry`, che nessuno di noi cita e che dice «*makes visible
what nobody finds until someone complains*».

I DUE NUMERI, entrambi del prodotto, sulla STESSA operazione::

    `verimem recall --help`      «Recall the top-k facts for a query — the
                                  2-second read quickstart»
    `verimem telemetry`          hippo_facts_recall · p50 PRIMA CHIAMATA 61585 ms

⚠️ **E l'help di `telemetry` dichiara gia' come si leggono le sue colonne**, il che
impedisce la lettura pigra: «*the latency columns are FIRST-CALL vs LATER […] since
mid-July **nearly every process makes one call and dies** (the client times out and
respawns), and those processes are not a random sample — **the slow ones got
killed***». ⇒ Il numero **non** e' «quanto costa una chiamata»: e' quanto costa **la
prima**, e il campione e' distorto **verso i veloci**.

🔑 LA DOMANDA CHE RESTA, e che nessuno dei due help risponde: **quanti utenti pagano la
prima chiamata invece della seconda?** Se quasi tutti i processi ne fanno una sola,
allora **la latenza che l'utente sperimenta E' quella del primo uso**, e il «2-second
read» descrive un regime che quasi nessuno incontra.

⇒ Il banco legge `telemetry --json` e mette in colonna, per i tool piu' usati, **la
quota di processi che hanno fatto UNA SOLA chiamata**. E' il dato che trasforma «la
prima chiamata e' lenta» in «la maggioranza paga la prima».

🔴 ESITO — **la maggioranza dei processi paga la PRIMA chiamata**::

    tool                        calls   1a chiam.       dopo   processi (1 sola)
    hippo_remember               1380      831 ms     204 ms    230 (97)    42%
    hippo_facts_search            894      103 ms      90 ms    222 (79)    36%
    hippo_facts_recall            423   61585 ms      392 ms   311 (262)    84%
    hippo_record_episode          405      357 ms     149 ms     85 (30)    35%
    hippo_recall                  165      184 ms      68 ms     92 (44)    48%
    hippo_health                  134      210 ms      10 ms     97 (60)    62%
    hippo_trust_report             60     4090 ms    2404 ms     24 (9)     38%
    hippo_status                   56     2092 ms       1 ms     47 (24)    51%
    ---------------------------------------------------------------------------
    sui 12 piu' usati            1211 processi · 645 con UNA SOLA chiamata · 53%

🔴 **① `hippo_facts_recall`: 61.585 ms alla prima chiamata contro 392 dopo**, e **262
processi su 311 (84%) ne fanno una sola**. ⇒ **Chi chiama il recall una volta sperimenta
il primo numero**, e il «*2-second read quickstart*» dell'altro help descrive un regime
che su quel tool incontra **il 16%**.

⚠️ **② E il 53% complessivo va letto con l'avvertenza che il prodotto stesso da'**:
«*nearly every process makes one call and dies (**the client times out and respawns**),
and those processes are not a random sample — **the slow ones got killed***». ⇒ **La
quota di processi «con una sola chiamata» puo' essere l'effetto del timeout, non
dell'uso.** Se cosi' fosse, il reperto sarebbe **piu' grave**, non meno: vorrebbe dire
che su quel tool il client va in timeout **sistematicamente**. **Non l'ho misurato, e
quindi non lo affermo.**

⇒ **PER IL RILASCIO, il fatto solido e' uno**: due comandi dello stesso prodotto danno
due numeri **incompatibili** sulla stessa operazione, e **nessuno dei due dice a quale
chiamata si riferisce**. ⇒ `recall --help` dovrebbe dire **quale** delle due — e' una
riga, non una patch.

📌 E chiude col mio reperto del 26/08 («*mediana recall 33s contro il «2-second read»
dell'help*»): allora era una mia misura, **ora e' il prodotto a misurarlo**, e il numero
e' quasi il doppio.

SOLA LETTURA: `verimem telemetry --json`, che legge l'audit log e non scrive.
⚖️ PUNTI DEBOLI: la telemetria e' **di questa macchina** e la popolano **le nostre**
sessioni, non utenti veri; il campione e' distorto come l'help dichiara; e il «2-second»
dell'altro help potrebbe riferirsi alla **seconda** chiamata — nel qual caso il difetto
non e' il numero ma il fatto che **non dice quale delle due**.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-due-help-due-numeri-sulla-stessa-operazione.py
"""
import json
import subprocess


def main():
    out = subprocess.run(["verimem", "telemetry", "--json", "--top", "12"],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace").stdout
    inizio = out.find("{")
    if inizio < 0:
        inizio = out.find("[")
    if inizio < 0:
        print("  🔴 nessun JSON nell'output di `verimem telemetry --json`")
        print("     primi 300 caratteri: %s" % " ".join(out.split())[:300])
        return
    dati = json.loads(out[inizio:])
    per_tool = dati.get("per_tool")
    if not isinstance(per_tool, dict):
        print("  🔴 forma inattesa: chiavi %s" % list(dati)[:8])
        return
    righe = sorted(per_tool.items(), key=lambda kv: -kv[1].get("count", 0))

    print("  %-26s %6s %11s %10s %13s %s"
          % ("tool", "calls", "1a chiam.", "dopo", "processi", "una sola"))
    print("  " + "-" * 88)
    tot_pid = tot_uno = 0
    for nome, r in righe[:12]:
        prima = r.get("latency_p50_first_call_ms")
        dopo = r.get("latency_p50_later_calls_ms")
        pids = r.get("n_unique_pids", 0) or 0
        uno = r.get("n_single_call_pids", 0) or 0
        tot_pid += pids
        tot_uno += uno
        q = (100.0 * uno / pids) if pids else 0.0
        print("  %-26s %6s %11s %10s %13s %5.0f%%"
              % (nome[:26], r.get("count", 0),
                 ("%.0f ms" % prima) if prima is not None else "-",
                 ("%.0f ms" % dopo) if dopo is not None else "-",
                 "%d (%d)" % (pids, uno), q))

    print("\n=== LETTURA ===")
    if tot_pid:
        q = 100.0 * tot_uno / tot_pid
        print("  Sui dodici tool piu' usati: %d processi, %d con UNA SOLA chiamata (%.0f%%)."
              % (tot_pid, tot_uno, q))
        if q >= 50:
            print("  🔴 LA MAGGIORANZA DEI PROCESSI PAGA LA PRIMA CHIAMATA e muore.")
            print("     ⇒ La latenza che l'utente sperimenta e' quella della PRIMA, non")
            print("       della seconda — e il «2-second read» descrive il regime che")
            print("       la minoranza incontra.")
        else:
            print("  🟢 la maggioranza dei processi fa piu' di una chiamata: il costo del")
            print("     primo uso si ammortizza, e il «2-second read» e' rappresentativo.")
    else:
        print("  ⚠️ la telemetria non espone i processi: la quota non e' calcolabile")
        print("     da questo output, e il reperto resta non misurato.")


main()
