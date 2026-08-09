# VeriMem — istruzioni di progetto

Le regole di condotta sono nel CLAUDE.md globale (`~/.claude/CLAUDE.md`), fonte
unica: qui non si ricopiano, si citano per ID (`A1`, `O2`, `E-STUCK`).
Questo file dice solo ciò che è vero **di questo repo**.

## Cos'è
Memoria **verificata** per agenti: un fatto passa un gate di grounding (il "moat")
prima di contare come vero, quindi il recall non restituisce confabulazioni.
Tre proprietà vendute, e che vanno difese in ogni PR: **scrittura gated**,
**provenienza a ogni lettura**, **astensione invece di allucinazione**.

Package reale = `verimem/`. `engram/` e `hippoagent/` sono shim di
compatibilità: `engram.X is verimem.X`. Il rename profondo dei **tool MCP**
(`hippo_*` → `verimem_*`) è **fase 2, gated su decisione di Aurelio** — rompe ~231
riferimenti in CLAUDE.md/hook/skill/memoria (fact `4ba7460d5f51`). Finché non è
deciso, i tool si chiamano `hippo_*` ed è corretto così.

## Comandi canonici
La CLI `verimem` è la strada per la continuità di sessione — **non `clp`** (deciso
23/07, i tool `clp-bridge` `memory_save`/`chain_*`/`digest` sono il predecessore).

```
verimem save "..." --topic <ns> --lineage-to auto   # checkpoint sulla catena, passa dal gate
verimem tip                                          # dove eravamo rimasti
verimem recent / digest / chain / handoff            # continuità
verimem facts / episodes / trust / stats             # ispezione dello store
verimem audit                                        # tamper-evidence sulle catene
```

Store reale: `~/.engram/semantic/semantic.db` (tabella `facts`). `~/.engram/memory.db` è vuoto — non è quello.

## Come si lavora qui
- **O2 senza sconti**: test RED prima, falsificato con mutazione (rimetti il bug → il
  test deve fallire), poi GREEN, poi critic gate. Budget critic max 2 giri.
- **Mai push né merge senza Aurelio.** Il commit locale sì, il push è suo.
- **Full suite prima di proporre un push.** Oltre mille file di test (`find tests -name 'test_*.py' | wc -l` per il numero vero); una regressione
  introdotta e non vista è già costata due volte.
- **Security → Opus, e da avversario mentre scrivi**, non solo quando critici
  (`B2`). L'analisi statica veloce su cripto/path si è dimostrata inaffidabile: 0/6
  buchi trovati a occhio, 6/6 con dataflow ostile.
- **Avversari esterni**: `veri chat -m <glm|kimi> --effort high --yes` con packet
  **< 3 KB** (oltre 4 KB fallisce). Binario in `~/Code/veriagent`.

## Trappole del repo — verificate, non teoriche
- **I fake nei test sono call-site a tutti gli effetti.** Un fake che accetta una
  firma che la produzione rifiuta nasconde il bug invece di trovarlo. Quando cambi
  una firma nel core, lo sweep include `tests/`.
- **`filterwarnings=error`**: un warning nuovo rompe la suite. Gli shim sono silent apposta.
- **Env-watcher**: storicamente ripristinava i `.py` fra un tool-call e l'altro →
  edit+add+commit **atomici** in un solo comando. Dal 19/07 non lo faceva più: verifica, non assumere.
- **CI ≠ locale**: il CI non scalda il gate CE e gira su Linux. Test che dipendono da
  un modello scaricato o da path assolute vogliono skip-guard o branch per OS.
- **Sandbox**: `verimem/sandbox.py` è tooling agentico, **non** il prodotto-memoria.
  Il suo `allowed_cwds` confina la CWD contro il danno operativo, non è un confine di
  confidenzialità in lettura — e non deve esserlo. Chiuso come non-finding il 24/07:
  non riaprirlo.

## Stato
Non è in questo file — cambia. `verimem tip`, `git log`, e `MEMORY.md`
(`~/.claude/projects/C--Users-aurel-Desktop-ProgettiAI/memory/`) per il quadro corrente.
Prima azione di ogni task su questo repo: `git log` + `git status` + recall.
**Git vince sulla memoria**: se la memoria dice "da fare" e git dice "già committato", git ha ragione.
