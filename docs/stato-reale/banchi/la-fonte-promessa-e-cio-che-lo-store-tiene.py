"""Il README promette «facts ... stored with their sources». Quanti ce l'hanno?

La riga 33 del README dice: «facts are admitted through an anti-confabulation
gate, **stored with their sources**, revised through explicit supersession...».

Il codice dice un'altra cosa, e lo dice da se' (semantic.py:1467-1477, v17 del
2026-08-08): «della fonte restava solo `source_signature`, un'impronta sha256. Si
sapeva che due fatti venivano dalla stessa fonte e NON SI SAPEVA PIU' COSA QUELLA
FONTE DICESSE — misurato a due livelli: la fonte non e' in nessuno dei due». La
v17 ha aggiunto `grounding_span`, che e' un ESTRATTO (budget 400), non la fonte.

E le colonne di `facts` non contengono nessun campo `source`.

CRITERIO, dichiarato prima: il commento stesso dice che i due casi sono
distinguibili — «fonte c'era» ha `source_signature`. Quindi:
  · con source_signature e con grounding_span  -> un ESTRATTO della fonte c'e'
  · con source_signature e SENZA grounding_span -> la fonte c'era e NON c'e' piu'
  · senza source_signature                      -> nessuna fonte data (non e' un difetto)

Sola lettura, `mode=ro`, zero RAM, nessun modello.
"""
import sqlite3
import sys

from verimem.config import CONFIG

db = str(CONFIG.semantic_db)
print(f"  store: {db}")
conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
try:
    q = conn.execute("""
        SELECT
          COUNT(*),
          SUM(CASE WHEN source_signature IS NOT NULL AND source_signature <> '' THEN 1 ELSE 0 END),
          SUM(CASE WHEN source_signature IS NOT NULL AND source_signature <> ''
                    AND grounding_span IS NOT NULL AND grounding_span <> '' THEN 1 ELSE 0 END),
          SUM(CASE WHEN grounding_span IS NOT NULL AND grounding_span <> '' THEN 1 ELSE 0 END)
        FROM facts
    """).fetchone()
    tot, con_firma, con_firma_e_span, con_span = (x or 0 for x in q)
    senza_span_ma_con_firma = con_firma - con_firma_e_span
    print()
    print(f"  fatti nello store                                  {tot}")
    print(f"  con una FONTE dichiarata (source_signature)        {con_firma}"
          f"   ({100*con_firma/tot:.1f}%)")
    print(f"     di cui con un ESTRATTO (grounding_span)         {con_firma_e_span}"
          f"   ({100*con_firma_e_span/con_firma:.1f}% di quelli con fonte)")
    print(f"     di cui la fonte c'era e NON c'e' piu'           {senza_span_ma_con_firma}"
          f"   ({100*senza_span_ma_con_firma/con_firma:.1f}%)")
    print(f"  con un estratto, in totale                         {con_span}"
          f"   ({100*con_span/tot:.1f}% dello store)")
    print()
    print("  e la FONTE INTERA, per quanti?  ZERO: nessuna colonna la conserva")
    print("  (colonne di facts: id proposition topic confidence source_episodes")
    print("   created_at embedding superseded_* verified_by status source_signature")
    print("   trigger_keywords applicable_when worked_example lineage_to")
    print("   writer_role meta_narrative writer_principal last_verified_at")
    print("   + grounding_span dalla v17)")
    # CONTROLLO CHE DEVE ACCENDERSI: se lo span e' un estratto a budget fisso,
    # devono esistere span ESATTAMENTE al tetto (fonti tagliate) e NESSUNO
    # appena sopra. Il massimo assoluto non serve: un solo record fuori scala
    # spegnerebbe un controllo altrimenti corretto (successo il 02/09: 932).
    al_tetto = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE LENGTH(grounding_span)=400").fetchone()[0]
    appena_sopra = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE LENGTH(grounding_span) BETWEEN 401 AND 600"
    ).fetchone()[0]
    oltre = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE LENGTH(grounding_span) > 600").fetchone()[0]
    print()
    print(f"  span esattamente a 400 (fonte TAGLIATA)   {al_tetto}")
    print(f"  span fra 401 e 600                        {appena_sopra}")
    print(f"  span oltre 600 (fuori scala, da spiegare) {oltre}")
    if al_tetto > 0 and appena_sopra == 0:
        print("  CONTROLLO ACCESO: il budget e' 400 e le fonti piu' lunghe sono tagliate")
        print("  => sotto il tetto lo span PUO' essere la fonte intera; al tetto NO")
    else:
        print("  CONTROLLO SPENTO: il tetto non si vede, i numeri sopra NON vanno usati")
        sys.exit(1)
finally:
    conn.close()
sys.exit(0)
