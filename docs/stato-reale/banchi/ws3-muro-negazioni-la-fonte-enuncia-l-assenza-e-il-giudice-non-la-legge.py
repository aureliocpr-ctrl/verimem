"""Muro delle negazioni (M5): la fonte ENUNCIA l'assenza e il giudice non la legge?

Le coppie sono quelle VERE di stanotte (Aldo ws6 05:05/05:08, Iris ws7 00:40),
prese dal corpus in sola lettura con lo `grounding_span` che il giudice HA LETTO,
id citati accanto a ogni testo. Il layer L4-negazione (anti_confab_gate.py
~2704) promette nell'advice: «passa una fonte che ENUNCI l'assenza ... su quella
forma il giudizio torna affidabile». In 4 dei 5 span qui sotto la fonte enuncia
l'assenza («dice CHI: NESSUN CAMPO», «compare? False», «ha seguito l'env? NO»,
«(vuoto = nessun chiamante lo passa)») e il fatto cade a 0,52 / 0,48 / 2,12 /
31,9. E solo TRE dei cinque originali sono negazioni sintattiche: «apre lo
stesso file della prima» (2,12) e «importa il pacchetto dell albero condiviso»
(0,27) sono positivi nella forma. «Negazione» e «interpretazione» sono quindi
due variabili confuse, e il banco le separa.

GRIGLIA, una variabile per volta. Per ogni caso quattro claim:
  neg_int  negazione con lessico INTERPRETATO (l'originale, dove lo era)
  neg_cit  negazione con il lessico DELLA FONTE
  pos_cit  affermazione che CITA l'output (la cura di Aldo/Iris, ammessa)
  pos_int  affermazione con lessico interpretato
e tre fonti:
  S1  lo span originale (output di script: chiave: valore)
  S2  S1 + UNA riga di PROSA che enuncia la stessa assenza
  S3  S1 senza la riga «contraria» (il controllo positivo che porta un numero
      opposto), dove esiste; altrimenti S3 = S1

PREDIZIONI depositate PRIMA (canale a8189455dcf9ca2d, 06:08):
  P-N1  riproduzione: R ridà i 12 originali a ±2 dal corpus (controllo
        positivo dell'impianto; se cade: NESSUN VERDETTO, exit 1)
  P-N2  polarita' a lessico fisso: neg_cit@S1 < 50 in >= 4/5
  P-N3  la promessa del layer: neg_cit@S2 > 80 in >= 4/5 — se < 50 in >= 3/5
        l'advice di L4-negazione va riscritto
  P-N4  famiglia vs fine-tuning: su neg_cit@S2 i modelli A (base 3 classi) e B
        (deberta-large mnli-fever-anli) danno entailment > 0,5 in >= 4/5 dove R no
Controipotesi misurata da S3: il numero contrario del controllo positivo
(«chi passa grounder=: 1» accanto a «nessuno lo passa») spiega il 31,9.

Eseguire da qui (slot/inferenza-1 preso, finestra <= 15 min):
  ENGRAM_ENCODE_SERVICE=0 python docs/stato-reale/banchi/<questo file>
Scrive solo su stdout. Store di Aurelio: mai aperto.

ESITO 06/09 06:16-06:18 (BANCO_EXIT=0, R 24,9 s di warmup, griglia 3 s, B 85 s):
  P-N1  9/9 riprodotti a ±0,02 (tre positivi ammessi avevano uno span piu'
        lungo del negativo gemello e non stanno nella griglia: 9, non 12).
  P-N2  🔴 FALSIFICATA 1/5: la negazione col lessico della fonte PASSA gia' su
        S1 — 95,5 · 99,5 · 99,9 · 99,9; effetto della polarita' a lessico
        citato: mediana +0,1; effetto del lessico a polarita' negativa: +95,0.
        Non e' la polarita', e' l'INTERPRETAZIONE (le parole del claim che la
        fonte non ha), e vale uguale per i due positivi interpretati (2,1 e 0,3).
  P-N3  regge in modo VACUO su neg_cit (passava gia'); sull'originale
        interpretato la riga di prosa salva 3/5 (31,9->98,8 · 1,0->99,9 ·
        3,7->99,6) e non salva log (0,5->22,4) ne' Iris (0,5->0,7).
  S3    la riga contraria del controllo positivo pesa +25,1 su aldo_fresh
        (31,9->57,0) e +0,3 su Iris: spiega una parte, non il verdetto.
  P-N4  indeciso: su neg_cit@S2 R 4/5, B 4/5, A 3/5 — R legge la prosa quanto
        la famiglia; il muro NON e' nel fine-tuning.
  POST-HOC su Iris (cella non depositata, sezione `iris_quale_parola`): il
        claim porta «mcp_audit.log», che la fonte non nomina. Senza quel
        termine: S1 2,2 · S2 99,8 · S3 2,6 (la prosa salva, lo script no); con
        il termine: 0,4 · 0,3 · 0,6 — e B fa lo stesso (0,00 contro 1,00). Un
        termine fuori fonte costa ~100 punti a un claim NEGATIVO e 0 a uno
        positivo (99,7 con lo stesso termine). La citazione letterale «Il
        registro dice CHI: NESSUN CAMPO» passa a 100 su tutte e tre le fonti.
  Il prodotto (negation_scope.e_un_claim_negativo) NON vede «Nessun chiamante
        passa…», «Nessun file … nomina…», «nessun campo dice CHI», «Il campo
        manca» come negazioni (colonna neg/p): il quarantinato 436851d26dff non
        ha ricevuto l'avviso L4-negazione.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import time

os.environ.setdefault("ENGRAM_ENCODE_SERVICE", "0")
QUI = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(QUI.parents[3]))

SOGLIA_BASSA = 50.0
SOGLIA_ALTA = 80.0

# Per ogni claim: (id nel corpus, punteggio nel corpus, testo). Gli span sono
# copiati per intero dal campo grounding_span; i «\n» sono le righe.
CASI = {
    "iris": {
        "S1": ("  === il registro esiste? True ===\n  righe nel registro: 2\n"
               "  campi: ['args_hash', 'caller_pid', 'error', 'latency_ms', 'outcome', 'tool', 'ts']\n"
               "  dice CHI: NESSUN CAMPO · dice COSA: ['tool']\n"
               "   · {\"tool\": \"hippo_remember\", \"outcome\": \"ok_new\", \"latency_ms\": 20522.0173}\n"
               "  === T6: la chiamata RIFIUTATA compare nel registro? ===\n"
               "    righe che nominano 'recall': 0"),
        "prosa": "Nessun campo del registro dice chi ha fatto la chiamata.",
        "riga_contraria": "  campi: ['args_hash', 'caller_pid', 'error', 'latency_ms', 'outcome', 'tool', 'ts']\n",
        "neg_int": ("1f6aa2aad6b6", 0.52, "Il registro mcp_audit.log non ha un campo che dice CHI."),
        "neg_cit": (None, None, "Nel registro mcp_audit.log nessun campo dice CHI."),
        "pos_cit": ("2d4cfecab3eb", 99.98, "I campi del registro mcp_audit.log sono args_hash, caller_pid, error, latency_ms, outcome, tool, ts."),
        "pos_int": (None, None, "Il registro mcp_audit.log identifica lo strumento chiamato attraverso il campo tool."),
    },
    "aldo_log": {
        "S1": ("[la domanda] assess_fact_freshness compare? False\n"
               "strumenti registrati (163 chiamate, 12 distinti):\n"
               "   hippo_remember 91 · hippo_facts_search 41 · hippo_facts_recall 10"),
        "prosa": "assess_fact_freshness non e' mai stato chiamato: non compare nel log.",
        "riga_contraria": None,
        "neg_int": ("3b2bbd2981e9", 0.48, "Il log delle chiamate non contiene nessuna invocazione di assess_fact_freshness."),
        "neg_cit": (None, None, "assess_fact_freshness non compare fra gli strumenti registrati."),
        "pos_cit": (None, None, "Il controllo «assess_fact_freshness compare?» stampa False."),
        "pos_int": (None, None, "Il log delle chiamate registra 163 invocazioni di 12 strumenti distinti."),
    },
    "aldo_fresh": {
        "S1": ("=== freshness_fn viene mai passato da un chiamante? ===\n"
               "(vuoto = nessun chiamante lo passa)\n"
               "[controllo positivo] chi passa 'grounder=' :\n1"),
        "prosa": "Nessun file di verimem passa freshness_fn a un chiamante.",
        "riga_contraria": "\n[controllo positivo] chi passa 'grounder=' :\n1",
        "neg_int": ("436851d26dff", 31.92, "Nessun file di verimem fuori da epistemic_health.py nomina freshness_fn."),
        "neg_cit": (None, None, "Nessun chiamante passa freshness_fn."),
        "pos_cit": ("8cd59769d028", 99.44, "Il controllo positivo su grounder stampa 1."),
        "pos_int": (None, None, "Il controllo su freshness_fn produce un risultato vuoto."),
    },
    "aldo_memory": {
        "S1": ("Memory() dopo A -> C:\\Users\\aurel\\AppData\\Local\\Temp\\dirA-2jhx3_3r\\semantic\\semantic.db\n"
               "Memory() dopo B -> C:\\Users\\aurel\\AppData\\Local\\Temp\\dirA-2jhx3_3r\\semantic\\semantic.db\n"
               ">>> la seconda Memory ha seguito l'env? NO — resta su A"),
        "prosa": "La seconda Memory non ha seguito la variabile d'ambiente: apre lo stesso file della prima.",
        "riga_contraria": None,
        "neg_int": (None, None, "La seconda Memory non apre il file della seconda cartella."),
        "neg_cit": (None, None, "La seconda Memory non ha seguito l'env e resta su A."),
        "pos_cit": ("ac89be2c16f0", 99.91, "Le due chiamate a Memory stampano tutte e due il percorso dirA-2jhx3_3r semantic semantic.db."),
        "pos_int": ("4b78de4ca903", 2.12, "Dopo aver cambiato le variabili di data dir la seconda Memory apre lo stesso file della prima."),
    },
    "aldo_albero": {
        "S1": ("sys.path[0]: '...\\\\scratchpad'\n"
               "verimem: C:\\Users\\aurel\\Code\\HippoAgent\\verimem\\__init__.py\n"
               "cura A presente? False"),
        "prosa": "Lo script importa verimem dall'albero condiviso in Code HippoAgent, non dal worktree.",
        "riga_contraria": None,
        "neg_int": (None, None, "Uno script eseguito fuori dal worktree non importa il pacchetto del worktree."),
        "neg_cit": (None, None, "La cura A non e' presente."),
        "pos_cit": ("64eafd24e5db", 99.96, "L esecuzione dallo scratchpad stampa verimem C:\\Users\\aurel\\Code\\HippoAgent\\verimem\\__init__.py."),
        "pos_int": ("6fd226dcbb48", 0.27, "Uno script eseguito fuori dal worktree importa il pacchetto dell albero condiviso."),
    },
}
CLAIM = ("neg_int", "neg_cit", "pos_cit", "pos_int")
FONTI = ("S1", "S2", "S3")


def fonti(c: dict) -> dict[str, str]:
    s1 = c["S1"]
    s3 = s1.replace(c["riga_contraria"], "").strip() if c["riga_contraria"] else s1
    return {"S1": s1, "S2": s1 + "\n" + c["prosa"], "S3": s3}


def carica(nome: str):
    spec = importlib.util.spec_from_file_location(nome.replace("-", "_"), QUI.parent / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    import verimem
    from verimem.local_grounding import get_local_judge, try_local_score
    print("IMPORT DA", verimem.__file__, "· ENGRAM_ENCODE_SERVICE =", os.environ.get("ENGRAM_ENCODE_SERVICE"))
    # Warmup ESPLICITO, come `verimem warmup`: senza, `try_local_score` con il
    # daemon di casa vivo DELEGA (anche con ENGRAM_ENCODE_SERVICE=0), riceve
    # vuoto, avvia il warmup asincrono e torna None — misurato qui alle 06:14:
    # «giudice R ASSENTE» in 8 s mentre `_ensure_scorer()` carica in 20,5 s.
    t_w = time.perf_counter()
    get_local_judge()._ensure_scorer()
    print(f"warmup del giudice R in-process: {time.perf_counter() - t_w:.1f} s")
    try:
        from verimem.anti_confab_gate import _e_un_claim_negativo as neg_prodotto
    except ImportError:  # il nome puo' cambiare: il banco non dipende da lui
        def neg_prodotto(t: str) -> bool:
            return " non " in f" {t.lower()} " or t.lower().startswith("nessun")

    # Scala: il corpus scrive 99,98; se il giudice torna 0,9998 si moltiplica.
    c0 = CASI["iris"]
    r0 = try_local_score(c0["S1"], c0["pos_cit"][2])
    if r0 is None:
        print("giudice R ASSENTE: NESSUN VERDETTO")
        return 1
    scala = 100.0 if float(r0[0]) <= 1.0 else 1.0
    print(f"scala del giudice: x{scala:g} (primo valore grezzo {float(r0[0]):.4f})\n")

    def R(fonte: str, claim: str) -> float:
        r = try_local_score(fonte, claim)
        if r is None:
            raise SystemExit("giudice R sparito a meta' banco: nessun verdetto")
        return float(r[0]) * scala

    # ---- P-N1 riproduzione degli originali con lo span S1 del caso ----------
    print("P-N1 riproduzione (id · corpus · R · scarto):")
    scarti = []
    for nome, c in CASI.items():
        for k in CLAIM:
            fid, corpus, testo = c[k]
            if fid is None:
                continue
            p = R(c["S1"], testo)
            scarti.append(abs(p - corpus))
            print(f"   {fid} {nome:12s} {k:8s} corpus {corpus:6.2f}  R {p:6.2f}  scarto {abs(p - corpus):5.2f}")
    riprodotti = sum(1 for s in scarti if s <= 2.0)
    regge1 = riprodotti >= len(scarti) - 2
    print(f"   => {riprodotti}/{len(scarti)} entro ±2  {'REGGE' if regge1 else '🔴 NON RIPRODUCE: NESSUN VERDETTO'}\n")
    if not regge1:
        return 1

    # ---- la griglia con R ----------------------------------------------------
    t0 = time.perf_counter()
    tab: dict[str, dict[str, dict[str, float]]] = {}
    for nome, c in CASI.items():
        tab[nome] = {sk: {k: R(fonte, c[k][2]) for k in CLAIM} for sk, fonte in fonti(c).items()}
    print(f"griglia R (60 coppie): {time.perf_counter() - t0:.0f} s")
    print(f"   {'caso':12s} {'neg/p':8s} " + " ".join(f"{sk}:{k[:7]:>7s}" for sk in FONTI for k in CLAIM))
    for nome, c in CASI.items():
        visto = "/".join("N" if neg_prodotto(c[k][2]) else "p" for k in CLAIM)
        riga = " ".join(f"{tab[nome][sk][k]:10.1f}" for sk in FONTI for k in CLAIM)
        print(f"   {nome:12s} {visto:8s} {riga}")

    def conta(sk: str, k: str, sotto: float | None = None, sopra: float | None = None) -> int:
        v = [tab[n][sk][k] for n in CASI]
        return sum(1 for x in v if (sotto is not None and x < sotto) or (sopra is not None and x > sopra))

    n2 = conta("S1", "neg_cit", sotto=SOGLIA_BASSA)
    print(f"\nP-N2 neg_cit@S1 < 50 in >= 4/5      : {n2}/5   {'REGGE' if n2 >= 4 else '🔴 FALSIFICATA'}")
    n3a = conta("S2", "neg_cit", sopra=SOGLIA_ALTA)
    n3b = conta("S2", "neg_cit", sotto=SOGLIA_BASSA)
    esito3 = "REGGE: la prosa salva" if n3a >= 4 else ("🔴 CADE: la promessa dell'advice non regge" if n3b >= 3 else "indeciso")
    print(f"P-N3 neg_cit@S2 > 80 in >= 4/5      : {n3a}/5 (sotto 50: {n3b}/5)   {esito3}")
    npi = conta("S1", "pos_int", sotto=SOGLIA_BASSA)
    print(f"      pos_int@S1 < 50 (interpretazione senza negazione): {npi}/5")
    s3 = {n: tab[n]["S3"]["neg_int"] - tab[n]["S1"]["neg_int"] for n in CASI if CASI[n]["riga_contraria"]}
    print(f"      S3 − S1 su neg_int dove c'e' una riga contraria: {', '.join(f'{n} {d:+.1f}' for n, d in s3.items())}")
    effetto_pol = sorted(tab[n]["S1"]["pos_cit"] - tab[n]["S1"]["neg_cit"] for n in CASI)
    effetto_les = sorted(tab[n]["S1"]["neg_cit"] - tab[n]["S1"]["neg_int"] for n in CASI)
    print(f"      effetto POLARITA' a lessico citato (pos_cit − neg_cit @S1): mediana {effetto_pol[2]:+.1f}")
    print(f"      effetto LESSICO a polarita' negativa (neg_cit − neg_int @S1): mediana {effetto_les[2]:+.1f}")

    # ---- P-N4: A e B sui bracci decisivi -------------------------------------
    p3 = carica("ws3-P3-la-popolazione-implicita-contro-quattro-scorer")
    modelli = {e: n for e, n in p3.MODELLI.items() if e.startswith(("A", "B"))}
    print(f"\nP-N4 famiglia vs fine-tuning — modelli: {list(modelli)}")
    # punteggi_hf legge triple (fonte, x, v) e torna (lista su v, lista su x)
    dati = [(fonti(CASI[n])["S2"], CASI[n]["neg_int"][2], CASI[n]["neg_cit"][2]) for n in CASI]
    esiti4 = {}
    for etichetta, hf in modelli.items():
        t1 = time.perf_counter()
        try:
            cit, integ = p3.punteggi_hf(hf, dati)
        except Exception as e:  # noqa: BLE001 — un modello che non carica si dichiara, non si tace
            print(f"   {etichetta}: NON CARICATO ({type(e).__name__}: {str(e)[:80]})")
            continue
        esiti4[etichetta] = (cit, integ)
        print(f"   {etichetta:28s} neg_cit@S2 entail>0,5: {sum(1 for x in cit if x > 0.5)}/5 "
              f"[{', '.join(f'{x:.2f}' for x in cit)}]  neg_int@S2: {sum(1 for x in integ if x > 0.5)}/5 "
              f"[{', '.join(f'{x:.2f}' for x in integ)}]  ({time.perf_counter() - t1:.0f} s)")
    r_s2 = [tab[n]["S2"]["neg_cit"] for n in CASI]
    print(f"   {'R nostro giudice':28s} neg_cit@S2 > 50: {sum(1 for x in r_s2 if x > 50)}/5 [{', '.join(f'{x:.1f}' for x in r_s2)}]")
    if esiti4:
        reggono = [e for e, (cit, _) in esiti4.items() if sum(1 for x in cit if x > 0.5) >= 4]
        r_no = sum(1 for x in r_s2 if x > 50) <= 1
        if reggono and r_no:
            print(f"   => P-N4 REGGE: {reggono} leggono l'assenza in prosa, R no => il muro e' nel NOSTRO fine-tuning")
        elif not reggono:
            print("   => P-N4 CADE: anche A/B cadono => e' la famiglia; la cura e' la formulazione (Aldo)")
        else:
            print("   => P-N4 indeciso: R legge la prosa quanto A/B")

    iris_quale_parola(R, p3, modelli)
    return 0


VARIANTI_IRIS = {
    "orig neg_cit (mcp_audit.log, CHI)": "Nel registro mcp_audit.log nessun campo dice CHI.",
    "a senza mcp_audit.log": "Nel registro nessun campo dice CHI.",
    "b minuscolo": "Nel registro nessun campo dice chi.",
    "c prosa piena": "Il registro non ha un campo che dice chi ha chiamato.",
    "d citazione letterale": "Il registro dice CHI: NESSUN CAMPO.",
    "e positivo con mcp_audit.log": "Il registro mcp_audit.log ha 2 righe.",
    "f positivo senza": "Il registro ha 2 righe.",
}


def iris_quale_parola(R, p3, modelli: dict[str, str]) -> None:
    """POST-HOC, non depositata: Iris cadeva su tutte e tre le fonti (0,3-0,6) e
    anche su A e B (0,00). Una variabile per volta: il termine «mcp_audit.log»
    (assente dalla fonte), il maiuscolo «CHI», la prosa, la citazione letterale,
    e gli stessi termini su un claim POSITIVO."""
    c = CASI["iris"]
    F = fonti(c)
    print("\nPOST-HOC Iris — quale parola fa cadere il claim (R):")
    print(f"   {'variante':36s} {'S1':>7s} {'S2':>7s} {'S3':>7s}")
    for k, t in VARIANTI_IRIS.items():
        print(f"   {k:36s} " + " ".join(f"{R(F[s], t):7.1f}" for s in FONTI))
    v = VARIANTI_IRIS
    dati = [(F["S2"], v["orig neg_cit (mcp_audit.log, CHI)"], v["a senza mcp_audit.log"]),
            (F["S2"], v["b minuscolo"], v["c prosa piena"]),
            (F["S2"], v["d citazione letterale"], v["f positivo senza"])]
    for etichetta, hf in modelli.items():
        try:
            vv, xx = p3.punteggi_hf(hf, dati)
        except Exception as e:  # noqa: BLE001
            print(f"   {etichetta}: NON CARICATO ({type(e).__name__})")
            continue
        print(f"   {etichetta:28s} @S2  orig {xx[0]:.2f} · a {vv[0]:.2f} · b {xx[1]:.2f} · c {vv[1]:.2f} · d {xx[2]:.2f} · f {vv[2]:.2f}")


if __name__ == "__main__":
    sys.exit(main())
