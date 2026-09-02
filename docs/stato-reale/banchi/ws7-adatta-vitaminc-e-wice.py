"""VitaminC e WiCE nello schema `pairs` che il C10 sa leggere.

PERCHE'. Mandato di Aurelio (02/09 20:00): il numero di vetrina deve diventare
una TABELLA su piu' dataset pubblici con etichette umane, stesso comando, stesse
grandezze. Oggi abbiamo TruthfulQA (15,9%) e HaluEval (35,7%, misurato da me).

I DUE NUOVI, verificati esistenti con licenza e dimensione:
  VitaminC  huggingface.co/datasets/tals/vitaminc  >400k coppie, CC-BY-SA 3.0
  WiCE      huggingface.co/datasets/tasksource/wice  5.377 righe, CC-BY-SA+ODC-BY

🔑 VITAMINC E' IL CONTROLLO CHE RENDE ONESTA LA TABELLA: le sue coppie sono
CONTRASTIVE — evidenze quasi identiche in lingua e contenuto, una che sostiene e
una che non sostiene. ⇒ Il criterio cieco del C10 (indovinare la classe dalla
sola forma) deve stare vicino a 50 per costruzione. Se il nostro gate regge li',
regge dove non si puo' barare sulla forma.

═══ LE SCELTE CHE FACCIO, dichiarate e non nascoste ═══
① MAPPATURA DELLE ETICHETTE. Il C10 vuole due classi, vero e falso.
   VitaminC  SUPPORTS -> vero · REFUTES -> falso · NOT ENOUGH INFO -> SCARTATO
   WiCE      supported -> vero · not_supported -> falso
             partially_supported -> SCARTATO
   ⚠️ Scartare la classe intermedia NON e' neutro: toglie i casi difficili e
   rende il banco piu' facile del dataset. Lo dichiaro e stampo quanti ne perdo.
② VITAMINC HA REVISIONI SINTETICHE. Il campo `revision_type` distingue `real`
   dalle coppie costruite. Il mandato dice: sintetico solo come regressione, MAI
   come numero di vetrina ⇒ TENGO SOLO `real`.
③ WICE HA L'EVIDENZA COME LISTA di frasi: le unisco con uno spazio. E' l'unica
   ricomposizione che faccio, ed e' meccanica.
④ BILANCIAMENTO 200+200 come HaluEval, cosi' i quattro numeri della tabella
   sono confrontabili a parita' di n e con lo stesso baseline del 50%.

⚠️ Disciplina degli split: uso `test`, lo ESEGUO e non lo leggo. Qui stampo solo
CONTEGGI, mai il testo dei casi.
"""
import json
import sys
from pathlib import Path

N_PER_CLASSE = 200

CONFIG = {
    "vitaminc": {
        "repo": "tals/vitaminc",
        "vero": {"SUPPORTS"},
        "falso": {"REFUTES"},
        "solo_reali": True,
    },
    "wice": {
        "repo": "tasksource/wice",
        "vero": {"supported"},
        "falso": {"not_supported"},
        "solo_reali": False,
    },
}


def testo(v) -> str:
    """WiCE ha l'evidenza come lista: la unisco. Unica ricomposizione, meccanica."""
    if isinstance(v, (list, tuple)):
        return " ".join(str(x) for x in v)
    return str(v)


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in CONFIG:
        print(f"  uso: <banco> {'|'.join(CONFIG)} <file di uscita>")
        return 2
    nome, uscita = sys.argv[1], Path(sys.argv[2])
    cfg = CONFIG[nome]

    from datasets import load_dataset

    ds = load_dataset(cfg["repo"], split="test", streaming=True)
    veri, falsi = [], []
    letti = scartati_label = scartati_sintetici = 0

    for r in ds:
        letti += 1
        if cfg["solo_reali"] and str(r.get("revision_type", "")) != "real":
            scartati_sintetici += 1
            continue
        lab = str(r.get("label", ""))
        if lab in cfg["vero"]:
            secchio, etichetta = veri, 1
        elif lab in cfg["falso"]:
            secchio, etichetta = falsi, 0
        else:
            scartati_label += 1
            continue
        if len(secchio) >= N_PER_CLASSE:
            if len(veri) >= N_PER_CLASSE and len(falsi) >= N_PER_CLASSE:
                break
            continue
        secchio.append({"claim": str(r.get("claim", "")),
                        "source": testo(r.get("evidence", "")),
                        "label": etichetta, "kind": nome, "category": lab})
        if len(veri) >= N_PER_CLASSE and len(falsi) >= N_PER_CLASSE:
            break

    fuori = []
    for a, b in zip(veri, falsi):      # alternati, come il formato pairs
        fuori.extend([a, b])
    uscita.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in fuori),
                      encoding="utf-8")

    print(f"  {nome}: righe lette {letti}")
    if cfg["solo_reali"]:
        print(f"    scartate perche' SINTETICHE           {scartati_sintetici}")
    print(f"    scartate per etichetta intermedia      {scartati_label}")
    print(f"    tenute: VERI {len(veri)}  FALSI {len(falsi)}  totale {len(fuori)}")
    print(f"    scritte in {uscita}")

    # controllo positivo dell'adattatore: popolazioni pari e non vuote, o la
    # conversione ha perso qualcosa in silenzio
    if not veri or len(veri) != len(falsi):
        print("  🔴 popolazioni non pari: conversione difettosa")
        return 1
    print("  ✅ popolazioni pari e non vuote")
    print("  ⚠️ La classe intermedia scartata rende il banco PIU' FACILE del")
    print("     dataset: il numero va letto con questo accanto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
