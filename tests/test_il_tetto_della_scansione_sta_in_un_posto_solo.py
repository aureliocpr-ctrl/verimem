"""Il tetto della scansione è scritto 34 volte a mano dentro `mcp_server.py`.

Dopo la PR del tetto dichiarato, `_SCAN_CAP` esiste e porta con sé la ragione
(«`list_facts` ordina `created_at DESC`, quindi il tetto taglia i più VECCHI»).
Ma il letterale `10000` restava battuto a mano in **34** punti, su **30 tool**::

    letterali limit=10000 in mcp_server.py: 34
    tool coinvolti: 30
    di cui  list_facts: 22   memory.all: 12

⇒ È la classe «una copia invece della superficie unica», la stessa che ha reso
necessario T49: là la cura giusta esisteva dal 20 luglio **in 1 chiamante su
38** e non si era propagata. Un tetto scritto 34 volte è una decisione presa 34
volte, e il quarantesimo chiamante nascerà col suo numero a mano.

📌 CHE COSA PRESIDIA QUESTO FILE, e cosa no. Presidia che il **valore** stia in
un posto solo — non che ogni tool lo dichiari nel proprio payload. La
dichiarazione (`n_scanned`/`n_total`) è nella PR del tetto per la porta
dell'export, e per le altre 35 resta un ticket aperto: **questo cricchetto
tiene fermo il numero mentre quel lavoro procede**.

⚠️ E IL TETTO NON RIGUARDA SOLO I FATTI: 12 delle 34 chiamate sono
`memory.all(limit=10000)` sugli EPISODI. Sul corpus di casa gli episodi sono
494, quindi oggi quel tetto non morde — ma è lo stesso taglio silenzioso, e
quando morderà nessuno lo saprà. Il numero da guardare è nel journal, non qui.

🔒 CRICCHETTO, non un divieto assoluto: se un chiamante nuovo ha davvero
bisogno di un tetto diverso, lo passa come parametro con la sua ragione — il
test cade solo sul letterale battuto a mano.

📌 Non duplica i cricchetti di @ws8 (PR #14, R2/R3/R6: copie, moduli senza
chiamante, righe per PR): quelli contano nomi ripetuti e moduli, questo tiene
un valore di configurazione.
"""

from __future__ import annotations

import pathlib
import re

#: Il file dove il tetto era battuto a mano. Gli altri (client.py,
#: self_curation.py, session_recap.py, memory.py) hanno ciascuno il proprio
#: contesto e non passano da `_SCAN_CAP`: sono fuori dal perimetro di questa
#: PR e restano dichiarati qui perché chi legge non li creda coperti.
SORVEGLIATO = pathlib.Path(__file__).resolve().parents[1] / "verimem" / "mcp_server.py"

LETTERALE = re.compile(r"limit\s*=\s*10_?000\b")


def test_nessun_tetto_battuto_a_mano_nel_server() -> None:
    """IL CUORE: zero letterali; il tetto si legge da `_SCAN_CAP`."""
    testo = SORVEGLIATO.read_text(encoding="utf-8")
    colpevoli = [
        (i, r.strip()[:70])
        for i, r in enumerate(testo.split("\n"), 1)
        if LETTERALE.search(r)
    ]
    assert not colpevoli, (
        f"{len(colpevoli)} tetti battuti a mano invece di `_SCAN_CAP`: "
        f"{colpevoli[:5]}")


def test_la_costante_esiste_e_porta_la_sua_ragione() -> None:
    """⚠️ IL CONTROLLO POSITIVO: se `_SCAN_CAP` sparisse o diventasse un numero
    nudo senza il commento che dice PERCHÉ, il test sopra passerebbe lo stesso
    — zero letterali `limit=10000` — e questo file starebbe sorvegliando il
    nulla. Il commento non è ornamentale: senza, il prossimo lettore prende il
    tetto per un dettaglio di prestazione e lo alza o lo abbassa a caso."""
    testo = SORVEGLIATO.read_text(encoding="utf-8")
    assert "_SCAN_CAP = int(" in testo, "la costante non c'è più"
    assert "created_at DESC" in testo, (
        "la ragione del tetto (taglia i più VECCHI) non è più scritta accanto "
        "alla costante")
    assert testo.count("limit=_SCAN_CAP") >= 34, (
        f"solo {testo.count('limit=_SCAN_CAP')} chiamate usano la costante: "
        "lo sweep non copre più i 34 punti di partenza")
