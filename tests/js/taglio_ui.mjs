/* Il taglio della sala motore non deve mutilare i caratteri.
 *
 * Mandato lingue (Aurelio, 2026-08-07), parte ws7 — le superfici. In
 * JavaScript il difetto e' PEGGIORE che in Python: `String.slice` taglia a
 * UNITA' UTF-16, quindi spezza le coppie surrogate e produce un surrogato
 * spaiato, che si vede come il carattere di sostituzione. Misurato sul
 * motore vero (node), tagliando dove la coppia si spezza:
 *
 *     '仓库𠮷有'.slice(0,3)        -> "仓库\ud842"   SPAIATO
 *     'dep 🇮🇹'.slice(0,5)         -> "dep \ud83c"   SPAIATO
 *     'nota 𝄞'.slice(0,6)         -> "nota \ud834"  SPAIATO
 *     'Città Sant Angelo'.slice(0,3) -> "Cit"       (italiano: intatto)
 *
 * ⚠️ Questo banco legge `engine.js` VERO ed estrae la funzione da li'. Una
 * copia della funzione dentro il test misurerebbe la copia — che e' la
 * prima delle classi che questo prodotto ripete.
 *
 * Si esegue con:  node tests/js/taglio_ui.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const qui = dirname(fileURLToPath(import.meta.url));
const sorgente = readFileSync(join(qui, "..", "..", "verimem", "webui",
  "engine.js"), "utf8");

const m = sorgente.match(/function safeCut\s*\([\s\S]*?\n {2}\}/);
if (!m) {
  console.error("FALLITO: `safeCut` non esiste in engine.js");
  process.exit(1);
}
const safeCut = new Function(m[0] + "; return safeCut;")();

let rossi = 0;
const prova = (nome, ok, extra = "") => {
  if (!ok) { rossi++; console.error("  ROSSO  " + nome + " " + extra); }
  else { console.log("  verde  " + nome); }
};
const spaiato = (t) =>
  /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:^|[^\uD800-\uDBFF])[\uDC00-\uDFFF]/
    .test(t);

/* 1. i tre casi che si rompono davvero */
for (const [nome, s, n] of [
  ["CJK esteso", "仓库\u{20BB7}有", 3],
  ["bandiera", "dep \u{1F1EE}\u{1F1F9}", 5],
  ["simbolo musicale", "nota \u{1D11E}", 6],
]) {
  const t = safeCut(s, n);
  prova(nome + ": nessun surrogato spaiato", !spaiato(t), JSON.stringify(t));
  prova(nome + ": non piu' lungo del richiesto", t.length <= n);
}

/* 2. IL PRESIDIO: l'italiano e l'inglese non cambiano.
 *    Senza questo confronto non si sa se il difetto e' della lingua o della
 *    funzione — la trappola pagata undici volte oggi. */
for (const s of ["Citta' Sant'Angelo, magazzino", "The depot in Milan"]) {
  for (const n of [3, 7, 15, 500]) {
    prova("latino invariato n=" + n, safeCut(s, n) === s.slice(0, n));
  }
}

/* 3. un accento COMPOSTO non perde il suo segno (stesso caso del lato
 *    Python, dove 'caffé' diventava 'caffe') */
const composta = "caffé macchiato";
prova("accento composto non si stacca",
  !/́/.test(safeCut(composta, 5)) &&
  safeCut(composta, 5) === "caff", JSON.stringify(safeCut(composta, 5)));

/* 4. un ZWJ non resta penzolante */
prova("nessun ZWJ in coda",
  !safeCut("op \u{1F469}‍\u{1F4BB}", 5).endsWith("‍"));

/* 5. taglio piu' lungo del testo */
prova("testo corto invariato", safeCut("breve", 100) === "breve");

console.log(rossi ? `\nROSSI: ${rossi}` : "\nTUTTO VERDE");
process.exit(rossi ? 1 : 0);
