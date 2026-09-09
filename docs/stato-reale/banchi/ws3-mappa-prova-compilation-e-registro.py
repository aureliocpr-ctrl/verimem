"""`compilation.py` (13) e `tool_registry.py` (11), funzione per funzione.

Due domande che valgono più delle altre:
  · `execute_macro` promette di eseguire **senza nessuna chiamata all'LLM**:
    lo si prova con strumenti finti che REGISTRANO di essere stati chiamati, e
    un LLM finto che si fa sentire se qualcuno lo tocca.
  · `CapabilityRegistry.get` restituisce «DEFAULT_CAPABILITY (READ/low)» per un
    tool sconosciuto: è scritto nel docstring, ma la conseguenza va misurata —
    uno strumento che scrive o esegue comandi, finché non è registrato, si
    presenta come sola lettura a basso rischio.
"""
from __future__ import annotations

import pathlib
import sys

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
from verimem import compilation as CP  # noqa: E402
from verimem import tool_registry as TR  # noqa: E402

print("=" * 74)
print("A. compilation.py")
print("=" * 74)
s = CP.MacroStep(tool="cerca", args={"q": "{{TASK}}", "extra": ["{{LAST_OBSERVATION}}"]})
d = s.to_dict()
s2 = CP.MacroStep.from_dict(d)
print("MacroStep round-trip:", d, "| uguale dopo il giro:", s2.to_dict() == d)
mac = CP.CompiledMacro(skill_id="sk1", steps=[s],
                       derived_from_episodes=["ep1", "ep2"], confidence=0.7)
dm = mac.to_dict()
print("CompiledMacro round-trip:", str(dm)[:130],
      "| uguale:", CP.CompiledMacro.from_dict(dm).to_dict() == dm)
print("from_dict su un dict VUOTO (i default reggono?):",
      CP.CompiledMacro.from_dict({}).to_dict())

print("\n_extract_json su tre involucri:")
for testo in ('{"a": 1}',
              'Ecco il risultato:\n```json\n{"a": 2}\n```\ngrazie',
              'nessun json qui'):
    print(f"  {testo[:38]!r:42} -> {CP._extract_json(testo)}")


class _Traccia:
    def __init__(self, step, action, action_input):
        self.step = step
        self.action = action
        self.action_input = action_input


class _Ep:
    """Un episodio come lo legge `trajectories_to_prompt`: `task_text`,
    `final_answer` e `traces` (letti nel codice, righe 135-151)."""

    def __init__(self, t, ok=True):
        self.task_text = t
        self.final_answer = "5900 euro"
        # una traccia ha `step`, `action`, `action_input` (letti alle righe
        # 140-141 di compilation.py), NON un dizionario `tool`/`args`
        self.traces = [_Traccia(1, "cerca", '{"q": "' + t + '"}')]
        self.outcome = "success" if ok else "failure"
        self.skills_used = ["sk1"]
        self.tools_used = ["cerca"]
        self.id = "ep-" + t


print("\ntrajectories_to_prompt(3 episodi, cap=2):")
print(" ", CP.trajectories_to_prompt([_Ep("uno"), _Ep("due"), _Ep("tre")], 2)[:160])

print("\n_substitute (ricorsivo su str/dict/list):")
ctx = {"TASK": "trova il canone", "LAST_OBSERVATION": "5900 euro"}
print("  str :", CP._substitute("{{TASK}} -> {{LAST_OBSERVATION}}", ctx))
print("  dict:", CP._substitute({"q": "{{TASK}}", "n": [1, "{{LAST_OBSERVATION}}"]}, ctx))
print("  segnaposto ignoto:", CP._substitute("{{BOH}}", ctx))

print("\nexecute_macro: deterministico, e l'LLM non deve nemmeno essere sfiorato")
chiamate: list[tuple[str, dict]] = []


class _Spec:
    """Uno strumento come lo vuole `execute_macro`: un oggetto con `.handler`
    (riga 267 di compilation.py), non una funzione nuda."""

    def __init__(self, nome, ritorno):
        self.nome = nome
        self.ritorno = ritorno

    def handler(self, **kw):
        chiamate.append((self.nome, kw))
        return self.ritorno


macro = CP.CompiledMacro(
    skill_id="sk1",
    steps=[CP.MacroStep(tool="cerca", args={"q": "{{TASK}}"}),
           CP.MacroStep(tool="scrivi", args={"testo": "{{LAST_OBSERVATION}}"})])
res = CP.execute_macro(macro, "qual e' il canone?",
                       {"cerca": _Spec("cerca", "5900 euro"),
                        "scrivi": _Spec("scrivi", "scritto")})
print("  risultato:", str(res)[:200])
print("  chiamate registrate:", chiamate)
print("  >>> LAST_OBSERVATION del primo passo è arrivato al secondo:",
      any(c[1].get("testo") == "5900 euro" for c in chiamate))
mancante = CP.execute_macro(macro, "x", {"cerca": _Spec("cerca", "5900 euro")})
print("  con uno strumento MANCANTE:", str(mancante)[:160])


class _SpecCheEsplode:
    def handler(self, **kw):
        raise RuntimeError("il tool e' caduto")


rotto = CP.execute_macro(macro, "x", {"cerca": _SpecCheEsplode(),
                                      "scrivi": _Spec("scrivi", "y")})
print("  con uno strumento che SOLLEVA:", str(rotto)[:160])

