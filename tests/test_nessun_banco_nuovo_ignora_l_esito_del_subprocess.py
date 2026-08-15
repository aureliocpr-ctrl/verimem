"""Il cricchetto sulla classe «`subprocess.run` e l'esito non lo guarda nessuno».

STORIA, perché il numero è il punto:

- 2026-08-14 — `test_la_ricevuta_non_diceva_quale_cifra_mancava.py` era rosso in
  CI e verde in locale, senza causa da un giorno. Il banco leggeva
  ``(stdout or "") + (stderr or "")`` e **non guardava il `returncode`**: un
  processo morto lasciava un output tronco e ogni assert riferiva «manca la
  stringa X» invece di «il processo è morto». Curato in `76d18180`.
- Lo stesso giorno ws3 aveva curato la stessa forma su un altro file.
- **Due per caso in un giorno.** ws8 ha fatto lo sweep: **13 file su 44**.
  Rimisurato con un righello indipendente: stesso 44, stesso 13, stessa lista
  nome per nome.

🔑 **IL CAMPIONE CASUALE SOTTOSTIMAVA DI SEI VOLTE**, e questo è il motivo per
cui questo file esiste: curare tredici file lascia libero il posto per il
quattordicesimo, e fra un mese nessuno rifarà quel `grep`. **Un cricchetto sì.**

⚠️ **POI IL RIGHELLO È STATO CAMBIATO, E IL NUMERO È RIMASTO 13 CAMBIANDO TRE
NOMI IN ENTRAMBE LE DIREZIONI** — è il dato più istruttivo di tutta la vicenda:

- **tre erano di troppo**: la sequenza ``subprocess.run(`` compariva come DATO,
  non come chiamata (in ``test_mcp_server_security.py`` sta dentro
  ``_looks_shell_like("subprocess.run('id')")``) — e quel file era uno dei due
  indicati come prioritari *«dove il silenzio costa di più»*;
- **tre mancavano**: il `grep` cercava una sola forma, e ``subprocess.Popen``,
  ``check_output`` e ``call`` sono altrettanto ciechi — fra i tre entrati ci
  sono ``test_crash_injection_g3.py`` e ``test_mcp_stdout_purity_g2.py``.

🪞 **Due misure indipendenti che concordano sul TOTALE possono sbagliare gli
elementi**, e nessuna delle due se ne accorge: la conferma incrociata ha
confermato il numero, non l'insieme. ⇒ **su una lista, si confrontano i NOMI.**
(Stessa forma del diff dei nomi dei test rossi, che qui non avevamo applicato
alla lista dei file.)

⚖️ **POI ws8 HA TROVATO IL TERZO GENERE DI ERRORE, ed è quello che decide cosa
questo file può affermare: un banco può guardare l'esito IN UN ALTRO MODO.**
``test_crash_injection_g3.py`` non nomina il `returncode` e non è cieco: verifica
**per comportamento** — quanti ack sono arrivati, quante scritture sono atterrate
— con due guardie sulle popolazioni opposte (*«worker died before reaching the
kill point»* e *«worker completed the burst; nothing was injected»*). In un test
di crash injection quella forma è **più forte** del codice d'uscita, perché lì il
processo *deve* morire e il codice non distingue «ucciso come volevo» da «morto
all'avvio».

⇒ **PERCIÒ QUESTA LISTA NON DICE «FILE DIFETTOSI», DICE «FILE CHE NON DICHIARANO
COME GUARDANO L'ESITO»**, e il cricchetto chiede di *esaminarli*, non di curarli.
La distinzione non è cortesia: un presidio che grida al lupo su banchi corretti
viene spento, e un presidio spento è peggio di uno assente — nessuno sa che manca.

⚖️ PERCHÉ NON `check=True` OVUNQUE: in molti di questi banchi il processo *deve*
poter fallire, ed è il fallimento il dato. La forma che regge è leggere il
`returncode` e **metterlo nel messaggio d'errore**, così un processo morto si
distingue da un assert caduto. Il lettore condiviso di `tests/_esito.py` la
implementa una volta sola — tredici copie della stessa lettura divergerebbero,
e la prima a divergere sarebbe quella che nessuno rilegge.

⚠️ LIMITE DICHIARATO, e va letto prima di fidarsi del verdetto: **l'avvio del
processo si riconosce sull'albero, la lettura dell'esito ancora sul testo**, e
quest'ultima è **per FILE, non per chiamata**. Un file che legge il `returncode`
in una funzione e lo ignora in un'altra qui risulta a posto.
La dissimmetria è voluta: sbagliare per prudenza sulla *lettura* costa un falso
allarme che si legge e si chiude, mentre sbagliare sull'*avvio* costava una
lista che manda a curare il file sbagliato — ed è successo. Chi raffina anche
la seconda metà, aggiorni questa riga.
"""
from __future__ import annotations

