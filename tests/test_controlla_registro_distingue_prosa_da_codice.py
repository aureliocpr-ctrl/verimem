"""Il controllo del registro blocca un'attribuzione e lascia passare un'omonimia.

Lo strumento serve a impedire che identificativi di lavoro interni escano col
pacchetto. Ha un solo modo di essere inutile e due modi di essere dannoso:

  inutile   non blocca niente — allora si può togliere
  dannoso   blocca su un'omonimia (``ws`` sta anche per *workspace*), e chi lo
            usa impara a ignorarlo
  dannoso   blocca su codice che nomina l'identificativo come VALORE, non come
            attribuzione: ``principal="cli:local/ws7"`` è un dato di prova

Il collaudo copre ENTRAMBE le popolazioni. Un test che guarda solo il caso
negativo non distingue «riconosce le attribuzioni» da «blocca sempre»: senza il
caso positivo, «non rilevato» non si distingue da «sensore spento».

registro-esente: gli identificativi qui sotto sono i dati di prova del controllo,
non attribuzioni. Senza questa dichiarazione il controllo boccia il file che
dimostra che funziona, e l'unico modo di far passare il rilascio sarebbe
cancellare la prova. Le righe restano contate e compaiono nel referto.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PRESIDIO = Path(__file__).resolve().parent.parent / "scripts" / "controlla_registro.py"


def _esegui(cartella: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(PRESIDIO), str(cartella)],
                          capture_output=True, text=True, errors="replace")


def test_lo_strumento_esiste_ed_e_eseguibile():
    """Prima di misurare cosa dice: dice qualcosa?"""
    assert PRESIDIO.is_file(), f"{PRESIDIO} non c'è"
    esito = _esegui(PRESIDIO.parent.parent / "tests")
    assert "artefatto:" in esito.stdout, esito.stdout[:400] + esito.stderr[:400]


def test_blocca_un_attribuzione_in_un_docstring(tmp_path: Path):
    """Il caso per cui lo strumento esiste: un nome di sessione in prosa."""
    (tmp_path / "modulo.py").write_text(
        '"""Il difetto è stato misurato da ws4 il primo del mese."""\n'
        "VALORE = 1\n", encoding="utf-8")
    esito = _esegui(tmp_path)
    assert esito.returncode == 1, (
        "un'attribuzione in un docstring deve bloccare il rilascio\n"
        + esito.stdout[-600:])
    assert "identificativo di sessione" in esito.stdout


def test_blocca_un_attribuzione_in_un_commento(tmp_path: Path):
    (tmp_path / "modulo.py").write_text(
        "# ws3 ha isolato la causa con un A/B\nVALORE = 2\n", encoding="utf-8")
    assert _esegui(tmp_path).returncode == 1


def test_non_blocca_un_omonimia_nel_codice(tmp_path: Path):
    """``ws`` sta anche per *workspace*: un veto qui insegna a ignorare il controllo.

    È il caso che ha motivato la cura dello strumento — la prima versione
    bloccava, e su un artefatto pubblicato avrebbe dato un falso allarme.
    """
    (tmp_path / "test_qualcosa.py").write_text(
        "def test_percorsi(tmp_path):\n"
        '    ws = tmp_path / "ws1"\n'
        "    ws.mkdir()\n"
        "    assert ws.is_dir()\n", encoding="utf-8")
    esito = _esegui(tmp_path)
    assert esito.returncode == 0, (
        "un'omonimia fuori dalla prosa NON deve bloccare\n" + esito.stdout[-600:])


def test_non_blocca_un_identificativo_usato_come_valore(tmp_path: Path):
    """``principal="cli:local/ws7"`` è un dato di prova, non un'attribuzione."""
    (tmp_path / "test_attore.py").write_text(
        "def test_principal(store):\n"
        '    store.supersede(a, b, principal="cli:local/ws7", reason="b")\n',
        encoding="utf-8")
    assert _esegui(tmp_path).returncode == 0


#: I file di prova. Composti in pezzi perché la riga finita non esista qui come
#: attribuzione vera.
#:
#: Devono essere **un docstring solo**: due stringhe consecutive fanno di quella
#: dopo un'espressione isolata, che il controllo — giustamente — non tratta come
#: prosa. Scritte separate, i due casi qui sotto passavano entrambi per la strada
#: sbagliata e il collaudo misurava un'altra cosa senza dirlo.
_ATTRIBUZIONE = "Il difetto è stato misurato da " + "ws4" + " il primo del mese."
_CON_DICHIARAZIONE = (
    '"""registro-esente: dati di prova, non attribuzioni.\n\n'
    + _ATTRIBUZIONE + '"""\nVALORE = 1\n')
_SENZA_DICHIARAZIONE = '"""' + _ATTRIBUZIONE + '"""\nVALORE = 1\n'


