# TenderProof

## Hack Apertus Track 2B | SwissChivers

**Sovereign engineering review for equipment procurement.** Prepared 15 October 2026. Team GitHub account: Vishwa-docs. Participant details are supplied separately in the submission form.

## 1. Product and intended users

An infrastructure contractor must keep its customer commitments, supplier purchase and delivered equipment aligned. TenderProof connects source clauses, supplier facts, acceptance evidence and release decisions in one versioned package. Apertus proposes structured interpretations; people review meaning; deterministic checks assess encoded facts; role approvals belong to the exact reviewed snapshot.

The proposed users are EPC package engineers, procurement engineers and quality inspectors. The economic buyer is the engineering or commercial director responsible for delivery and margin. A paid project deployment is the entry hypothesis. No customer deployment, savings or revenue is claimed.

| Launch capability | Implemented mechanism | Decision supported |
| --- | --- | --- |
| Commitment compiler | Source-linked typed candidates; interpretation review | What must the contractor deliver? |
| Supplier comparison | Constraint checks; documented price/delivery bases | What is supported, conditional or unresolved? |
| Acceptance evidence | Unit/design/revision applicability and missing-evidence checks | Does the evidence support this equipment? |
| Change and approval control | Versioned content, stale decisions, role gates and immutable packets | Does the approval still apply? |

Our authentic case is GPA-070-25 / purchase order OP34276, item 2: three 750 kVA transformers, 13.8 kV primary and 120/208 V secondary. The recorded line value is USD 111,316.50, or 3 x USD 37,105.50. The separate 300 kVA item is outside scope. This public historical procurement illustrates the workflow; Guam Power Authority is not a claimed customer or partner. [G1-G5]

The differentiator under test is evidence-controlled purchasing and acceptance. A generated answer cannot itself authorize release. The demonstration uses actual model output, an audited source-linked correction and a blocked acceptance state.

<!-- PAGEBREAK -->

## 2. Architecture and sovereign deployment

**Deployment target: a) on-premise.** React, FastAPI, PostgreSQL, Temporal and Apertus run on infrastructure controlled by the operator. The application services run locally in Docker; the recorded model execution used a participant-provided Linux GPU host over a private authenticated relay. This demonstrates operator control, not Swiss geographic residency or a certified air gap.

Docling converts complete documents into source spans. Four bounded Apertus roles interpret documents, map obligations, analyze evidence and challenge findings. Temporal runs parsing/inference as activities and retains workflow state. PostgreSQL stores canonical versioned content and operation identity. Raw request/response artifacts remain separate from model proposals and audited corrections.

The model emits typed data, never executable verifier code. Z3 checks supported numerical constraints after unit normalization and verifies consistency before implication. Missing conditions, unsupported representations and solver uncertainty remain unknown. A logical result concerns the encoded statements; it does not certify physical performance. Commercial amounts use integer minor units. Unspecified price bases and incompatible units/lot totals cannot support a feasible commercial selection.

Package content includes extraction assurance: coverage gaps, rejected rows, row caps and failed audits remain attached to the reviewed snapshot and block release while unresolved. A correction does not erase raw output or approve a proposal. Purchase requires Engineer and Commercial authority; shipment requires Inspector and Commercial authority. Content changes trigger conservative full-package reassessment and stale prior decisions. This prototype does not implement selective incremental reasoning or an external ERP write.

## 3. Actual Apertus execution

We served `swiss-ai/Apertus-v1.5-8B`, revision `ef4bbc54d6fe658bc782280ff9f3b53a10a9758f`, using the official Swiss AI vLLM image pinned by digest. Hardware: NVIDIA RTX 5090 Laptop GPU, 24 GB VRAM, Linux. The working profile used a 32,768-token context, one sequence, GPU utilization 0.89 and 2 GiB CPU offload. Decoding and request details are preserved with the run evidence. No fine-tuning was performed. [M1]

Fifteen extraction attempts were retained: five completed and ten failed. Sixty-four raw call-trace triplets preserve requests, responses and metadata. The five completed source-kind runs cover four distinct PDFs; the standalone specification was parsed but not inferred separately because its scans are embedded in the full tender. All resulting records remain pending.

The model endpoint was stopped after testing and both borrowed GPU workloads restored. Recorded execution is real; the video is a shortened walkthrough of captured states, not a claim that inference completes within two minutes.

<!-- PAGEBREAK -->

## 4. Authentic sources and observed output

