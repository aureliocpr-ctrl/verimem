"""Chiude un limite dichiarato: i quarantinati senza `quarantined_by`.

Avevo lasciato aperto: "i 207 quarantinati di agosto non dichiarano quale
layer li ha fermati". Ipotesi nata guardando il topic veriagent (48 fatti, 47
quarantinati, quarantined_by NULL su tutti e 48, tutti della forma "Task
completato con receipt"): sono i fermati dallo SCREEN LESSICALE, che il
prodotto dichiara e che gira SENZA chiamata LLM - quindi non ha un layer da
registrare.

⚠️ Misuro ENTRAMBE le popolazioni: sui soli quarantinati-senza-layer qualunque
criterio sembrerebbe ottimo. Il confronto e' con i quarantinati CHE il layer
lo dichiarano: se la quota di auto-claim fosse simile, il criterio non
discrimina e l'ipotesi non regge.

SOLA LETTURA sullo store.
"""
import os
import re
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))

# marcatori di auto-claim: le parole che il prodotto dichiara di intercettare
# ("it works / verified / done"), nelle due lingue del corpus.
AUTO = re.compile(
    r"\b(complet\w+|esegui\w*\s+con\s+successo|riuscit\w+|funziona\w*|verificat\w+|"
    r"fatto\b|done\b|works?\b|working\b|verified\b|succeed\w*|successful\w*|"
    r"passed\b|ok\b|receipt\b)", re.I)

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
righe = con.execute(
    "SELECT id, quarantined_by, proposition, topic FROM facts "
    "WHERE status = 'quarantined' AND superseded_by IS NULL").fetchall()
con.close()

senza = [r for r in righe if not r[1]]
con_layer = [r for r in righe if r[1]]
print("quarantinati non-superseduti: %d" % len(righe))
print("  SENZA quarantined_by : %d" % len(senza))
print("  CON   quarantined_by : %d" % len(con_layer))


def quota(gruppo):
    if not gruppo:
        return 0, 0, 0.0
    n = len(gruppo)
    k = sum(1 for r in gruppo if AUTO.search(str(r[2] or "")))
    return k, n, 100.0 * k / n


print("\nQUOTA DI AUTO-CLAIM nelle DUE popolazioni")
ks, ns, ps = quota(senza)
kc, nc, pc = quota(con_layer)
print("  SENZA layer : %4d/%-4d = %5.1f%%" % (ks, ns, ps))
print("  CON   layer : %4d/%-4d = %5.1f%%" % (kc, nc, pc))
print("  divario     : %+.1f punti" % (ps - pc))
print("\n  Se il divario e' AMPIO l'ipotesi regge: chi non dichiara il layer e'")
print("  fermato dallo screen lessicale, che non fa chiamate LLM. Se e' PICCOLO")
print("  il criterio non discrimina e l'ipotesi cade.")

print("\nI TOPIC che concentrano i quarantinati SENZA layer (top 8)")
per_topic = {}
for _i, _q, _p, t in senza:
    pref = str(t or "").split("/")[0]
    per_topic[pref] = per_topic.get(pref, 0) + 1
for t, n in sorted(per_topic.items(), key=lambda x: -x[1])[:8]:
    print("  %-28s %4d" % (t[:28], n))

print("\nesempi SENZA layer:")
for r in senza[:4]:
    print("  %s" % str(r[2])[:88])
print("esempi CON layer:")
for r in con_layer[:4]:
    print("  [%s] %s" % (r[1], str(r[2])[:74]))
