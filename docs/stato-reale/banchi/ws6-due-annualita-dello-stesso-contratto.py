"""Due fatti veri dallo stesso contratto, e il prodotto risponde con l'anno sbagliato.

IL CASO D'USO PIU' NATURALE CHE ESISTA: un utente indicizza un contratto ed
estrae due fatti, uno per annualita'. Entrambi veri, entrambi nella stessa fonte
che li contiene entrambi, entrambi ben sostenuti dal giudice (99,9 e 100,0).

ESITO misurato il 2026-08-29 (porta SDK, store temporaneo, modello vero):
con lo STESSO topic il secondo fatto SUPERSEDE il primo, e alla domanda
«Qual era il canone nel 2025?» il recall risponde «Il canone annuo del 2026 e'
15000 EUR». Non e' una perdita: e' una RISPOSTA SBAGLIATA a una domanda precisa,
e nulla la segnala.

I due fatti NON sono in conflitto: sono due anni diversi, nominati esplicitamente
nella proposition E nella fonte. Il prodotto li tratta come evoluzione dello
stesso valore perche' il raggruppamento e' per TOPIC.

⛔ IL CONTROLLO, ed e' cio' che rende il difetto azionabile: con TOPIC DISTINTI
le supersessioni sono zero e la risposta e' corretta. La discriminante e' il
topic, non la fonte ne' il contenuto.

⇒ Per un utente e' una riga di documentazione, non una patch: «dai un topic per
entita'/periodo, non per argomento». Ma oggi non e' scritto da nessuna parte, e
chi sbaglia non riceve un avviso: riceve una risposta plausibile e falsa.

    HIPPO_DATA_DIR=$(mktemp -d) python docs/stato-reale/banchi/ws6-due-annualita-dello-stesso-contratto.py
"""
import sqlite3

from verimem.config import CONFIG

assert "Temp" in str(CONFIG.semantic_db) or "tmp" in str(CONFIG.semantic_db), (
    "NON ISOLATO - questo banco scrive. Serve HIPPO_DATA_DIR su una tempdir.")

from verimem import Memory  # noqa: E402

FONTE = ("Contratto di locazione. Il canone annuo era di 12000 EUR nel 2025 "
         "ed e' di 15000 EUR nel 2026.")
DOMANDA = "Qual era il canone nel 2025?"


def _prova(topic_2025: str, topic_2026: str) -> tuple[int, list[str]]:
    m = Memory()
    m.add("Il canone annuo del 2025 e' 12000 EUR.", topic=topic_2025, source=FONTE)
    m.add("Il canone annuo del 2026 e' 15000 EUR.", topic=topic_2026, source=FONTE)
    con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
    try:
        superseduti = con.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL").fetchone()[0]
    finally:
        con.close()
    return superseduti, [x.get("text", "") for x in m.recall(DOMANDA, k=5)]


def main() -> None:
    print("⚠️ Un solo regime per esecuzione: lo store e' condiviso e i casi si\n"
          "   mescolerebbero. Cambia i topic qui sotto e rilancia con una tempdir nuova.\n")
    superseduti, testi = _prova("contratto/canone", "contratto/canone")
    print(f"STESSO TOPIC — superseduti: {superseduti}")
    print(f"  «{DOMANDA}» -> {len(testi)}")
    for t in testi:
        print(f"     «{t}»")
    giusto = any("2025" in t and "12000" in t for t in testi)
    print(f"  ⇒ {'risponde con il 2025' if giusto else '🔴 NON restituisce il fatto del 2025'}")
    print("\nPer il controllo: rilancia con topic 'contratto/canone/2025' e "
          "'contratto/canone/2026' su una tempdir nuova.\n"
          "Misurato il 29/08: superseduti 0, e la risposta contiene il 2025.")


if __name__ == "__main__":
    main()
