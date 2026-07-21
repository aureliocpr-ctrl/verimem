"""Anti-spoof trusted-writer check (FASE 4 lab, buco #1 della falsificazione).

Il gate si fida di ``writer_role in {system_hook, trusted_hook}``, ma quel campo
e' settabile dal client MCP → spoofabile. Qui il ruolo trusted vale SOLO se
accompagnato da un token segreto server-side (env): un client non lo conosce.

PURA, fail-closed, HMAC-compare (timing-safe). WIRATA in produzione (il
paragrafo precedente diceva "NON wirata" ed era STALE — corretto 2026-07-21,
trovato leggendo il modulo durante il ciclo hook-che-non-inquinano; per un
prodotto che vende memoria verificata, un file che mente sul proprio stato e'
la stessa classe di difetto che il gate esiste per bloccare):

  * ``anti_confab_gate.run_validation_gate`` — il bypass meta-narrative vale
    solo se ``meta_narrative and verify_trusted_writer(writer_role,
    hook_token)`` (cerca "verify_trusted_writer" nel modulo);
  * ``semantic.py`` store — il provenance-skip dei fatti ``verified`` con
    ``meta_narrative`` richiede lo stesso predicato token-gated (security fix
    2026-06-02, sorelle loop): senza token il gate refs gira normalmente.

Fail-closed in entrambi i punti: env non configurato o token assente/errato →
False → nessun bypass.
"""
from __future__ import annotations

import hmac
import os

_TRUSTED_ROLES = ("system_hook", "trusted_hook")
_TOKEN_ENV = "ENGRAM_HOOK_TOKEN"


def verify_trusted_writer(writer_role: str | None, token: str | None) -> bool:
    """True solo se ``writer_role`` e' trusted E ``token`` combacia col segreto
    nel modulo-privato ``_TOKEN_ENV``. Fail-closed: env non configurato o token
    assente → False.

    Red-team vettore #1 chiuso (2026-06-03): l'env-name NON e' piu override-abile
    dal chiamante (rimosso il kwarg ``env_var``). Un attaccante non puo piu
    puntare il check a un env che controlla lui per far combaciare un token noto.
    """
    if writer_role not in _TRUSTED_ROLES:
        return False
    expected = os.environ.get(_TOKEN_ENV, "")
    if not expected or not token:
        return False
    return hmac.compare_digest(str(token), str(expected))
