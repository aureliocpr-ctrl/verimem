"""La gamba windows di `ci` non fallisce: SCADE. Un timeout unico per sei gambe
che durano da 17 a 45 minuti da' il margine a chi non ne ha bisogno e lo nega a
chi lo esaurisce.

=== MISURATO il 2026-08-13 su sei run consecutivi di origin/main ===
Durata del job `test (windows-latest / py3.12)` e suo esito::

    31633951408  cancelled  45,3 min   passo Tests
    31633374985  failure    39,9 min   passo Tests
    31632886567  cancelled  45,1 min   passo Tests
    31631810969  cancelled  45,3 min   passo Tests
    31630796638  failure    41,7 min   passo Tests
    31629151172  cancelled  45,3 min   passo Tests

**Quattro su sei muoiono a 45,1-45,3 minuti** con ``timeout-minutes: 45``: e' il
tetto che li uccide, non un test. Gli altri due concludono a 39,9 e 41,7 — dentro
il tetto per un pelo. Nello stesso run le altre cinque gambe stanno a **17,5-17,9
minuti** (ubuntu x4, macos), cioe' meno di **due quinti** del tempo di windows.

⚠️ **QUANTO CI METTA DAVVERO WINDOWS NON E' MISURABILE FINCHE' IL TETTO LA
TRONCA**: dei sei campioni, quattro sono censurati a 45. Il vero massimo e' >=
45,3 e ignoto; 39,9 e 41,7 sono gli unici due tempi *veri* che abbiamo. Il primo
run con il tetto alzato sara' la prima misura non censurata — e se anche 60 non
bastasse, questo file va riletto, non allargato per riflesso.

=== IL COMMENTO CHE PROMETTEVA IL MARGINE ===
Sopra ``timeout-minutes`` il file dichiara: «the windows-latest runners take
~20-24 min ... 45 min gives comfortable headroom» (2026-06-08). Sui sei run qui
sopra quel margine **non esiste piu'**: 40-45 minuti, non 20-24. Chi legge il
file conclude che 45 basti e avanzi, e il numero misurato dice il contrario —
per questo la cura tocca il commento insieme alla riga.

=== LA CURA E IL SUO PREZZO ===
Tetto **per sistema operativo**: 60 a windows (margine ~1,4x sul massimo vero
noto), 30 alle altre — dove 45 era largo il triplo del tempo osservato e non
avrebbe mai scoperto un rallentamento.

⚠️ **PREZZO**: nel caso peggiore un run di `ci` puo' arrivare a ~60 minuti invece
di ~45, e il verdetto arriva piu' tardi. Si paga solo sul caso patologico: le
cinque gambe veloci finiscono a 17,5 e ora hanno un tetto **piu' stretto** di
prima, quindi un rallentamento vero su ubuntu si scopre in 30 minuti anziche' 45.
"""
from __future__ import annotations

from pathlib import Path

import pytest

CI = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


@pytest.fixture
def job_test() -> dict:
    """Il job `test` **parsato**, non il testo.

    ⚠️ Leggere le righe qui sarebbe lo stesso difetto gia' misurato il 12/08 su
    `concurrency`: il banco trovava la chiave dentro il COMMENTO che la spiega e
    diventava rosso su un file corretto. Lo YAML parsato e' anche il livello a
    cui Actions legge il file, quindi il banco misura dove misura il prodotto.
    """
    import yaml
    return yaml.safe_load(CI.read_text(encoding="utf-8"))["jobs"]["test"]


