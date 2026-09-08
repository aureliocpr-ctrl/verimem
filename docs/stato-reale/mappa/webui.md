# `verimem/webui/` — la trust console servita dal gateway

**1 file Python, 36 righe** · più gli asset statici (`admin.html`, `admin.js`,
`app.js`, `engine.css`, `vendor/`).

## Cosa fa

Impacchetta e serve gli **asset statici** della pagina `/ui` — quella che il suo
stesso docstring chiama *«the product's FACE»*: odometro, grafo navigabile con la
catena di custodia, registro dei claim fermati. Due funzioni sole:

| funzione | cosa fa |
|---|---|
| `asset(name)` | legge un file impacchettato, con `@cache` (gli asset sono immutabili a runtime) |
| `media_type(name)` | estensione → content-type, con `application/octet-stream` come ripiego |

Niente build, niente CDN, niente motore di template: **file dentro il wheel**. La
proprietà di sicurezza è dichiarata nel docstring — la pagina è *statica per
costruzione*, ogni numero arriva da una fetch autenticata del browser, e la
chiave bearer sta in `sessionStorage`.

## È raggiungibile dal prodotto? **SÌ**

```
  verimem/gateway.py:1636    from . import webui as _webui
  verimem/gateway.py:1650    body = _webui.asset(fname)
  verimem/gateway.py:1660-61 Response(content=_webui.asset(fname),
                                      media_type=_webui.media_type(fname), …)
  verimem/gateway.py:1663    @app.get("/ui")
  verimem/gateway.py:1641    Response(status_code=307, headers={"Location": "/ui"})
  pyproject.toml:222-231     "webui/*.html", "webui/*.js", "webui/*.css",
                             "webui/vendor/*.js", … nei package-data del wheel
```
⇒ È servito dalla rotta `/ui`, e gli asset entrano nel pacchetto.

## 🪞 E per poco non lo dichiaravo orfano

Il mio primo conteggio diceva **«`webui/__init__.py`: importato da 0 file»**, perché
cercava `from verimem.webui import`. Il gateway lo importa **in forma relativa**:
`from . import webui as _webui`. **Il contatore perdeva l'intera classe degli import
relativi**, che in un package è il modo normale di importare.

⚠️ **Conseguenza per il resto di questa mappa**: gli altri «importato da 0 file» del
primo giro — `hooks/__init__.py`, `teams/__init__.py` — vanno **riverificati con la
forma relativa** prima di chiamarli orfani. Un modulo dichiarato morto per un difetto
del righello è il danno peggiore che questa mappa possa fare.