import ast
import pathlib

TESTS = pathlib.Path(__file__).resolve().parent

# I tredici del 2026-08-14, misurati. La lista **si accorcia e non si allunga**:
# è tutto il senso del cricchetto. Chi cura un file lo toglie da qui — e se se
# ne dimentica, il secondo test qui sotto glielo ricorda.
ANCORA_CIECHI = frozenset({
    # perf/bench_briefing_proactive.py e _v2.py — CURATI il 15/08, e qui il
    # silenzio costava una cosa DIVERSA dagli altri: su un banco di LATENZA un
    # processo morto non sembra rotto, **sembra veloce**.
    # Misurato puntando `HOOK_PATH` a uno script che scrive un `ImportError` su
    # stderr ed esce 1, con l'uscita dirottata e `_clear_session_state`
    # disinnescata (nessun file vivo toccato)::
    #
    #     hook MORTO   latency_p50_ms 177.9 · false_positive_chitchat_count 0
    #     hook VERO    latency_p50_ms 512.8 · false_positive_chitchat_count 0
    #
    # ⇒ Il guasto totale si sarebbe letto come un **miglioramento di latenza
    # del 65%**, accanto a una metrica di qualita' a ZERO che si legge come
    # perfetta. Otto numeri, due lusinghieri, **nessuno che dica che l'hook non
    # e' mai partito**. E la diagnosi non mancava: `capture_output=True` aveva
    # gia' catturato l'`ImportError`, ma la funzione rendeva solo `proc.stdout`.
    # 🔑 La cura NON e' `check=True` (ucciderebbe il giro al primo prompt): la
    # funzione RENDE l'esito, le latenze dei morti non entrano nelle percentili
    # — includerle abbassa il p50, cioe' il guasto MIGLIORA il numero — e il
    # referto porta in cima `measurement_valid` e `prompts_with_a_dead_hook`.
    # Le latenze diventano `None` e non `0.0` quando non c'e' nessun campione
    # valido: uno zero si legge come un risultato straordinario, non come una
    # misura assente. Verificato su ENTRAMBE le popolazioni (morto -> non
    # valido; hook vero -> valido, 20 campioni, p50 512.8 e 526.5).
    "perf/bench_self_model_ab.py",
    # test_crash_injection_g3.py — trovato dall'albero (il grep non lo vedeva:
    # usa `Popen`, non `run`) e CURATO il 14/08. Lì `check=True` sarebbe stato
    # sbagliato — il processo viene ucciso di proposito — e il difetto era
    # `stderr=DEVNULL`, che scartava il motivo quando il worker moriva PRIMA
    # del kill: su un banco di crash injection, lo scambio peggiore possibile.

    # ESAMINATO 15/08 — REGGE: assert su una stringa POSITIVA attesa
    # («DONE RuntimeError») e il messaggio porta stdout E stderr. Processo
    # morto -> stdout vuoto -> l'assert scatta, col perche' sotto gli occhi.
    "test_embedding_load_no_hang.py",

    # ESAMINATO 15/08 — REGGE: costruisce `_uscita = (stdout or "") + (stderr
    # or "")` e lo passa come MESSAGGIO all'assert su una stringa positiva
    # attesa. Processo morto -> stdout vuota -> l'assert scatta, con entrambi i
    # canali sotto gli occhi. E dichiara gia' la trappola del `None` al posto
    # della stringa vuota, che altrove e' costata un `TypeError`.
    "test_flow_surface_onesta.py",
    # I due banchi delle PROMESSE DEL README — curati il 14/08, e non erano
    # solo ciechi: se la sonda non rispondeva facevano `pytest.skip`, cioè
    # **si spegnevano da soli quando cadeva la promessa che verificano**.
    # Saltare è legittimo quando NON SI PUÒ misurare (docker assente, modello
    # non in cache); non quando il soggetto misurato ha fallito.

    # ESAMINATO 15/08 — REGGE: l'helper rende `stdout + stderr` e gli assert
    # cercano marcatori POSITIVI. Se il processo muore, `out` e' vuoto, l'assert
    # scatta — e il traceback e' gia' dentro `out`, quindi la diagnosi compare
    # nel messaggio senza doverla aggiungere.
    "test_log_level_env.py",
    # test_mcp_e2e_smoke.py — CURATO il 15/08, e il difetto era il piu' subdolo
    # della famiglia: il secondo dei due test iterava su `stdout.splitlines()`
    # senza verificare che ci FOSSE stdout. Server morto -> zero righe -> il
    # ciclo non gira -> «ogni riga e' JSON valido» risulta vero perche' non
    # c'e' nessuna riga. Un verde che non ha guardato niente, su un banco che
    # prova la purezza del protocollo MCP, cioe' la superficie del cliente.
    # 📌 Il gemello nello STESSO FILE (r.105) il controllo ce l'aveva gia', e
    # dichiarava pure perche' non guarda il returncode: la stessa cura entrata
    # in una chiamata e non nell'altra, a venti righe di distanza.
    # test_mcp_stdout_purity_g2.py — CURATO il 14/08. Tolto da qui *perché me
    # l'ha detto il test qui sotto*: l'avevo curato e dimenticato in lista, e
    # `test_il_cricchetto_non_si_arrugginisce` è diventato rosso nominandolo.
    # È la metà del meccanismo che di solito manca, e si è dimostrata da sola.
    # test_provenance_commit_ref_format.py — ESAMINATO il 15/08 e REGGEVA gia':
    # guarda l'esito PER COMPORTAMENTO (se `git` fallisce lo SHA e' vuoto e
    # l'`assert sha` scatta), come crash_injection_g3. Aggiunto solo il PERCHE'
    # nel messaggio: senza `stderr`, un `git` che fallisce per una ragione
    # strana si legge «no HEAD sha» e basta.
    # 🪞 E la prima versione di quell'aggiunta RENDEVA una stringa di diagnosi
    # (`f"__git_muto__ rc=…"`), che e' TRUTHY: avrebbe spento l'`assert sha`
    # che stavo arricchendo. Misurato a confronto sulle tre forme — vecchia:
    # assert scatta · quella rotta: NON scatta · curata: rosso col perche'.
    # ⇒ **Un valore di ripiego dentro una funzione il cui risultato viene
    # testato per verita' e' un modo silenzioso di disattivare un controllo.**

    # ESAMINATO 15/08 — REGGE, e per una ragione diversa dalle altre: qui il
    # subprocess e' STRUMENTALE, serve solo a fabbricare un pid morto. Il
    # soggetto misurato e' `_pid_alive`, non il processo. Un attrezzo che non
    # parte solleva da `Popen`; non c'e' un esito da leggere.
    "test_ram_footprint.py",             # ⬅ idem
})

