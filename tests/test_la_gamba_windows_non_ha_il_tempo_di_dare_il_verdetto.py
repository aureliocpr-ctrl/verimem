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
