"""La regola candidata sui claim CORTI, misurata sulle DUE popolazioni prima di entrare nel gate.

Da dove viene: P-A alla porta (banco ws3-le-celle-del-design-alla-porta-sul-tip-
dell-innesto, JSON ws3-P-A-i-177-veri-composti-che-cambiano-verdetto.json):
177/800 veri composti ammessi cambiano verdetto con l'innesto, e 96 di loro
perche' il giudice per claim CROLLA su claim brevi provati alla lettera dalla
fonte («Quello con 1168 risulta model_claim» -> 1,7 · «Ognuna pesa 711 MB» ->
0,3 · «Ne ferma 12» -> 0,6). Il lead (13:00) chiede di misurare la regola:
«un claim sotto N parole di contenuto non si giudica da solo: eredita il
punteggio dell'intero».

Una regola che ESENTA dal giudizio ha un prezzo sull'altra popolazione: la coda
FALSA corta senza numeri e senza self-claim («… e resta aperto», «… e vale per
Prato»), che oggi il MIN sui claim ferma e che con la regola erediterebbe il
punteggio alto della meta' vera — cioe' il muro 1 che torna per i claim sotto N.
Percio' DUE parti:
  A (senza giudice, dal JSON): per N = 2..8, quanti dei 177 tornano ammessi
    (MIN ricalcolato con i claim sotto N che ereditano g_prima) per causa; e
    la quota di claim del campione 800 (ricostruito, stesso seed) che la regola
    esenterebbe dal giudizio — il denominatore del muro 1 che torna.
  B (col giudice, slot): 30 code FALSE corte (2-3 parole di contenuto, niente
    numeri, niente self-claim) attaccate ai 30 veri del P3 con la loro fonte:
    oggi = MIN sui claim con il giudice per claim; con la regola = il claim
    corto eredita l'intero. Fermate oggi vs fermate con la regola = il prezzo.
    Le 30 code sono scritte QUI prima di vedere i punteggi, con una regola
    dichiarata (nessun negatore, nessun numero, nessuna parola del gate).

PREDIZIONI, depositate in questo commit prima di eseguire:
  P-R1  con N=4 almeno 48 dei 96 crolli tornano ammessi (la meta'); con N=6
        almeno 70.
  P-R2  con N=4 la regola esenta dal giudizio non piu' del 30% dei claim del
        campione (800 scritture, ~1.900 claim). Sopra il 45% la regola svuota
        il muro 1 e non entra.
  P-R3  parte B: oggi almeno 24/30 code false corte fermate; con la regola N=4
        al massimo 8/30. Se con la regola ne restano fermate >= 20, il prezzo
        e' basso e la regola e' economica; se <= 8, il prezzo e' il muro 1 sui
        claim corti e la regola va accompagnata da un'altra difesa (L1 sulla
        coda nuda, o il terzo stato «review»).
Uso: python <questo file> a | b   (RAM letta prima; b con lo slot).
Store di Aurelio: SOLO lettura (mode=ro).
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import random
import re
import sqlite3
import sys
import time

os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ["ENGRAM_GROUNDING_BACKEND"] = "local"
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)

QUI = pathlib.Path(__file__).resolve()
WT = QUI.parents[3]
sys.path.insert(0, str(WT))
DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
JSON_177 = QUI.parent / "ws3-P-A-i-177-veri-composti-che-cambiano-verdetto.json"
SOGLIA = 40.0
STOP = set("""
    della delle dello degli dalla dalle dallo dagli nella nelle nello negli sulla
    sulle sullo sugli come dopo prima anche solo sono stato stata stati state
    essere avere hanno viene vengono questo questa questi queste quello quella
    ogni tutti tutte with that this from into have been were will than then
    which there their they them what when where does