| Complete source | Pages / use | Completed inference result |
| --- | --- | --- |
| OP34276 purchase order | 9; scope, price and delivery | 1 pending offer in 49.243 s; 2 requirements in 41.281 s |
| E-004 Revision 10 | 20; engineering specification | Parsed; embedded in the full-tender run |
| GPA-070-25 bid abstract | 5; handwritten bidder tables | 3 pending offers in 33.871 s; incorrect item/bidder associations |
| Issuance/amendments | 4; amendments I-III and invitation | 0 saved requirements in 50.091 s; 11 invalid rows rejected |
| Full IFB + Amendment I | 57; complete tender, PPA mirror | 33 pending requirements in 427.118 s; 1,214 spans in six windows |

The five attachments contain 95 pages with overlap, not 95 unique pages. Full IFB pages 10-29 reproduce the standalone E-004 scans. Later Amendments II/III remain necessary. All originals retain SHA-256 provenance; redistribution permission is unestablished, so the repository supplies fetch URLs and hashes rather than republishing entire PDFs. [G1-G4, G6]

### Quality findings and the demonstrated correction

The full-tender run retained valid rows despite one truncated audit response and a 15-row window cap. Complete input-span coverage does not establish complete requirement extraction. Some requirements match the source; others mislabel equipment properties, merge voltages or include the excluded item. The bid abstract confuses bidders and item-1 prices. These errors are disclosed, not scored as correct extractions.

The PO offer originally put the three-unit line total into its price field: 11,131,650 cents. An audited assistant-assisted correction changed it to 3,710,550 cents per unit, citing PO PDF page 4. The original model data, source locator, reason and correction history remain intact; the offer is still pending. This is not expert engineering approval or improved model output. [G1]

Delivery is 24 weeks after GPA approves drawings. The offer captures that basis, but the extraction missed a separate delivery requirement row. No reviewed document establishes the drawing-approval date, so the application must not infer a due date from the order date. Amendment II answers the flip-top question “no”; it does not change the rating or describe an inspected unit. [G1, G4]

There is no applicable completed FAT, actual serial/nameplate or approved final unit drawing in this source set. Specification Revision 10 is not an equipment design revision. Missing acceptance evidence remains unknown; it is not proof of supplier noncompliance.

<!-- PAGEBREAK -->

## 5. Verification and research boundary

| Verification stream | Observed result | What it establishes |
| --- | --- | --- |
| Software QA | 330 backend / 39 frontend tests; TypeScript and production build passed | Encoded behavior, not real-document model accuracy |
| Trace integrity | 192 file hashes for 64 call triplets and all 15 run-response hashes matched | Preserved recorded execution |
| Input coverage | Completed mapper inputs matched original page/text spans, including 1,214/1,214 tender spans | Source delivery, not extraction recall |
| Persistence | Full-stack restart preserved project state; duplicate mid-run request attached to existing workflow | Observed persistence/idempotency cases |
| Runtime routes | App/worker reached database, Temporal and relay; two tested public destinations were unreachable | Bounded egress observation, not full network certification |
| Real review state | 35 requirements and 4 offers pending; no supplier approvals, evidence or release | No unsupported operational decision |

Strict conversion checks recorded 2,136 spans and 342,307 retained characters across the five attachments, with expected page coverage. Four isolated reparses succeeded; the full-tender API parse succeeded. A concurrent isolated parse attempt failed OOM/exit 137 and remains disclosed. Visual source review found OCR price errors. Successful conversion is not semantic correctness.

Regression tests use isolated constructed software cases. They never populate the demonstration, application package, or claimed model results. No expert-labeled held-out accuracy benchmark has been completed. The 35 source-reference facts supplied for future evaluation are assistant-reviewed and explicitly not expert-validated; they are never inference input.

A useful research question is whether source-linked interpretation review, configuration-conditioned evidence and snapshot-bound assurance reduce critical false acceptance and reviewer effort. A study would compare plain retrieval, full-context prompting and the complete workflow on independent real packages, with expert annotations and ablations. Report critical false accepts, applicability precision/recall, change-impact coverage, review time, latency and cost. Split by procurement package to avoid revision/translation leakage. Novelty and patentability are unestablished.

Incomplete runs remain blocked: a scoped assurance-resolution workflow is not implemented. Production recovery, independent security testing, accessibility and load testing remain work. A worker crash during active inference was not tested. No model-quality percentage, independent-agent verification, customer outcome or physical conformity claim is inferred from passing software tests.

<!-- PAGEBREAK -->

## 6. Reproduction and commercial next step

The repository retains `track_2b/` and an end-to-end root `make run` entry. Configure a genuine Apertus endpoint first; app startup alone does not start the remote GPU model. The documented on-premise lifecycle verifies model files/image identity, authenticates inference and restores borrowed workloads after use. Initial dependency and model downloads require network access; runtime restrictions are separate.

