# `verimem/migrations/` — il ladder di schema, e il perché non è Alembic

**1 file, 181 righe** · `__init__.py`.

## Cosa fa
Framework di migrazione SQLite **senza dipendenze**. Ogni database porta una
tabella `_schema_version` (chiave, valore) e sale per gradini.

## Perché non Alembic — è scritto, e la ragione regge
Dal docstring: Alembic è fatto per **uno** schema centralizzato, e qui i database
SQLite sono **tre** (episodes, skills_index, semantic) con cicli di vita
indipendenti; gli schemi esistenti usano `CREATE TABLE IF NOT EXISTS`, quindi il
salto v0 → v1 è un no-op sulle installazioni nuove; e «un framework di 100 righe
senza dipendenze è verificabile, Alembic ne aggiunge 3».

## È raggiungibile dal prodotto? **SÌ, ed è centrale**
```
  git grep 'from .migrations|verimem.migrations' -- verimem/
    verimem/cli.py · verimem/entity_kg.py · verimem/memory.py
    verimem/semantic.py · verimem/skill.py
```
Cinque moduli del prodotto, fra cui i tre che tengono i database. **Vivo.**
