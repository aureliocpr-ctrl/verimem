"""TDD — _is_sensitive copre l'INTERA famiglia dotenv (rescan2 HIGH/med).
Bug: match ESATTO sul nome -> '.env' bloccato ma '.env.local'/'.env.production'/
'prod.env' bypassano la deny-list -> leak di secret via fs_read/fs_list/fs_search.
Fix (classe, non istanza): .env, .env.<stage>, *.env, .envrc tutti sensibili."""
from __future__ import annotations

from pathlib import Path

from verimem.tools_extra import _is_sensitive


def test_dotenv_family_is_sensitive():
    base = Path.cwd()
    for n in (".env", ".env.local", ".env.production", ".env.development",
              ".env.prod", "prod.env", "config.env", ".envrc"):
        assert _is_sensitive(base / n), f"{n!r} deve essere sensibile (dotenv/secrets)"


def test_non_dotenv_not_over_blocked():
    base = Path.cwd()
    for n in ("environment.yaml", "readme.md", "data.json", "myenv.txt",
              ".environment", "settings.py"):
        assert not _is_sensitive(base / n), f"{n!r} NON deve essere bloccato (falso positivo)"
