r"""T4.4 — quante chiamate al giudice sono ripetizioni bit-identiche? Sul corpus VERO.

Anello del muro M4. La cache del verdetto su `hash(source, fatto)` rende **solo se le
ripetizioni esistono**: prima di implementarla, si conta.

📌 **PREDIZIONE, scritta PRIMA di guardare i dati** — e **NON coincide** con quella del
piano di ricerca («*≥15% delle chiamate al giudice sono ripetizioni bit-identiche*»)::

    sul corpus TOTALE      predico **sotto il 10%**
    sui QUARANTINATI       predico **sopra il 15%**

**Il perche', che e' la parte falsificabile**: ogni `verimem save` porta una source
diversa (output di comandi, con numeri e orari che cambiano), quindi le ripetizioni
esatte dovrebbero essere rare **in generale**. Ma **chi viene fermato RITENTA**, spesso
con lo stesso identico testo — e su quella popolazione c'e' gia' una misura nel
registro: **24 quarantene su 154 sono testi ritentati identici = 15,6%**.

⇒ Se ho ragione, **la cache non va valutata sul totale**: renderebbe poco li' e molto
sui ritentativi, che sono esattamente le chiamate che oggi si pagano due volte.
⇒ Se ho torto e il totale supera il 15%, la cache vale **piu'** di quanto penso e il
piano ha ragione. **Entrambi gli esiti sono utili; nessuno dei due lo so gia'.**

COSA SI CONTA, e con quale righello::

    coppie (proposition, grounding_span) IDENTICHE, contate sul corpus reale
    in SOLA LETTURA (`mode=ro`, percorso da `CONFIG.semantic_db`, mai dall'intuito)

⚠️ **IL PROXY E' IMPERFETTO, E NEL VERSO CHE MI FA COMODO**: la tabella **non ha** la
colonna `source`. Uso `grounding_span`, che e' un ESTRATTO troncato (400 char) della
fonte: due source diverse possono condividere lo stesso span. ⇒ **Il numero che esce e'
un LIMITE SUPERIORE** delle ripetizioni vere. Se anche cosi' resta basso, la conclusione
regge a maggior ragione; se esce alto, non basta per concludere.

⇒ E si contano **due popolazioni separate** (totale e quarantinati), perche' e' proprio
la differenza fra loro l'oggetto della predizione. Un aggregato le mescolerebbe e
direbbe una terza cosa che non e' ne' l'una ne' l'altra.

🔴 ESITO — **la predizione del PIANO cade di un fattore 12; la mia regge a meta'**::

    popolazione              con span    ripetizioni      quota
    TUTTI i giudicati            7830             95       1.2%
    QUARANTINATI                  763             46       6.0%
    AMMESSI (controllo)          7067             49       0.7%

    predetto dal piano:  >=15% sul totale      ->  misurato 1.2%   FALSIFICATO
    predetto da me:      <10% totale            ->  1.2%   regge
                         >15% quarantinati      ->  6.0%   CADE

⇒ **T4.4 (cache del verdetto) risparmierebbe l'1,2% delle chiamate al giudice**, non il
15%. E siccome `grounding_span` e' troncato, **quel numero e' un limite SUPERIORE**: le
ripetizioni vere sono ancora meno. ⇒ **La strada non vale il lavoro, e va detto prima
di implementarla, non dopo.**

✅ **Cosa regge della mia intuizione**: i **quarantinati si ripetono 5 volte piu' degli
ammessi** (6,0% contro 0,7%) — la DIREZIONE era giusta, chi viene fermato ritenta. ⇒ Se
mai si facesse una cache, andrebbe messa **li'**, non sul totale. Ma 6% di una
popolazione che e' il 9,7% del corpus non paga un componente nuovo.
❌ **Cosa non regge**: avevo predetto **>15%** sui quarantinati appoggiandomi a una
misura del registro («*24 quarantene su 154 sono testi ritentati identici*», 15,6%).
**Quella era una finestra specifica, questa e' tutto il corpus**: non si contraddicono,
misurano popolazioni diverse — e io le ho trattate come la stessa.

🔑 **CONSEGUENZA PER L'ORDINE DEI LAVORI**: l'ordine previsto era baseline → T4.4 → T4.1.
⇒ **T4.4 si puo' saltare**, e T4.1 (giudice come servizio condiviso) resta l'unica
strada che la baseline sostiene: il costo e' **tutto nel caricamento** (958 MB, 31,6s
cold contro 0,47s warm, memoria che non cresce), che e' esattamente cio' che un servizio
condiviso paga **una volta sola**.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-t44-quante-chiamate-al-giudice-si-ripetono.py
"""
import pathlib
import sqlite3
import sys