Use `make setup` for the application virtual environment and locked web dependencies; `make check` for QA/build; `make run` for Docker services. `make sources` downloads all five complete originals using the provenance catalog. `make ingest` imports those originals without invented requirements. The UI permits genuine extraction only when the configured endpoint is reachable. The submission also includes recorded evidence of the completed run; it is not replayed as fresh inference.

Select OP34276 item 2, retain unresolved conditions and review the original page before correction. Inspect the supplier's drawing-approval-relative delivery term. Acceptance remains blocked because unit-specific evidence and approvals are absent. An immutable review packet can only follow the implemented gates; the historical case contains no approved or released packet.

### Venture path

Start with a design partner's transformer package, one accountable review owner and a paid project deployment. Measure missed obligations, review effort, late corrections and deployment cost against an independently reviewed baseline. Expand to additional projects and equipment schemas only if those measurements support the purchase. Mercanis's June 2025 Series A of over USD 20 million is evidence of investment in adjacent procurement automation, not TenderProof traction. [V1]

The twenty planned extensions follow four waves: ERP/PLM and supplier workflow integration; broader engineering packs; manufacturing, shipment and commissioning evidence; then lifecycle economics and cross-project optimization. None is represented as an existing production integration. A USD 5 million annual-value or revenue hypothesis would require measured incident frequency, avoided costs, collected margin and customer pricing; this submission claims none of those outcomes.

### Submission and rights

The deliverables are this six-page report, the public source repository and a prototype video of at most two minutes. The supporting editable deck is optional. Participant contact details, student status and final public URLs belong in the official Track 2B submission form. The portal deadline is 16 October 2026, 12:00 CEST. [H1-H3]

Team-authored code is Apache-2.0; documentation/design CC-BY-4.0; team-owned annotations CDLA-Permissive-2.0. Third-party source rights remain with their owners. The repository does not contain tokens, private deployment configuration, model weights, virtual environments or complete source PDFs. [H4]

<!-- PAGEBREAK -->

## References

G1. Guam Power Authority. Purchase order OP34276, 9 pages, 13 October 2025; item 2 and price correction: PDF page 4. https://go.opengovguam.com/uploads/ggbids/packet_1765520985_OP%2034276.pdf

G2. Guam Power Authority. Specification E-004 Revision 10, 20 pages, 29 July 2022. https://go.opengovguam.com/app/webroot/userfiles/files/Spec%20E-004%20Revision%2010%20-%20Three%20Phase%20Pad%20Mounted%20Distribution%20Transformer%282%29.pdf

G3. Guam Power Authority. GPA-070-25 bid abstract, 5 PDF pages, 16 September 2025. https://go.opengovguam.com/uploads/ggbids/packet_1765520985_GPA-070-25%20Bid%20Abstract.pdf

G4. Guam Power Authority. GPA-070-25 issuance/amendments attachment, 4 PDF pages; Amendment II: page 2. https://go.opengovguam.com/uploads/ggbids/packet_1765520985_GPA-070-25%20IFB%20Issuance.pdf

G5. Official award/attachment record. https://go.opengovguam.com/tenders/tender_details/gpa/GPA-070-25

G6. Guam Power Authority. Original GPA-070-25 IFB plus Amendment I, 57 pages; Pacific Power Association mirror. https://www.ppa.org.fj/wp-content/uploads/2025/08/220825GPA-GPA-070-25-with-Amendment-I.pdf

M1. Swiss AI. Apertus v1.5 8B model card and deployment guidance. https://huggingface.co/swiss-ai/Apertus-v1.5-8B

V1. Partech. Mercanis secures over USD 20m in Series A, 18 June 2025. https://partechpartners.com/news/mercanis-secures-over-20m-in-series-a-round

H1. Hack Apertus. Track 2B template and required delivery. https://github.com/HackApertus/project-template/blob/main/track_2b/README.md

H2. Hack Apertus. Official submission portal; deadline rechecked 15 October 2026. https://hackapertus.ch/online-hack/submissions

H3. Hack Apertus. Devpost event rules. https://hackapertus.devpost.com/rules

H4. aiLights Association. Terms and Conditions, section 6. https://hackapertus.ch/terms-and-conditions

All external sources accessed 15 October 2026. Repository evidence: `track_2b/data/sources.json`, `track_2b/submission/REAL_SOURCE_EVIDENCE.json`, `docs/REAL_MODEL_INTEGRATION.md`, and the final submission verification record. Raw full-document traces are retained locally; published summaries do not relicense the original documents.
