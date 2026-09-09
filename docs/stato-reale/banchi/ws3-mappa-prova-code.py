"""`code.py` (35): il REPL di scrittura codice — `VerimemCode`.

⛔ **Quello che NON faccio**: non chiamo l'LLM (l'agente è finto e registra le
chiamate), non eseguo `/forget` (cancella TUTTA la memoria persistente), non
apro la sessione interattiva (`run`, `main`), non lancio il ciclo di sleep.
Provo i comandi che si possono chiamare direttamente, e per gli altri scrivo
NON MISURATO col motivo.

Il pezzo che vale: `_slash` promette «restituisce True se il comando è
riconosciuto» — si prova con un comando **inventato**, che è il caso in cui una
dispatch table sbagliata si vede.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-code-"))
os.environ["HIPPO_DATA_DIR"] = str(tmp)
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ["VERIMEM_DATA_DIR"] = str(tmp)
from verimem import code as CD  # noqa: E402
from verimem.skill import Skill, SkillLibrary  # noqa: E402


class _Memoria:
    def __init__(self):
        self.episodi = []

    def count(self):
        return len(self.episodi)

    def all(self, *a, **k):
        return self.episodi


class _AgenteFinto:
    """Un agente che NON chiama nessun LLM e registra cosa gli viene chiesto."""

    def __init__(self, skills, memoria):
        self.skills = skills
        self.memory = memoria
        self.chiamate = []
        self.semantic = memoria

    def run(self, task, **kw):
        self.chiamate.append(task)
        return {"answer": "risposta finta", "episode": None}


lib = SkillLibrary(dir_path=tmp / "sk", db_path=tmp / "sk.db")
lib.store(Skill(id="aaaaaaaa1111", name="canoni", trigger="calcolare un canone",
                body="corpo", status="candidate", trials=6, successes=5))
lib.store(Skill(id="bbbbbbbb2222", name="portineria", trigger="turni",
                body="corpo", status="promoted", trials=4, successes=4))
agente = _AgenteFinto(lib, _Memoria())

ws = tmp / "ws"
ws.mkdir()
(ws / "modulo.py").write_text("def somma(a, b):\n    return a + b\n", encoding="utf-8")
sess = CD.VerimemCode(workspace=ws, agent=agente)
print("VerimemCode costruito · workspace:", sess.workspace.name,
      "· plan_mode:", sess.plan_mode)

print("\n=== _status_line / _banner / _contextual_tip / _episodes_since_sleep")
print("  _status_line:", repr(str(sess._status_line())[:110]))
sess._banner()
print("  _episodes_since_sleep:", sess._episodes_since_sleep())
print("  _contextual_tip:", repr(str(sess._contextual_tip())[:90]))

print("\n=== _ensure_repomap / _system_addendum")
sess._ensure_repomap(3600)
print("  repomap costruita, lunghezza:", len(sess._repomap_text),
      "· costruita a:", round(sess._repomap_built_at, 1) > 0)
print("  _system_addendum:", repr(sess._system_addendum()[:120]))

print("\n=== _slash: il comando che esiste e quello INVENTATO")
print("  /status      ->", sess._slash("/status"))
print("  /comando-che-non-esiste ->", sess._slash("/comando-che-non-esiste"),
      "(True = 'gestito', e stampa 'unknown command')")

print("\n=== i comandi che si possono chiamare senza LLM")
print("--- /help")
sess._cmd_help("")
print("--- /help diff")
sess._cmd_help("diff")
print("--- /skills")
sess._cmd_skills("5")
print("--- /model (senza argomento = mostra)")
sess._cmd_model("")
print("--- /provider (senza argomento = mostra)")
sess._cmd_provider("")
print("--- /plan (interruttore)")
sess._cmd_plan("")
print("  plan_mode dopo:", sess.plan_mode)
sess._cmd_plan("")
print("  plan_mode dopo il secondo giro:", sess.plan_mode)
print("--- /repomap")
sess._cmd_repomap("")
print("--- /status")
sess._cmd_status("")
print("--- /diff (workspace senza git)")
sess._cmd_diff("")

print("\n=== _resolve_skill_id / _cmd_promote / _cmd_retire")
print("  _resolve_skill_id('aaaaaaaa'):", sess._resolve_skill_id("aaaaaaaa"))
print("  _resolve_skill_id(id intero):", sess._resolve_skill_id("aaaaaaaa1111"))
print("  _resolve_skill_id('zzzz'):", sess._resolve_skill_id("zzzz"))
sess._cmd_promote("aaaaaaaa")
lib.invalidate_cache()
print("  status dopo /promote:", lib.get("aaaaaaaa1111").status)
# REPERTO: /retire chiede conferma interattiva (rich Confirm.ask), /promote NO.
# Senza uno stdin l'attesa diventa EOFError: lo catturo e lo dichiaro invece di
# rispondere «y» a una domanda che il prodotto fa apposta.
try:
    sess._cmd_retire("bbbbbbbb")
except EOFError as e:
    print("  /retire -> chiede CONFERMA e senza stdin da'", type(e).__name__,
          "· /promote invece agisce SENZA conferma")
lib.invalidate_cache()
print("  status dopo il tentativo di /retire:", lib.get("bbbbbbbb2222").status)
sess._cmd_promote("prefisso-inesistente")

print("\n=== _show_diff / _preview_block")
sess._show_diff("--- a\n+++ b\n@@ -1 +1 @@\n-vecchio\n+nuovo\n", "modulo.py")
blocco = {"path": "modulo.py",
          "search": "def somma(a, b):\n    return a + b\n",
          "replace": "def somma(a, b):\n    return a + b + 0\n"}
try:
    print("  _preview_block:", repr(str(CD._preview_block(blocco, ws))[:140]))
except Exception as e:  # noqa: BLE001
    print("  _preview_block ->", type(e).__name__, str(e)[:110])

print("\n=== _resolve_vision_drops: senza marcatori il testo NON deve cambiare")
testo = "Sistema la funzione somma in modulo.py"
print("  senza marcatori:", repr(CD._resolve_vision_drops(testo, sess.console)))
print("  (il ramo con [image: ...] chiama la visione: NON eseguito)")

print("\n=== quello che NON eseguo, e perche'")
for n, motivo in (("_cmd_forget", "cancella TUTTA la memoria persistente"),
                  ("_cmd_sleep", "lancia il ciclo di consolidamento, pesante"),
                  ("_cmd_review", "chiede all'agente, cioe' all'LLM"),
                  ("submit", "manda il compito all'LLM"),
                  ("_retry_failed_edits", "richiede un fallimento vero e l'LLM"),
                  ("_apply_edits_with_preview", "scrive sui file dopo conferma interattiva"),
                  ("run", "apre il ciclo interattivo"),
                  ("main", "avvia la sessione")):
    print(f"  {n:26} esiste: {hasattr(sess, n) or hasattr(CD, n)} · {motivo}")
print("\n  chiamate all'agente finto in tutto il banco:", agente.chiamate)
