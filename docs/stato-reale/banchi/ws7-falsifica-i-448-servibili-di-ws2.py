"""I «+448 servibili» di @ws2 sono tutti recuperabili, o alcuni sono SUPERATI?

COSA VERIFICO. @ws2 il 02/09 alle 19:11 ha chiuso l'anello ③ di M3: il
versioning costa lo 0,21% del DB e recupera 448 fatti, cioe' 2,6 punti di
servibilita' (da 13594 su 17240 = 78,9% a 14042 = 81,5%). La sua predizione
(«>=80% dei muti torna servibile») e' stata falsificata: sono il 22,4%.

IL CAMPO DIVERSO NON E' RICONTARE, E' CHIEDERE SE IL NUMERATORE E' QUELLO GIUSTO.
Un fatto ritirato perche' SUPERATO da una versione piu' recente non e' «perso»:
e' vecchio. Recuperarlo come servibile significherebbe servire, accanto alla
versione nuova, anche quella superata.

⚠️ MA LA DOMANDA HA DUE FACCE, e la memoria del progetto porta la seconda: «la
supersessione mangia i fatti veri» — spesso il successore NON e' una correzione,
sono DUE FATTI DIVERSI sullo stesso topic (i due bracci di un A/B: 274 ritiri su
340 in sette giorni). Se il ritiro era sbagliato, il recupero e' giusto.

⇒ IL TEST DISCRIMINANTE, a costo zero: il fatto ritirato e il suo successore
hanno la STESSA fonte?
  · stessa source_signature  → stesso oggetto, stessa prova ⇒ probabile
    AGGIORNAMENTO legittimo, e recuperarlo servirebbe una versione superata
  · source DIVERSA           → due fatti che poggiano su prove diverse ⇒
    probabile SUPERSESSIONE SBAGLIATA, e il recupero e' giustificato

⚠️ E' UNA SONDA, NON UN VERDETTO. «Stessa source» non implica correzione: dalla
stessa fonte si possono estrarre due fatti diversi, e anche quella sarebbe una
supersessione sbagliata. ⇒ La quota difendibile misurata qui e' un PAVIMENTO, e
il 2,6 di @ws2 e' il TETTO.

⚠️ Sola lettura (mode=ro), percorso chiesto a CONFIG e non all'intuito.
"""
import sqlite3
import sys

BASE = ("FROM facts f JOIN facts s ON f.superseded_by = s.id "
        "WHERE f.superseded_by IS NOT NULL AND f.grounding_score >= 90 "
        "  AND f.status != 'quarantined' ")


def main() -> int:
    from verimem.config import CONFIG

    con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)

    def q(sql: str) -> int:
        return con.execute(sql).fetchone()[0]

    tot = q("SELECT COUNT(*) FROM facts")
    rit = q("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL")
    # CONTROLLO POSITIVO: devo riprodurre il suo 448 con una query mia, o non ho
    # titolo per discuterlo.
    n448 = q("SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL "
             "AND grounding_score >= 90 AND status != 'quarantined'")
    print(f"  fatti {tot} · ritirati {rit}")
    print(f"  CONTROLLO POSITIVO — il suo numero, con la mia query: {n448}")
    if n448 == 0:
        print("  🔴 non riproduco: verdetto «non riproducibile», difetto MIO")
        return 1

    piu = q("SELECT COUNT(*) " + BASE + "AND s.created_at > f.created_at")
    print(f"  di cui superati da un fatto PIU' RECENTE: {piu}/{n448}")

    stessa = q("SELECT COUNT(*) " + BASE +
               "AND f.source_signature = s.source_signature")
    div = q("SELECT COUNT(*) " + BASE +
            "AND f.source_signature != s.source_signature")
    nulla = q("SELECT COUNT(*) " + BASE +
              "AND (f.source_signature IS NULL OR s.source_signature IS NULL)")
    st = q("SELECT COUNT(*) " + BASE + "AND f.topic = s.topic")

    print(f"\n  il ritirato e il suo successore hanno...")
    print(f"    la STESSA fonte    {stessa:>4}  = {100*stessa/n448:4.1f}%"
          f"   ⇒ probabile aggiornamento: recuperarlo serve una versione vecchia")
    print(f"    fonte DIVERSA      {div:>4}  = {100*div/n448:4.1f}%"
          f"   ⇒ probabile supersessione sbagliata: recupero giustificato")
    print(f"    una fonte assente  {nulla:>4}  = {100*nulla/n448:4.1f}%"
          f"   ⇒ indecidibile con questo criterio")
    print(f"    lo stesso topic    {st:>4}  = {100*st/n448:4.1f}%")

    print(f"\n  ⇒ guadagno DIFENDIBILE oggi (solo fonte diversa): "
          f"{div}/{tot} = {100*div/tot:.1f} punti")
    print(f"    guadagno dichiarato da @ws2 (tutti i {n448}): "
          f"{100*n448/tot:.1f} punti")
    print("  🔑 Il primo e' un PAVIMENTO e il secondo un TETTO: se anche parte")
    print("     dei «stessa fonte» fosse supersessione sbagliata, il numero")
    print("     difendibile sale verso il suo.")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
