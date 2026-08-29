"""Il buco ha un identikit ma non un BORDO: dove scende sotto 80?

Misurato in `706de500`: un claim **irrilevante**, **senza numeri**, che il
giudice punteggia **sopra 80** non ha nessuno strato che lo fermi — sopra la
banda 40-80 non c'e' `L4-review`, senza numeri non c'e' `L4.1`, e il moat dice
`passed`. I due che entravano avevano **99,0** e **87,7**.

Ma «irrilevante» non e' un interruttore: e' un **gradiente**. Un claim puo'
parlare **dello stesso soggetto** e di un dettaglio che la fonte tace, oppure di
tutt'altro. **Quanto deve essere lontano perche' il punteggio scenda sotto 80 e
la banda lo raccolga?** Senza quel bordo il buco non e' dimensionabile, e la
riga di prosa che propongo resta vaga.

LA SCALA, cinque gradini, **stessa fonte** e distanza crescente:

    L1 PERTINENTE     la fonte lo dice          (controllo alto)
    L2 STESSO SOGG.   stesso soggetto, dettaglio che la fonte TACE
    L3 SOGG. + TEMA   stesso soggetto, tema lontano
    L4 AFFINE         soggetto diverso, dominio affine
    L5 ESTRANEO       nessun legame

LA PREDIZIONE, scritta prima di eseguire:
    · il punteggio **scende** lungo la scala (monotonia, tolleranza 1 inversione)
    · il **bordo degli 80** cade fra **L2 e L4** in tutte e tre le fonti

⚠️ **TRE FONTI, non una.** Ieri ho ritirato cinque verdetti costruiti su una
fonte sola. Un bordo misurato su una fonte e' un aneddoto con un decimale.

CONDIZIONE DI FALSIFICAZIONE: se la scala **non e' monotona**, o se il bordo
cade a gradini **diversi** nelle tre fonti, **non c'e' un bordo dimensionabile**
— e lo dico, invece di mediare tre numeri che non parlano della stessa cosa.

CONTROLLO CHE DEVE POTER FALLIRE: **L1 deve stare sopra 80 in tutte e tre**. Se
il gradino piu' pertinente non passa, la scala non misura la distanza: misura
una fonte scritta male.

🔴 **ESITO: PREDIZIONE FALSIFICATA, e il risultato vero sta nel controllo che
avevo aggiunto per curiosita'.**

    fonte        L1 pert  L2 stesso  L3 sogg+tema  L4 affine  L5 estraneo   bordo
    corso           99.4      98.7        95.0         0.2        0.4       L4
    fornitore       99.6      89.4        95.4         0.4       33.0       L4
    server          99.8      73.2         1.1         0.3        0.3       L2

**Controllo retto: L1 sopra 80 in 3 fonti su 3.**

**Il bordo cade a gradini NON adiacenti** — `L4` per due fonti, `L2` per la
terza — e la scala ha inversioni (1, 2, 1). ⇒ **NON c'e' un bordo dimensionabile
dalla distanza semantica**, e non medio tre numeri che non parlano della stessa
cosa.

🔑 **MA IL SALTO E' LA COSA VERA:**

    calo massimo fra due gradini consecutivi:  94,8  ·  95,0  ·  72,1 punti

⇒ **Non e' un gradiente: e' un PRECIPIZIO.** Il punteggio **non degrada** con la
distanza: sta a **90-99** e poi **crolla a 0-1**, e **dove** crolli dipende dalla
**fonte**, non dal gradino. E' la stessa **bimodalita'** gia' misurata sul corpus
in `897d0048` (91,73% sopra 95 · 5,46% sotto 40 · **1,08% in banda**): qui la si
vede nascere, caso per caso.

🔴 **E QUESTO RIDIMENSIONA UNA COSA BUONA CHE AVEVO DETTO IO** un'ora fa
(`706de500`): avevo scritto che **`L4-review`** — la banda 40-80 — «*fa il
lavoro*», perche' aveva raccolto due irrilevanti a **73,7** e **80,0**. Con la
bimodalita' davanti, quella lettura va corretta: **la banda raccoglie poco per
COSTRUZIONE**, perche' quasi nessun punteggio ci cade. Quei due casi erano
**fortunati**, non rappresentativi. ⇒ **La banda non e' un guardiano affidabile
per questa classe**: e' una rete tesa dove i pesci quasi non passano.
🔑 *Avevo trasformato due celle in un meccanismo. La distribuzione dice che erano
due celle.*

📌 **Cosa cambia nella proposta**: non posso dire «i claim oltre il gradino X
entrano» — la distanza semantica non predice nulla. Posso dire, e basta:
**quando il giudice sta alto sta MOLTO alto (>87), quindi sopra la banda, quindi
senza rete** — e non e' prevedibile quando accada.

REGIME: store TEMPORANEO, cross-encoder locale (nessuna API esterna). Lo store
di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-dove-sta-il-bordo-dell-irrilevante.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

SOGLIA = 80.0

#: (nome, fonte, [L1 pertinente, L2 stesso sogg., L3 sogg+tema, L4 affine,
#:  L5 estraneo])  — nessun claim contiene numeri: isola il moat da `L4.1`
SCALE: list[tuple[str, str, list[str]]] = [
    (
        "corso",
        "Il corso avanzato si tiene in aula e prevede una prova finale "
        "scritta, con frequenza obbligatoria.",
        [
            "Il corso avanzato prevede una prova finale scritta.",
            "Il corso avanzato e' tenuto da un docente universitario.",
            "Il corso avanzato e' finanziato dalla regione.",
            "La biblioteca comunale e' aperta il sabato mattina.",
            "Il vento di maestrale soffia da nord-ovest.",
        ],
    ),
    (
        "fornitore",
        "Il fornitore Bianchi consegna con corriere espresso e accetta resi "
        "entro il termine di legge, con imballaggio riciclabile.",
        [
            "Il fornitore Bianchi accetta resi entro il termine di legge.",
            "Il fornitore Bianchi ha sede in Veneto.",
            "Il fornitore Bianchi e' certificato per la qualita'.",
            "Il magazzino comunale chiude per inventario a gennaio.",
            "La cattedrale ha una facciata in marmo bianco.",
        ],
    ),
    (
        "server",
        "Il server alfa e' monitorato dal sistema interno, ha un contratto di "
        "assistenza attivo e viene sottoposto a manutenzione programmata.",
        [
            "Il server alfa ha un contratto di assistenza attivo.",
            "Il server alfa e' ospitato in un data center tedesco.",
            "Il server alfa e' stato acquistato in leasing.",
            "La rete aziendale usa un firewall perimetrale.",
            "Il pane raffermo si conserva in un sacchetto di carta.",
        ],
    ),
]

GRADINI = ("L1 pertinente ", "L2 stesso sogg", "L3 sogg+tema  ",
           "L4 affine     ", "L5 estraneo   ")


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print(f"  soglia sotto la quale la banda 40-80 puo' raccogliere: {SOGLIA}")
    mem = Memory(str(tmp / "bordo.db"))
    n = 0

    def punteggio(claim: str, fonte: str) -> tuple[float, bool]:
        nonlocal n
        n += 1
        r = mem.add(claim, topic=f"bd/{n}", source=fonte, validate="full")
        gs = r.get("grounding_score")
        return (-1.0 if gs is None else float(gs),
                str(r.get("status")) != "quarantined")

    righe: dict[str, list[float]] = {}
    bordi: dict[str, str] = {}
    print(f"\n  {'fonte':<12} " + " ".join(f"{g[:6]:>7}" for g in GRADINI)
          + "   bordo <80")
    print("  " + "-" * 66)
    for nome, fonte, claims in SCALE:
        gs_list = []
        entrati = []
        for claim in claims:
            gs, entra = punteggio(claim, fonte)
            gs_list.append(gs)
            entrati.append(entra)
        righe[nome] = gs_list
        sotto = [i for i, g in enumerate(gs_list) if g < SOGLIA]
        bordo = GRADINI[sotto[0]].strip() if sotto else "MAI"
        bordi[nome] = bordo
        print(f"  {nome:<12} " + " ".join(f"{g:>7.1f}" for g in gs_list)
              + f"   {bordo}")
        print(f"  {'':<12} " + " ".join(
            f"{('ENTRA' if e else 'ferm'):>7}" for e in entrati))

    # ── CONTROLLO ────────────────────────────────────────────────────────
    l1_ok = sum(1 for v in righe.values() if v[0] >= SOGLIA)
    print(f"\n  [1] CONTROLLO — L1 (pertinente) sopra {SOGLIA:.0f} in "
          f"{l1_ok}/{len(SCALE)} fonti")
    if l1_ok < len(SCALE):
        print("      CONTROLLO CADUTO: il gradino piu' pertinente non passa ⇒")
        print("      la scala non misura la distanza, misura una fonte scritta")
        print("      male. NESSUN VERDETTO.")
        return 1

    # ── MONOTONIA ────────────────────────────────────────────────────────
    print("\n  [2] LA SCALA E' MONOTONA? (inversioni per fonte)")
    inversioni = {}
    for nome, v in righe.items():
        # ⚠️ `zip(v, v[1:], strict=True)` esplode: le due liste hanno lunghezza
        # diversa per costruzione. `strict` va usato dove le lunghezze DEVONO
        # coincidere, non dove per definizione differiscono di uno.
        inv = sum(1 for a, b in zip(v[:-1], v[1:], strict=True) if b > a)
        inversioni[nome] = inv
        print(f"      {nome:<12} inversioni: {inv}/{len(v) - 1}")

    # ── IL SALTO: quanto e' ripido il passaggio sopra/sotto soglia ────────
    print("\n  [3] E' UN GRADIENTE O UN PRECIPIZIO? (salto massimo fra gradini)")
    salti = {}
    for nome, v in righe.items():
        cali = [a - b for a, b in zip(v[:-1], v[1:], strict=True)]
        salti[nome] = max(cali)
        print(f"      {nome:<12} calo massimo fra due gradini consecutivi: "
              f"{max(cali):.1f} punti")

    print("\n  ══ VERDETTO ══")
    distinti = sorted(set(bordi.values()))
    print("     bordo per fonte: "
          + " · ".join(f"{k}={v}" for k, v in bordi.items()))
    # ⚠️ CRITERIO CORRETTO: due bordi contano come «vicini» solo se ADIACENTI
    # sulla scala. Nella prima stesura bastava «al piu' due valori distinti»,
    # che avrebbe chiamato «tendenza» anche L2 contro L4 — cioe' i due estremi
    # della mia stessa predizione. Un criterio indulgente e' un criterio che
    # non puo' falsificare niente.
    idx = {g.strip(): i for i, g in enumerate(GRADINI)}
    posizioni = sorted(idx[b] for b in distinti if b in idx)
    adiacenti = (len(posizioni) <= 1
                 or (posizioni[-1] - posizioni[0]) <= 1)
    tante_inv = sum(1 for i in inversioni.values() if i > 1)
    if len(distinti) == 1 and tante_inv == 0:
        print("     PREDIZIONE RETTA: bordo NETTO e uguale in tutte e tre le")
        print(f"     fonti ({distinti[0]}), scala monotona ⇒ il buco e'")
        print("     DIMENSIONABILE: sotto quel gradino la banda lo raccoglie.")
    elif adiacenti and tante_inv <= 1:
        print("     PREDIZIONE PARZIALE: il bordo cade in due gradini ADIACENTI")
        print("     ⇒ c'e' una tendenza, non una soglia: «di solito», non")
        print("     «sempre».")
    else:
        print("     PREDIZIONE FALSIFICATA: il bordo cade a gradini NON")
        print(f"     adiacenti ({', '.join(distinti)}) e/o la scala non e'")
        print("     monotona ⇒ NON c'e' un bordo dimensionabile, e non medio")
        print("     tre numeri che non parlano della stessa cosa.")
        print("     🔑 Ma il [3] dice l'altra meta': il passaggio non e' un")
        print("        gradiente, e' un PRECIPIZIO. Il punteggio non degrada")
        print("        con la distanza: sta alto e poi crolla, e DOVE crolli")
        print("        dipende dalla fonte, non dal gradino.")

    print(f"\n  ⚠️ LIMITI: {n} celle, 3 fonti, 5 gradini, italiano, un giudice")
    print("     (cross-encoder locale). La scala e' la MIA idea di distanza:")
    print("     un altro avrebbe ordinato i gradini diversamente, e questo")
    print("     e' un confondente che non ho separato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
