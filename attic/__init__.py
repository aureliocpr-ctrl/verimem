"""Codice che NESSUNA PORTA del prodotto raggiunge — versionato, non installato.

Non e' un cestino: e' l'archivio del perimetro. Qui stanno i moduli che
`benchmark/` e `scripts/` usano per il nostro lavoro e che l'utente non
riceve, piu' quelli che li importano. Misurato il 2026-09-17: il wheel di
quel giorno ne portava 62 su 62, 9 908 righe non vuote installate su ogni
macchina senza servire a nessuna delle tre porte, provato spegnendoli e
usando il prodotto (zero tentativi di importarli).

`attic/` sta alla RADICE e non sotto `verimem/`: `pyproject.toml` include
`["verimem*", "engram*", "hippoagent*"]`, quindi un `verimem/attic/`
verrebbe ripreso dalla wildcard e continuerebbe a viaggiare.

Nessun file qui dentro si cancella. Chi cerca un modulo che non trova piu'
nel pacchetto lo trova qui, con la sua storia in `git log --follow`.
"""