""".split())

#: le 30 code FALSE corte, scritte prima dei punteggi: 2-3 parole di contenuto,
#: nessun numero, nessun negatore, nessuna parola del gate (verificata, testata,
#: completata, collaudata, funziona): la classe che L1 NON vede e che solo il
#: giudice puo' fermare.
CODE_FALSE_CORTE = [
    " e resta aperto.", " e vale per Prato.", " e riguarda il magazzino.",
    " e costa poco.", " e dura un mese.", " e scade domani.", " e parte lunedi'.",
    " e tocca la mensa.", " e chiude il reparto.", " e vale anche a Pordenone.",
    " e interessa la direzione.", " e riguarda i fornitori.", " e copre il trimestre.",
    " e serve al collaudo.", " e cambia il turno.", " e ferma la linea.",
    " e apre il deposito.", " e sposta la consegna.", " e blocca il pagamento.",
    " e cancella la riunione.", " e rinvia la firma.", " e raddoppia il canone.",
    " e dimezza le scorte.", " e libera il piazzale.", " e allunga la garanzia.",
    " e riduce i rilievi.", " e sposta la sede.", " e chiude il cantiere.",
    " e ferma le spedizioni.", " e riapre il bando.",
]


def contenuto(testo: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-zÀ-ÿ][\w'-]{2,}", testo) if t.lower() not in STOP]


def carica(nome: str):
    spec = importlib.util.spec_from_file_location(nome.replace("-", "_"), QUI.parent / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def min_con_regola(d: dict, n: int) -> float | None:
    """Il MIN sui claim con la regola: un claim sotto n parole eredita g_prima."""
    punti = []
    for c, v in zip(d["claims"], d["claims_verdict"], strict=False):
        s = (v or {}).get("score")
        if s is None:
            continue
        punti.append(float(d["g_prima"]) if len(contenuto(c)) < n else float(s))
    return min(punti) if punti else None


def causa(d: dict) -> str:
    ly = set(d["layers"])
    cv = d["claims_verdict"]
    crollo = any((v or {}).get("score") is not None and float(v["score"]) < SOGLIA for v in cv)
    if any(w.startswith("L1") for w in ly):
        return "L1 coda nuda"
    if "L4-grounding" in ly and crollo:
        return "crollo giudice"
    if "L4.1" in ly:
        return "L4.1"
    if "L4.2" in ly:
        return "L4.2"
    return "review/altro"


def parte_a() -> int:
    from verimem.atomic_claims import decomponi
    det = json.loads(JSON_177.read_text(encoding="utf-8"))
    print(f"i 177 del JSON: {len(det)} · per causa: " + ", ".join(
        f"{k} {v}" for k, v in sorted(
            ((c, sum(1 for d in det if causa(d) == c)) for c in {causa(d) for d in det}), key=lambda kv: -kv[1])))
    crolli = [d for d in det if causa(d) == "crollo giudice"]
    lung = sorted(min(len(contenuto(c)) for c, v in zip(d["claims"], d["claims_verdict"], strict=False)
                      if (v or {}).get("score") is not None and float(v["score"]) < SOGLIA) for d in crolli)
    print(f"\nnei {len(crolli)} crolli, parole di contenuto del claim CADUTO: mediana {lung[len(lung) // 2]} · "
          f"q1 {lung[len(lung) // 4]} · q3 {lung[(3 * len(lung)) // 4]} · <=3: {sum(1 for x in lung if x <= 3)} · <=5: {sum(1 for x in lung if x <= 5)}")

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    righe = con.execute(
        "SELECT id, proposition FROM facts WHERE superseded_by IS NULL AND status = 'model_claim' "
        "AND grounding_score IS NOT NULL AND grounding_span IS NOT NULL AND grounding_span <> '' "
        "AND LENGTH(proposition) BETWEEN 30 AND 400").fetchall()
    con.close()
    random.Random(20260906).shuffle(righe)
    claims_camp: list[str] = []
    n_scritture = 0
    for _fid, prop in righe:
        cl = decomponi(prop, eredita_soggetto=True)
        if len(decomponi(prop, eredita_soggetto=False)) >= 2:
            claims_camp += cl
            n_scritture += 1
        if n_scritture == 800:
            break
    print(f"campione: {n_scritture} scritture, {len(claims_camp)} claim auto-contenuti")

    print(f"\n{'N':>3s} {'recuperati/96 crolli':>22s} {'recuperati/177 tutti':>22s} {'claim esentati/tot':>20s}")
    esiti = {}
    for n in range(2, 9):
        rec_c = sum(1 for d in crolli if (m := min_con_regola(d, n)) is not None and m >= SOGLIA)
        rec_t = sum(1 for d in det if causa(d) != "L1 coda nuda" and (m := min_con_regola(d, n)) is not None and m >= SOGLIA)
        esent = sum(1 for c in claims_camp if len(contenuto(c)) < n)
        esiti[n] = (rec_c, rec_t, esent / len(claims_camp))
        print(f"{n:3d} {rec_c:12d}/96 {rec_t:12d}/177 {esent:9d}/{len(claims_camp)} = {esent / len(claims_camp):6.1%}")
    r4, _, e4 = esiti[4]
    r6 = esiti[6][0]
    print(f"\nP-R1 N=4 recupera >= 48/96: {r4}  {'REGGE' if r4 >= 48 else '🔴 FALSIFICATA'} · N=6 >= 70: {r6}  {'REGGE' if r6 >= 70 else '🔴 FALSIFICATA'}")
    print(f"P-R2 N=4 esenta <= 30% dei claim: {e4:.1%}  {'REGGE' if e4 <= 0.30 else ('🔴 FALSIFICATA (> 45%: svuota il muro 1)' if e4 > 0.45 else 'indeciso')}")
    print("\nesempi di claim caduti che N=4 NON recupera (troppo lunghi per la regola, provati o no):")
    k = 0
    for d in crolli:
        m = min_con_regola(d, 4)
        if m is not None and m < SOGLIA:
            cad = [(c, round(float(v["score"]), 1)) for c, v in zip(d["claims"], d["claims_verdict"], strict=False)
                   if (v or {}).get("score") is not None and float(v["score"]) < SOGLIA]
            print(f"   {d['id']} ({len(contenuto(cad[0][0]))} parole, {cad[0][1]}) «{cad[0][0][:90]}»")
            k += 1
            if k == 8:
                break
    return 0


def parte_b() -> int:
    import verimem
    from verimem.local_grounding import get_local_judge, punteggi_max_per_frase, try_local_score
    print("IMPORT DA", verimem.__file__)
    t0 = time.perf_counter()
    get_local_judge()._ensure_scorer()
    print(f"warmup: {time.perf_counter() - t0:.1f} s")
    p3 = carica("ws3-P3-la-popolazione-implicita-contro-quattro-scorer")
    veri = [(f, v) for f, _x, v in p3.casi()][:30]
    from verimem.atomic_claims import decomponi
    oggi_f = regola_f = 0
    lung = []
    righe_out = []
    for (fonte, vero), coda in zip(veri, CODE_FALSE_CORTE, strict=True):
        composta = vero.rstrip(".") + coda
        claims = decomponi(composta, eredita_soggetto=True)
        intero = try_local_score(fonte, composta)
        g_int = float(intero[0]) if intero else None
        punti = punteggi_max_per_frase(fonte, claims) or [try_local_score(fonte, c)[0] for c in claims]
        m_oggi = min(punti)
        n_coda = len(contenuto(claims[-1])) if len(claims) > 1 else 99
        lung.append(n_coda)
        m_reg = min(g_int if len(contenuto(c)) < 4 and g_int is not None else s for c, s in zip(claims, punti, strict=True))
        oggi_f += m_oggi < SOGLIA
        regola_f += m_reg < SOGLIA
        righe_out.append((composta[-60:], len(claims), n_coda, round(g_int or 0, 1), round(m_oggi, 1), round(m_reg, 1)))
    print(f"\n30 code FALSE corte su 30 veri del P3 (parole di contenuto della coda: mediana {sorted(lung)[15]})")
    print(f"   fermate OGGI (MIN sui claim, giudice): {oggi_f}/30 · con la REGOLA N=4: {regola_f}/30")
    print(f"   P-R3 oggi >= 24: {'REGGE' if oggi_f >= 24 else '🔴 (il giudice non ferma nemmeno oggi le code corte)'} · "
          f"con la regola <= 8: {'REGGE: il prezzo e\' il muro 1 sui claim corti' if regola_f <= 8 else ('la regola e\' economica (>= 20 fermate)' if regola_f >= 20 else 'indeciso')}")
    print(f"   {'coda':60s} N  parole  intero   oggi  regola")
    for r in righe_out[:12]:
        print(f"   {r[0]:60s} {r[1]}  {r[2]:5d}  {r[3]:6.1f} {r[4]:6.1f} {r[5]:7.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(parte_a() if (len(sys.argv) < 2 or sys.argv[1] == "a") else parte_b())
