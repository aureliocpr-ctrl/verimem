"""BISEZIONE: quale pezzo della fonte fa entrare lo scambio — smetto di congetturare.

Il dossier ⑬ elenca **14 ipotesi cadute** nel predire quali scambi entrano, e
W7-39 ha appena stabilito che **il verdetto e' ripetibile al bit** sul CE
locale: la variabile **e'** nel testo, e le congetture non l'hanno trovata.

⇒ Cambio metodo: invece di un'altra ipotesi, **una ricerca**. Il banco
`non-e-l-unita-e-la-fonte-intorno` aveva misurato che lo scambio «euro grandi»
si ferma sulla fonte NUDA (`72.1`) ed entra sulla RICCA (`100.0`). La differenza
fra le due sono **sei articoli**. Se ne basta **uno**, quello e' la variabile;
se servono tutti, la variabile e' la quantita' e non il contenuto.

DUE PASSATE, e la seconda e' quella che decide:
  ① CUMULATIVA — aggiungo gli articoli uno alla volta: dice DOVE si ribalta.
  ② SINGOLA    — ogni articolo da solo sulla NUDA: dice SE uno basta.
La cumulativa da sola non distingue «serve il 4°» da «servono quattro».

CONTROLLI CHE POSSONO FALLIRE:
 (1) la riproduzione: NUDA deve FERMARE e RICCA deve AMMETTERE. Se non si
     riproduce, il banco non ha oggetto e lo dico invece di misurare altro.
 (2) il claim VERO deve entrare su ENTRAMBE: se anche il vero si muove, non sto
     misurando lo scambio, sto misurando il gate che cambia umore.

    python -u docs/stato-reale/banchi/bisezione-quale-articolo-fa-entrare-lo-scambio.py
"""

from __future__ import annotations

import sys

NUDA = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)

AGGIUNTE = [
    ("Art. 9  acconto 34%",
     " Art. 9 - L'acconto alla stipula e' pari al 34% del corrispettivo."),
    ("Art. 11 saldo 61%",
     " Art. 11 - Il saldo alla consegna e' pari al 61% del corrispettivo."),
    ("Art. 13 diritti 16 euro",
     " Art. 13 - I diritti di segreteria ammontano a 16 euro."),
    ("Art. 15 spese 50 euro",
     " Art. 15 - Le spese di registrazione ammontano a 50 euro."),
    ("Art. 17 preavviso 8 giorni",
     " Art. 17 - Il preavviso per il recesso e' di 8 giorni."),
    ("Art. 19 contestazione 45 giorni",
     " Art. 19 - Il termine per la contestazione dei vizi e' di 45 giorni."),
]

SCAMBIO = "La cauzione definitiva e' pari a 148000 euro."   # 148000 e' dell'importo
VERO = "L'importo contrattuale e' di 148000 euro."


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    def giudica(claim, fonte):
        g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                                agent=None, source=fonte, ground_write=True)
        return (getattr(g, "grounding_score", None), getattr(g, "action", None))

    RICCA = NUDA + "".join(t for _n, t in AGGIUNTE)

    print("  -- CONTROLLO (1): il fenomeno si riproduce?")
    s_nuda, a_nuda = giudica(SCAMBIO, NUDA)
    s_ricca, a_ricca = giudica(SCAMBIO, RICCA)
    print(f"     SCAMBIO su NUDA  ({len(NUDA)} char): score={s_nuda}  action={a_nuda}")
    print(f"     SCAMBIO su RICCA ({len(RICCA)} char): score={s_ricca}  action={a_ricca}")
    if a_nuda == a_ricca:
        print("     CADUTO - stesso verdetto sulle due fonti: il fenomeno che")
        print("     questo banco cerca non c'e' piu' su questo codice. Lo dico")
        print("     invece di misurare qualcos'altro.")
        return 1
    print(f"     retto - il verdetto cambia: {a_nuda} -> {a_ricca}")

    print("\n  -- CONTROLLO (2): il claim VERO sta fermo su entrambe?")
    v_nuda = giudica(VERO, NUDA)
    v_ricca = giudica(VERO, RICCA)
    print(f"     VERO su NUDA : {v_nuda}")
    print(f"     VERO su RICCA: {v_ricca}")
    if v_nuda[1] != v_ricca[1]:
        print("     CADUTO - anche il VERO cambia verdetto: non sto isolando lo")
        print("     scambio, sto guardando il gate muoversi su tutto.")
        return 1
    print(f"     retto - il vero resta {v_nuda[1]} su entrambe")

    print("\n  == ① CUMULATIVA — aggiungo un articolo alla volta")
    fonte = NUDA
    ribalta_a = None
    for nome, testo in AGGIUNTE:
        fonte = fonte + testo
        s, a = giudica(SCAMBIO, fonte)
        marchio = "ENTRA" if a == "persist" else "ferma"
        print(f"     +{nome:<32} ({len(fonte):>4} char)  {marchio}  score={s:.1f}")
        if ribalta_a is None and a == "persist":
            ribalta_a = nome

    print("\n  == ② SINGOLA — ogni articolo DA SOLO sulla nuda")
    da_soli = []
    for nome, testo in AGGIUNTE:
        s, a = giudica(SCAMBIO, NUDA + testo)
        marchio = "ENTRA" if a == "persist" else "ferma"
        print(f"     NUDA +{nome:<32} ({len(NUDA + testo):>4} char)  {marchio}"
              f"  score={s:.1f}")
        if a == "persist":
            da_soli.append(nome)

    print("\n  == IL RISULTATO")
    # ⚠️ LA PRIMA VERSIONE DI QUESTO VERDETTO ERA SBAGLIATA, e l'errore e'
    # istruttivo: diceva «se qualcuno da solo basta ⇒ e' il CONTENUTO». Vale
    # solo se ne basta QUALCUNO. Se bastano TUTTI, il contenuto e' irrilevante
    # per costruzione — sei testi diversi che fanno la stessa cosa non possono
    # distinguersi per cio' che dicono.
    if len(da_soli) == len(AGGIUNTE):
        corti = [len(t) for _n, t in AGGIUNTE]
        print(f"     TUTTI E {len(AGGIUNTE)} BASTANO DA SOLI ⇒ NON e' il CONTENUTO.")
        print("     Sei articoli diversi — percentuali, euro piccoli, giorni —")
        print("     fanno la stessa identica cosa: quindi decide la QUANTITA'.")
        print(f"     ⇒ SOGLIA: bastano +{min(corti)} caratteri su una fonte di"
              f" {len(NUDA)}")
        print(f"       per portare lo scambio da {s_nuda:.1f} a oltre 99.")
    elif da_soli:
        print(f"     SOLO {len(da_soli)} SU {len(AGGIUNTE)} bastano: {da_soli}")
        print("     ⇒ QUESTA volta la variabile e' nel CONTENUTO, perche' gli")
        print("       altri, della stessa taglia, non bastano.")
    elif ribalta_a:
        print(f"     NESSUNO DA SOLO basta, e la cumulativa si ribalta a"
              f" «{ribalta_a}».")
        print("     ⇒ la variabile NON e' un pezzo: e' un ACCUMULO. Serve una")
        print("       quantita', e il contenuto dei singoli articoli non decide.")
    else:
        print("     NON SI RIBALTA nemmeno con tutti e sei: il fenomeno del")
        print("     banco originale non si riproduce con questi articoli, e")
        print("     l'unica cosa che posso dire e' questa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
