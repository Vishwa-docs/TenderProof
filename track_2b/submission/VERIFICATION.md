# Verification record — 16 October 2026

Code reference: `c1141f19b5bde590b650b1f1215f692353f609ec`.
This record separates software checks from model quality.
Private runtime logs retain detailed requests and responses.
The public provenance manifest records hashes and execution facts.

## Application and deployment

`make check` passed 380 Python tests and 51 frontend tests.
TypeScript checking and the Vite production build passed.
`make run` rebuilt the image and started the application stack.
Served JavaScript and CSS hashes match the local production build.
A database backup preceded deployment.
Read-only verification confirmed that every existing business record remained unchanged.

The current snapshot is `fec4b6ba125c296f9564f2e475ef6e441b1ee93a55a7ccbc2df826b2a2620ba6`, version 13.
The package contains five documents, 35 pending requirements, four pending offers, and one recorded price correction.
It contains zero approved suppliers, acceptance records, approvals, and releases.
The review queue contains 48 issues, including 43 blocking issues.
Purchase and shipment remain blocked.

## New workbench checks

| Check | Observed result | Scope |
| --- | --- | --- |
| Price retrieval | PO page 4 ranks first for `37,105.50` | Original text and citation match |
| Delivery retrieval | PO page 3 appears within the first three results | Drawing-approval trigger remains explicit |
| Duplicate passages | Equivalent source text retains duplicate citations | Duplicates do not imply corroboration |
| Snapshot comparison | Revision 11 to 12 changes price from 11,131,650 to 3,710,550 cents | Original and corrected values remain recorded |
| Draft dossier | Repeated reads return identical content and a valid canonical JSON hash | Draft export grants no approval |
| Authorization | Invalid identities return 401; unassigned projects return 403 | Five new read endpoints checked |
| Bounds | Oversized queries return 422; unknown snapshots return 404 | No partial replacement result |
| Record preservation | Project content remains identical after verification | No new model call or business mutation |

Five read-only source queries took a median 81.02 milliseconds in this local check.
This small measurement is not a load test or latency guarantee.
All returned excerpts, adjacent passages, and duplicate citations matched retained source text.
The first negative query contained common words and returned matches as designed.
A subsequent single absent token returned zero results.

Safari verification covered source search, original page preview, revision comparison, review issues, and Markdown export.
Safari displayed the draft-download confirmation.
API checks verified the current snapshot and preserved pending states.
The recording starts on the authenticated Overview workspace.

The responsive audit checked 36 views at widths of 1440, 1280, 768, and 390 pixels.
No tested page overflowed its viewport.
Visible text measured at least 13 pixels; body text uses 16 pixels.
The audit recorded zero browser script errors and zero external requests.
It used preserved real records with read-only response interception.
The separate deployed API checks used the actual running database.

## Genuine Apertus execution

The recorded run used `swiss-ai/Apertus-v1.5-8B` at revision `ef4bbc54d6fe658bc782280ff9f3b53a10a9758f`.
The model ran on a participant-controlled NVIDIA RTX 5090 Laptop GPU through the pinned Swiss AI vLLM image.
The profile used a 32,768-token context, one sequence, 0.89 GPU utilization, and 2 GiB CPU offload.
The team performed no fine-tuning.

Fifteen attempts remain recorded: five completed source-kind runs and ten failed attempts.
The archive contains 64 raw call triplets.
Verification checked 192 trace-file hashes and 15 run-response hashes.
Completed mapper inputs matched original source spans and page text.
The full 57-page tender supplied 1,214 spans across six windows and took 427.118 seconds.

One full-tender audit response truncated at its output limit.
One extraction window reached its 15-row cap.
The historical run linked 23 of 24 calls; a separate trace reconciled the missing failed audit.
Historical records remain unchanged.
The amendment run saved zero requirements because eleven returned rows failed schema validation.

Model quality remains mixed.
Bid proposals contain incorrect bidder prices, and several requirements use wrong labels or equipment scope.
An AI assistant corrected one PO proposal from a three-unit total to the source's unit price.
The correction cites PO page 4 and awaits qualified review.
The new workbench improves investigation; it does not establish better extraction accuracy.

The model endpoint is stopped.
The operator restored borrowed GPU workloads after the recorded inference.
An identical request during inference joined the existing workflow.
An earlier full-stack restart preserved state.
The team has not tested a worker crash during active inference.

## Source and network boundary

Five complete authentic attachments contain 95 pages with overlap, 2,136 spans, and 342,307 retained characters.
The full tender repeats the standalone 20-page specification.
One isolated concurrent parse failed with OOM exit 137 and remains recorded.
The successful API parse retained the complete full tender.
Page coverage does not establish OCR accuracy or obligation recall.

The sources lack applicable completed FAT results, actual unit identity, approved unit drawings, and a drawing-approval date.
Missing evidence remains unknown.
Operators fetch originals from catalog URLs because redistribution permission remains unestablished.

Earlier bounded probes confirmed access to PostgreSQL, Temporal, and the model relay.
The app and worker could not reach two tested public destinations.
These probes do not certify an air gap, Swiss residency, or a complete security boundary.
The deployment target is infrastructure under the operator's administration.

## Submission artifacts and remaining work

The report follows all eight official sections.
It contains six content pages and a references-only seventh page.
Every report page received visual review.
The optional HTML and PDF deck contains ten slides.
Every slide received visual review, plus offline and viewport checks.
The application-only script contains 189 spoken words and targets 1 minute 55 seconds.
The user supplies the final recording, video URL, and remaining personal fields.
No final video duration or anonymous playback claim applies before that recording exists.

The project lacks an expert-labeled held-out benchmark, customer pilot, validated pricing, and measured ROI.
Selective incremental reassessment and scoped extraction-assurance resolution remain future work.
The initial twenty-customer revenue calculation is a commercial target, not measured traction.
