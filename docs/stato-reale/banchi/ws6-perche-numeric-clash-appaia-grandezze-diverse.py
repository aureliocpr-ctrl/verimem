"""Le tre coppie vere: perche' _values_clash le dichiara in conflitto?

Non tocco contradiction.py: chiamo la funzione del prodotto sulle frasi
ESATTE prese dallo store (mode=ro) e stampo cosa confronta con cosa.
"""
from verimem.contradiction import _values_clash, _classify_numbers

COPPIE = [
    ("Nel run 32764736605 il job build e' success con durata 0.5 min.",
     "Dalle 16:06 i verdetti di run di ci sono 2."),
    ("Il run 32764736605 ha 9 job totali e due wheel install-from-scratch risultano queued.",
     "Dalle 16:06 i verdetti di run di ci sono 2."),
    ("Il run 32998186539 riporta 3 failed e 11983 passed e 81 xfailed in 1206.09s.",
     "Il criterio G2 di RELEASE_GATE elenca MCP server starts fra i suoi passi con un segno di spunta del 2026-07-04."),
]

print("=== LE TRE COPPIE VERE ===")
for i, (a, b) in enumerate(COPPIE, 1):
    ta, tb = _classify_numbers(a), _classify_numbers(b)
    clash = _values_clash([], [], tolerance=0.05, text_a=a, text_b=b) if False else None
    # la firma vuole a_vals/b_vals non vuoti per non uscire subito
    from verimem.contradiction import _extract_numbers
    av, bv = _extract_numbers(a), _extract_numbers(b)
    clash = _values_clash(av, bv, tolerance=0.05, text_a=a, text_b=b)
    print(f"\ncoppia {i}: CLASH={clash}")
    for kind in ("year", "percent", "other"):
        if ta[kind] or tb[kind]:
            n = min(len(ta[kind]), len(tb[kind]))
            print(f"  {kind:<8} A={ta[kind]}")
            print(f"  {'':<8} B={tb[kind]}")
            for j in range(n):
                print(f"           -> confronta A[{j}]={ta[kind][j]} con B[{j}]={tb[kind][j]}")

print("\n=== CONTROLLO POSITIVO: una VERA contraddizione deve dare CLASH ===")
from verimem.contradiction import _extract_numbers
for a, b in [("Il run 32764736605 ha 9 job totali.", "Il run 32764736605 ha 14 job totali."),
             ("La suite riporta 3 failed.", "La suite riporta 7 failed.")]:
    print(f"  CLASH={_values_clash(_extract_numbers(a), _extract_numbers(b), tolerance=0.05, text_a=a, text_b=b)}  <- {a[:40]}... / {b[:40]}...")

print("\n=== CONTROLLO NEGATIVO: due frasi su GRANDEZZE DIVERSE non dovrebbero ===")
for a, b in [("Il file pesa 5 MB.", "Il processo dura 900 secondi."),
             ("Ci sono 3 utenti.", "Il test dura 1206.09 secondi.")]:
    print(f"  CLASH={_values_clash(_extract_numbers(a), _extract_numbers(b), tolerance=0.05, text_a=a, text_b=b)}  <- {a} / {b}")