class TestIlTettoDistingueLeGambe:

    def test_il_tetto_esiste(self, job_test):
        """CONTROLLO POSITIVO: se qualcuno togliesse `timeout-minutes`, i test
        sotto fallirebbero con un KeyError invece di passare a vuoto."""
        assert "timeout-minutes" in job_test

    def test_il_tetto_dipende_dal_SISTEMA_OPERATIVO(self, job_test):
        """IL ROSSO: con un numero fisso, windows (40-45 min) e ubuntu (17,5)
        condividono lo stesso tetto. Quattro run su sei muoiono per questo."""
        tetto = str(job_test["timeout-minutes"])
        assert "matrix.os" in tetto, (
            "il tetto e' unico per sei gambe che durano da 17,5 a >=45,3 minuti: "
            f"windows scade e le altre non sono sorvegliate — timeout-minutes = {tetto}"
        )

    def test_a_windows_va_il_margine_piu_largo(self, job_test):
        """L'altra meta': distinguere non basta, il margine deve andare a CHI
        LO ESAURISCE. Un tetto per-OS che desse 30 a windows sarebbe peggio del
        45 fisso."""
        tetto = str(job_test["timeout-minutes"])
        assert "windows" in tetto, (
            f"il tetto distingue qualcosa, ma non windows: {tetto}"
        )
        numeri = [int(n) for n in __import__("re").findall(r"\b(\d{2,3})\b", tetto)]
        assert numeri, f"nessun numero leggibile nel tetto: {tetto}"
        assert max(numeri) >= 60, (
            "il margine piu' largo deve coprire il massimo VERO noto (>=45,3 min, "
            f"censurato dal tetto vecchio): numeri letti = {numeri}"
        )

    def test_anche_la_gamba_veloce_ha_margine_sulla_VARIABILITA(self, job_test):
        """L'errore che c'era nella PRIMA versione di questo tetto: tararlo sul
        tempo OSSERVATO, letto per giunta su un run solo.

        Passo `Tests` di ubuntu/py3.11, tre run consecutivi del 2026-08-13:
        **706 s · 1196 s · 1331 s** — quasi il doppio — con esito IDENTICO in
        ogni cifra (20 failed, 92 skipped, 8 ``not_run:no_judge``) e setup
        costante (~2 min in tutti e tre). Lo stesso lavoro puo' costare
        **1,88x** per una ragione che non e' nostra e non e' nota.

        ⇒ Un tetto che lasciava 4,9 minuti al peggiore osservato (25,1) non
        sorveglia: aspetta il primo run sfortunato. Il margine deve coprire la
        VARIABILITA', non il campione.
        """
        tetto = str(job_test["timeout-minutes"])
        numeri = [int(n) for n in __import__("re").findall(r"\b(\d{2,3})\b", tetto)]
        assert numeri, f"nessun numero leggibile nel tetto: {tetto}"
        assert min(numeri) >= 35, (
            "il tetto piu' stretto non copre la variabilita' misurata (1,88x a "
            f"parita' di esito): numeri letti = {numeri}"
        )

    def test_il_lavoro_lento_del_gate_non_e_stato_aggiunto_di_nascosto(self):
        """GUARDIANO PER LA CURA DI UN'ALTRA: togliere `--no-gate` dal warmup
        accende 16+6 test del giudice ma scarica **711,5 MB** in
        ``~/.engram/models`` — che la cache di questo workflow NON copre (il
        passo di cache elenca solo ``~/.cache/huggingface`` e
        ``~/.cache/torch/sentence_transformers``). Su windows, che gia' finisce
        il tempo, quel download e il caricamento del cross-encoder arrivano
        DOPO questo tetto: le due modifiche vanno fatte insieme o non vanno
        fatte. Questo test non vieta la cura — pretende che chi la fa metta
        anche il modello in cache.
        """
        import yaml
        testo = CI.read_text(encoding="utf-8")
        wf = yaml.safe_load(testo)
        passi = wf["jobs"]["test"]["steps"]
        warmup = [p for p in passi if "warmup" in str(p.get("run", ""))]
        assert warmup, "il passo di warmup e' sparito: rileggere questo banco"
        senza_gate = any("--no-gate" in str(p.get("run", "")) for p in warmup)
        if senza_gate:
            return  # il gate non si scarica: niente da mettere in cache
        cache = [p for p in passi if "actions/cache" in str(p.get("uses", ""))]
        percorsi = " ".join(str(p.get("with", {}).get("path", "")) for p in cache)
        assert ".engram/models" in percorsi, (
            "il warmup ora scarica il modello del giudice (711,5 MB) ma nessuna "
            "cache lo trattiene: sono ~4,3 GB per run su sei gambe, ogni run"
        )

    def test_la_cache_si_salva_ANCHE_quando_il_job_e_rosso(self):
        """⚠️ IL TEST SOPRA NON BASTAVA, ed e' la lezione che questo aggiunge:
        pretendeva che il modello fosse *elencato* in una cache, e quella riga
        c'era. Ma una cache dichiarata e mai SALVATA non e' una cache — e la
        differenza non si vede leggendo il workflow, si vede nel log.

        MISURATO nel job ubuntu-py3.12 del run 31816624316::

            Cache not found for input keys: hf-Linux-<hash>, hf-Linux-
            (nessun passo «Post Cache HuggingFace» nel log: solo Post job cleanup)

        cioe' in oltre 24 ore la chiave non e' MAI stata scritta, nemmeno sul
        ripiego generico. Il circolo che ne segue si chiude da solo: job rosso
        -> cache mai salvata -> il modello si riscarica -> huggingface.co non
        risponde (14 volte in quel job) -> 7 errors -> job rosso.

        🔑 Percio' il criterio non e' «esiste un passo di cache» ma «esiste un
        passo che salva SU UN JOB FALLITO»: e' l'unico caso che qui si presenta.
        Un presidio che copre solo il caso riuscito e' spento proprio dove
        serve — come il guardiano che eredita lo skip di cio' che sorveglia.
        """
        import yaml
        wf = yaml.safe_load(CI.read_text(encoding="utf-8"))
        passi = wf["jobs"]["test"]["steps"]
        save = [p for p in passi
                if "actions/cache/save" in str(p.get("uses", ""))]
        assert save, (
            "nessun passo SALVA la cache: con `actions/cache` in un solo passo "
            "il salvataggio non ha lasciato traccia in 24 ore di job rossi"
        )
        # ⚠️ `True` non basta: YAML rende `if: always() && …` una stringa, ma
        # un `if: success()` sarebbe altrettanto presente e altrettanto inerte.
        condizione = str(save[0].get("if", ""))
        assert "always()" in condizione, (
            f"il passo di salvataggio esiste ma la sua condizione e' "
            f"{condizione!r}: su un job rosso non scatta, ed e' l'unico "
            f"genere di job che questa CI produce da 24 ore"
        )

    def test_una_cache_INCOMPLETA_non_viene_salvata(self):
        """⚠️ IL SEGUITO DEL TEST QUI SOPRA, e nasce da un difetto di quella
        stessa cura — la mia, del 14/08.

        `always()` fa salvare la cache anche da un job rosso, che era il punto.
        Ma il primo job a scriverla e' morto di SIGSEGV (exit 139) dopo 2698
        test su 11349, e ha salvato quello che c'era in quel momento. Misurato
        sul run successivo (31823644806): la cache viene ripristinata, pesa
        1656 MB, e `intfloat/multilingual-e5-base` non ci si trova — otto test
        cadono al setup con «couldn't connect to huggingface.co».

        🔑 E non si ripara da solo: con la chiave primaria scritta, `cache-hit`
        e' vero e il salvataggio non riparte MAI. **Una cache incompleta e'
        peggio di una assente**: l'assente si riempie al primo run, l'incompleta
        resta finche' non cambia l'hash della chiave.
        ⇒ Salvare SEMPRE non basta: si salva solo cio' che serve a qualcosa.
        """
        import yaml
        wf = yaml.safe_load(CI.read_text(encoding="utf-8"))
        passi = wf["jobs"]["test"]["steps"]
        save = [p for p in passi
                if "actions/cache/save" in str(p.get("uses", ""))]
        assert save, "nessun passo salva la cache: vedi il test qui sopra"
        cond = str(save[0].get("if", ""))
        assert "completa" in cond, (
            f"il salvataggio non guarda se la cache CONTIENE il modello: "
            f"{cond!r}. Un job morto a meta' scriverebbe una cache monca, e "
            f"nessun run successivo potrebbe piu' ripararla."
        )

    def test_la_guardia_della_cache_CONTA_invece_di_prendere_il_primo(self):
        """⚠️ Il difetto che questa riga presidia mi e' costato la cura intera.

        La prima versione della guardia faceva ``find -type d -name
        'models--intfloat--…' | head -1`` e poi cercava i pesi dentro. Ma le
        cartelle con quel nome sono DUE — ``hub/.locks/models--intfloat--…``
        (i lock di huggingface_hub) e ``hub/models--intfloat--…`` (i pesi) — e
        la visita incontra ``.locks`` per prima. Riprodotto in A/B su una
        struttura finta::

            dir trovata:  …/hub/.locks/models--intfloat--multilingual-e5-base
            pesi:         ''
            -> completa=FALSE      ← sempre, anche con la cache perfetta

        ⇒ il salvataggio non sarebbe mai avvenuto e ogni run avrebbe fatto
        miss. **Un sensore che risponde sempre la stessa cosa non e' severo,
        e' scollegato** — e questo lo era nella direzione che blocca tutto.

        🔑 Terza volta in due giorni che «prendo la prima corrispondenza» mi
        da' quella sbagliata: il body col trailer in fondo letto con ``head
        -4``, il ``grep`` con due copie del package, e questa. ⇒ **dove le
        corrispondenze possono essere piu' d'una, si CONTA**: un conteggio non
        dipende dall'ordine di visita, e ``head`` invece si', in silenzio.
        """
        import yaml
        wf = yaml.safe_load(CI.read_text(encoding="utf-8"))
        passi = wf["jobs"]["test"]["steps"]
        guardia = [p for p in passi
                   if str(p.get("id", "")) == "hf_completa"]
        assert guardia, (
            "il passo che verifica la completezza della cache non c'e' piu': "
            "senza, un job morto a meta' torna a scrivere una cache monca")
        comando = str(guardia[0].get("run", ""))
        assert "head -1" not in comando, (
            "la guardia prende «il primo» risultato di una ricerca che ne ha "
            "piu' d'uno: hub/.locks/ viene visitata prima di hub/, quindi i "
            "pesi non si trovano mai e la cache non si salva mai. Conta i "
            "file (`wc -l`) invece di sceglierne uno.")
        assert "wc -l" in comando, (
            "la guardia non conta: senza un conteggio il verdetto dipende "
            "dall'ordine di visita del filesystem, che nessuno controlla")

    def test_ogni_cartella_MODELLO_del_prodotto_e_coperta_dalla_cache(self):
        """🔑 LA CLASSE CHE CI MORDE DA GIORNI, chiusa dal lato che si può
        chiudere: **due liste che devono restare d'accordo e vivono in file
        diversi.**

        `local_grounding.py` dichiara dove il modello del gate viene scritto;
        `ci.yml` dichiara quali cartelle mettere in cache. Nessuno dei due sa
        dell'altro. Il 15/08 ws1 ha spostato il modello in
        ``~/.cache/verimem/models`` (`42f03411`) — cura giusta, il modello sotto
        una cartella-dati decideva dove vive la memoria dell'utente — e ws3 ha
        visto per primo che, atterrando, quel percorso sarebbe uscito da questa
        lista: la cache avrebbe salvato una cartella vuota.

        ⚖️ Nessuno dei due aveva torto e nessuno poteva vederlo dal proprio
        file. Il presidio è l'unico posto da cui **si vedono entrambi**.
        """
        import re

        import yaml
        wf = yaml.safe_load(CI.read_text(encoding="utf-8"))
        in_cache = []
        for p in wf["jobs"]["test"]["steps"]:
            if "actions/cache" in str(p.get("uses", "")):
                in_cache += [r.strip() for r in
                             str(p.get("with", {}).get("path", "")).splitlines()
                             if r.strip()]
        assert in_cache, "il workflow non mette in cache nessuna cartella"

        sorgente = (CI.parents[2] / "verimem" / "local_grounding.py")
        testo = sorgente.read_text(encoding="utf-8", errors="ignore")
        # `Path.home() / "a" / "b" / …`  ->  `~/a/b/…`
        voluti = set()
        for m in re.finditer(r'Path\.home\(\)((?:\s*/\s*"[^"]+")+)', testo):
            pezzi = re.findall(r'"([^"]+)"', m.group(1))
            voluti.add("~/" + "/".join(pezzi))
        assert voluti, (
            "nessuna cartella-modello trovata in local_grounding.py: se le "
            "costanti sono state riscritte, questo test va riletto — non "
            "cancellato, o le due liste tornano a divergere in silenzio")

        scoperti = [v for v in sorted(voluti)
                    if not any(v.startswith(c) for c in in_cache)]
        assert not scoperti, (
            f"il prodotto scrive i modelli in {scoperti} e il workflow non "
            f"mette quelle cartelle in cache ({in_cache}): la CI le "
            f"riscaricherebbe a ogni run, e la guardia di completezza "
            f"guarderebbe nel posto sbagliato")

    def test_il_salvataggio_della_cache_viene_PRIMA_dei_test(self):
        """⚠️ Il terzo modo in cui questa cura non funzionava, e il piu' banale.

        Guardia e salvataggio stavano **in fondo al job**, dopo i test, lo
        smoke install e il caricamento della copertura. Li' non girano affatto
        quando il job MUORE — e il job che ha avvelenato la cache era morto di
        SIGSEGV **durante i test**, cioe' esattamente nel tratto che li
        precedeva. Visto leggendo gli step di un job in corso::

            Cache HuggingFace models                completed / success
            Warm embedding model                    completed / success
            La cache contiene davvero il modello?   pending      ← dopo i test
            Save HuggingFace models cache           pending

        🔑 **Un presidio piazzato dopo il punto in cui le cose si rompono non e'
        un presidio.** Il modello lo produce il WARMUP: e' li' che va misurato e
        salvato, prima che qualunque test possa impedirlo.
        ⚖️ Prezzo dichiarato: non si cattura piu' cio' che scaricano i test. E'
        voluto — i test non devono scaricare nulla, e' tutto il punto della
        cache; se scaricassero sarebbe un difetto da vedere, non da nascondere
        dentro una cache piu' grassa.
        """
        import yaml
        wf = yaml.safe_load(CI.read_text(encoding="utf-8"))
        nomi = [str(p.get("name") or p.get("uses", ""))
                for p in wf["jobs"]["test"]["steps"]]
        i_save = next(i for i, n in enumerate(nomi) if "Save HuggingFace" in n)
        i_test = next(i for i, n in enumerate(nomi) if n.strip() == "Tests")
        assert i_save < i_test, (
            f"il salvataggio della cache (passo {i_save}) viene DOPO i test "
            f"(passo {i_test}): un job che muore durante i test non lo esegue, "
            f"ed e' proprio cosi' che la cache e' rimasta vuota per un giorno")

    def test_la_guardia_della_cache_non_MUORE_se_la_cartella_non_esiste(self):
        """⚠️⚠️ IL SECONDO DIFETTO DELLA STESSA GUARDIA, che il primo nascondeva.

        Actions lancia `shell: bash` come
        ``/usr/bin/bash --noprofile --norc -e -o pipefail {0}`` — letto nel log
        del job, non dedotto. Un `find` su una cartella che non esiste esce
        non-zero; ``2>/dev/null`` ne nasconde il messaggio ma **non il codice**;
        `pipefail` lo propaga attraverso la pipe e `-e` uccide lo step::

            run 1c2491ed, ubuntu py3.11 (segnalato da ws8):
              «La cache contiene davvero il modello?»  ->  completed/FAILURE
              «Save HuggingFace models cache»          ->  completed/skipped
              output della guardia:  NESSUNO — morta prima di stampare

        E in quel job «Warm embedding model» era SKIPPED, quindi
        ``~/.cache/huggingface`` non esisteva affatto: **il caso peggiore e'
        anche il piu' comune** — il primo run su una cache vuota, cioe' proprio
        quello che la cura deve far funzionare.

        🔑 Una guardia che MUORE non e' una guardia che dice «no»: l'uscita
        resta vuota, la condizione `!= 'true'` e' comunque vera, il salvataggio
        non parte. **Stesso sintomo del difetto precedente, causa diversa** — e
        curata la prima, la seconda sarebbe rimasta indistinguibile dal
        fallimento della cura.
        """
        import yaml
        wf = yaml.safe_load(CI.read_text(encoding="utf-8"))
        guardia = [p for p in wf["jobs"]["test"]["steps"]
                   if str(p.get("id", "")) == "hf_completa"]
        assert guardia, "il passo di verifica non c'e' piu'"
        comando = str(guardia[0].get("run", ""))
        assert "mkdir -p" in comando, (
            "la guardia cerca dentro una cartella che potrebbe non esistere e "
            "lo shell di Actions gira con `-e -o pipefail`: il `find` esce "
            "non-zero e lo STEP MUORE prima di decidere. Creala prima di "
            "cercarci dentro.")
        assert "|| true" in comando, (
            "manca la cintura: anche con la cartella creata, un `find` puo' "
            "uscire non-zero (permessi, race) e con `pipefail` + `-e` questo "
            "uccide lo step invece di produrre un verdetto")

    def test_la_chiave_della_cache_distingue_le_GAMBE_della_matrice(self):
        """⚠️ Misurato da ws3 il 2026-08-15 sul run `16c68894`, e la mia cura
        reggeva **per fortuna, non per costruzione**.

        Con una chiave che nomina solo il sistema operativo, le gambe della
        matrice corrono per la stessa voce di cache e si bloccano a vicenda::

            windows py3.12:  Cache not found for input keys: hf-Windows-1a59512b…
                             Failed to save: Unable to reserve cache with key
                             hf-Windows-1a59512b…, another job may be creating
                             this cache

        ⇒ su windows la cache **non si popolava mai**, cioe' li' il circolo
        restava chiuso; su linux funzionava solo perche' una delle tre gambe
        vinceva la corsa e le altre facevano hit sul suo risultato.
        🔑 Il difetto non e' «windows e' diverso»: e' che **la chiave non
        nominava una dimensione lungo cui i job sono davvero paralleli**. Un
        identificatore che non distingue cio' che corre insieme non e' un
        identificatore, e' una collisione in attesa.
        """
        import yaml
        wf = yaml.safe_load(CI.read_text(encoding="utf-8"))
        passi = wf["jobs"]["test"]["steps"]
        cache = [p for p in passi if "actions/cache" in str(p.get("uses", ""))]
        assert cache, "nessun passo di cache: vedi i test qui sopra"
        for p in cache:
            k = str(p.get("with", {}).get("key", ""))
            assert "matrix.python-version" in k, (
                f"la chiave {k!r} non nomina la gamba: le gambe dello stesso "
                f"sistema operativo correranno per la stessa voce e si "
                f"bloccheranno a vicenda («another job may be creating this "
                f"cache»), lasciando quella piattaforma senza cache")

    def test_il_RIPIEGO_non_ripesca_la_chiave_abbandonata(self):
        """🔑 IL GUARDIANO CHE MI HA QUASI PRESO MENTRE SCRIVEVO LA CURA.

        Per buttare una cache gia' scritta l'unico modo, senza toccare le
        impostazioni del repository, e' cambiare la chiave. Ma `restore-keys`
        e' un PREFISSO: cambiare `key` e lasciare il ripiego sul prefisso
        vecchio ripesca esattamente la cache che si voleva abbandonare, e
        l'operazione sembra riuscita perche' la cache «c'e'».
        ⚖️ E' la forma generale di un difetto che vediamo spesso: **la porta
        di servizio di una cosa che credi di aver buttato.**
        """
        import yaml
        wf = yaml.safe_load(CI.read_text(encoding="utf-8"))
        passi = wf["jobs"]["test"]["steps"]
        restore = [p for p in passi
                   if "actions/cache/restore" in str(p.get("uses", ""))]
        save = [p for p in passi
                if "actions/cache/save" in str(p.get("uses", ""))]
        assert restore and save, "restore e save separati sono il presupposto"
        k_r = str(restore[0]["with"]["key"])
        k_s = str(save[0]["with"]["key"])
        ripiego = str(restore[0]["with"].get("restore-keys", ""))
        assert k_r == k_s, (
            f"restore e save usano chiavi diverse:\n  restore {k_r}\n  save    "
            f"{k_s}\nla cache verrebbe scritta dove nessuno la cerca")
        prefisso = k_r.split("-")[0]
        assert ripiego.startswith(prefisso), (
            f"il ripiego {ripiego!r} non parte dal prefisso della chiave "
            f"({prefisso!r}): ripescherebbe una cache di una generazione "
            f"precedente, cioe' proprio quella che il cambio di chiave "
            f"serviva ad abbandonare")
