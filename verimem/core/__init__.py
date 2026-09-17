"""Il nucleo: due percorsi, sei operazioni, una ricevuta (D-0002).

⚠️ REGOLA DEL CONFINE, e vale come codice e non come buon proposito: **niente
qui dentro importa dal contorno**. Il nucleo non conosce `mcp_server`, `cli`,
`client`: sono loro a chiamare lui. Il controllo di questa regola e' un test,
non una convenzione — se un giorno un import entra, deve accendersi un rosso.

Fetta 1 (oggi): la ricevuta. Le porte NON sono ancora toccate: lo saranno nella
1b, una per volta, con la proprieta' verde a ogni passo.
"""
from __future__ import annotations

from .ricevuta import (
                       ALIAS_NON_ATTRIBUIBILE,
                       CHIAVI,
                       ESITI,
                       NON_MISURATO_REMOTA,
                       STATI_LIVELLO,
                       Livello,
                       Ricevuta,
)

__all__ = ["ALIAS_NON_ATTRIBUIBILE", "CHIAVI", "ESITI",
           "NON_MISURATO_REMOTA", "STATI_LIVELLO", "Livello", "Ricevuta"]
