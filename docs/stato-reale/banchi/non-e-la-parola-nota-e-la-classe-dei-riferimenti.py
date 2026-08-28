# -*- coding: utf-8 -*-
"""LA CAUSA di B, misurata: e' la lista _RIFERIMENTO_RE o la parola 'nota'?

Se la causa e' la lista, ALTRE parole della stessa lista devono accecare allo
stesso modo, e parole fuori dalla lista no. Controllo che puo' fallire: se
'pagina' e 'art' NON accecano, la mia attribuzione a _RIFERIMENTO_RE cade.
"""
from verimem.quantity_match import extract_quantities
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

CLAIM = "Con soglia 0.40 i cluster sono 1."
RIGA = "    0.40         1         431           0"

# nella lista _RIFERIMENTO_RE (quantity_match.py:1071-1079)
DENTRO = ["nota", "note", "pagina", "art", "comma", "tabella", "riga", "figura"]
# fuori dalla lista
FUORI = ["alfa", "beta", "soglia", "misura", "gamma"]

print("  claim:", repr(CLAIM))
print("  fonte: '<PAROLA>\n' + la riga di dati\n")


def prova(parola):
    fonte = "  " + parola + "\n" + RIGA
    assenti = valori_non_nella_fonte(CLAIM, fonte)
    cieco = any(abs(float(getattr(a, "valore", 0.0)) - 0.40) < 1e-9 for a in assenti)
    try:
        q = extract_quantities(fonte, come_fonte=True)
    except TypeError:
        q = extract_quantities(fonte)
    return cieco, sorted({v for _u, v in q})


print("  == parole DENTRO la lista _RIFERIMENTO_RE")
dentro_ciechi = 0
for p in DENTRO:
    c, nums = prova(p)
    dentro_ciechi += 1 if c else 0
    print(f"     {p:<10} {'ACCECA ' if c else 'trova  '}  fonte estrae -> {nums}")

print("\n  == parole FUORI dalla lista")
fuori_ciechi = 0
for p in FUORI:
    c, nums = prova(p)
    fuori_ciechi += 1 if c else 0
    print(f"     {p:<10} {'ACCECA ' if c else 'trova  '}  fonte estrae -> {nums}")

print(f"\n  dentro: {dentro_ciechi}/{len(DENTRO)} accecano"
      f"   ·   fuori: {fuori_ciechi}/{len(FUORI)} accecano")
print("\n  -- CONTROLLO: l'attribuzione a _RIFERIMENTO_RE regge?")
if dentro_ciechi >= len(DENTRO) - 1 and fuori_ciechi == 0:
    print("     RETTA - la lista separa le due popolazioni. Non e' la parola")
    print("     'nota': e' la CLASSE dei riferimenti a sezione.")
elif fuori_ciechi > 0:
    print(f"     CADUTA - accecano anche {fuori_ciechi} parole FUORI dalla lista:")
    print("     l'attribuzione e' sbagliata, il meccanismo e' un altro.")
else:
    print(f"     PARZIALE - solo {dentro_ciechi}/{len(DENTRO)} della lista accecano:")
    print("     la lista non basta a spiegare, serve un'altra variabile.")
