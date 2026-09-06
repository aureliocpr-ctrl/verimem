"""Il presidio del 2026-08-04, riscritto con il righello giusto.

    python docs/stato-reale/banchi/il-presidio-con-le-due-colonne.py

PERCHE' RISCRITTO. Il presidio originale misurava «quanti fatti restano vivi» e dava
1 · 1 · 1 sui tre casi. Misurato il 06/09 separando i meccanismi::

    caso                        vivi  superseded  quarantined  layer
    source DIVERSE                1        1           0       L3-supersession
    STESSA source aggiornata      1        0           1       **L4.1**
    nessuna source                1        1           0       L3-supersession

Due sono RITIRI, uno e' una QUARANTENA decisa da un layer che non c'entra con la
supersessione: **«quanti vivi» fondeva due meccanismi in un numero solo**, ed e' per
questo che nel 04/08 la regressione «non si sapeva spiegare».

E IL CASO 2 ERA COSTRUITO MALE (lead, 06/09 08:06): non era «un aggiornamento
legittimo che la cura rompeva», era **un claim col valore NUOVO contro una source che
ha ancora il valore VECCHIO** — L4.1 lo quarantina perche' il valore non sta nella
fonte, e fa bene. Qui il caso 2 e' rifatto BENE: **la source e' aggiornata insieme al
valore**, quindi il testo cambia e la firma con lui.

PERCHE' UNO SCRIPT E NON UN TEST: `tests/conftest.py:121` stubba l'embedder in una
fixture `autouse` e questi rami decidono col coseno; dentro pytest il verdetto e'
quello dello stub. (Modello: `docs/stato-reale/banchi/ws5-il-caso-reale-del-ramo-semantico.py`.)

⚠️ IL CASO 4 E' CAMBIATO IL 06/09 08:21, e la ragione va letta: l'attesa era «campo
`supersedes` dichiarato al write → 1 vivo per ritiro dichiarato», ma **quel campo non
esiste**: `Memory.add` ha 19 parametri e `supersedes` non e' fra loro (verificato con
`inspect.signature`). La via esplicita che ESISTE e' un'operazione a posteriori,
`SemanticMemory.supersede(old_id, new_id, principal=...)`, ed e' quella che il caso 4
misura adesso. Un caso che chiama un campo inesistente non misura niente.

ATTESE — oggi (senza cura) e dopo le due cure, secondo la D-1::

    caso                     oggi                          con la cura ①+②
    1 source DIVERSE         1 vivo, ritiro                2 vivi, coesistenza + warning
    2 source AGGIORNATA      1 vivo, ritiro                2 vivi, coesistenza + warning
    3 nessuna source         1 vivo, ritiro                come oggi (NON si tocca)
    4 supersessione ESPLICITA 1 vivo                       1 vivo (la via dichiarata resta)
    5 i due bracci di un A/B 1 vivo, ritiro                2 vivi
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

# La radice del checkout PRIMA di tutto: `sys.path[0]` e' la cartella dello
# SCRIPT, non del repo, e senza questa riga `import verimem` risolve su un altro
# albero senza dirlo — in un worktree misureresti l'albero di qualcun altro.
# (`pytest` non ha questo problema; uno script si'.)
_RADICE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, _RADICE)

_TMP = tempfile.mkdtemp(prefix="presidio-")
for _v in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
    os.environ[_v] = _TMP
os.environ["ENGRAM_SEMANTIC_CONFLICT"] = "1"

import verimem                                   # noqa: E402
from verimem.client import Memory                # noqa: E402


def _layer(ric) -> str:
    ws = (ric.get("warnings") or []) if isinstance(ric, dict) else []
    ls = [str(w.get("layer")) for w in ws if isinstance(w, dict) and w.get("layer")]
    return " + ".join(ls) if ls else "-"


def _id_di(ric):
    """L'id del fatto appena scritto, comunque si chiami la chiave.

    ⚠️ Non si indovina: se nessuna delle chiavi note c'e', STAMPA quelle che ci
    sono. Un `None` silenzioso qui farebbe fallire il caso 4 per la ragione
    sbagliata — e sarebbe la quarta volta."""
    if not isinstance(ric, dict):
        return None
    for k in ("fact_id", "id", "stored_id", "new_id"):
        if ric.get(k):
            return ric[k]
    print(f"     ⚠️ id non trovato; chiavi della ricevuta: {sorted(ric)}")
    return None


def caso(n, nome, primo, secondo, *, src_a=None, src_b=None, kw_b=None,
         supersede_esplicito=False):
    """Scrive i due fatti e riporta le DUE colonne di meccanismo separate.

    🔑 `superseded` e `quarantined` non si sommano in «vivi»: sono due cose diverse
    e il presidio vecchio le confondeva."""
    db = os.path.join(_TMP, f"c{n}.db")
    m = Memory(db)
    ric_a = m.add(primo, topic=f"reg{n}", **({"source": src_a} if src_a else {}))
    ric = m.add(secondo, topic=f"reg{n}", **({"source": src_b} if src_b else {}),
                **(kw_b or {}))
    nota = ""
    if supersede_esplicito:
        # LA VIA DICHIARATA, quella che esiste davvero: un'operazione, non un campo.
        _old, _new = _id_di(ric_a), _id_di(ric)
        if _old and _new:
            try:
                m.semantic.supersede(_old, _new, principal="ws6-banco",
                                     reason="il banco dichiara il ritiro")
                nota = "  [supersede ESPLICITO chiamato]"
            except Exception as e:                       # noqa: BLE001
                nota = f"  [supersede ESPLICITO FALLITO: {type(e).__name__}: {e}]"
        else:
            nota = "  [supersede NON chiamato: id mancanti]"
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    tot = c.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    sup = c.execute("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL").fetchone()[0]
    qua = c.execute("SELECT COUNT(*) FROM facts WHERE status='quarantined'").fetchone()[0]
    emb = c.execute("SELECT COUNT(*) FROM facts WHERE embedding IS NOT NULL").fetchone()[0]
    c.close()
    vivi = tot - sup - qua
    print(f"  {n}. {nome:32s} vivi={vivi}  superseded={sup}  quarantined={qua}"
          f"  emb={emb}/{tot}  layer={_layer(ric)}{nota}")


print("ALBERO MISURATO:", verimem.__file__)
print("ENGRAM_SEMANTIC_CONFLICT:", os.environ.get("ENGRAM_SEMANTIC_CONFLICT"))
# 🔑 IL CONTROLLO POSITIVO CHE DEVE ACCENDERSI: se le cure non sono nell'albero
# che sto misurando, il banco lo dice QUI, prima dei numeri — invece di dare
# cinque righe plausibili e sbagliate.
from verimem.supersession_policy import canonical_source_of  # noqa: E402
import types                                                 # noqa: E402
_prova = types.SimpleNamespace(source_signature="sha256:PROVA", verified_by=[])
print("CURA ① presente:", canonical_source_of(_prova) == "sha256:PROVA",
      f"(canonical_source_of di una firma -> {canonical_source_of(_prova)!r})")
from verimem.anti_confab_gate import _TESTI_VERDETTO_L3      # noqa: E402
print("CURA ② presente:", "L3-fonti-distinte" in _TESTI_VERDETTO_L3, "\n")

caso(1, "source DIVERSE (due cartelle)",
     "Il paziente Rossi pesa 70 kg", "Il paziente Rossi pesa 95 kg",
     src_a="Cartella A: il paziente Rossi pesa 70 kg",
     src_b="Cartella B: il paziente Rossi pesa 95 kg")

# ⚠️ IL CASO 2 RIFATTO BENE: la SOURCE e' aggiornata insieme al valore, quindi il
# testo cambia e con lui la firma. Nel presidio del 04/08 la source restava quella
# VECCHIA e L4.1 quarantinava — giustamente, perche' il valore nuovo non c'era nella
# fonte. Quello non era «l'aggiornamento legittimo»: era un claim non sostenuto.
caso(2, "source AGGIORNATA col valore",
     "Il paziente Rossi pesa 70 kg", "Il paziente Rossi pesa 95 kg",
     src_a="Cartella clinica, visita di marzo: il paziente Rossi pesa 70 kg",
     src_b="Cartella clinica, visita di settembre: il paziente Rossi pesa 95 kg")

caso(3, "nessuna source (compatibilita')",
     "Il paziente Rossi pesa 70 kg", "Il paziente Rossi pesa 95 kg")

caso(4, "supersessione ESPLICITA",
     "Il paziente Rossi pesa 70 kg", "Il paziente Rossi pesa 95 kg",
     src_a="Cartella clinica, visita di marzo: il paziente Rossi pesa 70 kg",
     src_b="Cartella clinica, visita di settembre: il paziente Rossi pesa 95 kg",
     supersede_esplicito=True)

caso(5, "i due bracci di un A/B",
     "Con ENGRAM_GRADED_ADMISSION acceso il gate ammette 296 falsi su 300",
     "Con ENGRAM_GRADED_ADMISSION spento il gate ammette 40 falsi su 300",
     src_a="Banco del 30 agosto, braccio acceso: 296 falsi ammessi su 300",
     src_b="Banco del 30 agosto, braccio spento: 40 falsi ammessi su 300")
