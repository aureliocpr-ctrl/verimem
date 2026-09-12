"""Dove gira il giudice: una scelta sola, dichiarabile da fuori.

PERCHE' ESISTE. Misurato il 2026-09-11 su una macchina con una sola scheda:
NOVE processi del prodotto tenevano un contesto CUDA aperto, 7836 MiB di 8151
occupati (96 %) e utilizzo di calcolo allo 0 %. Nessuno di quei processi stava
usando la scheda: l'avevano presa all'avvio e non la restituivano. Con 315 MiB
liberi, la prossima allocazione di chiunque fallisce.

La causa non era una scelta sbagliata, era l'ASSENZA DI UNA SCELTA: due punti
del prodotto decidevano da soli `"cuda" if torch.cuda.is_available() else
"cpu"`, e non c'era modo di dire di no. Giusto per UN processo; moltiplicato per
nove, un tetto fisico che si riempie.

IL PUNTO DELICATO, e per questo la funzione e' scritta cosi': chiedere a CUDA se
c'e' NON e' gratis. `torch.cuda.is_available()` inizializza il runtime della
scheda, cioe' costruisce il contesto che stiamo cercando di non costruire. Chi
ha chiesto "cpu" non deve vedere quella domanda partire: qui infatti il callable
`cuda_disponibile` NON viene chiamato nel ramo "cpu".

LA POLITICA, e i numeri che l'hanno decisa (misurati il 2026-09-12, A/B nella
stessa esecuzione, una variabile sola):

  commit di un processo appena avviato   con scheda   senza scheda   differenza
    che NON giudica (il caso di oggi)      1088,0 MB     1071,5 MB      16,6 MB
    che giudica                            2412,2 MB     2126,5 MB     285,7 MB

  un giudizio sulla stessa frase         con scheda   senza scheda
    a regime (mediana di tre)               0,120 s       0,206 s
    PRIMA inferenza                        20,95 s        1,75 s   <- il numero

La scheda fa guadagnare 86 ms a giudizio e ne fa perdere 19,2 all'ingresso:
pareggia dopo ~223 giudizi. Un processo a vita breve non ci arriva mai, quindi
per lui la scheda non e' un acceleratore, e' un pedaggio — oltre ai 285,7 MB di
contesto moltiplicati per quanti processi ci sono.

DUNQUE: **il default e' `cpu`**. La scheda si CHIEDE, e la chiede chi vive
abbastanza da ammortizzarla (il daemon, non il server di una sessione). `auto`
resta disponibile come scelta esplicita e vale «la scheda se c'e'».

⚠️ E' un cambio di comportamento per chi non configura niente: prima prendeva la
scheda in silenzio, adesso sta su CPU. E' il punto della cura, non un effetto
collaterale — ma va letto qui e non scoperto da un rallentamento.
"""
from __future__ import annotations

import os
from collections.abc import Callable

#: La variabile che sceglie: `cpu` (default), `cuda`, oppure `auto`.
ENV_DEVICE = "ENGRAM_JUDGE_DEVICE"

_AMMESSI = ("auto", "cpu", "cuda")

#: Assente = CPU. Chi vuole la scheda la chiede: vedi i numeri in cima.
_SENZA_VARIABILE = "cpu"


def device_richiesto(ambiente: dict[str, str] | None = None) -> str:
    """Che cosa CHIEDE la configurazione. Non tocca torch, non tocca la scheda.

    Vuoto o assente -> "cpu": la scheda si chiede. Maiuscole e spazi non contano.
    """
    grezzo = (ambiente if ambiente is not None else os.environ).get(ENV_DEVICE, "")
    voluto = str(grezzo).strip().lower()
    if not voluto:
        return _SENZA_VARIABILE
    if voluto not in _AMMESSI:
        raise ValueError(
            f"{ENV_DEVICE}={grezzo!r} non e' un valore ammesso "
            f"({', '.join(_AMMESSI)}). Meglio fermarsi che scegliere al posto "
            "di chi ha scritto qualcosa che non capiamo.")
    return voluto


def scegli_device(
    cuda_disponibile: Callable[[], bool],
    ambiente: dict[str, str] | None = None,
) -> str:
    """Il device su cui caricare il modello: "cpu" o "cuda".

    `cuda_disponibile` e' passato come CALLABLE apposta, e non come booleano
    gia' calcolato: il chiamante non deve interrogare la scheda prima di sapere
    se la domanda serve. Nel ramo "cpu" questa funzione non lo chiama affatto —
    ed e' l'unica cosa che la rende capace di NON creare un contesto.

    "cuda" esplicito su una macchina senza scheda e' un ERRORE, non un ripiego
    silenzioso: chi l'ha chiesto sta contando su prestazioni che non avra', e
    scoprirlo da un rallentamento costa piu' che leggerlo subito.
    """
    voluto = device_richiesto(ambiente)
    if voluto == "cpu":
        return "cpu"                      # NESSUNA domanda alla scheda

    if voluto == "cuda":
        if not cuda_disponibile():
            raise RuntimeError(
                f"{ENV_DEVICE}=cuda ma CUDA non e' disponibile in questo "
                "processo. Non ripiego sulla CPU in silenzio: togli la "
                "variabile per tornare ad 'auto', o mettila a 'cpu'.")
        return "cuda"
    return "cuda" if cuda_disponibile() else "cpu"


def device_dichiarato(ambiente: dict[str, str] | None = None) -> str | None:
    """Per le librerie che il device lo scelgono DA SOLE (sentence-transformers,
    CrossEncoder): la stringa quando qualcuno ha deciso, `None` quando no.

    QUESTA E' LA META' DEL PROBLEMA CHE UN `grep` NON TROVA. `SentenceTransformer(m)`
    senza `device=` prende la scheda per conto suo: nel nostro codice la parola
    `cuda` non compare, eppure il contesto nasce. Cercare "cuda" nei sorgenti
    dava due punti; i punti veri erano il doppio.

    `None` e' il valore che quelle librerie interpretano come «scegli tu»: lo
    restituisce SOLO `auto`, che ormai e' una scelta esplicita. Senza variabile
    esce `"cpu"`, e il modello non va piu' sulla scheda di sua iniziativa.
    """
    voluto = device_richiesto(ambiente)
    return None if voluto == "auto" else voluto
