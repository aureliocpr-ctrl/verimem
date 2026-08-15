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
