# TenderProof workbench

React + TypeScript engineering review desk. Requires the TenderProof API on `127.0.0.1:8000`.

```sh
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the API. `npm run build` creates `dist/`; production hosting must route `/api` to the backend. `npm test` runs isolated UI QA tests based on public GPA-070-25 / OP34276 facts.

The application uses project `default`, bearer authentication, and server-owned roles/project authorization. Enter a server-issued token; it is kept in browser tab-session storage. No source documents, suppliers, quotes, test records, or model responses are bundled as application data. All four workspaces remain empty until real sources are uploaded and reviewed.

Set **Project details** before extraction or approval: the actual project reference, issuing customer, and one explicit equipment/configuration scope. Metadata updates use snapshot-bound PATCH and invalidate prior package approvals. Uploads may precede metadata completion; real extraction and approval require a complete scope.

The workspaces support explicit requirement witness review, supplier comparison, sourced delivery scheduling, evidence applicability/proposal review, authorized approval gates, immutable JSON release downloads, and server-recorded change history. The source inspector supports original authenticated download, image preview, document upload, and Apertus extraction by purpose and supplier. Unknown evidence remains unknown; no missing model output is replaced with a stored case. Large document work displays elapsed time without fabricated progress percentages.

Apertus is the semantic model. Real endpoint configuration and document parsing are backend prerequisites. PDF support needs the optional Docling environment. Confirm actual unit/configuration references and real test reports; procurement obligations to provide reports do not establish received acceptance evidence.

Typography uses DM Sans and IBM Plex Mono from Google Fonts with system fallbacks. For strictly disconnected browser operation, prevent external font requests or self-host the permitted fonts. Motion respects reduced-motion preferences.