# `esito(` e' il lettore condiviso di tests/_esito.py: chi lo usa sta leggendo
# il returncode per costruzione, ed e' la forma che vogliamo diffondere.
_SEGNI_DI_LETTURA = ("returncode", "check=True", "check_returncode", "esito(")


def _avvia_processi(albero: ast.AST) -> bool:
    """Vero se il file CHIAMA davvero `subprocess.run` (o le sue sorelle).

    ⚠️ SULL'ALBERO E NON SUL TESTO, e non è pedanteria: cercare la stringa
    ``subprocess.run(`` dava **tre falsi positivi su tredici**, perché la stessa
    sequenza compare come DATO — in `test_mcp_server_security.py` sta dentro
    ``_looks_shell_like("subprocess.run('id')")``, cioè è l'input di un test
    sulla sicurezza, non una chiamata. E quel file era uno dei due indicati
    come prioritari *«dove il silenzio costa di più»*: la lista mandava a
    curare un banco che non ha il difetto.
    🪞 Il difetto era nel MISURATORE, non nel misurato — e in questo stesso
    file: il rilevatore testuale trovava sé stesso, e restava zitto solo
    perché la parola «returncode» compare qui sotto come dato. Per fortuna,
    non per progetto.
    """
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        if not isinstance(f, ast.Attribute):
            continue
        if f.attr not in ("run", "Popen", "check_output", "call"):
            continue
        if isinstance(f.value, ast.Name) and f.value.id == "subprocess":
            return True
        if isinstance(f.value, ast.Attribute) and f.value.attr == "subprocess":
            return True
    return False


