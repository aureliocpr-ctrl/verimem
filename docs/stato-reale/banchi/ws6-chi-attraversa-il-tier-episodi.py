"""Il tier episodi è SCRITTO ogni giorno. Qualcuno lo LEGGE?

    python docs/stato-reale/banchi/ws6-chi-attraversa-il-tier-episodi.py

Il tier non è fermo — è la prima cosa che si scopre guardando il file giusto:
**481 episodi, l'ultimo del 02/09**, scritti dall'auto-consolidamento
(`_persist_master` fa `mem.store(ep)` dopo ogni nodo). E **23 moduli del
pacchetto** importano `EpisodicMemory`, quindi non è orfano nel codice.

⚠️ MA «IMPORTATO DA 23 MODULI» NON È «ATTRAVERSATO». Un metodo può essere
definito, importato, e non essere mai chiamato da un flusso vero. Questo banco
non legge il codice: **conta le chiamate** mentre il prodotto fa il suo lavoro
normale — scrivere un fatto, richiamarlo, chiedere.

⚠️ E LA TRAPPOLA DEL FILE, che ha già ingannato me: `~/.engram/episodes.db`
**alla radice è VUOTO** (`tabelle []`); quello vero è `~/.engram/episodes/episodes.db`.
Chi misura il tier aprendo il primo conclude che non c'è niente.

METODO: si avvolgono i metodi di LETTURA di `EpisodicMemory` con un contatore,
poi si esegue un flusso realistico. Alla fine si guarda **chi ha letto e quante
volte**. Il controllo positivo è la colonna delle SCRITTURE: se anche quelle
fossero a zero, il contatore non starebbe contando nulla e il banco non
misurerebbe niente.

⛔ Store isolato in tempdir: non tocca lo store di casa.

═══ ESITO (03/09 19:32), e corregge la domanda ═══

Il banco stampa **zero letture E zero scritture**, e la colonna delle scritture
è il controllo che rende leggibile lo zero: se anche quelle sono a zero, il
numero non dice «nessuno legge», dice «non ho guardato».

Verificato a parte, e il contatore FUNZIONA: avvolgendo `EpisodicMemory.store` e
chiamandolo direttamente, la chiamata viene contata (1). Lo zero ha quindi
un'altra causa, ed è questa:

    attributi di istanza di Memory:
    ['_ledger', '_preset_defaults', '_principal', 'grounding_llm', 'llm',
     'preset', 'semantic']

⇒ **`Memory` non ha un tier episodi e non lo crea mai**: `verimem/client.py` non
nomina `EpisodicMemory` in nessun punto. Nessun `recall`, `search`, `count` o
`explain` della porta SDK può attraversarlo — non per un difetto, **per
costruzione**.

Lo creano invece: `agent.py:62`, `cli.py:4572` e `:5430`, `auto_dream_worker.py:376`,
`dashboard_routes/memory_map.py:311`, `dream.py:192`.

🔑 **La formulazione giusta non è «il tier è scritto e non letto»**: è **«il tier
non è raggiungibile dalla porta SDK»**. Le altre superfici lo leggono.

📌 E il DB vuoto alla radice è il residuo di un incidente **già curato**, che
`cli.py:4556` racconta: *«the canonical layout … is the SUBDIR
<data>/episodes/episodes.db. This helper previously hardcoded the flat
<data>/episodes.db, so on a standard install `consolidate apply` wrote the master
Episode to an orphan file nobody reads (the master Fact's source_episodes then
dangled)»*. `_consolidate_em()` ora preferisce il subdir.
"""
import os
import tempfile
from collections import Counter

_tmp = tempfile.mkdtemp(prefix="ws6_tier_episodi_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402
from verimem.memory import EpisodicMemory  # noqa: E402

LETTURE = ("recall", "recall_by_context", "recall_explain", "search_episodes",
           "get", "all", "find_by_task_text")
SCRITTURE = ("store", "store_batch", "add_causal_edge")

conta: Counter = Counter()


def _spia(nome: str):
    originale = getattr(EpisodicMemory, nome)

    def avvolto(self, *a, **k):
        conta[nome] += 1
        return originale(self, *a, **k)

    avvolto.__name__ = getattr(originale, "__name__", nome)
    setattr(EpisodicMemory, nome, avvolto)


for _n in LETTURE + SCRITTURE:
    if hasattr(EpisodicMemory, _n):
        _spia(_n)

print("CHI ATTRAVERSA IL TIER EPISODI, contando le chiamate su un flusso vero\n")

m = Memory()
FONTI = [
    ("Il deposito di Verona ospita quattromilaseicento pallet.",
     "Inventario: il deposito di Verona ospita 4600 pallet."),
    ("La squadra di turno e' composta da quattro operai.",
     "Turni: la squadra e' composta da quattro operai."),
    ("Il lotto B12 e' uscito dal deposito il nove giugno.",
     "Registro: il lotto B12 e' uscito il 9 giugno."),
]

fasi: list[tuple[str, Counter]] = []


def _fase(nome: str, azione) -> None:
    prima = Counter(conta)
    try:
        azione()
    except Exception as e:                      # noqa: BLE001 — il banco misura, non giudica
        print("  (%s ha sollevato: %s)" % (nome, str(e)[:60]))
    fasi.append((nome, Counter(conta) - prima))


_fase("scrittura di 3 fatti",
      lambda: [m.add(p, topic="tier/%d" % i, source=s) for i, (p, s) in enumerate(FONTI)])
_fase("recall", lambda: m.recall("quanti pallet ospita il deposito di Verona", k=5))
_fase("search", lambda: m.search("pallet"))
_fase("count", lambda: m.count())
_fase("explain", lambda: m.explain("quanti pallet ospita il deposito di Verona"))

print("  %-26s %s" % ("fase", "chiamate al tier episodi"))
for nome, delta in fasi:
    voci = ", ".join("%s x%d" % (k, v) for k, v in sorted(delta.items())) or "— NESSUNA —"
    print("  %-26s %s" % (nome, voci))

let = sum(v for k, v in conta.items() if k in LETTURE)
scr = sum(v for k, v in conta.items() if k in SCRITTURE)
print("\n  LETTURE del tier   %3d   %s" % (let, sorted(k for k in conta if k in LETTURE)))
print("  SCRITTURE nel tier %3d   %s" % (scr, sorted(k for k in conta if k in SCRITTURE)))
print("\n  ⚠️ CONTROLLO: se anche le SCRITTURE fossero 0, il contatore non conta")
print("     nulla e il banco non misura niente — il numero delle letture non")
print("     significherebbe «nessuno legge», ma «non ho guardato».")
