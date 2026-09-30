"""`1,5 x 10^3` e `1500` sono lo stesso numero, e il layer non lo sapeva.

IL DIFETTO, misurato prima della cura (banco
`docs/stato-reale/banchi/ws3-M5-T51-le-tre-classi-numeriche-non-misurate.py`):
sulla classe «notazione scientifica» il gate ferma **6 VERI su 6**, e in **3 casi
su 6** a fermarli e' `L4.1` **DA SOLO** mentre il giudice li approva::

    caso  grounding  layers
      8     89,91    ['L4.1']            <- il moat dice VERO, il layer trattiene
      9     99,37    ['L4.1']
     11     98,45    ['L4.1']

E' `withheld_despite_judge`: un fatto vero, che il giudice promuove a 99, fermato
perche' `_QUANT_RE` legge `1,5 x 10^3` come **tre numeri separati** — 1.5, 10 e 3
— e nessuno dei tre sta nella fonte che dice `1500`.

⚠️ MA IL PEZZO CHE DECIDE LA CURA E' L'ALTRA POPOLAZIONE: prima della cura il
claim FALSO `2,5 x 10^3` produce **gli stessi identici assenti** del vero
(`['2.5', '3', '10']` contro `['1.5', '3', '10']`). ⇒ Su questa classe il layer
oggi **non distingue il vero dal falso**: li segna assenti entrambi. Una cura che
si limitasse a togliere l'accusa al vero non aggiungerebbe capacita' di
distinguere — toglierebbe soltanto il controllo, ed e' l'errore che questo
stesso modulo ha gia' pagato una volta (riga 228: «i falsi negativi nascono
convertendo i veri positivi in silenzio»).

🔁 RIVERIFICATO SUL TRONCO, perche' questa cura e' rimasta diciassette
giorni fuori da `main` e un difetto non curato non resta fermo. Il modulo aveva
ancora lo stesso blob, e il banco ferma ancora **6 VERI su 6** nella condizione
`trasformata`, con la condizione di controllo `identica` a **0/6** - quindi e' la
notazione che li ferma e non altro. Dalla porta della CLI lo stesso caso esce
`quarantined layers=['L4.1'] grounding_score=85.0`: il giudice lo sostiene e il
layer lo trattiene da solo. La classe del separatore decimale, misurata insieme,
e' invece scesa a 0/6: quella l'ha curata qualcun altro nel frattempo.

Percio' le due celle qui sotto vanno lette insieme: la prima dice che il vero
entra, la seconda che il falso resta fuori. Se passasse solo la prima, la cura
sarebbe falsificata.
"""
from __future__ import annotations

from verimem.valore_non_nella_fonte import valori_non_nella_fonte

FONTE = "Il contatore ha registrato 1500 impulsi nella prova."


def test_il_vero_in_notazione_scientifica_non_e_piu_un_valore_assente():
    """`1,5 x 10^3` == 1500, che nella fonte c'e': nessun valore da accusare."""
    assenti = valori_non_nella_fonte(
        "Gli impulsi registrati sono 1,5 x 10^3.", FONTE)

    assert [v.come_scritto() for v in assenti] == [], (
        "il layer accusa un valore che nella fonte c'e', scritto in un'altra "
        "notazione: e' il caso withheld_despite_judge con grounding 89-99")


def test_il_falso_in_notazione_scientifica_resta_un_valore_assente():
    """LA POPOLAZIONE OPPOSTA, ed e' la cella che puo' falsificare la cura.

    `2,5 x 10^3` == 2500, che nella fonte NON c'e'. Se dopo la cura anche
    questo sparisce dagli assenti, non abbiamo insegnato al layer a leggere la
    notazione: gli abbiamo tolto il controllo.
    """
    assenti = valori_non_nella_fonte(
        "Gli impulsi registrati sono 2,5 x 10^3.", FONTE)

    scritti = [v.come_scritto() for v in assenti]
    assert scritti, (
        "il falso 2500 non viene piu' accusato: la cura ha spento il controllo "
        "invece di insegnargli la notazione")
    assert any("2500" in s or "2.5" in s or "2,5" in s for s in scritti), (
        f"il valore accusato non e' quello falso: {scritti}")


def test_la_potenza_intera_grande():
    """L'altra forma dello stesso banco: `6 x 10^4` == 60000 (caso 11 di T5.1),
    uno dei tre `withheld_despite_judge`."""
    assert [v.come_scritto() for v in valori_non_nella_fonte(
        "Le iterazioni del ciclo sono 6 x 10^4.",
        "Il ciclo ha eseguito 60000 iterazioni.")] == []


def test_l_esponente_negativo_NON_e_curato_e_il_motivo_sta_a_monte():
    """⚠️ IL LIMITE DELLA CURA, scritto come cella perche' non resti implicito.

    `4 x 10^-4` viene espanso correttamente in `0.0004` — l'espansione fa il suo
    lavoro. Ma il valore resta accusato lo stesso, e la causa **non e' in questo
    modulo**::

        extract_quantities("La cella misura 0,0004 metri di spessore.",
                           come_fonte=True)   ->   set()

    ⇒ Il parser **non estrae affatto** quel decimale dalla fonte: non c'e' nulla
    con cui confrontare il valore espanso. Nessuna canonicalizzazione qui puo'
    chiudere un buco che sta nell'estrazione.

    📌 Questa cella asserisce il comportamento di OGGI, difetto incluso. Se
    qualcuno curera' `extract_quantities`, diventera' ROSSA — ed e' il punto:
    un limite dichiarato in un commento si dimentica, un limite dichiarato in
    una cella si fa notare da solo.
    """
    from verimem.quantity_match import extract_quantities

    assert extract_quantities(
        "La cella misura 0,0004 metri di spessore.", come_fonte=True) == set(), (
        "il parser ora estrae il decimale dalla fonte: il buco a monte e' "
        "chiuso, e questa cella va riscritta insieme al caso 12 del banco T5.1")

    assert [v.come_scritto() for v in valori_non_nella_fonte(
        "Lo spessore della cella e' 4 x 10^-4 metri.",
        "La cella misura 0,0004 metri di spessore.")] == ["0.0004"], (
        "l'espansione ha prodotto un valore diverso da 0.0004, oppure il "
        "confronto con la fonte e' cambiato")
