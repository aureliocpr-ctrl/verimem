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

Non decide la politica: rende possibile deciderla. Il default resta `auto`,
cioe' il comportamento di prima.
"""
from __future__ import annotations

import os
from collections.abc import Callable

#: La variabile che sceglie. `auto` (default) = come prima.
ENV_DEVICE = "ENGRAM_JUDGE_DEVICE"

_AMMESSI = ("auto", "cpu", "cuda")


def device_richiesto(ambiente: dict[str, str] | None = None) -> str:
    """Che cosa CHIEDE la configurazione. Non tocca torch, non tocca la scheda.

    Vuoto o assente -> "auto". Maiuscole e spazi non contano.
    """
    grezzo = (ambiente if ambiente is not None else os.environ).get(ENV_DEVICE, "")
    voluto = str(grezzo).strip().lower()
    if not voluto:
        return "auto"
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
