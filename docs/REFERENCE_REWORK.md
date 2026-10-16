# Reference decisions for the evidence workbench

Reviewed 16 October 2026. The rework applies selected architectural and interaction patterns from these nine repositories. The project does not install their complete systems.

## Design decisions

| Primary reference | Relevant mechanism | TenderProof decision |
| --- | --- | --- |
| [Docling](https://github.com/docling-project/docling) | Structured conversion preserves document layout information and a unified document representation. | Retain the existing Docling parser. Return document, page and span references from evidence views. |
| [Kotaemon](https://github.com/Cinnamon/kotaemon) | Retrieved citations connect to document previews and relevance scores. | Open the original page from each search result. Keep its source locator beside the excerpt. |
| [Outlines](https://github.com/dottxt-ai/outlines) | Generation follows explicit output types and schemas. | Retain existing vLLM JSON-schema decoding and Pydantic validation. This rework adds no Outlines dependency. |
| [PaperQA](https://github.com/Future-House/paper-qa) | The pipeline separates search, evidence gathering and answer generation. | Use BM25 over stored source spans. Return cited excerpts without generating an answer. |
| [BlackBox](https://github.com/alejandro-publius/blackbox-datahub) | Tool evidence gates root-cause claims before repair and verification. | Expose blockers, record lineage and correction history. Keep release authority in the existing gate service. |
| [Camel](https://github.com/allisterb/Camel) | Its constrained JavaScript environment limits access to approved forensic APIs. | Add typed MCP read tools for queue, search, diff and dossier. Keep project authorization in the API. |
| [Mulder](https://github.com/calebevans/mulder) | Findings cite tool-call records. Published reports and scorecards preserve individual run results. | Retain raw model traces and failed attempts. Separate software QA from model-quality evidence. |
| [evo.ninja](https://github.com/agentcoinorg/evo.ninja) | Its execution loop selects predefined personas for task-specific work. | Retain four fixed Apertus prompt roles. Expose audit conditions without adding an autonomous task loop. |
| [Logic-LM](https://github.com/teacherpeterpan/Logic-LLM) | Language models produce symbolic formulations before deterministic solver inference. | Retain typed constraints and Z3 checks. Return unknown when supported facts cannot establish the requirement. |

These are TenderProof design choices. They do not establish equivalent behavior or reproduce the reference projects' benchmark results.

## Implementation boundary

Docling, Z3 and Temporal already operate in the application. Existing vLLM serving enforces JSON schemas. Schema validity does not establish factual correctness. The rework adds no third-party agent framework.

The workbench design specifies an issue queue, source search, stored snapshot comparisons and draft review dossiers. These views derive their content from preserved package records. Search requires no model call.

BM25 scores express lexical relevance. They do not measure factual confidence. Citation coverage counts referenced source spans. It does not measure obligation recall. Lineage connects existing records through recorded source references. It does not prove causal change impact.

Snapshot comparisons identify stored field changes. The service still reassesses the whole package after a content change. A draft dossier preserves pending states and unresolved conditions. Its hash identifies packet content. Purchase and shipment still require the existing role approvals and gate checks.

The new MCP queue, search, diff and dossier tools use GET requests. The existing `prepare_purchase_draft` tool uses POST to create a pending decision. The API remains the authorization boundary. The [workbench contracts](EVIDENCE_WORKBENCH.md) define read limits and response meanings.

The recorded package contains 35 pending requirements and four pending offers. This rework adds no live model inference or fine-tuning. It creates no engineering approval or acceptance evidence. New tests establish software behavior within their tested scope.

## Award verification

DataHub names BlackBox the Grand Prize winner of its 2026 agent hackathon. The organizer reports more than 600 submitted projects. The announcement does not support a 10,000-participant claim. [Official DataHub announcement](https://datahub.com/blog/meet-the-winners-of-build-with-datahub-the-agent-hackathon/).
