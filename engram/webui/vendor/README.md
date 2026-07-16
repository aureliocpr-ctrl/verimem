# Vendored graph stack (self-hosted by CSP design)

The trust console's CSP is `script-src 'self'` — no CDN at runtime. These
bundles are copied verbatim from the official npm registry (`npm pack`),
unmodified, licenses alongside.

| file | package | version | license | global |
|---|---|---|---|---|
| `graphology.umd.min.js` | graphology | 0.25.4 | MIT | `graphology` |
| `sigma.min.js` | sigma | 2.4.0 | MIT | `Sigma` |
| `graphology-library.min.js` | graphology-library | 0.8.0 | MIT | `graphologyLibrary` (FA2Layout worker supervisor, layoutForceAtlas2.inferSettings) |

To upgrade: `npm pack <pkg>@<version>`, copy the UMD build from the tarball,
update this table. Never edit the bundles in place.