# IL CONTROLLO POSITIVO: la macro deve CHIUDERSI con `submit_solution`
# (righe 303-305). Senza, il risultato è ok=False con
# «macro completed without submit_solution» — ed è il caso qui sopra.
macro_ok = CP.CompiledMacro(
    skill_id="sk1",
    steps=[CP.MacroStep(tool="cerca", args={"q": "{{TASK}}"}),
           CP.MacroStep(tool="submit_solution", args={"answer": "{{LAST_OBSERVATION}}"})])
buona = CP.execute_macro(macro_ok, "qual e' il canone?",
                         {"cerca": _Spec("cerca", "5900 euro"),
                          "submit_solution": _Spec("submit_solution", "ok")})
print("  con submit_solution in fondo -> ok:", buona.ok,
      "| final_answer:", repr(buona.final_answer), "| passi:", len(buona.traces))

print("\ncompile_macro: NON MISURATO senza un LLM vero — provo con uno finto")


class _LLMFinto:
    """`compile_macro` chiama `llm.complete(system=…, messages=…, …)`
    (riga 173): un oggetto chiamabile non basta, serve il metodo."""

    def __init__(self, risposta):
        self.risposta = risposta
        self.chiamato = 0

    def complete(self, **kw):
        self.chiamato += 1
        return _Risposta(self.risposta)


class _Risposta:
    """La risposta dell'LLM viene letta con `.text` (misurato: con una stringa
    nuda si prende `AttributeError: 'str' object has no attribute 'text'`).
    La firma dichiara solo `llm: Any`, quindi il contratto sta nel corpo."""

    def __init__(self, text):
        self.text = text


class _SkillFinta:
    id = "sk1"
    name = "cerca il canone"
    trigger = "quando serve un canone"
    body = "usa lo strumento cerca"


llm_ok = _LLMFinto('{"steps": [{"tool": "cerca", "args": {"q": "{{TASK}}"}}], '
                   '"confidence": 0.8}')
episodi = [_Ep("uno"), _Ep("due"), _Ep("tre"), _Ep("quattro"), _Ep("cinque")]
try:
    out = CP.compile_macro(_SkillFinta(), episodi, llm_ok)
    print("  con LLM finto valido ->", str(out)[:150], "| chiamate all'llm:", llm_ok.chiamato)
except Exception as e:  # noqa: BLE001
    print("  ->", type(e).__name__, str(e)[:130])
llm_ko = _LLMFinto("non e' json")
try:
    print("  con LLM finto che risponde spazzatura ->",
          CP.compile_macro(_SkillFinta(), episodi, llm_ko), "| chiamate:", llm_ko.chiamato)
except Exception as e:  # noqa: BLE001
    print("  ->", type(e).__name__, str(e)[:130])
print("  con MENO episodi del minimo (1):",
      CP.compile_macro(_SkillFinta(), [_Ep("uno")], llm_ok),
      "→ non chiama nemmeno l'LLM (chiamate totali:", llm_ok.chiamato, ")")

print("\n" + "=" * 74)
print("B. tool_registry.py")
print("=" * 74)
reg = TR.build_default_registry()
print("build_default_registry: strumenti registrati:", len(reg.all()))
noti = sorted(c.name for c in reg.all())[:8]
print("  primi otto:", noti)
print("\n>>> IL PUNTO: che cosa torna per uno strumento SCONOSCIUTO?")
print("    Il docstring di `get` dice «Returns DEFAULT_CAPABILITY (READ/low)»,")
print("    ma il commento sopra il default (righe 57-60) racconta una cura")
print("    fail-CLOSED dopo un audit. Misuro invece di scegliere quale credere.")
uno = reg.all()[0]
n = reg.get(uno.name)
print(f"  get({uno.name!r}) -> capability={n.capability} risk={n.risk_level} "
      f"reversibility={n.reversibility} confirm={n.requires_confirm}")
ig = reg.get("uno_strumento_mai_visto_che_cancella_tutto")
print(f"  get(SCONOSCIUTO) -> capability={ig.capability} risk={ig.risk_level} "
      f"reversibility={ig.reversibility} confirm={ig.requires_confirm} "
      f"sandbox={ig.requires_sandbox} bypass={ig.gating_bypass}")

print("\nle viste per capacita' e per rischio:")
print("  writes_memory   :", len(reg.writes_memory()), "->",
      [c.name for c in reg.writes_memory()][:4])
print("  executes_command:", len(reg.executes_command()), "->",
      [c.name for c in reg.executes_command()][:4])
print("  requires_confirm:", len(reg.requires_confirm()), "->",
      [c.name for c in reg.requires_confirm()][:4])
for r in ("low", "medium", "high", "critical"):
    try:
        print(f"  by_risk({r}):", len(reg.by_risk(r)))
    except Exception as e:  # noqa: BLE001
        print(f"  by_risk({r}) ->", type(e).__name__, str(e)[:60])
for c in ("READ", "WRITE", "EXECUTE"):
    try:
        print(f"  by_capability({c}):", len(reg.by_capability(c)))
    except Exception as e:  # noqa: BLE001
        print(f"  by_capability({c}) ->", type(e).__name__, str(e)[:60])

print("\nregister: aggiunta e sovrascrittura (idempotente)")
prima = len(reg.all())
reg.register(TR.ToolCapability(name="mio_tool", capability="WRITE",
                               risk_level="high",
                               reversibility="no"))
print("  dopo register:", reg.get("mio_tool").capability, reg.get("mio_tool").risk_level,
      "| totale:", len(reg.all()), f"(era {prima})")
reg.register(TR.ToolCapability(name="mio_tool", capability="READ",
                               risk_level="low",
                               reversibility="yes"))
print("  dopo la sovrascrittura:", reg.get("mio_tool").capability,
      "| totale (non deve crescere):", len(reg.all()))