def test_un_collaudo_che_dichiara_i_propri_dati_di_prova_passa(tmp_path: Path):
    """Senza questa uscita il controllo boccia il file che dimostra che funziona.

    E l'unico modo di far passare il rilascio sarebbe cancellare quella prova:
    un veto che punisce il proprio collaudo si fa disattivare, non correggere.
    """
    (tmp_path / "test_finto.py").write_text(_CON_DICHIARAZIONE, encoding="utf-8")
    esito = _esegui(tmp_path)
    assert esito.returncode == 0, esito.stdout[-600:]
    assert "esentate" in esito.stdout, (
        "l'esenzione non compare nel referto: un'esenzione silenziosa fa "
        "apparire pulito ciò che non lo è, ed è il difetto contro cui il "
        "controllo esiste\n" + esito.stdout[-600:])


def test_la_dichiarazione_non_vale_per_un_modulo_del_prodotto(tmp_path: Path):
    """L'uscita non è un buco: solo un collaudo può dichiararsi."""
    (tmp_path / "modulo.py").write_text(_CON_DICHIARAZIONE, encoding="utf-8")
    assert _esegui(tmp_path).returncode == 1, (
        "un modulo del prodotto si è esentato da solo: basterebbe scrivere la "
        "dichiarazione per far passare qualsiasi cosa")


def test_senza_dichiarazione_un_collaudo_blocca_come_gli_altri(tmp_path: Path):
    """E il marcatore deve servire davvero: senza, niente esenzione."""
    (tmp_path / "test_finto.py").write_text(_SENZA_DICHIARAZIONE, encoding="utf-8")
    assert _esegui(tmp_path).returncode == 1, (
        "l'esenzione è stata concessa senza che il file la dichiarasse: allora "
        "vale per tutti i collaudi, e il controllo non copre più la cartella "
        "che l'artefatto sorgente imbarca")


def _archivio_con(tmp_path: Path, nome_interno: str, sorgente: Path | str) -> Path:
    """Un ``.tar.gz`` che contiene un solo file, sotto il nome dato."""
    import tarfile

    percorso = tmp_path / "pacchetto.tar.gz"
    if isinstance(sorgente, str):
        vero = tmp_path / "contenuto.py"
        vero.write_text(sorgente, encoding="utf-8")
    else:
        vero = sorgente
    with tarfile.open(percorso, "w:gz") as archivio:
        archivio.add(vero, arcname=nome_interno)
    return percorso


def test_il_controllo_dentro_un_archivio_non_accusa_se_stesso(tmp_path: Path):
    """Il difetto è latente finché ``scripts/`` non entra nel sorgente distribuito.

    Puntato a una directory il controllo si esclude confrontando il percorso.
    Dentro un archivio quel confronto non ha nulla da confrontare — la voce del
    tar non è un percorso sul disco — e il file si troverebbe addosso la propria
    lista, bocciando il rilascio a causa di sé stesso.
    """
    archivio = _archivio_con(tmp_path, "verimem-1.0/scripts/controlla_registro.py",
                             PRESIDIO)
    esito = subprocess.run([sys.executable, str(PRESIDIO), str(archivio)],
                           capture_output=True, text=True, errors="replace")
    assert esito.returncode == 0, (
        "il controllo boccia se stesso quando viene letto dentro un archivio\n"
        + esito.stdout[-700:])
    assert "esentate" in esito.stdout, (
        "l'esenzione non compare nel referto: dichiararla è la differenza fra "
        "un'eccezione e un buco\n" + esito.stdout[-700:])


def test_un_omonimo_senza_la_lista_non_puo_approfittarne(tmp_path: Path):
    """Il riconoscimento non è il nome del file: chiunque potrebbe chiamarsi così."""
    archivio = _archivio_con(
        tmp_path, "pacchetto/scripts/controlla_registro.py",
        '"""Un omonimo qualsiasi."""\n' + "# " + _ATTRIBUZIONE + "\nX = 1\n")
    esito = subprocess.run([sys.executable, str(PRESIDIO), str(archivio)],
                           capture_output=True, text=True, errors="replace")
    assert esito.returncode == 1, (
        "un file che si chiama come il controllo si è esentato da solo: basterebbe "
        "il nome per far passare qualsiasi cosa\n" + esito.stdout[-700:])


def test_un_file_pulito_passa(tmp_path: Path):
    """Il controllo negativo del controllo negativo: senza niente, non inventa."""
    (tmp_path / "pulito.py").write_text(
        '"""Un modulo che non nomina nessuno."""\n\n\ndef somma(a, b):\n'
        "    return a + b\n", encoding="utf-8")
    esito = _esegui(tmp_path)
    assert esito.returncode == 0
    assert "Nessun identificativo di sessione" in esito.stdout
