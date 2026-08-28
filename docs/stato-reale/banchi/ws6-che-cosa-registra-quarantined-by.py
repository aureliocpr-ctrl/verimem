"""Che cosa registra `quarantined_by`: il detector, la famiglia, o altro?

Chiude l'n=1 della cella LANT-35 di ws7, che chiedeva esplicitamente:
«se qualcuna lo fa su 20 fatti, la cella diventa un fatto invece che un indizio».

Dodici claim scelti per attivare layer DIVERSI (nove che devono essere fermati,
tre che devono passare: la popolazione di controllo). Per ognuno si confronta
cio' che la RICEVUTA dice con cio' che il DB scrive, nella stessa esecuzione.

REGIME: store temporaneo con assert di isolamento, modello vero (FUORI pytest:
sotto pytest l'embedder e' lo stub SHA-256 e il giudizio non varrebbe), un
processo solo.

    HIPPO_DATA_DIR=$(mktemp -d) python docs/stato-reale/banchi/ws6-che-cosa-registra-quarantined-by.py

ESITO misurato il 2026-08-29: 7 dei 9 quarantinati scrivono `moat`, uno `L1`,
uno `gate`; i tre ammessi scrivono NULL. La regola «il db nomina la famiglia»
non regge: `moat` e `gate` sono categorie. Cio' che i dati sostengono e' che il
campo registra il PUNTO DEL PIPELINE che ha fermato la scrittura.
"""
import asyncio
import json
import sqlite3

from verimem.config import CONFIG

assert "Temp" in str(CONFIG.semantic_db) or "tmp" in str(CONFIG.semantic_db), (
    "NON ISOLATO - questo banco scrive, e senza HIPPO_DATA_DIR scriverebbe nello "
    "store vero. Fermo prima di toccarlo.")

from verimem import mcp_server  # noqa: E402  (dopo l'assert, di proposito)

CASI = [
    ("il valore non e' nella fonte", "Il magazzino contiene 999 pezzi.", "Il magazzino contiene 320 pezzi."),
    ("grandezza diversa", "La durata e' di 320 minuti.", "Il magazzino contiene 320 pezzi."),
    ("contraddetto apertamente", "La potenza e' di 850 kW.", "La potenza installata e' di 320 kW."),
    ("autoclaim senza prova", "Il sistema funziona correttamente.", "Il collaudo e' previsto per marzo."),
    ("autoclaim verificato", "Ho verificato che tutto e' a posto.", "Il collaudo e' previsto per marzo."),
    ("conclusione non nella fonte", "Il lavoro e' concluso.", "Il collaudo e' previsto per marzo."),
    ("numero da contare", "Ci sono tre sedi.", "Le sedi sono Verona, Trento e Bolzano."),
    ("negazione rovesciata", "Il collaudo e' stato superato.", "Il collaudo non e' stato superato."),
    ("data assente", "La consegna e' del 2027-01-15.", "La consegna e' prevista per gennaio."),
    ("CONTROLLO fatto vero", "Le sedi sono Verona, Trento e Bolzano.", "Le sedi sono Verona, Trento e Bolzano."),
    ("percentuale inventata", "Il tasso e' del 47%.", "Il tasso misurato e' del 12%."),
    ("relazione causale non detta", "Il ritardo e' causato dal maltempo.", "Il ritardo e' di tre giorni e il maltempo persiste."),
]


async def _chiama(nome, args):
    r = await mcp_server.call_tool(nome, args)
    if isinstance(r, list):
        return "".join(getattr(x, "text", str(x)) for x in r)
    return str(r)


async def main():
    visti = {}
    for i, (etichetta, claim, fonte) in enumerate(CASI):
        out = await _chiama("hippo_remember", {
            "proposition": claim, "topic": f"banco/livelli/caso{i:02d}", "source": fonte})
        try:
            d = json.loads(out)
        except ValueError:
            print(f"  [{etichetta}] risposta non JSON: {out[:120]}")
            continue
        visti[d.get("id")] = (etichetta, d.get("status"))

    con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
    c = con.cursor()
    print(f"\n{'caso':<30} {'status':<13} DB quarantined_by")
    print("-" * 66)
    for fid, (etichetta, status) in visti.items():
        riga = c.execute("SELECT quarantined_by FROM facts WHERE id=?", (fid,)).fetchone()
        print(f"{etichetta:<30} {str(status):<13} {(riga[0] if riga else '?') or '(NULL)'}")
    con.close()


if __name__ == "__main__":
    asyncio.run(main())
