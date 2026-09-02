# -*- coding: utf-8 -*-
"""M6 — BASELINE: quanti fatti promettono una fonte e non ne conservano il testo.

    python docs/stato-reale/banchi/ws6-m6-baseline-fonte-non-conservata.py

UN COMANDO, sola lettura, nessuna dipendenza oltre la stdlib: chiunque lo rifà e
deve ottenere gli stessi numeri sullo stesso corpus.

IL MURO: un fatto che dichiara una fonte ma non ne conserva il testo **non è più
riverificabile**. Il punteggio dice che qualcuno l'ha giudicato; senza lo span,
nessuno può rifare quel giudizio.

⚠️ «DICHIARARE UNA FONTE» HA DUE DEFINIZIONI E DANNO NUMERI DIVERSI. Il fatto
originale (`f66944f38563`, 02/09 04:59) usava `source_signature`; la lettura
naturale userebbe `grounding_score`. Non sono lo stesso insieme, e il banco le
misura ENTRAMBE perché un numero solo qui è illeggibile:

  source_signature IS NOT NULL  ->  esiste una FIRMA della fonte
  grounding_score  IS NOT NULL  ->  una fonte è stata GIUDICATA

  non conserva il testo  ->  grounding_span IS NULL OR grounding_span = ''
  span al tetto          ->  length(grounding_span) = 400 esatti
      (il fatto originale diceva «lunghi esattamente 400»; con `>=` il numero
       cambia, ed è il genere di scarto che fa sembrare irriproducibile una
       misura corretta.)

⚠️ `created_at` è EPOCH, non stringa: `substr(created_at,1,10)` restituisce zero
righe senza errore (già costato una misura, il 02/09).

L'ISTANTE FA PARTE DEL NUMERO: il corpus cresce mentre si misura, quindi lo
script stampa l'ora e il totale insieme ai conteggi.
"""
import datetime as _dt
import os
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
SENZA = "(grounding_span IS NULL OR grounding_span = '')"
FIRMA = "source_signature IS NOT NULL AND source_signature <> ''"
GIUDIZIO = "grounding_score IS NOT NULL"
DICHIARA = FIRMA          # la definizione del fatto originale, per riprodurlo

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
q = lambda s, *a: con.execute(s, a).fetchone()[0]

ora = _dt.datetime.now()
tot = q("SELECT COUNT(*) FROM facts")
print("M6 — LA FONTE PROMESSA E NON CONSERVATA")
print("letto il %s · corpus %d fatti\n" % (ora.strftime("%Y-%m-%d %H:%M:%S"), tot))

print("  %-46s %7s %7s %7s" % ("«dichiara una fonte» =", "totale", "senza", "=400"))
for nome, w in (("source_signature  (la FIRMA — def. del fatto)", FIRMA),
                ("grounding_score   (il GIUDIZIO)", GIUDIZIO),
                ("entrambi", "%s AND %s" % (FIRMA, GIUDIZIO)),
                ("firma SENZA giudizio", "%s AND grounding_score IS NULL" % FIRMA),
                ("giudizio SENZA firma", "%s AND (source_signature IS NULL OR source_signature='')" % GIUDIZIO)):
    d = q("SELECT COUNT(*) FROM facts WHERE " + w)
    s = q("SELECT COUNT(*) FROM facts WHERE %s AND %s" % (w, SENZA))
    t = q("SELECT COUNT(*) FROM facts WHERE %s AND length(grounding_span) = 400" % w)
    print("  %-46s %7d %7d %7d" % (nome, d, s, t))

dich = q("SELECT COUNT(*) FROM facts WHERE " + DICHIARA)
senza = q("SELECT COUNT(*) FROM facts WHERE %s AND %s" % (DICHIARA, SENZA))
print("\n  ⇒ sulla definizione del fatto: %d con la firma, %d senza il testo = %.1f%%"
      % (dich, senza, 100.0 * senza / max(1, dich)))

# ── VIVO O STORICO? La stessa forma con cui il 02/09 si chiuse `quarantined_by`:
# il tasso sulle ultime 24h contro il tasso sul corpus intero. Se il difetto è
# storico, le 24h sono pulite; se è vivo, il tasso regge anche lì.
print("\nVIVO O DEBITO STORICO — il tasso per finestra")
print("  %-22s %8s %8s %7s" % ("finestra", "dichiara", "senza", "tasso"))
adesso = ora.timestamp()
for nome, ore in (("ultime 6 ore", 6), ("ultime 24 ore", 24), ("ultimi 7 giorni", 24 * 7),
                  ("ultimi 30 giorni", 24 * 30), ("TUTTO il corpus", None)):
    if ore is None:
        d = dich; s = senza
    else:
        soglia = adesso - ore * 3600
        d = q("SELECT COUNT(*) FROM facts WHERE %s AND created_at >= ?" % DICHIARA, soglia)
        s = q("SELECT COUNT(*) FROM facts WHERE %s AND %s AND created_at >= ?" % (DICHIARA, SENZA), soglia)
    print("  %-22s %8d %8d %6.1f%%" % (nome, d, s, 100.0 * s / max(1, d)))

# ── DA DOVE ARRIVANO: quale porta li ha scritti. I campi che possono dirlo.
for campo in ("writer_role", "writer_principal", "embedding_model", "verified_by"):
    print("\nDA DOVE — per %s (solo i fatti SENZA il testo della fonte)" % campo)
    righe = con.execute(
        "SELECT COALESCE(%s,'(nullo)'), COUNT(*) FROM facts WHERE %s AND %s "
        "GROUP BY 1 ORDER BY 2 DESC LIMIT 6" % (campo, DICHIARA, SENZA)).fetchall()
    tot_campo = con.execute(
        "SELECT COALESCE(%s,'(nullo)'), COUNT(*) FROM facts WHERE %s "
        "GROUP BY 1" % (campo, DICHIARA)).fetchall()
    base = dict(tot_campo)
    for val, n in righe:
        v = str(val)[:34]
        b = base.get(val, 0)
        # il tasso DENTRO ogni gruppo: senza di esso un gruppo grande sembra colpevole
        print("  %-36s %6d su %6d = %5.1f%%" % (v, n, b, 100.0 * n / max(1, b)))

print("\nIl primo e l'ultimo fatto senza il testo della fonte:")
for etichetta, ordine in (("piu' vecchio", "ASC"), ("piu' recente", "DESC")):
    r = con.execute("SELECT created_at, id, substr(proposition,1,58) FROM facts "
                    "WHERE %s AND %s ORDER BY created_at %s LIMIT 1" % (DICHIARA, SENZA, ordine)).fetchone()
    if r:
        print("  %-13s %s  %s  %s"
              % (etichetta, _dt.datetime.fromtimestamp(float(r[0])).strftime("%Y-%m-%d %H:%M"), r[1], r[2]))
con.close()