def conta(con, dove, etichetta):
    """Quante scritture hanno una coppia (proposition, span) gia' vista?"""
    q = ("select proposition, coalesce(grounding_span,'') from facts "
         "where grounding_span is not null and grounding_span <> '' %s" % dove)
    righe = list(con.execute(q))
    if not righe:
        return etichetta, 0, 0, 0.0, []
    visti = {}
    for prop, span in righe:
        visti[(prop, span)] = visti.get((prop, span), 0) + 1
    doppioni = {k: v for k, v in visti.items() if v > 1}
    # le chiamate RISPARMIABILI sono le ripetizioni oltre la prima
    risparmiabili = sum(v - 1 for v in doppioni.values())
    perc = 100.0 * risparmiabili / len(righe)
    top = sorted(doppioni.items(), key=lambda kv: -kv[1])[:3]
    return etichetta, len(righe), risparmiabili, perc, top


def main():
    try:
        from verimem.config import CONFIG
        p = pathlib.Path(str(CONFIG.semantic_db))
    except Exception as e:
        print("  🔴 non riesco a leggere CONFIG.semantic_db: %s" % e)
        raise SystemExit(1)
    if not p.exists():
        print("  🔴 store assente: %s" % p)
        raise SystemExit(1)
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)   # SOLA LETTURA
    print("  corpus: %s" % p)
    print("  fatti totali: %d\n" % con.execute("select count(*) from facts").fetchone()[0])

    popolazioni = [
        ("TUTTI i giudicati", ""),
        ("QUARANTINATI", "and status = 'quarantined'"),
        ("AMMESSI (controllo)", "and status <> 'quarantined'"),
    ]
    print("  %-22s %10s %14s %10s" % ("popolazione", "con span", "ripetizioni", "quota"))
    print("  " + "-" * 62)
    esiti = {}
    for etichetta, dove in popolazioni:
        nome, tot, rip, perc, top = conta(con, dove, etichetta)
        esiti[etichetta] = perc
        print("  %-22s %10d %14d %9.1f%%" % (nome, tot, rip, perc))
        for (prop, _span), n in top:
            print("       %2d× %s" % (n, prop[:62]))
    con.close()

    tot_perc = esiti.get("TUTTI i giudicati", 0)
    q_perc = esiti.get("QUARANTINATI", 0)
    print("\n=== LA PREDIZIONE REGGE? ===")
    print("  predetto: totale <10%%  ·  quarantinati >15%%")
    print("  misurato: totale %.1f%%  ·  quarantinati %.1f%%" % (tot_perc, q_perc))
    a = tot_perc < 10
    b = q_perc > 15
    if a and b:
        print("  🟢 ENTRAMBE REGGONO: la cache rende POCO in generale e MOLTO sui")
        print("     ritentativi ⇒ va valutata su quella popolazione, non sul totale.")
    elif not a and tot_perc >= 15:
        print("  🔴 LA MIA PREDIZIONE CADE sul totale, e il piano ha ragione: le")
        print("     ripetizioni sono ≥15%% ⇒ la cache vale piu' di quanto pensassi.")
    elif a and not b:
        print("  🟡 il totale regge ma i quarantinati NO: i ritentativi non sono la")
        print("     popolazione che credevo ⇒ la cache rende poco ovunque.")
    else:
        print("  🟡 esito misto: leggi le due righe separate, non la media.")
    print("\n  ⚠️ e ricorda il verso del proxy: `grounding_span` e' TRONCATO, quindi")
    print("     questi numeri sono un LIMITE SUPERIORE delle ripetizioni vere.")


main()