def _ciechi() -> set[str]:
    """I file di tests/ che avviano un processo e non ne guardano l'uscita."""
    trovati = set()
    for f in sorted(TESTS.rglob("*.py")):
        testo = f.read_text(encoding="utf-8", errors="replace")
        if "subprocess" not in testo:          # scarto a buon mercato
            continue
        try:
            albero = ast.parse(testo)
        except SyntaxError:                     # un file rotto non è cieco:
            continue                            # è un altro problema, e si vede
        if not _avvia_processi(albero):
            continue
        # ⚠️ La LETTURA resta testuale, e il limite è dichiarato in cima: qui
        # sbagliare per eccesso di prudenza costa un falso allarme, mentre
        # sull'altro lato (trovare chiamate che non ci sono) costava una lista
        # che manda a curare il file sbagliato.
        if not any(s in testo for s in _SEGNI_DI_LETTURA):
            trovati.add(f.relative_to(TESTS).as_posix())
    return trovati


def test_nessun_banco_NUOVO_ignora_l_esito_del_subprocess():
    """La direzione che conta: il quattordicesimo non deve entrare senza essere
    stato guardato."""
    nuovi = _ciechi() - ANCORA_CIECHI
    assert not nuovi, (
        "questi banchi avviano un processo e non dichiarano come ne guardano "
        "l'esito:\n  " + "\n  ".join(sorted(nuovi))
        + "\n\nGUARDALI — non e' detto che siano rotti. Un processo ucciso "
          "lascia un output TRONCO e ogni assert riferisce «manca la stringa "
          "X» invece di «il processo e' morto»; in CI il messaggio viene anche "
          "troncato e la causa sparisce. Ma un banco puo' anche verificare "
          "l'esito PER COMPORTAMENTO (quanti ack, quante scritture atterrate), "
          "e in un test di crash injection quella forma e' PIU' forte del "
          "codice d'uscita.\n"
          "Se e' cieco: `from tests._esito import esito`. Non `check=True` — "
          "in molti banchi il fallimento E' il dato.\n"
          "Se guarda per comportamento: aggiungilo ad ANCORA_CIECHI con una "
          "riga che dice COME, cosi' il prossimo non rifa' questa verifica."
    )


def test_il_cricchetto_non_si_arrugginisce():
    """⚠️ L'ALTRA META', quella che di solito manca — e senza, il cricchetto
    smette di stringere in silenzio.

    Se un file viene curato e resta scritto qui, la lista non descrive piu' il
    mondo: continua a *permettere* un file che ormai e' a posto, e nessuno se
    ne accorge perche' il primo test resta verde. E' la stessa classe del
    documento con il ✅ scaduto — un elenco che assolve piu' di quanto dovrebbe.
    """
    curati = ANCORA_CIECHI - _ciechi()
    assert not curati, (
        "questi banchi sono stati CURATI ma sono ancora nella lista dei "
        "tollerati:\n  " + "\n  ".join(sorted(curati))
        + "\n\nToglili da ANCORA_CIECHI: finche' restano, il cricchetto "
          "tollera un difetto che non esiste piu' e smette di stringere."
    )


def test_il_rilevatore_vede_davvero_la_forma_cieca(tmp_path, monkeypatch):
    """🔑 IL GUARDIANO DEL GUARDIANO: un rilevatore che non trova mai niente
    darebbe verde a tutti e due i test qui sopra per sempre.

    Criterio di casa: «acceso = c'e' un test che diventa ROSSO se lo spegni».
    Qui lo si verifica dal basso — si costruiscono i due casi e si pretende che
    li distingua.
    """
    # ⚠️ `sys.modules[__name__]` e non un `import` per nome: il file si importa
    # come `tests.test_…` e il nome nudo non esiste. Sbagliarlo qui costerebbe
    # un `ModuleNotFoundError` che sembra un difetto del rilevatore.
    import sys
    mod = sys.modules[__name__]

    (tmp_path / "test_cieco.py").write_text(
        "import subprocess\n"
        "def test_x():\n"
        "    r = subprocess.run(['echo'], capture_output=True)\n"
        "    assert 'ok' in r.stdout\n", encoding="utf-8")
    (tmp_path / "test_vedente.py").write_text(
        "import subprocess\n"
        "def test_y():\n"
        "    r = subprocess.run(['echo'], capture_output=True)\n"
        "    assert r.returncode == 0\n", encoding="utf-8")
    (tmp_path / "test_senza_processi.py").write_text(
        "def test_z():\n    assert True\n", encoding="utf-8")

    monkeypatch.setattr(mod, "TESTS", tmp_path)
    visti = mod._ciechi()
    assert visti == {"test_cieco.py"}, visti
