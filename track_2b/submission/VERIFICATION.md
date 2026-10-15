# Final verification record

Verified 15 October 2026. This record separates software behavior from model quality. Detailed private logs and raw traces are retained locally; the public manifest provides hashes and execution summaries.

## Implementation and deployment

`make check` passed: **330 Python tests, 39 frontend tests, TypeScript checking and Vite production build**. A focused independent review also passed 96 backend tests and all 39 frontend tests. Constructed test fixtures are isolated software QA, never demonstration data or model evaluation.

The final changes persist extraction assurance with the exact package snapshot. Rejected rows, row caps, missing or failed audit accounting and audit findings block both purchase and shipment gates. The UI shows these conditions in each workspace. Invalid audit responses remain linked in telemetry. Unknown price bases and mixed unit/lot prices stay conditional. The gateway now resolves a replaced app container through Docker DNS, addressing the observed stale-upstream 502.

`make run` rebuilt and started the stack. Authenticated API responses and the actual served JS/CSS hashes matched the build. A database backup preceded the forward migration. All original documents, requirements, offers and event records remained identical. Version advanced from 12 to 13 as assurance became part of the snapshot. A subsequent app/worker restart preserved the current state and did not repeat migration.

Current snapshot: `fec4b6ba125c296f9564f2e475ef6e441b1ee93a55a7ccbc2df826b2a2620ba6`.

Current state: five documents, 35 pending requirements, four pending offers, zero approved suppliers, zero acceptance evidence and zero decisions. All five extracted source-kind runs remain incomplete. No engineering approval, external order or shipment was performed.

## Genuine inference

Apertus `swiss-ai/Apertus-v1.5-8B`, pinned revision `ef4bbc54d6fe658bc782280ff9f3b53a10a9758f`, ran on the participant's NVIDIA RTX 5090 Laptop GPU using the pinned official Swiss AI vLLM image. The serving profile used 32,768-token context, one sequence, 0.89 GPU utilization and 2 GiB CPU offload. No fine-tuning was performed.

Fifteen attempts were retained: five completed source-kind runs over four distinct PDFs and ten failed attempts. There are 64 raw call triplets. All 192 trace-file hashes and 15 run-response hashes were checked. Completed mapper inputs matched the original source span/page text. The full 57-page tender supplied all 1,214 spans in six windows and took 427.118 seconds.

The full-tender run includes one failed truncated audit and one 15-row window cap. The preserved historical run linked only 23 of 24 calls; the missing failed-audit raw record was separately reconciled. Historical records were not rewritten. The amendment run saved zero requirements because eleven rows failed schema validation, not because the raw response was empty.

Model quality is mixed. Bidder/item prices are wrong in the bid proposals; many requirements are mislabeled or out of scope. One actual PO offer correction changed the three-unit line total from 11,131,650 cents to a unit price of 3,710,550 cents, citing original PO page 4. This assistant source reading preserves the original value and remains pending, without qualified approval.

The GPU model was stopped after recording and both borrowed workloads restored. An identical request submitted during inference attached to the same existing workflow. Full-stack restart preserved state. A worker crash during active inference was not tested.

## Source and network scope

Five complete authentic PDF attachments contain 95 pages with overlap, 2,136 parsed spans and 342,307 retained characters. Full-tender pages 10-29 reproduce the standalone 20-page E-004 scans. Four isolated parses and a separate API full-tender parse succeeded; an isolated concurrent attempt failed OOM/exit 137 and remains recorded. Conversion/page coverage does not establish correct OCR or semantic extraction.

No applicable completed FAT, actual unit serial/nameplate, approved final unit drawing or drawing-approval date was found in these sources. Missing evidence is unknown, not proof of supplier noncompliance. Original PDFs are fetched from catalog URLs and stored privately because redistribution permission is unestablished.

App and worker could reach PostgreSQL, Temporal and the model relay. Two direct public destinations were unreachable. These bounded probes do not certify an air gap, Swiss geographic residency or a complete security boundary. Deployment target is operator-controlled on-premise infrastructure.

## Artifact review and remaining limits

The report has six pages including references. The deck has twelve slides and two native editable tables. Every report page and deck slide was rendered and visually inspected. Actual captures and cropped derivatives carry SHA-256 and snapshot provenance. Video duration, resolution, codecs, audio level, scene inputs and final hashes are in `VIDEO_METADATA.json`; any remaining playback check is stated there rather than assumed.

There is no expert-labeled held-out accuracy benchmark, customer pilot, measured ROI, selective incremental reassessment, production security certification or implemented scoped assurance-resolution workflow. Incomplete runs therefore remain blocked. No comparison between model accuracy and the software test pass count is implied.

## Final speaking deck and recording script

The frontend-slides deck has eight spoken slides and two appendices. All ten HTML slides and ten searchable 16:9 PDF pages were visually reviewed. Automated browser checks found no overflow, broken images, script errors or external HTTP requests. Keyboard navigation and inline editing passed; a 390×844 phone viewport preserves the 16:9 stage. `SLIDES_VERIFICATION.json` records the checks and file hashes. The 221-word `demo.md` script matches the eight speaker notes and targets 1:55. The user will record the final video; the earlier 116.021-second TTS output is rehearsal material, not the selected final recording.
